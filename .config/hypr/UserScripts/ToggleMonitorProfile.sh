#!/bin/bash

# ==============================================================================
# AJUSTES
# ==============================================================================
# Tiempo a esperar (en segundos) antes de recargar Waybar y otros componentes
# Si Cava o el Top Panel siguen saliendo en vertical, sube este número (ej. 2.5)
REFRESH_DELAY=1
# ==============================================================================

ACTIVE_FILE="$HOME/.config/nwg-displays/active_profile.json"
MONITORS_CONF="$HOME/.config/hypr/monitors.conf"
USER_DEFAULTS="$HOME/.config/hypr/UserConfigs/01-UserDefaults.conf"

CURRENT=$(jq -r '.active_profile' "$ACTIVE_FILE" 2>/dev/null || echo "normal")

# Obtener los monitores dinámicamente desde la config
MAIN_MON=$(grep -E '^\s*\$main_monitor\s*=' "$USER_DEFAULTS" | cut -d'=' -f2 | tr -d ' ' | tr -d '\r' | tr -d '\n')
SEC_MON=$(grep -E '^\s*\$secondary_monitor\s*=' "$USER_DEFAULTS" | cut -d'=' -f2 | tr -d ' ' | tr -d '\r' | tr -d '\n')
MAIN_MON=${MAIN_MON:-"DP-1"}
SEC_MON=${SEC_MON:-"HDMI-A-1"}

if [ "$CURRENT" = "normal" ]; then
    NEXT="programar"
    SEC_TRANSFORM=1   # 90° vertical
else
    NEXT="normal"
    SEC_TRANSFORM=0   # normal horizontal
fi

# Aplicar rotación en vivo
hyprctl keyword monitor "$SEC_MON,1920x1080@74.97,3000x160,1"
hyprctl keyword monitor "$SEC_MON,transform,$SEC_TRANSFORM"

# Guardar persistencia
cat > "$MONITORS_CONF" << EOL
monitor=$MAIN_MON,1920x1080@119.88,1080x160,1.0
monitor=$SEC_MON,1920x1080@74.97,3000x160,1.0
monitor=$SEC_MON,transform,$SEC_TRANSFORM
EOL

mkdir -p "$(dirname "$ACTIVE_FILE")"
printf '{\n  "active_profile": "%s"\n}\n' "$NEXT" > "$ACTIVE_FILE"

notify-send "Monitor Profile" "→ $NEXT" --icon=display --urgency=low

# Enviar proceso al fondo: Esperar X segundos y ejecutar Refresh.sh SOLO para Waybar
(
    sleep "$REFRESH_DELAY"
    "$HOME/.config/hypr/scripts/Refresh.sh" --waybar > /dev/null 2>&1
) & disown
