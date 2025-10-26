#!/bin/busybox sh

set -e

/bin/busybox --install -s /bin

chmod a-w / -R

mkdir /tmp
chmod a+rwx /tmp

sleep 0.5
echo -n "Flag (1/2): "
read flag

case $flag in
1)
	chmod o-rwx /flag1.txt
	rm /flag2.txt;;
2)
	rm /flag1.txt
	chmod a-rwx /flag2.txt
	chmod u+s /bin/busybox;;
*)
	echo "Bad choice"
	exit 1;;
esac

exec su guest
