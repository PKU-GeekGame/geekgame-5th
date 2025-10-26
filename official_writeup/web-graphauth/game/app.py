from flask import Flask, request, redirect, url_for, render_template, session, flash
from flask_limiter import Limiter
from flask_session import Session
import os
import requests
import secrets

try:
    from logger import log
except:
    log = print

AUTH_URL = os.environ.get('AUTH_URL', 'http://localhost:5001/graphql')

try:
    with open('/flag1') as f:
        FLAG1 = f.read().strip()
except:
    FLAG1 = 'fake{dummy_flag1}'

def graphql_request(query):
    payload = {'query': query}
    r = requests.post(AUTH_URL, json=payload, timeout=5)
    r.raise_for_status()
    return r.json()

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)
app.config['SESSION_TYPE'] = 'cachelib'
Session(app)
Limiter(key_func=lambda: "global", app=app, default_limits=['10 per minute', '200 per day'])

def clear_session():
    session.pop('username', None)
    session.pop('isAdmin', None)

def validate(username, password) -> bool:
    ok = True
    if not username:
        flash('必须填写用户名')
        ok = False
    elif len(username) > 32:
        flash('用户名过长')
        ok = False
    if not password:
        flash('必须填写密码')
        ok = False
    elif len(password) > 400:
        flash('密码过长')
        ok = False
    return ok


@app.route('/')
def index():
    return render_template(
        'index.html',
        username=session.get('username'),
        secret=FLAG1 if session.get('isAdmin') == True else None,
    )

@app.route('/login', methods=['POST'])
def login():
    clear_session()
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')
    if not validate(username, password):
        return redirect(url_for('index'))
    log('login:username', username)
    log('login:password', password)
    query = f'''
    query ($username: String = "{username}", $password: String = "{password}") {{
      login(username: $username, password: $password) {{
        ok
        isAdmin
        username
      }}
    }}
    '''
    log('login:query', query)
    try:
        response = graphql_request(query)
        log('login:response', response)
        result = response['data']['login']
        if result['ok']:
            session['username'] = result['username']
            session['isAdmin'] = result['isAdmin']
        else:
            flash('认证失败')
    except:
        flash('登录失败')
    return redirect(url_for('index'))

@app.route('/register', methods=['POST'])
def register():
    clear_session()
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')
    if not validate(username, password):
        return redirect(url_for('index'))
    log('register:username', username)
    log('register:password', password)
    query = f'''
    mutation ($username: String = "{username}", $password: String = "{password}") {{
      register(username: $username, password: $password) {{
        ok
      }}
    }}
    '''
    log('register:query', query)
    try:
        response = graphql_request(query)
        log('register:response', response)
        if response['data']['register']['ok']:
            flash('注册成功')
        else:
            flash('用户名已存在')
    except:
        flash('注册失败')
    return redirect(url_for('index'))

@app.route('/logout', methods=['POST'])
def logout():
    clear_session()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
