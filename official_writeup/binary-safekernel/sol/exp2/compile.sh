#!/bin/bash

set -e

musl-gcc exp.c -Os -static -s -o exp

gen() {
	echo "cat <<EOF > /tmp/exp.b64"
	base64 exp
	echo "EOF"
	echo "base64 -d /tmp/exp.b64 > /tmp/exp"
	echo "chmod +x /tmp/exp"
	echo ""
	echo "while true; do /tmp/exp; done"
}

gen | tee out
