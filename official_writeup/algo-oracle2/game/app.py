from flask import *
import random
import time
import base64
import json
import os

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

import logger
from flag import getflag
from secret import AES_KEYS, AES_TWEAKS

app = Flask(__name__)
uid = int(os.environ['hackergame_uid'])

def gen_token():
    ALPHABET='qwertyuiopasdfghjklzxcvbnm1234567890'
    LENGTH=16
    return ''.join([random.choice(ALPHABET) for _ in range(LENGTH)])

@app.template_filter('mosaic')
def mosaic_filter(s):
    #return s
    if len(s)<=6:
        return '*'*len(s)
    else:
        return s[:4] + '*'*(len(s)-4)

@app.route('/')
def index():
    return render_template('index.html')
    
@app.route('/<level>/gen-ticket')
def gen_ticket(level):
    if level not in ["1", "2", "3"]:
        return 'Error: 无效的关卡'
    l = int(level) - 1
    name = request.args['name']
    stuid = request.args['stuid']
    
    #print(name, len(name))
    if not 0<len(name)<=[99,22,18][l]:
        return 'Error: 姓名长度不正确'
    if not (len(stuid)==10 and stuid.isdigit()):
        return 'Error: 学号格式不正确'
    if 'flag' in request.args:
        return 'Error: 为支持环保事业，暂时无法选择需要礼品'
    
    match l:
        case 0:        
            data = {
                'stuid': stuid,
                'name': name,
                'flag': False,
                'timestamp': int(time.time()),
            }
        case 1:        
            data = {
                'stuid': stuid,
                'name': name,
                'flag': False,
                'code': gen_token(),
                'timestamp': int(time.time()),
            }
        case 2:        
            data = {
                'stuid': stuid,
                'code': gen_token(),
                'name': name,
                'flag': False,
            }
    
    cipher = Cipher(algorithms.AES(AES_KEYS[l]), modes.XTS(AES_TWEAKS[l])).encryptor()
    ct_bytes = cipher.update(json.dumps(data).encode())
    enc_out = base64.b64encode(ct_bytes).decode()
    
    logger.write(uid, ['gen', l+1, data, enc_out])
    return '<p>已为您生成购票凭证：</p><br><p>'+enc_out+'</p><br><p><a href="/">返回</a></p>'
    
@app.route('/<level>/query-ticket')
def query_ticket(level):
    if level not in ["1", "2", "3"]:
        return 'Error: 无效的关卡'
    l = int(level) - 1
    ticket_b64 = request.args['ticket'].strip()
    if len(ticket_b64) > 1024:
        return 'Error: 太长了'
    
    status_to_log = []
    try:
        try:
            ticket = base64.b64decode(ticket_b64)
            cipher = Cipher(algorithms.AES(AES_KEYS[l]), modes.XTS(AES_TWEAKS[l])).decryptor()
            plaintext = cipher.update(ticket)
        except:
            status_to_log = ['cannot_decrypt']
            return 'Error: 解密购票凭证失败'
        
        #print(plaintext)
        #print(plaintext.decode('utf-8', 'ignore'))

        try:
            data = json.loads(plaintext.decode('utf-8', 'ignore'))
        except:
            status_to_log = ['cannot_json_decode']
            return 'Error: 信息解码失败'
        
        status_to_log = ['ok', data]
        return render_template('query.html', ticket=data)
    
    finally:
        logger.write(uid, ['query', l+1, ticket_b64, *status_to_log])
    
@app.route('/<level>/getflag')
def flag(level):
    if level not in ["1", "2", "3"]:
        return 'Error: 无效的关卡'
    l = int(level) - 1
    ticket_b64 = request.args['ticket'].strip()
    code = request.args.get('redeem_code', '')
    if len(ticket_b64) > 1024 or len(code) > 1024:
        return 'Error: 太长了'
    
    status_to_log = []
    try:
        try:
            ticket = base64.b64decode(ticket_b64)
            cipher = Cipher(algorithms.AES(AES_KEYS[l]), modes.XTS(AES_TWEAKS[l])).decryptor()
            plaintext = cipher.update(ticket)
        except:
            status_to_log = ['cannot_decrypt']
            return 'Error: 解密购票凭证失败'
        
        try:
            data = json.loads(plaintext.decode('utf-8', 'ignore'))
        except:
            status_to_log = ['cannot_json_decode']
            return 'Error: 信息解码失败'
            
        if data['flag']!=True:
            status_to_log = ['no_flag_field', data]
            return 'Error: 您未选择需要礼品'
            
        if l!=0 and code!=data['code']:
            status_to_log = ['wrong_code', data]
            return 'Error: 兑换码错误'
        
        status_to_log = ['ok', data]
        return '<p>兑换成功，这是你的礼品：</p><br><p>'+getflag(l)+'</p>'

    finally:
        logger.write(uid, ['getflag', l+1, ticket_b64, code, *status_to_log])

if __name__=='__main__':
    app.run('127.0.0.1', 5000, debug=False)
