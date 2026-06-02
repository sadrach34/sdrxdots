#!/usr/bin/env bash

# Obtener la resolución del monitor enfocado usando hyprctl
monitor_info=$(hyprctl activeworkspace -j)
monitor_name=$(echo "$monitor_info" | jq -r '.monitor')
res=$(hyprctl monitors -j | jq -r ".[] | select(.name == \"$monitor_name\")")

width_px=$(echo "$res" | jq -r '.width')

# Lógica adaptable:
# 1080p (1920px) -> size 14
# 1440p (2560px) -> size 18
# 4K    (3840px) -> size 24

if [ "$width_px" -ge 3840 ]; then
    font_size=24
    width_chars=100
elif [ "$width_px" -ge 2560 ]; then
    font_size=18
    width_chars=85
elif [ "$width_px" -ge 1920 ]; then
    font_size=14
    width_chars=75
else
    font_size=11
    width_chars=60
fi

# Ejecutar fuzzel con los parámetros dinámicos
fuzzel --font="JetBrainsMono Nerd Font:size=$font_size" --width=$width_chars "$@"
