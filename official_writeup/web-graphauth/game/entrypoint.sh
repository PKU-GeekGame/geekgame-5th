#!/bin/sh

python secret_gen.py
/usr/bin/supervisord -c /etc/supervisord.conf
