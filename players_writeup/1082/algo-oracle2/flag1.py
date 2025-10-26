import math
import json
import time
import base64

def gen_data(name):
    print(f"{name = }, {len(name) = }")
    stuid = "1234567890"
    data = {
        'stuid': stuid,
        'name': name,
        'flag': False,
        'timestamp': int(time.time()),
    }
    j = json.dumps(data).encode()
    for i in range(int(math.ceil(len(j) / 16))):
        print(" ", j[i*16:i*16+16])
    return j

def main():
    gen_data("abcd")
    gen_data("abcd" + "01234567890" + "true,           ")
    gen_data("abcd" + "0123456789")
    c1 = base64.b64decode(input("encrypted 1: "))
    c2 = base64.b64decode(input("encrypted 2: "))
    c3 = base64.b64decode(input("encrypted 3: "))
    print()
    print(base64.b64encode(c1[:16*3] + c2[16*3:16*4] + c3[16*4:]))

main()
