import logger
import token_signer

#---
#---
#---
#---
#---
#---
#---
#---
#---
#---
FLAGS = [
    'flag{lian-wang-sou-suo, qi-dong!}',
    'flag{GettingIntoLifeCuzIFoundThatItsNotSoBoringNoAnymoreNeeyh}',
]
#---
#---
#---
#---
#---
#---
#---
#---
#---
#---

with open("2025.vk") as f:
    vk = token_signer.load_vk(f.read())

def getflag(token, idx):
    uid = token_signer.verify_token(vk, token)
    assert uid is not None
    #logger.write(uid, ['getflag', idx, token])
    return FLAGS[idx-1]

def checktoken(token):
    return token_signer.verify_token(vk, token)