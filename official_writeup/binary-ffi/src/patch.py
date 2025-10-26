def get_offset(data,pattern):
  for i in range(len(data)):
      if data[i:i+12] == bytes.fromhex(pattern):
          return i

if __name__ == '__main__':
    key = 0x42
    with open("challenge_min_obf", 'rb') as f:
        data = bytearray(f.read())

    pattern1 ="F3 0F 1E FA 55 53 48 83 EC 18 48 31"
    pattern2 ="F3 0F 1E FA 41 56 41 55 41 54 55 53"
    start = get_offset(data,pattern1)
    end = get_offset(data,pattern2)
    size = end-start
    for i in range(0, size):
        data[start+i] ^= (key + (i & 0xFF)) & 0xFF
        
    with open('challenge_min_obf_patched', 'wb') as f:
        f.write(data)