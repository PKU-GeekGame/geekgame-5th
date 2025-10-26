from pwn import *
from hashlib import sha1
import tqdm

try:
    from itertools import batched
except ImportError:
    from itertools import islice

    def batched(xs, k):
        it = iter(xs)
        while chunk := tuple(islice(it, k)):
            yield chunk

try:
    from Crypto.Util.Padding import pad, unpad
    from Crypto.Util.number import *
except:
    from Cryptodome.Util.Padding import pad, unpad
    from Cryptodome.Util.number import *


def crypt(data: bytes, key: bytes, mode: str, rounds: int):
    # block size: 4 bytes
    # key size: 6 bytes, 48 bits
    assert len(key) == 6
    assert len(data) % 4 == 0
    assert mode == "e" or mode == "d"
    res = bytearray()
    keys = [
        key[0:3],
        key[3:6],
    ]
    for i in range(0, len(data), 4):
        part = data[i : i + 4]
        L = part[0:2]
        R = part[2:4]
        for r in range(rounds):
            if mode == "e":
                round_key = keys[r % 2]
            else:
                round_key = keys[(r + 1) % 2]
            temp = sha1(R + round_key).digest()
            L, R = R, bytes([a ^ b for a, b, in zip(L, temp)])
        enc = R + L
        res += enc
    return bytes(res)


# context(log_level="debug")

hostname = input("hostname: ")
port = int(input("port: "))
token = input("token: ")

p = remote(hostname, port)
p.recvuntil(b"Please input your token: ")
p.sendline(token.encode())

p.recvuntil(b"easy or hard?")
p.sendline(b"hard")

enc_scrambled = bytes.fromhex(p.recvline().decode())
enc_xor_key = bytes.fromhex(p.recvline().decode())

# attack
dummy_input = bytes.fromhex("12345678")
assert len(dummy_input) == 4
dummy_L = dummy_input[0:2]
dummy_R = dummy_input[2:4]

p.sendline(dummy_input.hex().encode())
enc = bytes.fromhex(p.recvline().decode())

# enumerate ciphertext after encrypting one step with keys[0]
L = enc[2:4]
R = enc[0:2]

for batch in tqdm.tqdm(list(batched(range(256**2), 128))):
    for i in batch:
        new_L = R
        new_R = long_to_bytes(i, 2)

        enc2 = new_R + new_L
        assert len(enc2) == 4

        # decrypt enc2
        p.sendline(enc2.hex().encode())

    for i in batch:
        new_L = R
        new_R = long_to_bytes(i, 2)

        enc2 = new_R + new_L
        enc3 = bytes.fromhex(p.recvline().decode())

        # one step encrypted with keys[0]
        temp_L = enc3[2:4]
        temp_R = enc3[0:2]

        if temp_R == dummy_R:
            print(f"found possible intermediate {new_R.hex()}")

            # temp_L == dummy_L xor sha1(dummy_R + keys[0])
            good_key0 = []
            for j in tqdm.tqdm(range(256**3)):
                key0 = long_to_bytes(j, 3)
                temp = sha1(dummy_R + key0).digest()
                if temp_L == bytes([a ^ b for a, b, in zip(dummy_L, temp)]):
                    # possible key0, verify
                    temp = sha1(R + key0).digest()
                    if new_R == bytes([a ^ b for a, b, in zip(L, temp)]):
                        print(f"found possible key0 {key0.hex()}")
                        good_key0.append(key0)

            for key0 in good_key0:
                print(f"trying possible key0 {key0.hex()}")
                for j in tqdm.tqdm(range(256**3)):
                    key1 = long_to_bytes(j, 3)
                    if crypt(dummy_input, key0 + key1, "e", 32) == enc:
                        print(f"found possible key1 {key1.hex()}")
                        key = key0 + key1

                        scrambled = crypt(enc_scrambled, key, "d", 32)
                        xor_key = crypt(enc_xor_key, key, "d", 32)

                        flag_padded = bytes([a ^ b for a, b in zip(scrambled, xor_key)])
                        flag = unpad(flag_padded, 4)
                        if b"flag{" in flag:
                            print(flag)
                            exit()
