import requests

url = 'https://www.nyckel.com/v1/functions/cat-vs-dogs-identifier/invoke'
headers = {
    'Authorization': 'Bearer ' + 'eyJhbGciOiJSUzI1NiIsInR5cCI6ImF0K2p3dCJ9.eyJpc3MiOiJodHRwczovL3d3dy5ueWNrZWwuY29tIiwibmJmIjoxNzYwODQ3MDc3LCJpYXQiOjE3NjA4NDcwNzcsImV4cCI6MTc2MDg1MDY3Nywic2NvcGUiOlsiYXBpIl0sImNsaWVudF9pZCI6IjVvaTU1OWprNHB0cmgxbGlzbGwzNHE1dWZ5bGxqaGl0IiwianRpIjoiNDE3RTVGODU2RDk1QjRCMEVDMDI0RDk5RDM5MzYwQTgifQ.cmRjz7Q9u9ORpz-SzBYsLBd8LStap2bz_J6_nug_eccFAAb0qTZ72gQRlE2qF1McDq4F0fJKJterZWT4HcoS_DzmMHmDl_qJ5qqrbVc31KWv1xNBAdJc2yy_uraP9VcVeH_YI-uPe9RE9e1338i08atQWbGLttJRZ2LRbKP5TbRqz0gjP0buT717gV9O8H_Gqee5Np6Xes-Z4XBEWifizjPqWcv555LuusmC2OTJm5HzOv9ZObRU9IQcoZ4x8jrgwqWRt-RJAXJBXkdSnxB3TNCSzUWr2uHJXiIwDLBr8aN3X3Z-hTQ9EoceAYk1VFCnye4K-ht419tfdTbKwOOO2A',
}
for i in range(1416):
    with open('flag1_images/'+str(i)+'.png', 'rb') as f:
        result = requests.post(url, headers=headers, files={'data': f})
    if result.json()["labelName"]=="Dog":
        print("1")
    else:
        print("0")