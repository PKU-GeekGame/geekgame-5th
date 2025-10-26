import requests
import base64

BASE_URL = "https://prob14-lmyf2gzg.geekgame.pku.edu.cn//1"

def generate_ticket(name):
    params = {'name': name, 'stuid': '1234567890'}
    r = requests.get(f"{BASE_URL}/gen-ticket", params=params)
    return r.text.split('<p>')[2].split('</p>')[0]

def get_flag(ticket_b64):
    params = {'ticket': ticket_b64}
    r = requests.get(f"{BASE_URL}/getflag", params=params)
    return r.text

ticket1_b64 = generate_ticket("a" * 6)
ticket2_b64 = generate_ticket(" " * 15 + ': true        ,')

ticket1 = base64.b64decode(ticket1_b64)
ticket2 = base64.b64decode(ticket2_b64)

blocks1 = [ticket1[i:i+16] for i in range(0, len(ticket1), 16)]
blocks2 = [ticket2[i:i+16] for i in range(0, len(ticket2), 16)]

blocks1[3] = blocks2[3]
modified_ticket = b''.join(blocks1)
modified_b64 = base64.b64encode(modified_ticket).decode()

print(get_flag(modified_b64))