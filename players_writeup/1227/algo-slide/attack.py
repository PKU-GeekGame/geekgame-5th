import base64
from pwn import *
p = remote("prob12.geekgame.pku.edu.cn", 10012)
p.recv()
p.sendline("GgT-7erSFVt7I7Hvkg-YNtq9-GMIfZ2wcRbMIo07XWimUlDYAzRz6_5tpFKowzART9-pdpOemikQ-zInwP43iX0GA8sE".encode())
p.recv()
p.sendline("easy".encode())
a = p.recv().decode("utf-8", "ignore")
a = a[:len(a)-1]
b = ""
c = "{qwertyuiopasdfghjklzxcvbnmQWERTYUIOPASDFGHJKLZXCVBNM1234567890_}"
while True:
    for j in range(65):
        for i in range(65):
            d = b + c[i] +c[j]
            p.sendline(base64.b16encode(base64.b16encode(d.encode())))
            k = p.recv().decode("utf-8", "ignore")
            k = k[:len(k)-1]
            if a.startswith(k):
                b = b + c[i] +c[j]
                break
        if a.startswith(k):
            break
    print(b)
    if b[len(b)-1]=='}':
        break