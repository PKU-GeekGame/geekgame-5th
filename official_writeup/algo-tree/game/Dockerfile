FROM python:3.12-slim-bullseye
RUN pip install --no-cache-dir pycryptodome

COPY server.py /app.py
COPY utils.py /utils.py

CMD ["python3", "-u", "/app.py"]
