FROM ubuntu:24.04
RUN apt update && apt install -y python3 python3-pip

COPY requirements.txt /root
RUN pip3 install --break-system-packages -r /root/requirements.txt

COPY static /root/static
COPY templates /root/templates
COPY problemset.json /root
COPY app.py /root
COPY logger.py /root
COPY token_signer.py /root
COPY flag.py /root
COPY db.py /root
COPY chore.py /root
COPY 2025.vk /root

WORKDIR /root
ENV PYTHONUNBUFFERED=1

#CMD ["/usr/bin/python3", "-u", "/root/app.py"]
CMD [ \
    "uwsgi", \
    "--http", "0.0.0.0:5000", \
    "--master", "-p", "1", \
    "--enable-threads", "--lazy", \
    "--disable-logging", \
    "-w", "app:app"]

EXPOSE 5000
