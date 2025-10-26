#!/bin/bash

export TERM=xterm-256color

cat << 'EOF'


╔══════════════════════════════════════════════════════════════╗
║                Welcome to EzMCP Bastion Shell                ║
╚══════════════════════════════════════════════════════════════╝

Friendly reminder:
1. This shell is only for helping you solve the EzMCP challenge.
2. Do NOT try to attack this bastion server, or you will be banned.
3. Your starter pack is under /app
Good Luck!
EOF

/bin/bash -i
