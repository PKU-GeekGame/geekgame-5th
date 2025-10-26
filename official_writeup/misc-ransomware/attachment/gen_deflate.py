from base64 import b64encode
from math import factorial
from random import Random
from secrets import randbelow
from tqdm import tqdm
from zlib import decompress, crc32

class BitWriter:
    """Helper class to write individual bits to a byte stream."""

    def __init__(self):
        self.bytes = bytearray()
        self.current_byte = 0
        self.bit_count = 0

    def write_bits(self, value: int, num_bits: int):
        """Write num_bits from value (LSB first)."""
        for i in range(num_bits):
            bit = (value >> i) & 1
            self.current_byte |= bit << self.bit_count
            self.bit_count += 1

            if self.bit_count == 8:
                self.bytes.append(self.current_byte)
                self.current_byte = 0
                self.bit_count = 0

    def get_bytes(self) -> bytes:
        """Get final bytes, padding last byte with zeros if needed."""
        if self.bit_count > 0:
            self.bytes.append(self.current_byte)
        return bytes(self.bytes)


def reverse_bits(value: int, length: int) -> int:
    """Reverse the lowest ``length`` bits of ``value`` (for LSB-first streams)."""
    result = 0
    for _ in range(length):
        result = (result << 1) | (value & 1)
        value >>= 1
    return result


def encode_deflate(data: bytes, code_lengths: list[int]) -> bytes:
    # Build Huffman codes from lengths using canonical Huffman algorithm
    codes = build_canonical_codes(code_lengths)

    # Create bit stream
    bits = BitWriter()

    # Write DEFLATE block header
    bits.write_bits(1, 1)  # BFINAL = 1 (last block)
    bits.write_bits(2, 2)  # BTYPE = 10 (dynamic Huffman)

    # Write dynamic Huffman tables
    write_dynamic_huffman_header(bits, code_lengths)

    # Encode data using literal codes
    for byte in data:
        code, length = codes[byte]
        bits.write_bits(reverse_bits(code, length), length)

    # Write EOB symbol (256)
    code, length = codes[256]
    bits.write_bits(reverse_bits(code, length), length)

    if bits.bit_count != 1:
        # If bit_count != 1, the bit count lowerbound derived from the byte count can be
        # less than the actual bit count, and then the charset cannot be determined.
        raise Exception('bit count not one')

    # Return final bytes
    return bits.get_bytes()


def build_canonical_codes(code_lengths: list[int]) -> list[tuple[int, int]]:
    """
    Build canonical Huffman codes from code lengths.

    Returns list of (code, length) tuples for each symbol.
    """
    max_bits = max(code_lengths)

    # Count codes of each length
    bl_count = [0] * (max_bits + 1)
    for length in code_lengths:
        if length > 0:
            bl_count[length] += 1

    # Find the numerical value of the smallest code for each length
    next_code = [0] * (max_bits + 1)
    code = 0
    for bits in range(1, max_bits + 1):
        code = (code + bl_count[bits - 1]) << 1
        next_code[bits] = code

    # Assign codes to symbols
    codes = [(0, 0)] * len(code_lengths)
    for symbol, length in enumerate(code_lengths):
        if length > 0:
            codes[symbol] = (next_code[length], length)
            next_code[length] += 1

    return codes


def write_dynamic_huffman_header(bits: BitWriter, lit_lengths: list[int]):
    """
    Write dynamic Huffman table header.
    For simplicity, we only encode literal/length codes and use a minimal distance tree.
    """
    hlit = len(lit_lengths) - 257
    hdist = 1 - 1

    bits.write_bits(hlit, 5)
    bits.write_bits(hdist, 5)

    # Encode the code length sequence
    # First, we need to encode lit_lengths + one distance code length
    all_lengths = lit_lengths + [1]

    # Compress code lengths using run-length encoding
    compressed_lengths = compress_code_lengths(all_lengths)

    cl_lengths = [0] * 19
    cl_distinct = 0

    for code, _, _ in compressed_lengths:
        if cl_lengths[code] == 0:
            cl_distinct += 1
        cl_lengths[code] = 4

    assert 8 <= cl_distinct <= 16
    cl_length_3 = 16 - cl_distinct
    for code in range(19):
        if cl_length_3 == 0:
            break
        if cl_lengths[code] == 4:
            cl_lengths[code] = 3
            cl_length_3 -= 1

    # Code length code order (specified by DEFLATE)
    cl_order = [16, 17, 18, 0, 8, 7, 9, 6, 10, 5, 11, 4, 12, 3, 13, 2, 14, 1, 15]

    # Find HCLEN (number of code length codes - 4)
    hclen = 19
    for i in range(18, 3, -1):
        if cl_lengths[cl_order[i]] == 0:
            hclen = i
        else:
            break

    bits.write_bits(hclen - 4, 4)

    # Write code length code lengths
    for i in range(hclen):
        bits.write_bits(cl_lengths[cl_order[i]], 3)

    # Build codes for code length alphabet
    cl_codes = build_canonical_codes(cl_lengths)

    # Write compressed code lengths
    for code, extra_bits, extra_value in compressed_lengths:
        cl_code, cl_len = cl_codes[code]
        bits.write_bits(reverse_bits(cl_code, cl_len), cl_len)
        if extra_bits > 0:
            bits.write_bits(extra_value, extra_bits)


def compress_code_lengths(lengths: list[int]) -> list[tuple[int, int, int]]:
    """
    Compress code lengths using run-length encoding.
    Returns list of (code, extra_bits, extra_value) tuples.
    """
    result = []
    count = 0
    prev = None
    for len in lengths + [-1]:
        if len != prev or (len > 0 and count == 6) or count == 138:
            if count == 1:
                result.append((prev, 0, 0))
            elif count == 2:
                result.append((prev, 0, 0))
                result.append((prev, 0, 0))
            elif prev == 0:
                if count <= 10:
                    result.append((17, 3, count - 3))
                else:
                    result.append((18, 7, count - 11))
            elif count >= 3:
                result.append((16, 2, count - 3))
            if len == 0 or len == prev:
                count = 1
            elif len != -1:
                result.append((len, 0, 0))
                count = 0
            prev = len
        else:
            count += 1
    return result


def gen_deflate(seed: int):
    rng = Random(seed)
    literal_lengths = [1, 2, 3, 4, 14, 15] + [0] * 250
    eob_length = [8]
    len_lengths = [5, 6, 7, 9, 11] + [14] * 21 + [15] * 3
    rng.shuffle(literal_lengths)
    rng.shuffle(len_lengths)
    l14 = literal_lengths.index(14)  # code: 11111111101000
    l15 = literal_lengths.index(15)  # code: 111111111111100
    N = 30  # total data length
    K = 10  # number of code length 14
    try:
        encode_deflate(bytes([l14] * K + [l15] * (N - K)), literal_lengths + eob_length + len_lengths)
    except:
        return []
    # ensure that the crc32 is unique among all combinations
    crc32_set = set()
    total = factorial(N) // factorial(K) // factorial(N-K)
    choices = rng.choices(range(total), k=50)
    data = []
    count = 0
    for mask in tqdm(range(1 << N)):
        popcount = mask.bit_count()
        if not K - 7 <= popcount <= K:
            continue
        d = bytes(l14 if (mask >> i) & 1 else l15 for i in range(N))
        c = crc32(d)
        if c in crc32_set:
            return []
        crc32_set.add(c)
        if popcount == K:
            if count in choices:
                data.append(d)
            count += 1
    with open('deflate_list.txt', 'a') as f:
        for d in data:
            deflated = encode_deflate(d, literal_lengths + eob_length + len_lengths)
            # ensure that it can be decompressed correctly
            inflated = decompress(deflated, wbits=-15)
            assert inflated == d
            f.write(b64encode(deflated).decode() + '\n')

while True:
    gen_deflate(randbelow(2 ** 64))
