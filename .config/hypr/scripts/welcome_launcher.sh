#!/bin/bash
MARKER="$HOME/.local/share/sdrxdots-welcome-shown"
SCRIPT="$HOME/.config/quickshell/scripts/python/welcome.py"

[ -f "$MARKER" ] && exit 0
[ ! -f "$SCRIPT" ] && exit 0

sleep 3
python3 "$SCRIPT"
