from pwn import *
from utils import *
from concurrent.futures import ProcessPoolExecutor
import os

def get_d(msg: bytes):
    digest = F(msg, SEED, 32, HashType.MSG)
    assert 8 * len(digest) == m
    d1 = WOTS.pack(bytes_to_long(digest), l1, w)
    checksum = sum(w-1-i for i in d1)
    d2 = WOTS.pack(checksum, l2, w)
    return d1 + d2

while True:
    io = process(['python3', '../game/server.py'])
    io.recvuntil(b"Seed:")
    SEED = bytes.fromhex(io.recvline().strip().decode())

    target_d = get_d(b"Give me the flag")
    target_logprob = 0.0
    for d in target_d:
        target_logprob -= log2((w-d)/w)
    if target_logprob > 70:
        io.close()
        continue
    break
print(f"Target log probability: {target_logprob}")

def search(target_d):
    best_log_prob = 999.0
    best_msg = None
    for _ in range(2**16):
        msg = os.urandom(8).hex().encode()
        ds = get_d(msg)
        log_prob_new = 0.0
        for d, t in zip(ds, target_d):
            if t == -1:
                continue
            if d < t:
                log_prob_new -= log2((w-t)/w)
        if log_prob_new < best_log_prob:
            best_log_prob = log_prob_new
            best_msg = msg
    return best_log_prob, best_msg

def find_closest(target_d):
    with ProcessPoolExecutor() as executor:
        futures = [executor.submit(search, target_d) for _ in range(200)]
        best_log_prob = 999.0
        best_msg = None
        for future in futures:
            log_prob_new, msg = future.result()
            if log_prob_new < best_log_prob:
                best_log_prob = log_prob_new
                best_msg = msg

    print(f"Best message found: {best_msg} with log probability {best_log_prob}")
    return best_msg

msg1 = find_closest(target_d)
d1 = get_d(msg1)

new_target_d = []
for d, t in zip(d1, target_d):
    if d < t:
        new_target_d.append(t)
    else:
        new_target_d.append(-1)

msg2 = find_closest(new_target_d)
d2 = get_d(msg2)

io.sendlineafter(b">", b"1")
io.sendlineafter(b"Index:", b"255")
io.sendlineafter(b"Message:", msg1)
sig1 = bytes.fromhex(io.recvline().strip().decode())

io.sendlineafter(b">", b"1")
io.sendlineafter(b"Index:", b"-1")
io.sendlineafter(b"Message:", msg2)
sig2 = bytes.fromhex(io.recvline().strip().decode())

wots_sig1 = [sig1[16*i:16*(i+1)] for i in range(l)]
wots_sig2 = [sig2[16*i:16*(i+1)] for i in range(l)]
assert sig1[16*l:] == sig2[16*l:]

final_sig = b""
for i in range(l):
    d_target = target_d[i]
    d1_i = d1[i]
    d2_i = d2[i]
    if d1_i >= d_target:
        final_sig += WOTS.chain(wots_sig1[i], d1_i - d_target, SEED)
    elif d2_i >= d_target:
        final_sig += WOTS.chain(wots_sig2[i], d2_i - d_target, SEED)
    else:
        raise Exception("Bad message")
final_sig += sig1[16*l:]

io.sendlineafter(b">", b"2")
io.sendlineafter(b"Signature:", final_sig.hex().encode())
io.interactive()
