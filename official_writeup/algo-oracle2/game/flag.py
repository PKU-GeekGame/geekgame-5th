import hashlib

def getflag(lv):
    with open(f'/flag{lv+1}') as f:
        return f.read().strip()