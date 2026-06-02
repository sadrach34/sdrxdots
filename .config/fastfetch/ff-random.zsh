# Modo y tamaño de los PNG. kitty-direct muestra imagen real en kitty.
# Si quieres volver al modo ASCII/pixelado, usa: FF_PNG_MODE=chafa ff -p
#
# Si salen muy grandes, baja estos numeros.
# Tambien puedes probar sin editar el archivo:
#   FF_PNG_WIDTH=24 FF_PNG_HEIGHT=12 ff -p logo3.png
: ${FF_PNG_MODE:=kitty-direct}
: ${FF_PNG_WIDTH:=40}
: ${FF_PNG_HEIGHT:=24}

_ff_ascii_logo() {
  local logo_path="$1"
  local color="$2"
  local ff_config="$HOME/.config/fastfetch/config.jsonc"

  {
    printf '%s' "$color"
    cat "$logo_path"
    printf '\033[0m\n'
  } | fastfetch -c "$ff_config" --logo-type file-raw --logo -
}

_ff_png_logo() {
  local png_path="$1"
  local ff_config="$HOME/.config/fastfetch/config.jsonc"

  case "$FF_PNG_MODE" in
    kitty-direct)
      fastfetch -c "$ff_config" \
        --kitty-direct "$png_path" \
        --logo-width "$FF_PNG_WIDTH" \
        --logo-height "$FF_PNG_HEIGHT"
      ;;
    chafa)
      chafa -f symbols -s "${FF_PNG_WIDTH}x${FF_PNG_HEIGHT}" "$png_path" \
        | fastfetch -c "$ff_config" --logo-type file-raw --logo -
      ;;
    *)
      print -u2 "ff: FF_PNG_MODE debe ser kitty-direct o chafa"
      return 1
      ;;
  esac
}

_ff_pick_png() {
  local logo_dir="$HOME/.config/fastfetch/logos"
  local pngs=("$logo_dir"/*.png(N))

  if (( ${#pngs[@]} == 0 )); then
    print -u2 "ff: no hay PNGs en $logo_dir"
    return 1
  fi

  print -r -- "${pngs[$(( RANDOM % ${#pngs[@]} + 1 ))]}"
}

_ff_resolve_png() {
  local requested="$1"
  local logo_dir="$HOME/.config/fastfetch/logos"
  local png_path

  if [[ -z "$requested" ]]; then
    _ff_pick_png
    return
  fi

  if [[ "$requested" == */* ]]; then
    png_path="$requested"
  else
    png_path="$logo_dir/$requested"
    [[ -f "$png_path" || "$requested" == *.png ]] || png_path="$logo_dir/$requested.png"
  fi

  if [[ ! -f "$png_path" ]]; then
    print -u2 "ff: no existe el PNG: $requested"
    return 1
  fi

  print -r -- "$png_path"
}

ff() {
  local logo_dir="$HOME/.config/fastfetch/logos"
  local png_path

  clear

  case "$1" in
    -p|--png)
      png_path="$(_ff_resolve_png "$2")" || return 1
      _ff_png_logo "$png_path"
      return
      ;;
  esac

  case $(( RANDOM % 4 )) in
    0)
      _ff_ascii_logo "$logo_dir/logo1.txt" $'\033[1;38;2;255;0;0m'
      ;;
    1)
      _ff_ascii_logo "$logo_dir/logo2.txt" $'\033[1;38;2;255;136;0m'
      ;;
    2)
      png_path="$(_ff_pick_png)" || return 1
      _ff_png_logo "$png_path"
      ;;
    3)
      _ff_ascii_logo "$logo_dir/logo4.txt" $'\033[1;38;2;255;255;255m'
      ;;
  esac
}
