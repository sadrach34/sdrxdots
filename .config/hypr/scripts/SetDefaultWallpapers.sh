#!/bin/bash
# Aplica los wallpapers SDRX por defecto en el primer inicio post-install.
# Monitor 1 → wallpapperSDRX1.png, Monitor 2 → wallpapperSDRX2.png.
# Con un solo monitor elige uno al azar entre los dos.

MARKER="$HOME/.local/share/sdrxdots-default-wall-pending"
APPLY="$HOME/.config/hypr/UserScripts/WallpaperApply.sh"
WALL1="$HOME/Pictures/wallpapers/wallpapperSDRX1.png"
WALL2="$HOME/Pictures/wallpapers/wallpapperSDRX2.png"

[[ -f "$MARKER" ]] || exit 0
[[ -f "$WALL1" && -f "$WALL2" ]] || exit 0
[[ -x "$APPLY" ]] || exit 0

sleep 3

mapfile -t MONITORS < <(hyprctl -j monitors 2>/dev/null | jq -r '.[].name' 2>/dev/null)

if [[ ${#MONITORS[@]} -eq 0 ]]; then
    exit 0
elif [[ ${#MONITORS[@]} -eq 1 ]]; then
    WALLS=("$WALL1" "$WALL2")
    CHOSEN="${WALLS[$((RANDOM % 2))]}"
    WALL_OUTPUT="${MONITORS[0]}" "$APPLY" image "$CHOSEN"
else
    WALL_OUTPUT="${MONITORS[0]}" "$APPLY" image "$WALL1"
    WALL_OUTPUT="${MONITORS[1]}" "$APPLY" image "$WALL2"
fi

rm -f "$MARKER"
