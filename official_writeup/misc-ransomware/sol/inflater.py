from typing import Tuple, Dict, List

class BitReader:
    def __init__(self, data: bytes, bitpos: int = 0):
        self.data = data
        self.bytepos = bitpos // 8
        self.bitpos = bitpos % 8  # 0..7, LSB-first within each byte (deflate)
        self.total_bits_read = bitpos

    def read_bits(self, n: int) -> int:
        """Read n bits (n <= 32) and return as integer (LSB-first)."""
        val = 0
        bits_read = 0
        while bits_read < n:
            if self.bytepos >= len(self.data):
                raise EOFError("Not enough data while reading bits")
            avail = 8 - self.bitpos
            take = min(n - bits_read, avail)
            current_byte = self.data[self.bytepos]
            # extract bits (LSB-first)
            chunk = (current_byte >> self.bitpos) & ((1 << take) - 1)
            val |= chunk << bits_read
            bits_read += take
            self.bitpos += take
            self.total_bits_read += take
            if self.bitpos == 8:
                self.bitpos = 0
                self.bytepos += 1
        return val

    def get_bitpos(self):
        return self.total_bits_read

class BitWriter:
    def __init__(self):
        self.bytes = bytearray()
        self.current_byte = 0
        self.bit_count = 0

    def write_bits(self, value: int, num_bits: int):
        for i in range(num_bits):
            bit = (value >> i) & 1
            self.current_byte |= bit << self.bit_count
            self.bit_count += 1

            if self.bit_count == 8:
                self.bytes.append(self.current_byte)
                self.current_byte = 0
                self.bit_count = 0

    def get_bytes(self) -> bytes:
        if self.bit_count > 0:
            self.bytes.append(self.current_byte)
        return bytes(self.bytes)

def reverse_bits(value: int, bitlen: int) -> int:
    """Reverse `bitlen` lowest bits of value."""
    rev = 0
    for _ in range(bitlen):
        rev = (rev << 1) | (value & 1)
        value >>= 1
    return rev

def build_canonical_huffman(code_lengths: List[int]) -> Tuple[Dict[Tuple[int,int], int], int]:
    """
    Build canonical Huffman mapping from symbol -> length to (code_rev, length) -> symbol,
    where code_rev is the integer value you'd get by reading bits LSB-first from the stream.
    Returns (mapping, max_length).
    mapping keys are (code_as_int_read_lsb_first, length) -> symbol
    """
    max_bits = max(code_lengths) if code_lengths else 0
    # Count of codes for each length
    bl_count = [0] * (max_bits + 1)
    for l in code_lengths:
        if l > 0:
            bl_count[l] += 1

    # Determine the first code for each length (canonical)
    next_code = [0] * (max_bits + 1)
    code = 0
    for bits in range(1, max_bits + 1):
        code = (code + bl_count[bits - 1]) << 1
        next_code[bits] = code

    mapping: Dict[Tuple[int,int], int] = {}
    for symbol, length in enumerate(code_lengths):
        if length != 0:
            assigned_code = next_code[length]
            next_code[length] += 1
            # canonical codes are MSB-first; but DEFLATE bitstream is LSB-first,
            # so reverse bits when storing for direct lookup of bit sequences read LSB-first.
            code_lsb_first = reverse_bits(assigned_code, length)
            mapping[(code_lsb_first, length)] = symbol

    return mapping, max_bits

# order of code length code lengths (RFC 1951 3.2.7)
CL_ORDER = [16,17,18,0,8,7,9,6,10,5,11,4,12,3,13,2,14,1,15]

def parse_deflate_dynamic_header(data: bytes, bitpos: int = 0):
    """
    Parse a dynamic Huffman header from a deflate stream starting at given bitpos.
    Returns (litlen_tree, dist_tree, bits_consumed, nlits, ndists, code_lengths) where:
      - litlen_tree and dist_tree: mapping (code_as_int_read_lsb_first, length) -> symbol
      - bits_consumed: number of bits consumed from the starting bitpos
      - nlits: number of literal/length codes (HLIT + 257)
      - ndists: number of distance codes (HDIST + 1)
      - code_lengths: combined list of literal+distance code lengths
    """
    br = BitReader(data, bitpos)

    HLIT = br.read_bits(5)      # number of literal/length codes - 257
    HDIST = br.read_bits(5)     # number of distance codes - 1
    HCLEN = br.read_bits(4)     # number of code length codes - 4

    nlits = HLIT + 257
    ndists = HDIST + 1
    nclen = HCLEN + 4

    # read code length code lengths (3 bits each) in CL_ORDER
    cl_code_lengths = [0] * 19
    for i in range(nclen):
        val = br.read_bits(3)
        cl_code_lengths[CL_ORDER[i]] = val

    # build Huffman for code-length alphabet (symbols 0..18)
    cl_mapping, cl_maxbits = build_canonical_huffman(cl_code_lengths)

    # helper to decode one symbol from a mapping
    def decode_symbol_from_mapping(reader: BitReader, mapping: Dict[Tuple[int,int], int], max_len: int) -> int:
        """Read up to max_len bits LSB-first trying to match a (code,length) key."""
        code = 0
        for length in range(1, max_len + 1):
            b = reader.read_bits(1)
            code |= (b << (length - 1))  # accumulate LSB-first
            key = (code, length)
            if key in mapping:
                return mapping[key]
        raise ValueError("No matching Huffman code found while decoding")

    # decode the code lengths for literal/length + distance alphabets
    total_codes = nlits + ndists
    code_lengths = []
    prev_len = 0
    while len(code_lengths) < total_codes:
        sym = decode_symbol_from_mapping(br, cl_mapping, cl_maxbits)
        if 0 <= sym <= 15:
            code_lengths.append(sym)
            prev_len = sym
        elif sym == 16:
            # copy previous length 3-6 times (2 extra bits)
            if len(code_lengths) == 0:
                raise ValueError("Code 16 with no previous length")
            repeat = br.read_bits(2) + 3
            code_lengths.extend([prev_len] * repeat)
        elif sym == 17:
            # repeat zero 3-10 times (3 extra bits)
            repeat = br.read_bits(3) + 3
            code_lengths.extend([0] * repeat)
            prev_len = 0
        elif sym == 18:
            # repeat zero 11-138 times (7 extra bits)
            repeat = br.read_bits(7) + 11
            code_lengths.extend([0] * repeat)
            prev_len = 0
        else:
            raise ValueError(f"Invalid symbol in code-length alphabet: {sym}")

        # guard: don't overflow total
        if len(code_lengths) > total_codes:
            # If the header is malformed we might read too many; trim and continue
            code_lengths = code_lengths[:total_codes]

    # split into literal/length and distance code length arrays
    litlen_lengths = code_lengths[:nlits]
    dist_lengths = code_lengths[nlits:nlits+ndists]

    # build canonical Huffman trees for literal/length and distance
    litlen_tree, litlen_max = build_canonical_huffman(litlen_lengths)
    dist_tree, dist_max = build_canonical_huffman(dist_lengths)

    bits_consumed = br.get_bitpos() - bitpos
    return {
        "litlen_tree": litlen_tree,
        "litlen_max_bits": litlen_max,
        "dist_tree": dist_tree,
        "dist_max_bits": dist_max,
        "bits_consumed": bits_consumed,
        "nlits": nlits,
        "ndists": ndists,
        "litlen_lengths": litlen_lengths,
        "dist_lengths": dist_lengths
    }

def decode_symbol_from_tree(reader: BitReader, tree: Dict[Tuple[int,int], int], max_len: int) -> int:
    """
    Decode a symbol from `reader` using the provided tree mapping produced by build_canonical_huffman.
    The reader will be advanced by the number of bits used.
    """
    code = 0
    for length in range(1, max_len + 1):
        b = reader.read_bits(1)
        code |= (b << (length - 1))
        key = (code, length)
        if key in tree:
            return tree[key]
    raise ValueError("No matching code in tree")
