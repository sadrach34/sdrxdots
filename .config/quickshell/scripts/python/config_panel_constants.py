import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib, Gio

import json
import os
import subprocess
import time
from pathlib import Path
from copy import deepcopy
import re

HOME = Path.home()
CONFIG_PATH          = HOME / ".config/quickshell/data/config.json"
APPS_PATH            = HOME / ".config/quickshell/data/apps.json"
KEYBINDS_SYSTEM_PATH = HOME / ".config/hypr/configs/Keybinds.conf"
KEYBINDS_USER_PATH   = HOME / ".config/hypr/UserConfigs/UserKeybinds.conf"
USER_DEFAULTS_PATH   = HOME / ".config/hypr/UserConfigs/01-UserDefaults.conf"
ENV_VARIABLES_PATH   = HOME / ".config/hypr/UserConfigs/ENVariables.conf"
STARTUP_APPS_PATH    = HOME / ".config/hypr/UserConfigs/Startup_Apps.conf"
WINDOW_RULES_PATH    = HOME / ".config/hypr/UserConfigs/WindowRules.conf"
POWER_SCRIPT         = HOME / ".config/hypr/scripts/PowerProfileAuto.sh"
HYPRIDLE_CONF_PATH   = HOME / ".config/hypr/hypridle.conf"
WAYBAR_LAYOUTS_DIR   = HOME / ".config/waybar/configs"
WAYBAR_STYLES_DIR    = HOME / ".config/waybar/style"
WAYBAR_CONFIG_LINK   = HOME / ".config/waybar/config"
WAYBAR_STYLE_LINK    = HOME / ".config/waybar/style.css"
WAYBAR_STARTUP_LOG   = HOME / ".cache/quickshell/waybar-startup.log"
SKWD_WALL_CONFIG_PATH = HOME / ".config/skwd-wall/config.json"
POSITIONS_JSON_PATH  = HOME / ".config/quickshell/components/ModernClockWidget/positions.json"
SKWD_WALL_CACHE_DIR = Path(os.environ.get("SKWD_WALL_CACHE", HOME / ".cache/skwd-wall"))

KNOWN_TERMINALS = [
    "kitty",
    "alacritty",
    "foot",
    "wezterm",
    "konsole",
    "gnome-terminal",
    "xfce4-terminal",
    "xterm",
    "tilix",
    "cool-retro-term",
    "st",
]

GPU_PRESET_ENV = {
    "auto": [],
    "nvidia": [
        "env = LIBVA_DRIVER_NAME,nvidia",
        "env = __GLX_VENDOR_LIBRARY_NAME,nvidia",
        "env = NVD_BACKEND,direct",
    ],
    "amd": [
        "env = LIBVA_DRIVER_NAME,amdgpu",
        "env = VDPAU_DRIVER,va_gl",
    ],
    "intel": [
        "env = LIBVA_DRIVER_NAME,iHD",
        "env = VDPAU_DRIVER,va_gl",
    ],
    "other": [
        "env = LIBVA_DRIVER_NAME,",
        "env = VDPAU_DRIVER,",
    ],
}

THEME_MODE_PATH = HOME / ".cache/.theme_mode"

PAGES = [
    ("General",      "preferences-system-symbolic"),
    ("Screen",       "video-display-symbolic"),
    ("Components",   "view-app-grid-symbolic"),
    ("Power",        "battery-symbolic"),
    ("Clock",        "preferences-system-time-symbolic"),
    ("Rofi/Quickshell", "preferences-desktop-wallpaper-symbolic"),
    ("Integrations", "applications-engineering-symbolic"),
    ("Apps",         "applications-symbolic"),
    ("Intervals",    "preferences-system-time-symbolic"),
    ("Startup Apps", "system-run-symbolic"),
    ("Window Rules", "window-symbolic"),
    ("Keybinds",     "input-keyboard-symbolic"),
]


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}

def save_json(path: Path, data: dict):
    path.write_text(json.dumps(data, indent=2) + "\n")

def get_nested(data, keys, fallback=None):
    o = data
    for k in keys:
        if not isinstance(o, dict):
            return fallback
        o = o.get(k)
        if o is None:
            return fallback
    return o if o is not None else fallback

def set_nested(data, keys, value):
    o = data
    for k in keys[:-1]:
        if k not in o or not isinstance(o[k], dict):
            o[k] = {}
        o = o[k]
    o[keys[-1]] = value
