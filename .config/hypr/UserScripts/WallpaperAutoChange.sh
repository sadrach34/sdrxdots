#!/bin/bash
# /* ---- 💫 https://github.com/JaKooLit 💫 ---- */  ##
# Contributor: sadrach34 (mods and maintenance)
# source https://wiki.archlinux.org/title/Hyprland#Using_a_script_to_change_wallpaper_every_X_minutes

# This script will randomly go through the files of a directory, setting it
# up as the wallpaper at regular intervals
#
# NOTE: this script uses bash (not POSIX shell) for the RANDOM variable

set -euo pipefail

APPLY_SCRIPT="$HOME/.config/hypr/UserScripts/WallpaperApply.sh"

# Prevent multiple instances
PIDFILE="/tmp/wallpaper_auto_change.pid"
if [ -f "$PIDFILE" ]; then
    if kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
        echo "Script is already running with PID $(cat "$PIDFILE")"
        exit 1
    else
        rm -f "$PIDFILE"
    fi
fi
echo $$ > "$PIDFILE"

# Cleanup on exit
trap 'rm -f "$PIDFILE"; exit' INT TERM EXIT

focused_monitor=$(hyprctl monitors | awk '/^Monitor/{name=$2} /focused: yes/{print name}')

if [[ $# -lt 1 ]] || [[ ! -d $1   ]]; then
	echo "Usage:
	$0 <dir containing images>"
	exit 1
fi

if [[ ! -x "$APPLY_SCRIPT" ]]; then
	echo "ERROR: apply script missing or not executable: $APPLY_SCRIPT" >&2
	exit 1
fi

# Edit below to control the images transition
export SWWW_TRANSITION_FPS=60
export SWWW_TRANSITION_TYPE=simple

# This controls (in seconds) when to switch to the next image
# INTERVAL=1800 #30 minutes
INTERVAL=900	#15 minutes
# INTERVAL=300    #5 minutes
# INTERVAL=60    #1 minute

while true; do
	# Get all image files and randomize them
	mapfile -t images < <(find "$1" -type f \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" -o -iname "*.webp" -o -iname "*.bmp" \) | shuf)
	
	for img in "${images[@]}"; do
		if [ ! -f "$PIDFILE" ]; then
			echo "PID file removed, exiting..."
			exit 0
		fi
		
		echo "Setting wallpaper: $img"
		
		WALL_OUTPUT="$focused_monitor" "$APPLY_SCRIPT" image "$img"
		sleep $INTERVAL
	done
done
