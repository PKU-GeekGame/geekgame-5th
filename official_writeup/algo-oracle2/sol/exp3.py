import requests
import base64
import urllib.parse
import random
import html

base_server="http://127.0.0.1:5000/"
gen_ticket=lambda url: base64.b64decode(requests.get(url).text.split("<br>")[1][3:-4])

tx=gen_ticket(base_server+"3/gen-ticket?name=aaaaaaaaaaaaaaaa&stuid=0００００００００"+chr(130032))
while True:
    random_7=''.join([chr(random.randint(97,122)) for i in range(7)])
    t2=gen_ticket(base_server+"3/gen-ticket?name=aaaaaaaa"+random_7+"&stuid=0000000０"+chr(130032)*2)
    new_token_x=base64.b64encode(tx[:112]+t2[96:112]+tx[128:]).decode()
    detail_x=requests.get(base_server+"3/query-ticket?ticket="+urllib.parse.quote(new_token_x)).text
    if 'Error: 信息解码失败' in detail_x:
        continue
    if len(html.unescape(detail_x.split("<p>")[2][11:-9]))==16:
        break

crypt_block=t2[-8:]+html.unescape(detail_x.split("<p>")[2][11:-9])[8:].encode()


t1=gen_ticket(base_server+"3/gen-ticket?name=\\aaaaaaaaaaaaaaaa&stuid=0000000000")
t3=gen_ticket(base_server+"3/gen-ticket?name=啊aaaaaaaaaaaaaa&stuid=0000000０００")
t4=gen_ticket(base_server+"3/gen-ticket?name=啊aaaaaaaaaaa&stuid=00００００００００")
t5=gen_ticket(base_server+"3/gen-ticket?name=: true}         &stuid=0００００００００"+chr(130032))


new_token_y=base64.b64encode(t2[:96]+crypt_block+t5[112:128])
detail_y=requests.get(base_server+"3/query-ticket?ticket="+urllib.parse.quote(new_token_y)).text

new_token_1=base64.b64encode(t1[:64]+t2[64:80]+t3[80:96]+t4[96:]).decode()
detail_0=requests.get(base_server+"3/query-ticket?ticket="+urllib.parse.quote(base64.b64encode(t2))).text
detail_1=requests.get(base_server+"3/query-ticket?ticket="+urllib.parse.quote(new_token_1)).text
code=detail_0.split("<p>")[5][14:18]+detail_1.split("<p>")[2][13:25]

print(requests.get(base_server+"3/getflag?ticket="+urllib.parse.quote(new_token_y)+"&token=zzz&redeem_code="+code).text)
