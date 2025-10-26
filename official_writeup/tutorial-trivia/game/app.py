from flask import *
import time
import datetime
import db
import json
import re
import pytz
import chore

import logger
from flag import checktoken, getflag

MAX_ANSWER_LEN = 80
SUBMISSION_COOLDOWN = 900

def flags_based_on_correct_count(token, count):
    flags = []
    if count>=3:
        flags.append(getflag(token, 1))
    if count>=6:
        flags.append(getflag(token, 2))
        
    if not flags:
        flags.append('no flag yet :)')
    return flags

with open('problemset.json', encoding='utf-8') as f:
    _problemset = json.load(f)
    for p in _problemset:
        for ans in p['answer']:
            assert re.match(p['answer_validator'], ans)
        del ans

    problemset = [{**p, 'answer': 'you guess'} for p in _problemset]
    answers = {p['id']: p['answer'] for p in _problemset}

print('got', len(problemset), 'questions')

def judge_submissions(history_raw, cur_time):
    history = []
    last_ts = -SUBMISSION_COOLDOWN
    max_correct_count = 0
    
    for time_ts, submission in history_raw:
        if (time_ts-last_ts < SUBMISSION_COOLDOWN-1) or cur_time < time_ts:
            correct_count = None
        else:
            correct_count = len([1 for pid, ans in submission.items() if ans in answers[pid]])
            max_correct_count = max(max_correct_count, correct_count)
            
        history.append({
            'time_ts': time_ts,
            'correct_count': correct_count,
            'questions': [{
                'pid': pid,
                'answer': ans,
            } for pid, ans in submission.items()],
        })
        
    return history, max_correct_count

app = Flask(__name__)
app.secret_key = '863a99d6-43b1-4db0-a737-6540b6574946'

@app.template_filter(name='time')
def filter_time(s):
    date = datetime.datetime.fromtimestamp(s, pytz.timezone('Asia/Shanghai'))
    return date.strftime('%m-%d %H:%M:%S')

@app.route('/token', methods=['GET', 'POST'])
def token():
    if request.method=='POST':
        req_token = request.form['token'].strip()
        uid = checktoken(req_token)
        if uid:
            logger.write(uid, ['login', 'manual'])
            session['token'] = req_token
            return redirect('/')
        else:
            flash('Token无效')
    
    return render_template('token.html')

@app.route('/', methods=['GET', 'POST'])
def index():
    if 'token' in request.args:
        req_token = request.args['token']
        assert isinstance(req_token, str)
        uid = checktoken(req_token)
        if uid:
            logger.write(uid, ['login', 'auto'])
            session['token'] = req_token
            return redirect('/')
        else:
            return redirect('/token')

    if 'token' not in session:
        return redirect('/token')

    token = session['token']
    uid = checktoken(token)
    if not uid:
        flash('Token无效')
        return redirect('/token')

    cur_time = int(time.time())
    history_raw = db.query_history(uid)
    if history_raw:
        next_submit_ts = history_raw[-1][0]
        if cur_time >= next_submit_ts: # last submission is normal
            next_submit_ts += SUBMISSION_COOLDOWN
        else: # last submission is draft
            pass
        
        remaining_waiting_s = int(next_submit_ts - cur_time)
        if remaining_waiting_s <= 0:
            remaining_waiting_s = None
    else:
        next_submit_ts = None
        remaining_waiting_s = None

    if request.method=='POST':
        submission = {
            pid: request.form.get(pid, '')
            for pid in answers.keys()
        }
        for v in submission.values():
            if len(v)>MAX_ANSWER_LEN:
                logger.write(uid, ['submission_toolong', len(v), v[:MAX_ANSWER_LEN*2]])
                flash('答案太长')
                return redirect('/')
        
        if remaining_waiting_s:
            logger.write(uid, ['submission_draft', submission])
            db.push_draft(uid, next_submit_ts, submission)
            flash('提交草稿成功')
        else:
            logger.write(uid, ['submission', submission])
            try:
                db.push_history(uid, submission)
            except Exception as e:
                logger.write(uid, ['submission_exception', type(e), str(e)])
                flash('提交失败，可能是因为重复提交')
            else:
                flash('提交成功')

        return redirect('/')

    if remaining_waiting_s:
        flash(f'冷却中，直到 {filter_time(next_submit_ts)}（{remaining_waiting_s} 秒之后）才能再次提交')

    history, max_correct_count = judge_submissions(history_raw, cur_time)
    if history:
        last_history_answer = {x['pid']: x['answer'] for x in history[-1]['questions']}
    else:
        last_history_answer = {}

    flags = flags_based_on_correct_count(token, max_correct_count)
    
    logger.write(uid, ['get_page', max_correct_count])

    return render_template(
        'index.html',
        problemset=problemset,
        history=history,
        cooldown_ts=next_submit_ts if remaining_waiting_s else None,
        correct_count=max_correct_count,
        flags=flags,
        max_length=MAX_ANSWER_LEN,
        full_cooldown=SUBMISSION_COOLDOWN,
        last_history_answer=last_history_answer,
        stats=chore.stats,
    )
    
@app.route('/check_answer/<int:idx>', methods=['GET'])
def check_answer(idx):
    token = session['token']
    uid = checktoken(token)
    if not uid:
        return 'Token无效'

    req_ans = request.args['ans']
    assert isinstance(req_ans, str)
    
    if not 0<=idx<len(problemset):
        return '题号错误'
        
    logger.write(uid, ['check_answer', idx, req_ans[:MAX_ANSWER_LEN*2]])
        
    if not req_ans:
        return 'OK'
    if len(req_ans)>MAX_ANSWER_LEN:
        return '答案过长'
    
    p = problemset[idx]
    if not re.match(f"^{p['answer_validator']}$", req_ans):
        return '格式错误'
    else:
        return 'OK'
        
@app.route('/log/blur')
def log_blur():
    token = session['token']
    uid = checktoken(token)
    if not uid:
        return 'Token无效'
        
    logger.write(uid, ['log_blur'])
    return 'OK'
    
@app.route('/log/focus')
def log_focus():
    token = session['token']
    uid = checktoken(token)
    if not uid:
        return 'Token无效'
        
    logger.write(uid, ['log_focus'])
    return 'OK'
    
@app.route('/log/paste', methods=['POST'])
def log_paste():
    token = session['token']
    uid = checktoken(token)
    if not uid:
        return 'Token无效'
        
    target = request.args['target']
    payload = request.json
    
    logger.write(uid, ['log_paste', target, payload])
    return 'OK'

chore.start_chore_thread()
    
#if __name__=='__main__':
#    app.run('0.0.0.0', 5000)