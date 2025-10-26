import requests
import base64
import urllib.parse
base_server="http://127.0.0.1:5000/"
gen_ticket=lambda url: base64.b64decode(requests.get(url).text.split("<br>")[1][3:-4])
t1=gen_ticket(base_server+"1/gen-ticket?name=xxxxx&stuid=0000000000")
t2=gen_ticket(base_server+"1/gen-ticket?name=啊啊xxx             true&stuid=0000000000")
t3=gen_ticket(base_server+"1/gen-ticket?name=xxxxxxxxxxxxxxxx&stuid=0000000000")
new_token_1=base64.b64encode(t1[:48]+t2[48:64]+t3[64:]).decode()
print(requests.get(base_server+"1/getflag?ticket="+urllib.parse.quote(new_token_1)+"&token=zzz").text)