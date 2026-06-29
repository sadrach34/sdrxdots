#!/bin/bash
# Mute video wallpaper when a window is focused; unmute when desktop is bare.
# Only activates when wallpaperMute=false in skwd-wall config.

WALL_CFG="${SKWD_WALL_CONFIG:-$HOME/.config/skwd-wall}/config.json"
MPV_SOCK_GLOB="/tmp/mpv-wall-*.sock"

wall_mute_enabled() {
    [[ -f "$WALL_CFG" ]] || { echo true; return; }
    local val
    val=$(jq -r '.wallpaperMute' "$WALL_CFG" 2>/dev/null)
    [[ "$val" == "false" ]] && echo false || echo true
}

mpv_send() {
    local msg="$1"
    for sock in $MPV_SOCK_GLOB; do
        [[ -S "$sock" ]] || continue
        printf '%s\n' "$msg" | socat - "UNIX-CONNECT:$sock" >/dev/null 2>&1
    done
}

mute_wall()   { mpv_send '{"command":["set_property","mute",true]}'; }
unmute_wall() { mpv_send '{"command":["set_property","mute",false]}'; }

check_and_apply() {
    [[ "$(wall_mute_enabled)" == "true" ]] && return
    local focused_ws win_ws win_cls
    focused_ws=$(hyprctl -j monitors 2>/dev/null | jq -r '.[] | select(.focused) | .activeWorkspace.id' 2>/dev/null)
    win_ws=$(hyprctl -j activewindow 2>/dev/null | jq -r '.workspace.id // ""' 2>/dev/null)
    win_cls=$(hyprctl -j activewindow 2>/dev/null | jq -r '.class // ""' 2>/dev/null)
    if [[ -n "$win_cls" && "$win_cls" != "null" && "$win_ws" == "$focused_ws" ]]; then
        mute_wall
    else
        unmute_wall
    fi
}

until [[ -n "$HYPRLAND_INSTANCE_SIGNATURE" ]]; do sleep 1; done

check_and_apply

socat -u "UNIX-CONNECT:$XDG_RUNTIME_DIR/hypr/$HYPRLAND_INSTANCE_SIGNATURE/.socket2.sock" - 2>/dev/null \
| while IFS= read -r line; do
    event="${line%%>>*}"
    case "$event" in
        activewindow|workspace|focusedmon)
            check_and_apply
            ;;
        closewindow|destroywindow|movewindow)
            sleep 0.1
            check_and_apply
            ;;
    esac
done
