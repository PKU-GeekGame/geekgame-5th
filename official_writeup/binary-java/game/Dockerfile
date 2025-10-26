FROM ubuntu:24.04

RUN apt update && apt install -y \
  build-essential python3 curl

WORKDIR /root
RUN curl -L \
  https://mirrors.tuna.tsinghua.edu.cn/Adoptium/25/jdk/x64/linux/OpenJDK25U-jdk_x64_linux_hotspot_25_36.tar.gz | \
  tar xz
RUN chmod 777 /root && \
  mkdir root && \
  ln -s ../jdk-25+36 root/.

ENV JAVA_HOME=/root/jdk-25+36 \
  PATH="/root/jdk-25+36/bin:${PATH}"

COPY flag1 /game/flag1/.
COPY flag2 /game/flag2/.
COPY flag3 /game/flag3/.
COPY judge.py /game/judge.py

CMD ["python3", "-u", "/game/judge.py"]
