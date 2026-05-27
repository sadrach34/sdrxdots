#!/usr/bin/env python3
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib, Gio

import time
from copy import deepcopy

from config_panel_constants import *
from config_panel_helpers import (
    load_json, save_json, get_nested, set_nested,
    _read_userdefaults_terminal, _read_compositor, _read_gpu_vendor, _read_theme_mode,
    _parse_keybinds, _parse_startup_apps, _parse_workspace_rules,
)
from config_panel_rows import RowBuilderMixin
from config_panel_pages import PageBuilderMixin
from config_panel_actions import ActionsMixin


class ConfigWindow(ActionsMixin, PageBuilderMixin, RowBuilderMixin, Adw.ApplicationWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_default_size(1020, 740)
        self.set_size_request(760, 520)
        self.set_title("SdrxDots Settings")
        self.set_icon_name("preferences-system-symbolic")
        self.add_css_class("config-panel")

        self._config = load_json(CONFIG_PATH)
        if get_nested(self._config, ["hypridle", "enabled"], None) is None:
            set_nested(self._config, ["hypridle", "enabled"], True)
        if get_nested(self._config, ["hypridle", "warnMinutes"], None) is None:
            set_nested(self._config, ["hypridle", "warnMinutes"], 9)
        if get_nested(self._config, ["hypridle", "lockMinutes"], None) is None:
            set_nested(self._config, ["hypridle", "lockMinutes"], 10)
        if get_nested(self._config, ["hypridle", "ignoreDbusInhibit"], None) is None:
            set_nested(self._config, ["hypridle", "ignoreDbusInhibit"], False)
        if get_nested(self._config, ["appearance", "colorMode"], None) is None:
            set_nested(self._config, ["appearance", "colorMode"], _read_theme_mode())
        self._apps   = load_json(APPS_PATH)
        self._skwd_wall_config = load_json(SKWD_WALL_CONFIG_PATH)
        self._defaults_config = deepcopy(self._config)
        self._defaults_apps   = deepcopy(self._apps)
        self._defaults_skwd_wall_config = deepcopy(self._skwd_wall_config)
        self._saved_config    = deepcopy(self._config)
        self._saved_apps      = deepcopy(self._apps)
        self._saved_skwd_wall_config = deepcopy(self._skwd_wall_config)
        self._unsaved = False

        self._selected_terminal = _read_userdefaults_terminal()
        self._selected_compositor = _read_compositor()
        self._selected_gpu_vendor = _read_gpu_vendor()
        self._selected_color_mode = str(get_nested(self._config, ["appearance", "colorMode"], _read_theme_mode()) or "dark")
        self._startup_apps = _parse_startup_apps()
        self._startup_show_system = False
        self._workspace_rules = _parse_workspace_rules()

        self._keybinds_system_lines: list[str] = []
        self._keybinds_user_lines:   list[str] = []
        self._keybinds_all:   list[dict] = []
        self._keybinds_saved: list[dict] = []
        self._external_conflict_paths: list[str] = []
        self._suppress_external_reload_until = 0.0
        self._file_mtimes: dict[str, float | None] = {}
        self._built_pages: set[str] = set()
        self._load_keybinds()

        self._build_ui()
        self._install_css()
        self._apply_color_mode_style()
        self._setup_file_monitor()
        self._setup_shortcuts()
        self._update_title()

    # ── UI skeleton ───────────────────────────────────────────────────────────

    def _build_ui(self):
        toolbar_view = Adw.ToolbarView()

        # Header bar
        header_bar = Adw.HeaderBar()
        header_bar.set_show_title(True)

        self._save_btn    = Gtk.Button(label="Save")
        self._discard_btn = Gtk.Button(label="Discard")
        self._defaults_btn = Gtk.Button(label="Defaults")
        self._save_btn.add_css_class("suggested-action")
        self._discard_btn.add_css_class("destructive-action")
        self._save_btn.set_sensitive(False)
        self._discard_btn.set_sensitive(False)
        self._save_btn.connect("clicked", self._on_save)
        self._discard_btn.connect("clicked", self._on_discard)
        self._defaults_btn.connect("clicked", self._on_defaults)

        header_bar.pack_end(self._save_btn)
        header_bar.pack_end(self._discard_btn)
        header_bar.pack_start(self._defaults_btn)
        toolbar_view.add_top_bar(header_bar)

        # Unsaved banner
        self._banner = Adw.Banner(title="Unsaved changes")
        self._banner.set_button_label("Save now")
        self._banner.connect("button-clicked", self._on_save)
        toolbar_view.add_top_bar(self._banner)

        self._reload_banner = Adw.Banner(title="External changes detected")
        self._reload_banner.set_button_label("Reload now")
        self._reload_banner.connect("button-clicked", self._on_reload_external)
        toolbar_view.add_top_bar(self._reload_banner)

        # Split view: sidebar left, content right
        split = Adw.OverlaySplitView()
        split.set_sidebar_width_fraction(0.22)
        split.set_min_sidebar_width(180)
        split.set_max_sidebar_width(260)
        split.set_collapsed(False)
        split.set_show_sidebar(True)

        split.set_sidebar(self._build_sidebar())

        self._stack = Gtk.Stack()
        self._stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self._stack.set_transition_duration(180)
        self._stack.set_vexpand(True)
        self._stack.set_hexpand(True)

        self._page_builders = [
            self._build_general_page,
            self._build_screen_page,
            self._build_components_page,
            self._build_power_page,
            self._build_rofi_quickshell_page,
            self._build_integrations_page,
            self._build_apps_page,
            self._build_intervals_page,
            self._build_startup_apps_page,
            self._build_window_rules_page,
            self._build_keybinds_page,
        ]

        # Build pages lazily to keep startup responsive.
        self._page_builder_map = {
            name.lower(): self._page_builders[i]
            for i, (name, _icon) in enumerate(PAGES)
        }

        split.set_content(self._stack)
        toolbar_view.set_content(split)

        self._toast_overlay = Adw.ToastOverlay()
        self._toast_overlay.set_child(toolbar_view)
        self.set_content(self._toast_overlay)
        first_page = PAGES[0][0].lower()
        self._ensure_page(first_page)
        self._nav_list.select_row(self._nav_list.get_row_at_index(0))
        self._banner.set_revealed(False)
        self._reload_banner.set_revealed(False)

    def _ensure_page(self, page_name: str):
        if page_name in self._built_pages:
            return
        builder = self._page_builder_map.get(page_name)
        if builder is None:
            return
        page_widget = builder()
        scroll = Gtk.ScrolledWindow(vexpand=True, hexpand=True)
        scroll.set_child(page_widget)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self._stack.add_named(scroll, page_name)
        self._built_pages.add(page_name)

    def _build_sidebar(self) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.add_css_class("navigation-sidebar")

        # Search bar
        self._search_entry = Gtk.SearchEntry(placeholder_text="Search…")
        self._search_entry.set_margin_start(8)
        self._search_entry.set_margin_end(8)
        self._search_entry.set_margin_top(10)
        self._search_entry.set_margin_bottom(6)
        self._search_entry.connect("search-changed", self._on_global_search)
        box.append(self._search_entry)

        sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        sep.set_margin_bottom(4)
        box.append(sep)

        self._nav_list = Gtk.ListBox()
        self._nav_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self._nav_list.add_css_class("navigation-sidebar")
        self._nav_list.set_vexpand(True)
        self._nav_list.connect("row-selected", self._on_nav_select)

        for name, icon in PAGES:
            row = Gtk.ListBoxRow()
            hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
            hbox.set_margin_start(12)
            hbox.set_margin_end(12)
            hbox.set_margin_top(8)
            hbox.set_margin_bottom(8)
            img = Gtk.Image.new_from_icon_name(icon)
            img.set_pixel_size(16)
            lbl = Gtk.Label(label=name, xalign=0.0, hexpand=True)
            hbox.append(img)
            hbox.append(lbl)
            row.set_child(hbox)
            self._nav_list.append(row)

        box.append(self._nav_list)
        return box

    def _on_nav_select(self, listbox, row):
        if row is None or not hasattr(self, "_stack"):
            return
        idx = row.get_index()
        if 0 <= idx < len(PAGES):
            page_name = PAGES[idx][0].lower()
            self._ensure_page(page_name)
            self._stack.set_visible_child_name(page_name)

    def _on_global_search(self, entry):
        query = entry.get_text().strip().lower()
        if not query:
            return
        # Jump to first page whose name matches
        for i, (name, _) in enumerate(PAGES):
            if query in name.lower():
                self._nav_list.select_row(self._nav_list.get_row_at_index(i))
                return

    # ── Unsaved state ─────────────────────────────────────────────────────────

    def _mark_unsaved(self):
        if not self._unsaved:
            self._unsaved = True
            self._save_btn.set_sensitive(True)
            self._discard_btn.set_sensitive(True)
            self._banner.set_revealed(True)
            self._update_title()

    def _mark_saved(self):
        self._unsaved = False
        self._save_btn.set_sensitive(False)
        self._discard_btn.set_sensitive(False)
        self._banner.set_revealed(False)
        self._update_title()

    def _apply_color_mode_style(self):
        self.remove_css_class("system-dark")
        self.remove_css_class("system-light")
        if (self._selected_color_mode or "dark").strip().lower() == "light":
            self.add_css_class("system-light")
        else:
            self.add_css_class("system-dark")

    # ── Keyboard shortcuts ────────────────────────────────────────────────────

    def _setup_shortcuts(self):
        ctrl = Gtk.ShortcutController()
        ctrl.set_scope(Gtk.ShortcutScope.GLOBAL)

        trigger = Gtk.ShortcutTrigger.parse_string("<Ctrl>s")
        if trigger is not None:
            save_sc = Gtk.Shortcut(
                trigger=trigger,
                action=Gtk.CallbackAction.new(lambda *_: self._on_save(None) or True),
            )
            ctrl.add_shortcut(save_sc)

        esc_trigger = Gtk.ShortcutTrigger.parse_string("Escape")
        if esc_trigger is not None:
            close_sc = Gtk.Shortcut(
                trigger=esc_trigger,
                action=Gtk.CallbackAction.new(lambda *_: self.close() or True),
            )
            ctrl.add_shortcut(close_sc)
        self.add_controller(ctrl)

    # ── File monitor ──────────────────────────────────────────────────────────

    def _setup_file_monitor(self):
        self._file_mtimes = self._snapshot_file_mtimes()
        GLib.timeout_add(1500, self._poll_external_changes)

    def _tracked_files(self) -> dict[str, Path]:
        return {
            "config.json": CONFIG_PATH,
            "apps.json": APPS_PATH,
            "skwd-wall/config.json": SKWD_WALL_CONFIG_PATH,
            "Keybinds.conf": KEYBINDS_SYSTEM_PATH,
            "UserKeybinds.conf": KEYBINDS_USER_PATH,
            "01-UserDefaults.conf": USER_DEFAULTS_PATH,
            "ENVariables.conf": ENV_VARIABLES_PATH,
            "Startup_Apps.conf": STARTUP_APPS_PATH,
            "WindowRules.conf": WINDOW_RULES_PATH,
            "hypridle.conf": HYPRIDLE_CONF_PATH,
        }

    def _mtime(self, path: Path) -> float | None:
        try:
            return path.stat().st_mtime
        except FileNotFoundError:
            return None

    def _snapshot_file_mtimes(self) -> dict[str, float | None]:
        return {name: self._mtime(path) for name, path in self._tracked_files().items()}

    def _poll_external_changes(self):
        now = time.time()
        current = self._snapshot_file_mtimes()
        if now < self._suppress_external_reload_until:
            self._file_mtimes = current
            return True

        changed = [
            name for name, mtime in current.items()
            if mtime != self._file_mtimes.get(name)
        ]
        if changed:
            if self._unsaved:
                self._external_conflict_paths = changed
                self._reload_banner.set_title(
                    "External changes in " + ", ".join(changed) + ". Reload to discard local edits."
                )
                self._reload_banner.set_revealed(True)
            else:
                self._reload_from_disk(changed)
        self._file_mtimes = current
        return True

    def _install_css(self):
        css = b"""
        window.config-panel.system-dark {
            background: #1b1b1f;
            color: #e3e3e7;
        }

        window.config-panel.system-light {
            background: @view_bg_color;
            color: @view_fg_color;
        }

        window.config-panel.system-dark .navigation-sidebar {
            background: #232329;
            border-right: 1px solid #2e2f36;
        }

        window.config-panel.system-light .navigation-sidebar {
            border-right: 1px solid alpha(@view_fg_color, 0.10);
        }

        window.config-panel.system-dark preferencespage,
        window.config-panel.system-dark preferencesgroup,
        window.config-panel.system-dark preferencesgroup > box,
        window.config-panel.system-dark list,
        window.config-panel.system-dark row,
        window.config-panel.system-dark entry,
        window.config-panel.system-dark textview {
            background: #202126;
            color: #e3e3e7;
            border-color: #32333a;
        }

        window.config-panel.system-dark row:hover,
        window.config-panel.system-dark .navigation-sidebar row:hover {
            background: #2a2b33;
        }

        window.config-panel.system-dark .navigation-sidebar row:selected {
            background: #323441;
            color: #f2f2f4;
        }

        .navigation-sidebar {
            border-right: 1px solid alpha(@window_fg_color, 0.08);
        }

        .dim-label {
            opacity: 0.7;
        }
        """
        provider = Gtk.CssProvider()
        provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_display(
            self.get_display(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

    def _normalize_apps_data(self):
        for app_key, app_data in self._apps.items():
            if app_key.startswith("_") or not isinstance(app_data, dict):
                continue
            tags = app_data.get("tags")
            if isinstance(tags, str):
                app_data["tags"] = [t.strip() for t in tags.split(",") if t.strip()]

    def _refresh_pages(self):
        current = self._stack.get_visible_child_name() or PAGES[0][0].lower()
        # Remove all pages and invalidate cache; current page is rebuilt lazily.
        for name, _ in PAGES:
            child = self._stack.get_child_by_name(name.lower())
            if child:
                self._stack.remove(child)
        self._built_pages.clear()
        self._ensure_page(current)
        self._stack.set_visible_child_name(current)

    # ── Keybinds ──────────────────────────────────────────────────────────────

    def _load_keybinds(self):
        sys_text = KEYBINDS_SYSTEM_PATH.read_text() if KEYBINDS_SYSTEM_PATH.exists() else ""
        usr_text = KEYBINDS_USER_PATH.read_text()   if KEYBINDS_USER_PATH.exists()   else ""
        self._keybinds_system_lines = sys_text.splitlines()
        self._keybinds_user_lines   = usr_text.splitlines()
        self._keybinds_all   = _parse_keybinds(sys_text, "SYSTEM") + _parse_keybinds(usr_text, "USER")
        self._keybinds_saved = deepcopy(self._keybinds_all)


# ── Application ───────────────────────────────────────────────────────────────

class ConfigApp(Adw.Application):
    def __init__(self):
        super().__init__(
            application_id="com.sdrxdots.ConfigPanel",
            flags=Gio.ApplicationFlags.FLAGS_NONE,
        )
        self._win = None
        self.connect("activate", self._on_activate)

    def _on_activate(self, app):
        if self._win is None:
            self._win = ConfigWindow(application=app)
        self._win.present()


if __name__ == "__main__":
    import sys
    app = ConfigApp()
    sys.exit(app.run(None))
