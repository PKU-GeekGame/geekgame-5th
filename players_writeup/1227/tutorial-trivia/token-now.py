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

sk_hex, vk_hex = gen_keys()
print('sk:', sk_hex)
print('vk:', vk_hex)
sk = load_sk(sk_hex)
vk = load_vk(vk_hex)
print(sign_token(sk, 1234567890))