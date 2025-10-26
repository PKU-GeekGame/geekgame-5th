# modified_key 是你从 4030 地址 dump 出来的密钥
modified_key = b'in1T_Arr@y_1S_s0_E@sy'
# lookup_table 是从 21a0 地址 dump 出来的字节序列
lookup_table = b'\xb4\x20\x95\x44\x0c\x4e\x37\x07\x94\xfb\xfb\x70\x94\x1a\xd4\xa3\x1a\x5c\x42\x91\x38\xe8\x4b\x61\x15\x1a\x00\x51\x38\xc2\x7d\x1f\x7c\xd1\xf1\x22\x71\xde\xcb\xd3\x3f\x3c\x8b\x9d\x61'

key_len = len(modified_key)
flag1 = bytearray(45) # 循环执行 0x2d (45) 次

for i in range(45):
    # 1. 从密钥和查找表中各取一个字节
    key_char = modified_key[i % key_len]
    table_char = lookup_table[i]

    # 2. 进行一系列位运算
    temp = key_char ^ table_char      # 异或
    temp = temp ^ 0x3c                # 异或常数
    
    # ROL: 循环左移, 移动的位数是 (i % 4) + 1
    # 例如 i=0, 移1位; i=1, 移2位; i=2, 移3位; i=3, 移4(0)位; i=4, 移1位...
    # 注意：ROL 4位对于一个字节来说等于ROL 0位，这里可能写错了，应该是 (i & 3) + 1
    # 根据汇编 d2 c0 rol %cl,%al 和 83 e1 03 and $0x3,%ecx; 83 c1 01 add $0x1, %ecx
    # 确认位移数是 (i & 3) + 1
    shift = (i & 3) + 1
    temp = ((temp << shift) | (temp >> (8 - shift))) & 0xFF
    
    temp = temp ^ 0xa5                # 再次异或常数
    
    # 3. 得到 Flag 的一个字节
    flag1[i] = temp

print(flag1)