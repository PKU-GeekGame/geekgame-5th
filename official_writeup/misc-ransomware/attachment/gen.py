from base64 import b64decode
from construct import Struct, Int32ul, Int16ul, Bytes, this
from io import BytesIO
from pathlib import Path
from secrets import token_bytes, randbelow, choice
from string import ascii_letters, digits
from zipfile import ZipFile, ZipInfo
from zlib import decompress, crc32

EXT = "f58A66B51"
CHAL_ID = "misc-ransomware"
DIR_GZIP = f"{CHAL_ID}/geekgame-4th/official_writeup/algo-gzip/attachment"
DIR_RANSOMWARE = f"{CHAL_ID}/geekgame-5th/problemset/{CHAL_ID}"
README_NAME = f"ReadMe.{EXT}.txt"
ZIP_PATH = f"{CHAL_ID}/flag-is-not-stored-in-this-file.{EXT}.zip"
GZIP_PY_READ = "algo-gzip.py"
GZIP_PY_PATH = f"{DIR_GZIP}/algo-gzip.{EXT}.py"
FLAG_PATH = f"{DIR_RANSOMWARE}/flag1-2-3.{EXT}.txt"
FIRST_FILE_NAME = "no-flag-here"
DEFLATE_NAME = "also-not-here"
LFH_SIZE = 30
CDH_SIZE = 46
EOCDR_SIZE = 22
DEFLATE_PAYLOAD_LEN = (14 * 10 + 15 * 20 + 8) // 8
FLAG2_MARGIN_END = 4

with open("deflate_list.txt") as f:
    DEFLATE_LIST = f.readlines()

with open("tail", "rb") as f:
    TAIL = f.read()

with open(GZIP_PY_READ, "rb") as f:
    GZIP_PY_CONTENT = f.read()

with open(README_NAME) as f:
    README_CONTENT = f.read()

LocalFileHeader = Struct(
    "signature" / Int32ul,
    "version_needed" / Int16ul,
    "flags" / Int16ul,
    "compression" / Int16ul,
    "mod_time" / Int16ul,
    "mod_date" / Int16ul,
    "crc32" / Int32ul,
    "compressed_size" / Int32ul,
    "uncompressed_size" / Int32ul,
    "filename_length" / Int16ul,
    "extra_length" / Int16ul,
    "filename" / Bytes(this.filename_length),
    "extra" / Bytes(this.extra_length)
)

CentralDirHeader = Struct(
    "signature" / Int32ul,
    "version_made_by" / Int16ul,
    "version_needed" / Int16ul,
    "flags" / Int16ul,
    "compression" / Int16ul,
    "mod_time" / Int16ul,
    "mod_date" / Int16ul,
    "crc32" / Int32ul,
    "compressed_size" / Int32ul,
    "uncompressed_size" / Int32ul,
    "filename_length" / Int16ul,
    "extra_length" / Int16ul,
    "comment_length" / Int16ul,
    "disk_number_start" / Int16ul,
    "internal_attrs" / Int16ul,
    "external_attrs" / Int32ul,
    "local_header_offset" / Int32ul,
    "filename" / Bytes(this.filename_length),
    "extra" / Bytes(this.extra_length),
    "comment" / Bytes(this.comment_length)
)

charset = ascii_letters + digits
def rand_str(length):
    assert length >= 0
    return "".join(choice(charset) for _ in range(length))

def zipinfo(filename: str) -> ZipInfo:
    info = ZipInfo(filename, (2025, 10, 17, 11, 45, 14))
    info.create_system = 0
    return info

key = bytes()

def gen(user, ch) -> Path:
    flag1 = ch.flags[0].correct_flag(user)
    flag2 = ch.flags[1].correct_flag(user)
    flag3 = ch.flags[2].correct_flag(user)

    dst_path = Path("_gen").resolve() / str(user._store.id)
    dst_path.mkdir(exist_ok=True, parents=True)
    out_path = dst_path / f"{CHAL_ID}.zip"

    # flag2 from first external attributes to before the last 4 zeros of EOCDR
    assert len(flag2) == 8 + len(FIRST_FILE_NAME) + CDH_SIZE + len(DEFLATE_NAME) + EOCDR_SIZE - FLAG2_MARGIN_END
    assert len(flag3) == DEFLATE_PAYLOAD_LEN

    deflate_data = b64decode(choice(DEFLATE_LIST))

    flag1_file_len = (
        len(GZIP_PY_CONTENT)
        - LFH_SIZE
        - len(FIRST_FILE_NAME)
        - LFH_SIZE
        - len(DEFLATE_NAME)
        - (len(deflate_data) - DEFLATE_PAYLOAD_LEN)
    )

    zip_io = BytesIO()

    with ZipFile(zip_io, "w") as zip_file:
        zip_file.writestr(zipinfo(FIRST_FILE_NAME), token_bytes(flag1_file_len))
        zip_file.writestr(zipinfo(DEFLATE_NAME), deflate_data)

    zip_io.seek(0)
    LocalFileHeader.parse_stream(zip_io)
    zip_io.read(flag1_file_len)
    lfh2 = LocalFileHeader.parse_stream(zip_io)
    zip_io.read(len(deflate_data))
    CentralDirHeader.parse_stream(zip_io)
    cdh2 = CentralDirHeader.parse_stream(zip_io)

    assert lfh2 is not None
    assert cdh2 is not None

    inflated = decompress(deflate_data, wbits=-15)
    deflate_crc32 = crc32(inflated)

    lfh2.compression = 8
    lfh2.uncompressed_size = len(inflated)
    lfh2.crc32 = deflate_crc32

    cdh2.compression = 8
    cdh2.uncompressed_size = len(inflated)
    cdh2.crc32 = deflate_crc32

    zip_io.seek(0)
    LocalFileHeader.parse_stream(zip_io)
    zip_io.read(flag1_file_len)
    zip_io.write(LocalFileHeader.build(lfh2))
    zip_io.read(len(deflate_data))
    CentralDirHeader.parse_stream(zip_io)
    zip_io.write(CentralDirHeader.build(cdh2))

    zip_io.seek(0)
    zip_bytes = zip_io.read()

    secret_file = f'This file contains all flags of {CHAL_ID} and some garbage data.\r\n'
    secret_file += rand_str(randbelow(len(GZIP_PY_CONTENT) - len(secret_file) - len(flag1))) + flag1
    secret_file += rand_str(len(GZIP_PY_CONTENT) - len(secret_file)) + flag3
    secret_file += rand_str(len(zip_bytes) - len(secret_file) - len(flag2) - FLAG2_MARGIN_END) + flag2 + rand_str(FLAG2_MARGIN_END)
    # add an impossible-to-capture fake flag; something is wrong if it's submitted
    secret_file += "flag{this_is_the_real_secret}"

    def encrypt(data: bytes):
        global key
        delta = len(data) - len(key)
        if delta > 0:
            key += token_bytes(delta)
        return bytes(k ^ d for k, d in zip(key, data)) + TAIL

    with ZipFile(out_path, "w", 8) as attachment:
        attachment.writestr(zipinfo(ZIP_PATH), encrypt(zip_bytes))
        attachment.writestr(zipinfo(f"{CHAL_ID}/{README_NAME}"), README_CONTENT)
        attachment.writestr(zipinfo(GZIP_PY_PATH), encrypt(GZIP_PY_CONTENT))
        attachment.writestr(zipinfo(f"{DIR_GZIP}/{README_NAME}"), README_CONTENT)
        attachment.writestr(zipinfo(FLAG_PATH), encrypt(secret_file.encode()))
        attachment.writestr(zipinfo(f"{DIR_RANSOMWARE}/{README_NAME}"), README_CONTENT)

    return out_path
