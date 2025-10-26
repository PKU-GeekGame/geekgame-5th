FROM ubuntu:24.04

ENV DEBIAN_FRONTEND noninteractive

RUN apt update && apt -y upgrade && \
    apt install -y python3 python3-pip

COPY requirements.txt /

RUN pip install --no-cache-dir --break-system-packages -r requirements.txt

COPY . /
RUN chmod +x run.sh

CMD [ "bash", "run.sh" ]
