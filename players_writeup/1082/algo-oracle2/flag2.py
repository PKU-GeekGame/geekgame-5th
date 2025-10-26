import math
import json
import time
import base64
import random

def gen_token():
    ALPHABET='qwertyuiopasdfghjklzxcvbnm1234567890'
    LENGTH=16
    return ''.join([random.choice(ALPHABET) for _ in range(LENGTH)])

def gen_data(name, stuid="1234567890", token=None):
    assert len(stuid)==10 and stuid.isdigit()
    print(f"{name = }, {len(name) = }, {stuid=}")
    data = {
        'stuid': stuid,
        'name': name,
        'flag': False,
        'code': token or gen_token(),
        'timestamp': int(time.time()),
    }
    j = json.dumps(data).encode()
    for i in range(int(math.ceil(len(j) / 16))):
        print(f"{i:>2}  {j[i*16:i*16+16]}")
    return j

def main():
    print("--- leak token ---")
    p1 = gen_data("abcd")
    c1 = base64.b64decode(input("encrypted 1: "))
    gen_data("一二三四五 ")
    c2 = base64.b64decode(input("encrypted 2: "))
    print()
    print(base64.b64encode(c2[:16*4] + c1[16*4:]))

    print()
    print("--- build payload ---")
    p2 = gen_data('😂😂' + '",              ',
                  stuid="𝟎𝟏23456789")
    c2 = base64.b64decode(input("encrypted 2: "))

    p3 = gen_data('😂😂😂xxxx' + '"😂   ',
                  stuid="𝟎𝟏23456789")
    c3 = base64.b64decode(input("encrypted 3: "))

    p4 = gen_data('😂' + '":              ',
                  stuid="𝟎𝟏𝟐𝟑𝟒𝟓6789")
    c4 = base64.b64decode(input("encrypted 4: "))

    p5 = gen_data('😂😂😂😂xx' + '"xxxx',
                  stuid="𝟎𝟏𝟐𝟑456789")
    c5 = base64.b64decode(input("encrypted 5: "))

    p6 = gen_data('😂' + 'true,           ',
                  stuid="𝟎𝟏𝟐𝟑𝟒𝟓𝟔𝟕𝟖9")
    c6 = base64.b64decode(input("encrypted 6: "))

    p7 = gen_data("😂😂😂😂😂😂啊123")
    c7 = base64.b64decode(input("encrypted 7: "))

    def slice_it(d1, d2, d3, d4, d5, d6, d7):
        return d1[:16*5] + d2[16*5:16*6] + d3[16*6:16*7] + d4[16*7:16*8] + \
               d5[16*8:16*9] + d6[16*9:16*10] + d7[16*10:]

    j = slice_it(p1, p2, p3, p4, p5, p6, p7)
    print(j)
    print(json.loads(j.decode()))
    print()
    print(base64.b64encode(slice_it(c1, c2, c3, c4, c5, c6, c7)))


main()
