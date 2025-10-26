FROM debian:forky
RUN apt-get update && apt-get install -y \
    gcc-15 \
    g++-15 \
    python3 \
    python3-pip \
    vim 

RUN rm -rf /var/lib/apt/lists/*

COPY app.py /app.py

CMD ["python3", "-u", "/app.py"]
