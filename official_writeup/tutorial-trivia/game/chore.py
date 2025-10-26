import db
import time
import threading
import json
import random
import traceback

INTERVAL = 15*60

with open('problemset.json', encoding='utf-8') as f:
    _problemset = json.load(f)
    problemset = [{**p, 'answer': 'you guess'} for p in _problemset]
    answers = {p['id']: p['answer'] for p in _problemset}

def format_number(n):
    n = max(0, 5 * ((n - random.choice([0, 1, 2]))//5))
    return f'≥{n}'

def get_passed_count():
    ret = {p['id']: set() for p in problemset}
    
    for uid, _ts, submission in db.query_all_history():
        for pid, ans in submission.items():
            if ans in answers[pid] and pid in ret.keys():
                ret[pid].add(uid)
                
    return {pid: len(uids) for pid, uids in ret.items()}
    
stats = None

def run_job(ts):
    global stats
    cnt = get_passed_count()
    stats = {
        'ts': ts,
        'interval_minutes': INTERVAL//60,
        'cnt_str': {k: format_number(v) for k, v in cnt.items()},
    }

run_job(int(time.time()))
        
def main():
    print('=== chore thread start')
    while True:
        ts = time.time()
        target_ts = INTERVAL + INTERVAL * (ts//INTERVAL)
        if target_ts - ts > 0:
            time.sleep(target_ts - ts)
        
        print('=== chore thread run', target_ts)
        try:
            run_job(target_ts)
        except Exception:
            traceback.print_exc()
        
started = False
def start_chore_thread():
    global started
    if not started:
        threading.Thread(target=main, daemon=True).start()
        started = True
