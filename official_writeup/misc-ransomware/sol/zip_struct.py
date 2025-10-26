from construct import Struct, Int32ul, Int16ul, Bytes, this

LFH_SIGNATURE = 0x04034b50
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

CDH_SIGNATURE = 0x02014b50
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

EOCDR_SIGNATURE = 0x06054b50
Eocdr = Struct(
    "signature" / Int32ul,
    "disk_number" / Int16ul,
    "disk_start" / Int16ul,
    "disk_entries" / Int16ul,
    "total_entries" / Int16ul,
    "cd_size" / Int32ul,
    "cd_offset" / Int32ul,
    "comment_length" / Int16ul,
    "comment" / Bytes(this.comment_length)
)
