from nacl.encoding import URLSafeBase64Encoder
from nacl.signing import SigningKey, VerifyKey
import struct

from typing import Optional

def gen_keys() -> tuple[str, str]:
    sk = SigningKey.generate()
    vk = sk.verify_key

    sk_enc = sk.encode(encoder=URLSafeBase64Encoder).decode('utf-8')
    vk_enc = vk.encode(encoder=URLSafeBase64Encoder).decode('utf-8')

    return sk_enc, vk_enc

def load_sk(sk_enc: str) -> SigningKey:
    return SigningKey(sk_enc.strip().encode('utf-8'), encoder=URLSafeBase64Encoder)

def load_vk(vk_enc: str) -> VerifyKey:
    return VerifyKey(vk_enc.strip().encode('utf-8'), encoder=URLSafeBase64Encoder)

def sign_token(sk: SigningKey, uid: int) -> str:
    assert uid>=0
    encoded = struct.pack('<Q', int(uid)).rstrip(b'\x00')
    sig = sk.sign(encoded, encoder=URLSafeBase64Encoder).decode()
    return f'GgT-{sig}'

def verify_token(vk: VerifyKey, token: str) -> Optional[int]:
    if not token.startswith('GgT-'):
        return None

    try:
        verified = vk.verify(token[4:].encode('utf-8'), encoder=URLSafeBase64Encoder)
    except Exception:
        return None

    uid = struct.unpack('<Q', verified.ljust(8, b'\x00'))[0]
    return uid
