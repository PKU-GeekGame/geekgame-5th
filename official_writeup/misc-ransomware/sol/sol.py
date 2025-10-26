from io import BytesIO
from sys import argv
from tqdm import tqdm
from zlib import crc32
import re

from inflater import parse_deflate_dynamic_header, BitWriter
from zip_struct import CDH_SIGNATURE, EOCDR_SIGNATURE, LocalFileHeader, CentralDirHeader, Eocdr

root = argv[1]

with open('algo-gzip.py', 'rb') as f:
    known = f.read()

with open(f'{root}/geekgame-4th/official_writeup/algo-gzip/attachment/algo-gzip.f58A66B51.py', 'rb') as f:
    known_encrypted = f.read()

with open(f'{root}/geekgame-5th/problemset/misc-ransomware/flag1-2-3.f58A66B51.txt', 'rb') as f:
    flags_encrypted = f.read()

flags_partial = bytes(a ^ b ^ c for a, b, c in zip(known, known_encrypted, flags_encrypted))
print(flags_partial)
flag1 = re.search(br'flag\{.+?\}', flags_partial).group(0).decode()
print(f'{flag1 = }\n')

with open(f'{root}/flag-is-not-stored-in-this-file.f58A66B51.zip', 'rb') as f:
    zip_encrypted = f.read()

zip_partial = bytes(a ^ b ^ c for a, b, c in zip(known, known_encrypted, zip_encrypted))
zip_io = BytesIO(zip_partial)

lfh1 = LocalFileHeader.parse_stream(zip_io)
assert lfh1 is not None
data1 = zip_io.read(lfh1.compressed_size)
offset2 = zip_io.tell()

lfh2 = LocalFileHeader.parse_stream(zip_io)
assert lfh2 is not None
data2_offset = zip_io.tell()
data2_head = zip_io.read()

zip_io.write(b'\0' * (lfh2.compressed_size - len(data2_head)))
cd_offset = zip_io.tell()

external_attrs = 0x1800000

cdh1 = CentralDirHeader.build(dict(
    signature=CDH_SIGNATURE,
    version_made_by=lfh1.version_needed,
    version_needed=lfh1.version_needed,
    flags=lfh1.flags,
    compression=lfh1.compression,
    mod_time=lfh1.mod_time,
    mod_date=lfh1.mod_date,
    crc32=lfh1.crc32,
    compressed_size=lfh1.compressed_size,
    uncompressed_size=lfh1.uncompressed_size,
    filename_length=lfh1.filename_length,
    extra_length=0,
    comment_length=0,
    disk_number_start=0,
    internal_attrs=0,
    external_attrs=external_attrs,
    local_header_offset=0,
    filename=lfh1.filename,
    extra=bytes(),
    comment=bytes(),
))
zip_io.write(cdh1)

cdh2 = CentralDirHeader.build(dict(
    signature=CDH_SIGNATURE,
    version_made_by=lfh2.version_needed,
    version_needed=lfh2.version_needed,
    flags=lfh2.flags,
    compression=lfh2.compression,
    mod_time=lfh2.mod_time,
    mod_date=lfh2.mod_date,
    crc32=lfh2.crc32,
    compressed_size=lfh2.compressed_size,
    uncompressed_size=lfh2.uncompressed_size,
    filename_length=lfh2.filename_length,
    extra_length=0,
    comment_length=0,
    disk_number_start=0,
    internal_attrs=0,
    external_attrs=external_attrs,
    local_header_offset=offset2,
    filename=lfh2.filename,
    extra=bytes(),
    comment=bytes(),
))
zip_io.write(cdh2)

eocdr = Eocdr.build(dict(
    signature=EOCDR_SIGNATURE,
    disk_number=0,
    disk_start=0,
    disk_entries=2,
    total_entries=2,
    cd_size=len(cdh1)+len(cdh2),
    cd_offset=cd_offset,
    comment_length=0,
    comment=bytes(),
))
zip_io.write(eocdr)

zip_io.seek(0)
zip_complete = zip_io.read()

flags_partial2 = bytes(a ^ b ^ c for a, b, c in zip(flags_encrypted, zip_encrypted, zip_complete))[cd_offset:]
print(flags_partial2)
flag2 = re.search(br'flag\{.+?\}', flags_partial2).group(0).decode()
print(f'{flag2 = }\n')

deflate_info = parse_deflate_dynamic_header(data2_head, 3)

litlen_tree = deflate_info['litlen_tree']
l14 = 0
l15 = 0
c14 = (0, 0)
c15 = (0, 0)
eob_code = (0, 0)
print('literal codes:')
for code, sym in litlen_tree.items():
    if sym < 256:
        print(f'{sym}: {code}')
        if code[1] == 14:
            l14 = sym
            c14 = code
        elif code[1] == 15:
            l15 = sym
            c15 = code
    elif sym == 256:
        eob_code = code

n = lfh2.uncompressed_size
deflate_header_len = deflate_info['bits_consumed'] + 3
max_total_lit_len = lfh2.compressed_size * 8 - deflate_header_len - eob_code[1]
min_total_lit_len = max_total_lit_len - 7
all_15_len = 15 * n
print(f'{min_total_lit_len = }, {all_15_len = }')
min_14_count = all_15_len - max_total_lit_len
max_14_count = all_15_len - min_total_lit_len

for mask in tqdm(range(1 << n)):
    if not min_14_count <= mask.bit_count() <= max_14_count:
        continue
    data = bytes(l14 if (mask >> i) & 1 else l15 for i in range(n))
    if crc32(data) == lfh2.crc32:
        bits = BitWriter()
        bits.bytes.extend(data2_head[:deflate_header_len // 8])
        bits.bit_count = deflate_header_len % 8
        if bits.bit_count != 0:
            bits.current_byte = data2_head[deflate_header_len // 8] & ((1 << bits.bit_count) - 1)
        for i in range(n):
            code = c14 if (mask >> i) & 1 else c15
            bits.write_bits(*code)
        bits.write_bits(*eob_code)
        deflated = bits.get_bytes()
        flags_flag3 = bytes(a ^ b ^ c for a, b, c in zip(
            flags_encrypted[data2_offset:],
            zip_encrypted[data2_offset:],
            deflated,
        ))
        tqdm.write(str(flags_flag3))
        match = re.search(br'flag\{.+?\}', flags_flag3)
        if match is None:
            continue
        flag3 = match.group(0).decode()
        tqdm.write(f'{flag3 = }')
        break
