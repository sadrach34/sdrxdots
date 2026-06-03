#!/bin/bash
TEMPLATE="$HOME/.config/waybar/configs/[TOP] Default"
RUNTIME="/tmp/waybar-config-runtime.json"

# Esperar a que hyprctl esté listo
for i in $(seq 1 10); do
    MONITORS_JSON=$(hyprctl monitors -j 2>/dev/null)
    [ -n "$MONITORS_JSON" ] && break
    sleep 0.5
done

if [ -z "$MONITORS_JSON" ] || ! command -v jq &>/dev/null; then
    exec waybar
fi

# Limpiar template de comentarios // y /* */
CLEAN_JSON=$(sed 's|//.*||g' "$TEMPLATE" | tr -d '\n' | sed 's|/\*.*\*/||g')

# Generar la config combinando el template con el estado de rotación actual
# Usamos el monitor principal para la primera barra y el secundario para la segunda si existen
echo "$MONITORS_JSON" | jq \
    --argjson template "$CLEAN_JSON" \
    '($template) as $t |
     [ .[] | . as $m | 
       # Intentamos buscar la barra que le toca a este monitor en el template
       # Si no hay match por nombre, Bar 1 para el primero y Bar 2 para el segundo monitor detectado
       (($t[] | select(.output == $m.name)) // 
        (if $m.focused then $t[0] else ($t[1] // $t[0]) end)) |
       
       # Forzamos el output correcto
       .output = $m.name |

       # REGLA DE VERTICAL: si transform es impar (1, 3, 5, 7) quitamos módulos
       if (($m.transform % 2) == 1) then
         .["modules-left"]   = ((.["modules-left"] // [])   - ["custom/cava_mviz", "custom/qs_dashboard_top"]) |
         .["modules-center"] = ((.["modules-center"] // []) - ["custom/cava_mviz", "custom/qs_dashboard_top"]) |
         .["modules-right"]  = ((.["modules-right"] // [])  - ["custom/cava_mviz", "custom/qs_dashboard_top"])
       else
         .
       end
    ]' > "$RUNTIME"

exec waybar -c "$RUNTIME"
