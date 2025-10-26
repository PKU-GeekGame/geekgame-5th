FROM grafana/grafana:12.2-ubuntu
USER root

RUN apt-get update && apt-get install -y gpg
RUN curl --silent --location -o /tmp/influxdata-archive.key https://repos.influxdata.com/influxdata-archive.key && \
    cat /tmp/influxdata-archive.key | gpg --dearmor > /etc/apt/keyrings/influxdata-archive.gpg && \
    echo 'deb [signed-by=/etc/apt/keyrings/influxdata-archive.gpg] https://repos.influxdata.com/debian stable main' > /etc/apt/sources.list.d/influxdata.list
RUN apt-get update && apt-get install -y influxdb2 xxd

COPY grafana_data/ /var/lib/grafana/
# ↑ we did the following:
#   - login with admin:admin
#   - in the production env (not in this attachment) we change the admin password to a strong one
#   - create user geekgame:geekgame with viewer permission
#   - add influxdb data source to grafana

ADD entrypoint_geekgame.sh /

ENTRYPOINT [ "/bin/bash", "/entrypoint_geekgame.sh" ]
