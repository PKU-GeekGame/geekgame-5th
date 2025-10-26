#!/bin/bash
echo "fake{flag1}" > /root/flag_`shuf -i 1-99999999 -n 1`_`shuf -i 1-99999999 -n 1`
/root/helper >/root/log.txt 2>&1 &
sleep .2
su -P -l nobody