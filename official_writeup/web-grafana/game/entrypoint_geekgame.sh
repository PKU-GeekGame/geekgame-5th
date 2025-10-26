#!/bin/bash
set -e

flag1=$(cat /flag1)
flag2=$(cat /flag2 | xxd -ps -c 200)
rm /flag1
rm /flag2

# start influxdb

influxd &
sleep 2

# write flag1

influx setup -u admin -p password -t token -o org -b empty -r 0 -f

BUCKET_NAME=$(shuf -i 1-1000000000 -n 1)
influx bucket create -o org -n secret_$BUCKET_NAME -r 0
influx write -o org -b "secret_$BUCKET_NAME" "flag1 value=\"$flag1\""

unset flag1

# start grafana

/run.sh &
sleep 8

# write flag2

ADMIN_PASSWORD=AocSybCYt8Pa_r4ybFUiNCNV0Pc

curl --user "admin:$ADMIN_PASSWORD" http://127.0.0.1:3000/api/users/1 -XPUT --header "Content-Type: application/json" --data "{\"email\": \"$flag2\", \"login\": \"admin\"}"

unset flag2

# run forever
wait