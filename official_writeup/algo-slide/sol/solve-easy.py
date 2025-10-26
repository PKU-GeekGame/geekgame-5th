from pwn import *
import itertools
import tqdm
import base64

try:
    from itertools import batched
except ImportError:
    from itertools import islice

    def batched(xs, k):
        it = iter(xs)
        while chunk := tuple(islice(it, k)):
            yield chunk


hostname = input("hostname: ")
port = int(input("port: "))
token = input("token: ")

p = remote(hostname, port)
p.recvuntil(b"Please input your token: ")
p.sendline(token.encode())

p.recvuntil(b"easy or hard?")
p.sendline(b"easy")

alphabet = "0123456789ABCDEF\x01\x02\x03\x04"
enc_flag = bytes.fromhex(p.recvline().decode())

mapping = dict()

for batch in tqdm.tqdm(list(batched(itertools.product(alphabet, repeat=4), 128))):
    # send in batch
    p.sendline("".join(["".join(plain) for plain in batch]).encode().hex().encode())

    enc = bytes.fromhex(p.recvline().decode())
    assert len(enc) == 4 * len(batch)
    for i in range(len(batch)):
        plain = "".join(batch[i])
        mapping[enc[4 * i : 4 * (i + 1)]] = "".join(plain).encode()

base16 = ""

for i in range(0, len(enc_flag), 4):
    base16 += mapping[enc_flag[i : i + 4]].decode()

padding_len = ord(base16[-1])
base16 = base16[:-padding_len]
print(base64.b16decode(base16))
