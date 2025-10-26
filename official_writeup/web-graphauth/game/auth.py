from argon2 import PasswordHasher
from ariadne import QueryType, MutationType, gql, make_executable_schema, graphql_sync
from flask import Flask, request, jsonify
from secrets import token_hex
import sqlite3

DB_PATH = 'users.db'

try:
    with open('secret.gql') as f:
        SECRET_GQL = f.read()
except:
    SECRET_GQL = '''type Secret {
        flag2: String
        not_flag: String
    }'''

conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cur = conn.cursor()
cur.execute(
    '''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password_hash TEXT,
        is_admin INTEGER DEFAULT 0
    )'''
)
conn.commit()

ph = PasswordHasher()

def create_initial_admin():
    cur.execute('SELECT COUNT(*) FROM users WHERE is_admin=1')
    if cur.fetchone()[0] > 0:
        return None
    pw = token_hex(16)
    h = ph.hash(pw)
    cur.execute('INSERT INTO users (username, password_hash, is_admin) VALUES (?, ?, 1)', ('admin', h))
    conn.commit()
    return 'admin', pw

initial_admin = create_initial_admin()
if initial_admin:
    print('admin user:', initial_admin[0], 'password:', initial_admin[1])

type_defs = gql(f'''
type User {{
  ok: Boolean!
  isAdmin: Boolean
  username: String
}}

type RegisterResult {{
  ok: Boolean!
}}

{SECRET_GQL}

type Query {{
  login(username: String!, password: String!): User
  secret: Secret
}}

type Mutation {{
  register(username: String!, password: String!): RegisterResult
}}
''')

query = QueryType()
mutation = MutationType()

@query.field('login')
def login(_, info, username, password):
    cur.execute('SELECT username, password_hash, is_admin FROM users WHERE username=?', (username,))
    row = cur.fetchone()
    if row:
        try:
            ph.verify(row[1], password)
            return {'ok': True, 'isAdmin': bool(row[2]), 'username': row[0]}
        except Exception:
            pass
    return {'ok': False, 'isAdmin': False, 'username': None}

@query.field('secret')
def secret(_, info):
    try:
        from secret_handler import secret_handler
        return secret_handler()
    except:
        return {
            'flag2': 'fake{dummy_flag2}',
            'not_flag': 'this_is_not_a_flag',
        }


@mutation.field('register')
def register(_, info, username, password):
    try:
        cur.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)', (username, ph.hash(password)))
        conn.commit()
        return {'ok': True}
    except sqlite3.IntegrityError:
        return {'ok': False}

schema = make_executable_schema(type_defs, query, mutation)

app = Flask(__name__)

@app.route('/graphql', methods=['POST'])
def graphql_server():
    data = request.get_json()
    success, result = graphql_sync(schema, data, context_value=request, debug=False)
    return jsonify(result), (200 if success else 400)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
