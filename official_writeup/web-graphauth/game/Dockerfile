FROM python:3.13-alpine

RUN pip install --no-cache-dir flask Flask-Limiter Flask-Session requests ariadne argon2-cffi

RUN apk add supervisor
COPY supervisord.conf /etc/supervisord.conf

WORKDIR /app
COPY templates templates
COPY app.py auth.py logger.py secret_gen.py entrypoint.sh ./

RUN chmod +x entrypoint.sh
ENTRYPOINT ["./entrypoint.sh"]
