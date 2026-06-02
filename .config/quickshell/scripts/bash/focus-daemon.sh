#!/usr/bin/env bash
# focus-daemon.sh - Daemon para manejar el temporizador de concentración y bloqueo de apps

STATE_FILE="$HOME/.cache/quickshell/focus_timer.state"
BLACKLIST="discord|steam|heroic|lutris|org.telegram.desktop|whatsapp-for-linux"
BLOCKER_PID_FILE="$HOME/.cache/quickshell/focus_blocker.pid"

mkdir -p "$(dirname "$STATE_FILE")"

function cleanup_blocker() {
    if [ -f "$BLOCKER_PID_FILE" ]; then
        pid=$(cat "$BLOCKER_PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            # Matar el proceso y sus hijos (socat y el loop)
            pkill -P "$pid"
            kill "$pid"
        fi
        rm "$BLOCKER_PID_FILE"
    fi
}

function start_blocker() {
    if [ -f "$BLOCKER_PID_FILE" ]; then return; fi
    
    (
        socat -U - "UNIX-CONNECT:$XDG_RUNTIME_DIR/hypr/$HYPRLAND_INSTANCE_SIGNATURE/.socket2.sock" | while read -r line; do
            if [[ $line == openwindow* ]]; then
                # openwindow>>[address],[workspaceName],[class],[title]
                class=$(echo "$line" | cut -d',' -f3)
                if [[ "$class" =~ ^($BLACKLIST)$ ]]; then
                    hyprctl dispatch closewindow "class:^($class)$"
                    # Llamar al aviso visual de Quickshell
                    qs ipc call shell showFocusWarning >/dev/null 2>&1
                fi
            fi
        done
    ) &
    echo $! > "$BLOCKER_PID_FILE"
}

# Estado anterior para detectar cambios
was_running="0"

while true; do
    if [ -f "$STATE_FILE" ]; then
        # endTimestamp|running|totalTime|zenMode
        IFS='|' read -r end_ts running total zen < "$STATE_FILE"
        
        # Detectar inicio de sesión
        if [ "$running" == "1" ] && [ "$was_running" == "0" ]; then
            start_blocker
            if [ "$zen" == "1" ]; then
                hyprctl --batch "keyword animations:enabled 0;keyword decoration:blur:enabled 0;keyword decoration:shadow:enabled 0"
            fi
        fi

        # Detectar fin de sesión
        if [ "$running" == "0" ] && [ "$was_running" == "1" ]; then
            cleanup_blocker
            hyprctl reload
        fi

        was_running="$running"

        if [ "$running" == "1" ]; then
            now=$(date +%s%3N)
            if [ "$(echo "$now >= $end_ts" | bc -l)" -eq 1 ]; then
                echo "$end_ts|0|$total|$zen" > "$STATE_FILE"
                
                if ! pgrep -x quickshell >/dev/null; then
                    export DISPLAY=:0
                    export WAYLAND_DISPLAY=wayland-1
                    quickshell >/dev/null 2>&1 &
                    sleep 3
                fi
                
                for i in {1..3}; do
                    if qs ipc call shell showAlert >/dev/null 2>&1; then break; fi
                    sleep 1
                done
            fi
        fi
    fi
    sleep 1
done
