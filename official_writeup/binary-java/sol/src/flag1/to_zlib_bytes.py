#!/usr/bin/env python3

import sys
import zlib

if len(sys.argv) != 3:
  print(f'Usage: {sys.argv[0]} <binary file> <template file>', file=sys.stderr)
  sys.exit(1)

with open(sys.argv[1], 'rb') as f:
  so_bytes = f.read()
  so_bytes = zlib.compress(so_bytes, level=9)
  java_byte_array = ',\n    '.join(
      ', '.join(f'(byte)0x{b:02x}' for b in so_bytes[i:i + 16])
      for i in range(0, len(so_bytes), 16)
  )
  java_code = '  static final byte[] compressed = new byte[]{\n'
  java_code += f'    {java_byte_array}\n'
  java_code += '  };'

with open(sys.argv[2], 'r') as f:
  template = f.read()
  output = template.replace('/* compressed */', java_code)

print(output)
