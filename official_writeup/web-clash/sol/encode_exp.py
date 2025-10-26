import gzip
import base64

def encode_exp(fn):
    with open(fn, 'rb') as f:
        s = f.read()
    d = gzip.compress(s)
    b = base64.b64encode(d).decode()
    print(f'echo "{b}"|base64 -d|gunzip|python3')

print('===== flag 1')
encode_exp('exp_flag1.py')
print('===== flag 2')
encode_exp('exp_flag2.py')