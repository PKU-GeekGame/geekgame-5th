import token_signer

FLAGS = [
    'flag{dont-laugh-you-try-you-also-cant-beat-the-second-level}',
    'flag{hello-newma-robert-prove-me-wrong}',
]

with open("2025.vk") as f:
    vk = token_signer.load_vk(f.read())

def checktoken(token):
    if token is None:
        return None
    return token_signer.verify_token(vk, token)
