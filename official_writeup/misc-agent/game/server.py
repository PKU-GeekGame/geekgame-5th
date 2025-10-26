from sanic import *
from agent import run_llm, CONTENT_EXAMPLE
import asyncio
import traceback
import random
import time

import logger
import ratelimit
from flag import checktoken
from sql import *

import traceback
def get_traceback(e):
    lines = traceback.format_exception(type(e), e, e.__traceback__)
    return ''.join(lines)

MAX_LEN = 800
DAILY_COUNT = 300
MIN_DELAY = 10

create_db()

prev_ts_by_uid = {}

def check_prev_ts(uid) -> str | None:
    ts = time.time()
    prev_ts = prev_ts_by_uid.get(uid, 0)

    delay = prev_ts + MIN_DELAY - ts
    if delay > .1:
        return f'提交过于频繁，请等待 {delay:.1f} 秒'
    else:
        prev_ts_by_uid[uid] = ts
        return None

app = Sanic('agent')

with open('index.html') as f:
    frontend = (
        f.read()
            .replace('__CONTENT_EXAMPLE__', CONTENT_EXAMPLE)
            .replace('__MAX_LEN__', str(MAX_LEN))
            .replace('__DAILY_COUNT__', str(DAILY_COUNT))
            .replace('__MIN_DELAY__', str(MIN_DELAY))
    )

@app.get('/')
async def index(request):
    if 'token' in request.args:
        req_token = request.args.get('token')
        uid = checktoken(req_token)
        if uid:
            resp = redirect('/')
            resp.add_cookie('token', req_token, httponly=True)
            return resp
        else:
            return text('Token无效，请从比赛平台进入', 400)

    uid = checktoken(request.cookies.get('token', None))
    if not uid:
        return text('Token无效，请从比赛平台进入', 400)
    
    logger.write(uid, ['visit'])

    return html(frontend)

@app.post('/run')
async def run(request):
    token = request.cookies.get('token', None)
    uid = checktoken(token)
    if not uid:
        return text('Token无效，请从比赛平台进入')
    
    user_input = request.form.get('content')

    if not 0 < len(user_input) <= MAX_LEN:
        return text('输入不满足长度限制')
    
    if ratelimit.exceeded():
        return text('啊这，上游 API 的 Rate Limit 爆炸辣')

    err = check_prev_ts(uid)
    if err:
        return text(err)
    
    ok, left = check_and_update_question_count(uid, DAILY_COUNT)
    if not ok:
        return text('今日使用次数已达上限')

    logger.write(uid, ['submit', user_input])

    response = await request.respond(content_type='text/event-stream; charset=utf-8')
    await response.send(f'=== BEGIN === （使用次数限制：本日剩余 {left} 次）\n')

    logs = []
    try:
        async for event in run_llm(user_input):
            logs.append(event)
            await response.send(event + '\n')
            await asyncio.sleep(.05 + random.random() * .15)

        logger.write(uid, ['finish', logs, user_input])
    except Exception as e:
        tb = get_traceback(e)
        logger.write(uid, ['exception', logs, user_input, str(type(e)), str(e), tb])
        await response.send(f'Agent 错误：{type(e)}\n')

    await response.send('=== END ===\n')

@app.get('/log/focus')
def log_focus(request):
    token = request.cookies.get('token', None)
    uid = checktoken(token)
    if not uid:
        return json({'error': 'Token无效，请从比赛平台进入'}, 400)

    logger.write(uid, ['log_focus'])
    return text('OK')
    
@app.get('/log/blur')
def log_blur(request):
    token = request.cookies.get('token', None)
    uid = checktoken(token)
    if not uid:
        return json({'error': 'Token无效，请从比赛平台进入'}, 400)

    logger.write(uid, ['log_blur'])
    return text('OK')

@app.post('/log/paste')
def log_paste(request):
    token = request.cookies.get('token', None)
    uid = checktoken(token)
    if not uid:
        return json({'error': 'Token无效，请从比赛平台进入'}, 400)
        
    payload = request.json
    
    logger.write(uid, ['log_paste', payload])
    return text('OK')

if __name__=='__main__':
    app.run(host='0.0.0.0', port=5000, debug=False, single_process=True)
