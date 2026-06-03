#!/bin/bash
# /* ---- 💫 https://github.com/JaKooLit 💫 ---- */  ##
# Contributor: sadrach34 (mods and maintenance)
# Scripts for refreshing ags, waybar, rofi, swaync, wallust

SCRIPTSDIR=$HOME/.config/hypr/scripts
UserScripts=$HOME/.config/hypr/UserScripts

# Define file_exists function
file_exists() {
    if [ -e "$1" ]; then return 0; else return 1; fi
}

# --- REFRESH WAYBAR ONLY ---
refresh_waybar() {
    echo "Refrescando solo Waybar..."
    pkill waybar
    sleep 0.5
    if [ -f "${SCRIPTSDIR}/StartWaybar.sh" ]; then
        "${SCRIPTSDIR}/StartWaybar.sh" &
    else
        waybar > /dev/null 2>&1 &
    fi
}

# --- REFRESH EVERYTHING ---
refresh_all() {
    echo "Refrescando todo el sistema..."
    
    # Kill already running processes
    _ps=(waybar rofi swaync ags)
    for _prs in "${_ps[@]}"; do
        if pidof "${_prs}" >/dev/null; then
            pkill "${_prs}"
        fi
    done

    # added since wallust sometimes not applying
    killall -SIGUSR2 waybar 2>/dev/null

    # quit quickshell & relaunch quickshell
    pkill -x quickshell 2>/dev/null
    pkill -x qs 2>/dev/null
    sleep 0.2
    if command -v quickshell >/dev/null 2>&1; then
        nohup quickshell > /dev/null 2>&1 &
    elif command -v qs >/dev/null 2>&1; then
        nohup qs > /dev/null 2>&1 &
    fi

    # Restart waybar usando el script inteligente
    sleep 1
    if [ -f "${SCRIPTSDIR}/StartWaybar.sh" ]; then
        "${SCRIPTSDIR}/StartWaybar.sh" &
    else
        waybar > /dev/null 2>&1 &
    fi

    # relaunch swaync
    sleep 0.5
    swaync > /dev/null 2>&1 &
    # reload swaync
    timeout 2s swaync-client --reload-config > /dev/null 2>&1 || true

    # Relaunching rainbow borders if the script exists
    sleep 1
    if file_exists "${UserScripts}/RainbowBorders.sh"; then
        ${UserScripts}/RainbowBorders.sh &
    fi
}

# --- MAIN LOGIC ---
case "$1" in
    --waybar)
        refresh_waybar
        ;;
    *)
        refresh_all
        ;;
esac

exit 0
