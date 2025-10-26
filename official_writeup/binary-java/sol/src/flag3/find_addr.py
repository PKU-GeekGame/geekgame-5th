#!/usr/bin/env python3

import sys
import re


ADDR_RE = re.compile(rb'\x00\x00\x00\x19(\x00\x00.{6})\x00\x00\x00\x00\x00\x00\x00\x6c\x00\x00\x00\x00\x00')


def find_addr(file: str) -> int | None:
  '''
  Finds the stack address in the given HPROF file.
  '''
  with open(file, 'rb') as f:
    if not (match := ADDR_RE.search(f.read())):
      return None
    addr_bytes = match.group(1)
    return int.from_bytes(addr_bytes, byteorder='big')


if __name__ == '__main__':
  if len(sys.argv) != 2:
    print(f'Usage: {sys.argv[0]} <hprof file>', file=sys.stderr)
    sys.exit(1)

  if (addr := find_addr(sys.argv[1])) is None:
    print('Address not found', file=sys.stderr)
    sys.exit(1)

  print(f'Found address: {addr:#x}')
