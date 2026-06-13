# If you come from bash you might have to change your $PATH.
# export PATH=$HOME/bin:/usr/local/bin:$PATH
export PATH="$HOME/.local/bin:$PATH"

cd "$HOME"

export ZSH="$HOME/.oh-my-zsh"
export MOZ_ENABLE_WAYLAND=1
export PATH=~/.npm-global/bin:$PATH

ZSH_THEME="gnzh"

plugins=(
    git
    archlinux
    zsh-autosuggestions
    zsh-syntax-highlighting
)

source $ZSH/oh-my-zsh.sh

# Check archlinux plugin commands here
# https://github.com/ohmyzsh/ohmyzsh/tree/master/plugins/archlinux

# Display Pokemon-colorscripts on startup unless explicitly disabled.
# Start kitty with ZSH_STARTUP_FETCH=0 when you want a minimal shell.
if [[ "${ZSH_STARTUP_FETCH:-1}" == 1 ]] && command -v pokemon-colorscripts >/dev/null 2>&1 && command -v fastfetch >/dev/null 2>&1; then
  pokemon_args=(--no-title -r)
  pokemon_shiny_label=
  if (( RANDOM < 8 )); then
    pokemon_args+=(-s)
    pokemon_shiny_label=SHINY
  fi
  pokemon-colorscripts "${pokemon_args[@]}" | POKEMON_SHINY_LABEL=$pokemon_shiny_label fastfetch -c $HOME/.config/fastfetch/config-pokemon.jsonc --logo-type file-raw --logo-height 10 --logo-width 5 --logo -
fi

# fastfetch. Will be disabled if above colorscript was chosen to install
#fastfetch -c $HOME/.config/fastfetch/config-compact.jsonc

# Set-up icons for files/directories in terminal using lsd
alias ls='lsd'
alias l='ls -l'
alias la='ls -a'
alias lla='ls -la'
alias lt='ls --tree'
alias rthunar='sudo --preserve-env=WAYLAND_DISPLAY,XDG_RUNTIME_DIR thunar'
alias cls='clear'
source "$HOME/.config/fastfetch/ff-random.zsh"

#------------------------------------------------------------------------------------------------------------------------
#ACTUALIZACIÓN DEL SISTEMA (PACMAN + AUR)
# Aliases de actualización del sistema
alias update='clear && ~/update.sh && clear && fastfetch'
alias upd='yay -Syu --noconfirm'  # Actualización rápida sin confirmación
alias updsys='sudo pacman -Syu'    # Solo paquetes oficiales
alias updaur='yay -Sua'            # Solo paquetes de AUR

# SdrxDots updater/installer wrapper
Sdrx() {
    local marker_new="$HOME/.local/share/sdrxdots-installed-v3"
    local marker_old="$HOME/.local/share/sadrach-dotfiles-installed-v3"
    local repo_dir=""
    local mode="--update"

    if [[ -f "$marker_new" ]]; then
        repo_dir="$(awk -F= '/^repo=/{print $2; exit}' "$marker_new" 2>/dev/null)"
    elif [[ -f "$marker_old" ]]; then
        repo_dir="$(awk -F= '/^repo=/{print $2; exit}' "$marker_old" 2>/dev/null)"
    fi

    if [[ -z "$repo_dir" && -d "$HOME/SdrxDots/.git" ]]; then
        repo_dir="$HOME/SdrxDots"
    fi
    if [[ -z "$repo_dir" && -d "$HOME/dotfiles/.git" ]]; then
        repo_dir="$HOME/dotfiles"
    fi

    if [[ -z "$repo_dir" || ! -f "$repo_dir/install.sh" ]]; then
        echo "No se encontro SdrxDots/install.sh. Clona el repo o ejecuta desde su carpeta."
        return 1
    fi

    case "${1:-}" in
        --install|install)
            mode="--install"
            shift
            ;;
        --update|update|"")
            [[ "${1:-}" != "" ]] && shift
            mode="--update"
            ;;
        --help|help|-h)
            mode=""
            ;;
    esac

    if [[ -z "$mode" ]]; then
        bash "$repo_dir/install.sh" --help
    else
        bash "$repo_dir/install.sh" "$mode" "$@"
    fi
}
alias sdrx='Sdrx'

# Actualizar aplicaciones específicas
alias updis='yay -S discord --noconfirm && clear && fastfetch && echo "✓ Discord actualizado"'
alias upvsc='yay -S visual-studio-code-bin --noconfirm && clear && fastfetch && echo "✓ VSCode actualizado"'

# Limpieza del sistema
alias cleanup='yay -Sc --noconfirm && yay -Yc --noconfirm && echo "✓ Caché limpiada"'
alias orphans='sudo pacman -Rns $(pacman -Qtdq) 2>/dev/null || echo "No hay paquetes huérfanos"'

#------------------------------------------------------------------------------------------------------------------------
# ALIAS PARA GIT
alias gits='git status'
alias gitp='git pull'
alias gitm='git commit -m "$1"'
alias gitps='git push'

#Alias de Git add, commit y push
gitacp() {
    echo "\n\033[1;34m📦 Archivos modificados:\033[0m"
    git status --porcelain
    
    echo "\n\033[1;36m✓ Selecciona los archivos a subir (TAB para multi-select, ENTER para confirmar):\033[0m"
    git status --porcelain | cut -c4- | fzf -m | xargs -r git add
    
    if [ $? -ne 0 ]; then
        echo "\n\033[1;31m✗ Operación cancelada\033[0m\n"
        return 1
    fi
    
    echo "\n\033[1;33m📝 Committing changes...\033[0m"
    git commit -m "$1" || { echo "\n\033[1;31m✗ Error al hacer commit\033[0m\n"; return 1; }
    
    echo "\n\033[1;32m🚀 Pushing to remote...\033[0m"
    if ! git push; then
        echo "\n\033[1;33m⚠️  Push falló. Intentando con --set-upstream...\033[0m"
        local branch=$(git branch --show-current)
        git push --set-upstream origin "$branch" || { echo "\n\033[1;31m✗ Error al hacer push\033[0m\n"; return 1; }
    fi
    
    echo "\n\033[1;32m✓ Completado!\033[0m\n"
}

#alias mysql
alias mc='mycli -u root -h 127.0.0.1'

# GLaDOS — Asistente de IA self-hosted
glados() {
    ~/.local/bin/glados "$@"
}
alias gl='glados'

alias cobble='cd ~/MinecraftServer && bash start.sh'

alias windows='sudo grub-reboot "Windows Boot Manager (en /dev/sdc1)" && reboot'

#

# Set-up FZF key bindings (CTRL R for fuzzy history finder)
{
  if [[ -r /usr/share/fzf/key-bindings.zsh ]]; then
    source /usr/share/fzf/key-bindings.zsh
  fi
  if [[ -r /usr/share/fzf/completion.zsh ]]; then
    source /usr/share/fzf/completion.zsh
  fi
} 2>/dev/null

HISTFILE=~/.zsh_history
HISTSIZE=10000
SAVEHIST=10000
setopt appendhistory

# --- PYENV ---
export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"

if command -v pyenv >/dev/null 2>&1; then
  eval "$(pyenv init - zsh)"
fi

export PYENV_REHASH_TIMEOUT=5

# Following line was automatically added by arttime installer
export MANPATH=/home/sadrach/.local/share/man:$MANPATH
alias sdrxdotsctl='git --git-dir=$HOME/.dotfiles/ --work-tree=$HOME'

# opencode
export PATH=/home/sadrach/.opencode/bin:$PATH

# bun completions
[ -s "/home/sadrach/.bun/_bun" ] && source "/home/sadrach/.bun/_bun"

# bun
export BUN_INSTALL="$HOME/.bun"
export PATH="$BUN_INSTALL/bin:$PATH"

alias claude-mem='/home/sadrach/.bun/bin/bun "/home/sadrach/.claude/plugins/marketplaces/thedotmack/plugin/scripts/worker-service.cjs"'

alias chadl='npx chadsay "linux > windows"'
chadsay() {
    npx chadsay "$@"
}

# ── SDRX-Beat shell integration ───────────────────────────────────────────────
if [[ -f "$HOME/.config/sdrx-beat/check-update.sh" ]]; then
    source "$HOME/.config/sdrx-beat/check-update.sh"
fi

# preexec: show SDRX-Beat update notice before yay or sudo pacman -Syu
_sdrx_beat_preexec() {
    case "$1" in
        yay\ *|yay|sudo\ pacman\ *-Syu*|sudo\ pacman\ *-Syuu*)
            _sdrx_beat_check_update ;;
    esac
}
autoload -Uz add-zsh-hook 2>/dev/null
add-zsh-hook preexec _sdrx_beat_preexec 2>/dev/null

# Ensure ~/.local/bin is in PATH
[[ ":$PATH:" != *":$HOME/.local/bin:"* ]] && export PATH="$HOME/.local/bin:$PATH"
# ── end SDRX-Beat ─────────────────────────────────────────────────────────────

# pnpm
export PNPM_HOME="/home/sadrach/.local/share/pnpm"
case ":$PATH:" in
  *":$PNPM_HOME:"*) ;;
  *) export PATH="$PNPM_HOME:$PATH" ;;
esac
# pnpm end
