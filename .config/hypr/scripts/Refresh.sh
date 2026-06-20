#!/bin/bash
# /* ---- 💫 https://github.com/JaKooLit 💫 ---- */  ##
# Contributor: sadrach34 (mods and maintenance)
# Scripts for refreshing ags, waybar, rofi, swaync, wallust, quickshell

SCRIPTSDIR=$HOME/.config/hypr/scripts
UserScripts=$HOME/.config/hypr/UserScripts

# Define file_exists function
file_exists() {
    if [ -e "$1" ]; then return 0; else return 1; fi
}

# --- WAYBAR ---
refresh_waybar() {
    echo "Refrescando Waybar..."
    pkill waybar
    killall -SIGUSR2 waybar 2>/dev/null
    sleep 0.5
    if [ -f "${SCRIPTSDIR}/StartWaybar.sh" ]; then
        "${SCRIPTSDIR}/StartWaybar.sh" &
    else
        waybar > /dev/null 2>&1 &
    fi
}

# --- ROFI ---
refresh_rofi() {
    echo "Refrescando Rofi..."
    pkill rofi
}

# --- SWAYNC ---
refresh_swaync() {
    echo "Refrescando SwayNC..."
    pkill swaync
    sleep 0.5
    swaync > /dev/null 2>&1 &
    timeout 2s swaync-client --reload-config > /dev/null 2>&1 || true
}

# --- AGS ---
refresh_ags() {
    echo "Refrescando AGS..."
    pkill ags
}

# --- QUICKSHELL ---
refresh_quickshell() {
    echo "Refrescando Quickshell..."
    pkill -x quickshell 2>/dev/null
    pkill -x qs 2>/dev/null
    sleep 0.2
    if command -v quickshell >/dev/null 2>&1; then
        nohup quickshell > /dev/null 2>&1 & disown
    elif command -v qs >/dev/null 2>&1; then
        nohup qs > /dev/null 2>&1 & disown
    fi
}

# --- WALLPAPER SYNC ---
refresh_wallpaper() {
    echo "Sincronizando estado del wallpaper..."
    if [ -f "$HOME/.config/quickshell/scripts/python/wallpaper_sync.py" ]; then
        python3 "$HOME/.config/quickshell/scripts/python/wallpaper_sync.py" > /dev/null 2>&1 &
    fi
}

# --- RAINBOW BORDERS ---
refresh_borders() {
    echo "Refrescando Rainbow Borders..."
    if file_exists "${UserScripts}/RainbowBorders.sh"; then
        ${UserScripts}/RainbowBorders.sh &
    fi
}

# --- REFRESH EVERYTHING ---
refresh_all() {
    echo "Refrescando todo el sistema..."
    
    # Kill common processes first
    pkill rofi
    pkill ags
    
    refresh_quickshell
    refresh_waybar
    refresh_swaync
    refresh_borders
}

# --- MAIN LOGIC ---
case "$1" in
    --waybar)
        refresh_waybar
        ;;
    --rofi)
        refresh_rofi
        ;;
    --swaync)
        refresh_swaync
        ;;
    --ags)
        refresh_ags
        ;;
    --quickshell|--qs)
        refresh_quickshell
        ;;
    --wallpaper)
        refresh_wallpaper
        ;;
    --borders)
        refresh_borders
        ;;
    *)
        refresh_all
        ;;
esac

exit 0
