FROM ubuntu:24.04
RUN apt update && apt install -y python3 python3-pip

COPY requirements.txt /root
RUN pip3 install --break-system-packages -r /root/requirements.txt

COPY static /root/static
COPY templates /root/templates
COPY app.py /root/
COPY flag.py /root/
COPY secret.py /root/
COPY logger.py /root/

WORKDIR /root

CMD ["/usr/bin/python3", "-u", "/root/app.py"]
EXPOSE 5000
