#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from typing import List, Tuple

from pwn import context, remote  # type: ignore
from tqdm import tqdm  # type: ignore

from utils import (
    F,
    HashType,
    WOTS,
    deserialize_signature,
    serialize_signature,
    MerkleTree,
    l,
    l1,
    l2,
    w,
)
from Crypto.Util.number import bytes_to_long  # type: ignore


HOST = "prob18.geekgame.pku.edu.cn"
PORT = 10018
TARGET_MESSAGE = b"Give me the flag"
INDEX_POS = 0
INDEX_NEG = INDEX_POS - (1 << 8)  # -256 for height 8
COVER1 = 49  # At least this many positions covered by the first message
TOKEN_PATH = os.path.join(os.path.dirname(__file__), "..", "token.txt")
with open(TOKEN_PATH, "r", encoding="utf-8") as fh:
    TOKEN = fh.read().strip()


@dataclass
class MessageInfo:
    text: str
    digits: List[int]
    cover_mask: int
    signature: List[bytes] | None = None


def compute_digits(seed: bytes, msg: bytes) -> List[int]:
    digest = F(msg, seed, 32, HashType.MSG)
    d1 = WOTS.pack(bytes_to_long(digest), l1, w)
    checksum = sum(w - 1 - d for d in d1)
    d2 = WOTS.pack(checksum, l2, w)
    return d1 + d2


def find_two_messages(seed: bytes, target_digits: List[int], cover1: int = COVER1) -> Tuple[MessageInfo, MessageInfo]:
    # Stage 1: find msg1 covering at least 'cover1' positions
    pbar1 = tqdm(desc=f"search msg1 (>= {cover1})", unit="trial")
    while True:
        s = os.urandom(8).hex()
        digits = compute_digits(seed, s.encode())
        cover_mask = 0
        for i, d in enumerate(digits):
            if d >= target_digits[i]:
                cover_mask |= 1 << i
        cnt = cover_mask.bit_count()
        pbar1.update(1)
        if cnt >= cover1:
            pbar1.close()
            msg1 = MessageInfo(s, digits, cover_mask)
            break

    # Stage 2: find msg2 that covers all remaining positions
    remaining_mask = ((1 << l) - 1) & ~msg1.cover_mask
    remaining_indices = [i for i in range(l) if (remaining_mask >> i) & 1]
    print("Target digits:", target_digits)
    print("Remaining indices count:", len(remaining_indices), "indices:", remaining_indices)
    pbar2 = tqdm(desc=f"search msg2 (cover remaining {len(remaining_indices)})", unit="trial")
    best_remain = 0
    best_msg = None
    best_digits = None
    report_every = 50000
    trials = 0
    while True:
        s = os.urandom(8).hex()
        digits = compute_digits(seed, s.encode())
        ok = True
        remain_cover = 0
        for i in remaining_indices:
            if digits[i] < target_digits[i]:
                ok = False
            else:
                remain_cover += 1
        pbar2.update(1)
        trials += 1
        if remain_cover > best_remain:
            best_remain = remain_cover
            best_msg = s
            best_digits = digits
            print(f"[improve] best remain cover = {best_remain}/{len(remaining_indices)} msg={best_msg}")
        if trials % report_every == 0:
            print("[progress] target:", target_digits)
            print(f"[progress] best remain cover {best_remain}/{len(remaining_indices)}")
            if best_msg is not None:
                print("[progress] best msg:", best_msg)
                print("[progress] best digits:", best_digits)
        if ok:
            pbar2.close()
            cover_mask = 0
            for i, d in enumerate(digits):
                if d >= target_digits[i]:
                    cover_mask |= 1 << i
            msg2 = MessageInfo(s, digits, cover_mask)
            break

    return msg1, msg2


def obtain_signature(conn, index: int, message: str) -> Tuple[List[bytes], List[Tuple[int, bytes]]]:
    conn.sendlineafter(b"> ", b"1")
    conn.sendlineafter(b"Index: ", str(index).encode())
    conn.sendlineafter(b"Message: ", message.encode())
    sig_hex = conn.recvline().strip().decode()
    sig = deserialize_signature(bytes.fromhex(sig_hex))
    return sig[0], sig[1:]


def perform_handshake(conn) -> None:
    try:
        for _ in range(3):
            line = conn.recvline(timeout=2)
            if not line:
                break
            if b"token" in line.lower():
                break
    except Exception:
        pass
    conn.sendline(TOKEN.encode())


def assemble_signature(
    seed: bytes,
    target_digits: List[int],
    selected: List[MessageInfo],
    signature_cache: dict[str, List[bytes]],
    auth_path: List[Tuple[int, bytes]],
) -> List:
    final_wots: List[bytes] = []
    for idx in range(l):
        chosen_info = None
        for info in selected:
            if info.digits[idx] >= target_digits[idx]:
                chosen_info = info
                break
        if chosen_info is None:
            raise RuntimeError(f"Position {idx} not covered")
        sig_list = signature_cache[chosen_info.text]
        delta = chosen_info.digits[idx] - target_digits[idx]
        final_elem = WOTS.chain(sig_list[idx], delta, seed)
        final_wots.append(final_elem)
    return [final_wots] + auth_path


def main():
    context.log_level = "error"
    if len(sys.argv) == 3:
        host, port = sys.argv[1], int(sys.argv[2])
    else:
        host, port = HOST, PORT

    conn = remote(host, port)
    perform_handshake(conn)
    conn.recvuntil(b"Seed: ")
    seed_hex = conn.recvline().strip().decode()
    conn.recvuntil(b"Public key (root): ")
    root_hex = conn.recvline().strip().decode()

    seed_bytes = bytes.fromhex(seed_hex)
    root_bytes = bytes.fromhex(root_hex)

    # Compute target digits for the flag request message
    target_digits = compute_digits(seed_bytes, TARGET_MESSAGE)

    # Two-stage search for messages
    msg1, msg2 = find_two_messages(seed_bytes, target_digits, COVER1)

    # Request two signatures using the same WOTS key via alias indices
    signature_cache: dict[str, List[bytes]] = {}
    auth_path: List[Tuple[int, bytes]] | None = None

    for idx, msg in enumerate([msg1.text, msg2.text]):
        index = INDEX_POS if idx == 0 else INDEX_NEG
        wots_sig, path = obtain_signature(conn, index, msg)
        signature_cache[msg] = wots_sig
        if auth_path is None:
            auth_path = path

    assert auth_path is not None

    final_sig = assemble_signature(
        seed_bytes,
        target_digits,
        [msg1, msg2],
        signature_cache,
        auth_path,
    )
    assert MerkleTree.verify(root_bytes, final_sig, TARGET_MESSAGE, seed_bytes)

    conn.sendlineafter(b"> ", b"2")
    sig_hex = serialize_signature(final_sig).hex().encode()
    conn.sendlineafter(b"Signature: ", sig_hex)
    flag_line = conn.recvline()
    print(flag_line.decode().strip())
    conn.close()


if __name__ == "__main__":
    main()
