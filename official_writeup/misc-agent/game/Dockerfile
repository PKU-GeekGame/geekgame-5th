FROM ubuntu:24.04

RUN apt update && apt install -y python3 python3-pip
COPY requirements.txt /root
RUN pip install --break-system-packages -r /root/requirements.txt

WORKDIR /root

COPY 2025.vk /root
COPY server.py /root
COPY agent.py /root
COPY config.json /root
COPY index.html /root
COPY token_signer.py /root
COPY logger.py /root
COPY flag.py /root
COPY sql.py /root
COPY ratelimit.py /root

CMD ["/usr/bin/python3", "-u", "/root/server.py"]
