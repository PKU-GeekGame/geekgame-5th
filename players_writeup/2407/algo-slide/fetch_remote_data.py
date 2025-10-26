#!/usr/bin/env python3
import os
import sys
import random

try:
    from pwn import remote, context
except Exception as e:
    print("[!] Failed to import pwntools: %s" % e)
    print("[!] Run with ../.venv/bin/python3 fetch_remote_data.py")
    sys.exit(1)

context.log_level = "warning"

HOST = "prob12.geekgame.pku.edu.cn"
PORT = 10012


def read_token(path="../token.txt") -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()


def choose_indices(count: int, universe: int = 100000) -> list[int]:
    if count > universe:
        raise ValueError(f"cannot select {count} unique indices from {universe}")
    if count == universe:
        return list(range(universe))
    rng = random.Random(os.urandom(16))
    return rng.sample(range(universe), count)


def main():
    out_path = os.getenv("OUT", "data_remote.txt")
    N = int(os.getenv("N", "100000"))
    if N <= 0:
        raise ValueError("N must be positive")
    if N > 100000:
        raise ValueError("N must not exceed 100000")
    token = read_token()

    r = remote(HOST, PORT)
    r.recvuntil(b"token:")
    r.sendline(token.encode())
    r.recvuntil(b"easy or hard?")
    r.sendline(b"hard")

    enc_scr_hex = r.recvline().strip().decode()
    enc_xk_hex = r.recvline().strip().decode()
    print("[net] headers received", flush=True)

    indices = choose_indices(N)
    if N != 100000:
        random.shuffle(indices)
    plains = [idx.to_bytes(4, "big") for idx in indices]
    lines = [blk.hex() for blk in plains]
    print(f"[net] sending {N} queries...", flush=True)
    r.send(("\n".join(lines) + "\n").encode())
    print("[net] receiving ciphertexts...", flush=True)
    ciphers = []
    for i in range(N):
        ct = bytes.fromhex(r.recvline().strip().decode())
        ciphers.append(ct)
        if (i + 1) % 5000 == 0:
            print(f"[net] {i+1}/{N}", flush=True)
    r.close()
    print("[net] done", flush=True)

    with open(out_path, "w") as f:
        f.write(enc_scr_hex + "\n")
        f.write(enc_xk_hex + "\n")
        f.write(str(N) + "\n")
        for i in range(N):
            f.write(plains[i].hex() + " " + ciphers[i].hex() + "\n")
    print(f"[ok] wrote {out_path}")


if __name__ == "__main__":
    main()
