#!/bin/bash
# /* ---- 💫 https://github.com/JaKooLit 💫 ---- */
# Contributor: sadrach34 (mods and maintenance)
# This script for selecting wallpapers (SUPER ctrl W)

set -euo pipefail

APPLY_SCRIPT="$HOME/.config/hypr/UserScripts/WallpaperApply.sh"
MONITORS_CONF="$HOME/.config/hypr/monitors.conf"

# Directory for swaync
iDIR="$HOME/.config/swaync/images"
iDIRi="$HOME/.config/swaync/icons"

# swww transition config
FPS=60
TYPE="any"
DURATION=2
BEZIER=".43,1.19,1,.4"
SWWW_PARAMS="--transition-fps $FPS --transition-type $TYPE --transition-duration $DURATION --transition-bezier $BEZIER"

# Check if package bc exists
if ! command -v bc &>/dev/null; then
  notify-send -i "$iDIR/error.png" "bc missing" "Install package bc first"
  exit 1
fi

# Variables
rofi_theme="$HOME/.config/rofi/config-wallpaper.rasi"
focused_monitor=$(hyprctl monitors -j | jq -r '.[] | select(.focused) | .name')

# Ensure focused_monitor is detected
if [[ -z "$focused_monitor" ]]; then
  notify-send -i "$iDIR/error.png" "E-R-R-O-R" "Could not detect focused monitor"
  exit 1
fi

# Monitor details
scale_factor=$(hyprctl monitors -j | jq -r --arg mon "$focused_monitor" '.[] | select(.name == $mon) | .scale')
monitor_height=$(hyprctl monitors -j | jq -r --arg mon "$focused_monitor" '.[] | select(.name == $mon) | .height')

icon_size=$(echo "scale=1; ($monitor_height * 3) / ($scale_factor * 150)" | bc)
adjusted_icon_size=$(echo "$icon_size" | awk '{if ($1 < 15) $1 = 20; if ($1 > 25) $1 = 25; print $1}')
rofi_override="element-icon{size:${adjusted_icon_size}%;}"

get_wall_dir_for_monitor() {
  local mon="$1"
  local transform
  transform=$(grep -oP "monitor=${mon},transform,\K[0-9]+" "$MONITORS_CONF" 2>/dev/null || echo "0")
  if [[ "$transform" == "1" ]]; then
    echo "$HOME/Pictures/wallpaperVertical"
  else
    echo "$HOME/Pictures/wallpapers"
  fi
}

# Rofi command
rofi_command="rofi -i -show -dmenu -config $rofi_theme -theme-str $rofi_override"

# Sorting Wallpapers
menu() {
  IFS=$'\n' sorted_options=($(sort <<<"${PICS[*]}"))

  printf "%s\x00icon\x1f%s\n" "$RANDOM_PIC_NAME" "$RANDOM_PIC"

  for pic_path in "${sorted_options[@]}"; do
    pic_name=$(basename "$pic_path")
    if [[ "$pic_name" =~ \.gif$ ]]; then
      cache_gif_image="$HOME/.cache/gif_preview/${pic_name}.png"
      if [[ ! -f "$cache_gif_image" ]]; then
        mkdir -p "$HOME/.cache/gif_preview"
        magick "$pic_path" -resize 1920x1080 "$cache_gif_image"
      fi
      printf "%s\x00icon\x1f%s\n" "$pic_name" "$cache_gif_image"
    elif [[ "$pic_name" =~ \.(mp4|mkv|mov|webm|MP4|MKV|MOV|WEBM)$ ]]; then
      cache_preview_image="$HOME/.cache/video_preview/${pic_name}.png"
      if [[ ! -f "$cache_preview_image" ]]; then
        mkdir -p "$HOME/.cache/video_preview"
        ffmpeg -v error -y -i "$pic_path" -ss 00:00:01.000 -vframes 1 "$cache_preview_image"
      fi
      printf "%s\x00icon\x1f%s\n" "$pic_name" "$cache_preview_image"
    else
      printf "%s\x00icon\x1f%s\n" "$(echo "$pic_name" | cut -d. -f1)" "$pic_path"
    fi
  done
}

# Main function
main() {
  local wallDIR selected_file choice_basename mode

  if [[ ! -x "$APPLY_SCRIPT" ]]; then
    notify-send -i "$iDIR/error.png" "E-R-R-O-R" "WallpaperApply.sh not found or not executable"
    exit 1
  fi

  wallDIR="$(get_wall_dir_for_monitor "$focused_monitor")"
  if [[ ! -d "$wallDIR" ]]; then
    notify-send -i "$iDIR/error.png" "E-R-R-O-R" "Wallpaper directory not found: $wallDIR"
    exit 1
  fi

  # Retrieve wallpapers (both images & videos)
  mapfile -d '' PICS < <(find -L "${wallDIR}" -type f \( \
    -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" -o -iname "*.gif" -o \
    -iname "*.bmp" -o -iname "*.tiff" -o -iname "*.webp" -o \
    -iname "*.mp4" -o -iname "*.mkv" -o -iname "*.mov" -o -iname "*.webm" \) -print0)

  if (( ${#PICS[@]} == 0 )); then
    notify-send -i "$iDIR/error.png" "E-R-R-O-R" "No wallpapers found in $wallDIR"
    exit 1
  fi

  RANDOM_PIC="${PICS[$((RANDOM % ${#PICS[@]}))]}"
  RANDOM_PIC_NAME=". random"

  choice=$(menu | $rofi_command)
  choice=$(echo "$choice" | xargs)
  RANDOM_PIC_NAME=$(echo "$RANDOM_PIC_NAME" | xargs)

  if [[ -z "$choice" ]]; then
    echo "No choice selected. Exiting."
    exit 0
  fi

  # Handle random selection correctly
  if [[ "$choice" == "$RANDOM_PIC_NAME" ]]; then
    choice=$(basename "$RANDOM_PIC")
  fi

  choice_basename=$(basename "$choice" | sed 's/\(.*\)\.[^.]*$/\1/')

  # Search for the selected file in the wallpapers directory, including subdirectories
  selected_file=$(find "$wallDIR" -iname "$choice_basename.*" -print -quit)

  if [[ -z "$selected_file" ]]; then
    echo "File not found. Selected choice: $choice"
    exit 1
  fi

  if [[ "$selected_file" =~ \.(mp4|mkv|mov|webm|MP4|MKV|MOV|WEBM)$ ]]; then
    mode="video"
  else
    mode="image"
  fi

  if ! WALL_OUTPUT="$focused_monitor" "$APPLY_SCRIPT" "$mode" "$selected_file"; then
    notify-send -i "$iDIR/error.png" "Wallpaper Error" "Failed to apply $selected_file on $focused_monitor"
    exit 1
  fi

}

# Check if rofi is already running
if pidof rofi >/dev/null; then
  pkill rofi
fi

main
