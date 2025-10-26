import base64
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric.ec import EllipticCurvePrivateKey
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

private_key = ec.generate_private_key(ec.SECP256R1(), default_backend())
public_key = private_key.public_key()
# serializing into PEM
rsa_pem = private_key.private_bytes(encoding=serialization.Encoding.PEM, format=serialization.PrivateFormat.PKCS8, encryption_algorithm=serialization.NoEncryption())
TOKEN_SIGNING_KEY: EllipticCurvePrivateKey = serialization.load_pem_private_key(rsa_pem, password=None)
def sign_token(uid: int) -> str:
    sig = base64.urlsafe_b64encode(TOKEN_SIGNING_KEY.sign(
        str(uid).encode(),
        ec.ECDSA(hashes.SHA256()),
    )).decode()
    return f'{uid}:{sig}'

print(sign_token(1234567890))