#!/usr/bin/env python3
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib

import os
import re
import shutil
import subprocess
from pathlib import Path

HOME = Path.home()
MARKER_FILE        = HOME / ".local/share/sdrxdots-welcome-shown"
KEYBINDS_USER_PATH = HOME / ".config/hypr/UserConfigs/UserKeybinds.conf"

BROWSERS = [
    {
        "id":      "zen-browser",
        "label":   "Zen Browser",
        "cmd":     "env MOZ_ENABLE_WAYLAND=1 MOZ_WEBRENDER=1 MOZ_USE_XINPUT2=1 zen-browser",
        "desktop": "zen-browser.desktop",
        "aur":     "zen-browser-bin",
    },
    {
        "id":      "firefox",
        "label":   "Firefox",
        "cmd":     "MOZ_ENABLE_WAYLAND=1 firefox",
        "desktop": "firefox.desktop",
        "aur":     "firefox",
    },
    {
        "id":      "brave-browser",
        "label":   "Brave",
        "cmd":     "brave-browser",
        "desktop": "brave-browser.desktop",
        "aur":     "brave-bin",
    },
    {
        "id":      "google-chrome-stable",
        "label":   "Google Chrome",
        "cmd":     "google-chrome-stable",
        "desktop": "google-chrome.desktop",
        "aur":     "google-chrome",
    },
    {
        "id":      "chromium",
        "label":   "Chromium",
        "cmd":     "chromium",
        "desktop": "chromium.desktop",
        "aur":     "chromium",
    },
]

BROWSER_KEYBIND_RE = re.compile(
    r'^(bind\s*=\s*\$mainMod\s*,\s*F\s*,\s*exec\s*,).*$',
    re.MULTILINE
)


def detect_installed():
    return [b for b in BROWSERS if shutil.which(b["id"])]


def set_keybind(browser):
    if not KEYBINDS_USER_PATH.exists():
        return
    text = KEYBINDS_USER_PATH.read_text()
    new_line = f"bind = $mainMod, F, exec, {browser['cmd']}"
    replaced = BROWSER_KEYBIND_RE.sub(new_line, text)
    if replaced != text:
        KEYBINDS_USER_PATH.write_text(replaced)


def set_xdg_default(browser):
    try:
        subprocess.run(
            ["xdg-settings", "set", "default-web-browser", browser["desktop"]],
            check=False, capture_output=True
        )
    except FileNotFoundError:
        pass


def mark_shown():
    MARKER_FILE.parent.mkdir(parents=True, exist_ok=True)
    MARKER_FILE.touch()


class WelcomeWindow(Adw.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="sdrxdots")
        self.set_default_size(460, -1)
        self.set_resizable(False)

        self._installed = detect_installed()
        self._selected_browser = self._installed[0] if self._installed else None

        self._build_ui()

    def _build_ui(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.set_content(box)

        # Header bar
        header = Adw.HeaderBar()
        header.set_show_end_title_buttons(False)
        header.set_show_start_title_buttons(False)
        header.add_css_class("flat")
        box.append(header)

        # Content
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_propagate_natural_height(True)
        box.append(scroll)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
        content.set_margin_top(24)
        content.set_margin_bottom(32)
        content.set_margin_start(32)
        content.set_margin_end(32)
        scroll.set_child(content)

        # Hero
        hero = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        hero.set_halign(Gtk.Align.CENTER)

        icon = Gtk.Image.new_from_icon_name("emblem-favorite-symbolic")
        icon.set_pixel_size(48)
        icon.add_css_class("accent")
        hero.append(icon)

        title = Gtk.Label(label="¡Gracias por instalar\nmis dotfiles!")
        title.set_justify(Gtk.Justification.CENTER)
        title.add_css_class("title-1")
        hero.append(title)

        subtitle = Gtk.Label(label="Configura tu navegador predeterminado\npara continuar.")
        subtitle.set_justify(Gtk.Justification.CENTER)
        subtitle.add_css_class("dim-label")
        hero.append(subtitle)

        content.append(hero)

        # Browser section
        if self._installed:
            self._build_browser_chooser(content)
        else:
            self._build_browser_install(content)

        # Done button
        done_btn = Gtk.Button(label="¡Listo! 🎉")
        done_btn.add_css_class("suggested-action")
        done_btn.add_css_class("pill")
        done_btn.set_halign(Gtk.Align.CENTER)
        done_btn.set_sensitive(bool(self._installed) or True)
        done_btn.connect("clicked", self._on_done)
        self._done_btn = done_btn
        content.append(done_btn)

    def _build_browser_chooser(self, parent):
        group = Adw.PreferencesGroup()
        group.set_title("Navegador predeterminado")
        group.set_description("Se usará con la tecla Super + F")

        labels = [b["label"] for b in self._installed]
        model = Gtk.StringList.new(labels)

        row = Adw.ComboRow()
        row.set_title("Navegador")
        row.set_subtitle(self._installed[0]["label"])
        row.set_model(model)
        row.connect("notify::selected", self._on_browser_selected)
        self._combo_row = row

        group.add(row)
        parent.append(group)

    def _build_browser_install(self, parent):
        group = Adw.PreferencesGroup()
        group.set_title("No se detectó ningún navegador")
        group.set_description("Instala uno de los siguientes (requiere yay/pacman):")

        for b in [BROWSERS[0], BROWSERS[1], BROWSERS[2]]:
            row = Adw.ActionRow()
            row.set_title(b["label"])
            row.set_subtitle(f"yay -S {b['aur']}")

            btn = Gtk.Button(label="Instalar")
            btn.add_css_class("pill")
            btn.set_valign(Gtk.Align.CENTER)
            btn.connect("clicked", self._on_install, b)
            row.add_suffix(btn)
            group.add(row)

        parent.append(group)

    def _on_browser_selected(self, row, _param):
        idx = row.get_selected()
        self._selected_browser = self._installed[idx]
        row.set_subtitle(self._selected_browser["label"])

    def _on_install(self, btn, browser):
        btn.set_sensitive(False)
        btn.set_label("Instalando…")
        installer = "yay" if shutil.which("yay") else "pacman"
        cmd = ["pkexec", installer, "-S", "--noconfirm", browser["aur"]] if installer == "pacman" \
              else ["yay", "-S", "--noconfirm", browser["aur"]]
        try:
            subprocess.Popen(cmd)
        except Exception:
            pass
        self._selected_browser = browser

    def _on_done(self, _btn):
        if self._selected_browser:
            set_keybind(self._selected_browser)
            set_xdg_default(self._selected_browser)
        mark_shown()
        self.close()


class WelcomeApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id="com.sdrxdots.Welcome")
        self.connect("activate", self._on_activate)

    def _on_activate(self, _app):
        win = WelcomeWindow(self)
        win.present()


if __name__ == "__main__":
    if MARKER_FILE.exists():
        raise SystemExit(0)
    app = WelcomeApp()
    app.run()
