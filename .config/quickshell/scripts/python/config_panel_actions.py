from copy import deepcopy
from config_panel_constants import *
from config_panel_helpers import (
    load_json, save_json, get_nested, set_nested,
    _visual_toggles_from_config, _apply_optimization_component_mode,
    apply_waybar, sync_waybar_links, _waybar_last_error_summary,
    _sync_userdefaults_terminal, _read_userdefaults_terminal,
    _read_compositor, _read_gpu_vendor, _sync_theme_mode,
    _parse_startup_apps, _parse_workspace_rules,
    _sync_startup_apps, _sync_workspace_rules,
    apply_hypr_reload, sync_hypridle_conf, apply_hypridle_enabled,
    rebuild_keybind_file,
)


class ActionsMixin:

    def _reload_from_disk(self, changed: list[str] | None = None):
        self._config = load_json(CONFIG_PATH)
        self._apps = load_json(APPS_PATH)
        self._skwd_wall_config = load_json(SKWD_WALL_CONFIG_PATH)
        self._saved_skwd_wall_config = deepcopy(self._skwd_wall_config)
        self._load_keybinds()
        self._selected_terminal = _read_userdefaults_terminal()
        self._selected_compositor = _read_compositor()
        self._selected_gpu_vendor = _read_gpu_vendor()
        self._selected_color_mode = str(get_nested(self._config, ["appearance", "colorMode"], _read_theme_mode()) or "dark")
        self._startup_apps = _parse_startup_apps()
        self._workspace_rules = _parse_workspace_rules()
        self._apply_color_mode_style()
        self._saved_config = deepcopy(self._config)
        self._saved_apps = deepcopy(self._apps)
        self._mark_saved()
        self._reload_banner.set_revealed(False)
        self._external_conflict_paths = []
        self._refresh_pages()
        if changed:
            self._toast("Reloaded external changes: " + ", ".join(changed))

    def _on_save(self, _widget):
        prev_bar    = get_nested(self._saved_config, ["components", "bar", "enabled"], True)
        prev_cfg_raw = get_nested(self._saved_config, ["components", "bar", "waybarConfig"], "~/.config/waybar/config")
        prev_sty_raw = get_nested(self._saved_config, ["components", "bar", "waybarStyle"], "~/.config/waybar/style.css")
        prev_pow_t  = get_nested(self._saved_config, ["power", "deviceType"], "auto")
        prev_pow_p  = get_nested(self._saved_config, ["power", "profile"], "performance")
        prev_opt    = bool(get_nested(self._saved_config, ["optimization", "enabled"], False))
        prev_visual_toggles = _visual_toggles_from_config(self._saved_config)
        prev_idle_enabled = bool(get_nested(self._saved_config, ["hypridle", "enabled"], True))
        prev_idle_warn = int(get_nested(self._saved_config, ["hypridle", "warnMinutes"], 9) or 9)
        prev_idle_lock = int(get_nested(self._saved_config, ["hypridle", "lockMinutes"], 10) or 10)
        prev_idle_ignore = bool(get_nested(self._saved_config, ["hypridle", "ignoreDbusInhibit"], False))

        cur_opt_enabled = bool(get_nested(self._config, ["optimization", "enabled"], False))
        _apply_optimization_component_mode(self._config, cur_opt_enabled)

        self._normalize_apps_data()
        save_json(CONFIG_PATH, self._config)
        save_json(APPS_PATH, self._apps)
        save_json(SKWD_WALL_CONFIG_PATH, self._skwd_wall_config)

        cur_bar = get_nested(self._config, ["components", "bar", "enabled"], True)
        cur_cfg_raw = get_nested(self._config, ["components", "bar", "waybarConfig"], "~/.config/waybar/config")
        cur_sty_raw = get_nested(self._config, ["components", "bar", "waybarStyle"], "~/.config/waybar/style.css")
        prev_cfg = str(Path(str(prev_cfg_raw).replace("~", str(HOME))))
        prev_sty = str(Path(str(prev_sty_raw).replace("~", str(HOME))))
        cur_cfg = str(Path(str(cur_cfg_raw).replace("~", str(HOME))))
        cur_sty = str(Path(str(cur_sty_raw).replace("~", str(HOME))))
        bar_paths_changed = (cur_cfg != prev_cfg) or (cur_sty != prev_sty)

        # Keep ~/.config/waybar/config and style.css aligned so external refresh scripts
        # (e.g. Win+Alt+R Refresh.sh) preserve the selected preset.
        sync_waybar_links(cur_cfg, cur_sty)

        if cur_bar != prev_bar:
            ok = apply_waybar(cur_bar, cur_cfg, cur_sty, restart=cur_bar)
            if cur_bar and not ok:
                set_nested(self._config, ["components", "bar", "waybarConfig"], prev_cfg_raw)
                set_nested(self._config, ["components", "bar", "waybarStyle"], prev_sty_raw)
                sync_waybar_links(prev_cfg, prev_sty)
                apply_waybar(True, prev_cfg, prev_sty, restart=True)
                save_json(CONFIG_PATH, self._config)
                reason = _waybar_last_error_summary(style_path=cur_sty)
                style_name = Path(cur_sty).name
                msg = f"Waybar failed for {style_name}; restored previous working style"
                if reason:
                    msg += f" ({reason})"
                self._toast(msg, timeout=4)
        elif cur_bar and bar_paths_changed:
            ok = apply_waybar(True, cur_cfg, cur_sty, restart=True)
            if not ok:
                set_nested(self._config, ["components", "bar", "waybarConfig"], prev_cfg_raw)
                set_nested(self._config, ["components", "bar", "waybarStyle"], prev_sty_raw)
                sync_waybar_links(prev_cfg, prev_sty)
                apply_waybar(True, prev_cfg, prev_sty, restart=True)
                save_json(CONFIG_PATH, self._config)
                reason = _waybar_last_error_summary(style_path=cur_sty)
                style_name = Path(cur_sty).name
                msg = f"Selected style failed: {style_name}; reverted to previous working style"
                if reason:
                    msg += f" ({reason})"
                self._toast(msg, timeout=4)

        if (get_nested(self._config, ["power", "deviceType"], "auto") != prev_pow_t or
                get_nested(self._config, ["power", "profile"], "performance") != prev_pow_p):
            apply_power_profile()

        cur_opt = bool(get_nested(self._config, ["optimization", "enabled"], False))
        cur_visual_toggles = _visual_toggles_from_config(self._config)
        if cur_visual_toggles != prev_visual_toggles:
            apply_visual_toggles(self._config)

        if cur_opt != prev_opt and cur_opt:
                self._toast("Optimization mode active: only wallpapers remain enabled")

        if _sync_userdefaults_terminal(self._selected_terminal):
            self._toast(f"Terminal set to {self._selected_terminal}")

        if _sync_envariables_gpu(self._selected_gpu_vendor):
            self._toast(f"GPU preset set to {self._selected_gpu_vendor}")

        if _sync_theme_mode(self._selected_color_mode):
            self._toast(f"System color mode set to {self._selected_color_mode}")
        self._apply_color_mode_style()

        if self._startup_apps:
            _sync_startup_apps(self._startup_apps)

        workspace_rules_changed = False
        if self._workspace_rules:
            workspace_rules_changed = _sync_workspace_rules(self._workspace_rules)
        if workspace_rules_changed:
            apply_hypr_reload()

        cur_idle_enabled = bool(get_nested(self._config, ["hypridle", "enabled"], True))
        cur_idle_warn = max(1, int(get_nested(self._config, ["hypridle", "warnMinutes"], 9) or 9))
        cur_idle_lock = max(1, int(get_nested(self._config, ["hypridle", "lockMinutes"], 10) or 10))
        cur_idle_ignore = bool(get_nested(self._config, ["hypridle", "ignoreDbusInhibit"], False))

        if cur_idle_warn >= cur_idle_lock:
            cur_idle_lock = cur_idle_warn + 1
            set_nested(self._config, ["hypridle", "lockMinutes"], cur_idle_lock)
            save_json(CONFIG_PATH, self._config)
            self._toast("Hypridle lock timeout adjusted to stay after warning")

        idle_changed = (
            cur_idle_enabled != prev_idle_enabled
            or cur_idle_warn != prev_idle_warn
            or cur_idle_lock != prev_idle_lock
            or cur_idle_ignore != prev_idle_ignore
        )

        if idle_changed:
            sync_hypridle_conf(
                warn_seconds=cur_idle_warn * 60,
                lock_seconds=cur_idle_lock * 60,
                ignore_dbus_inhibit=cur_idle_ignore,
            )
            apply_hypridle_enabled(cur_idle_enabled)

        if self._keybinds_all != self._keybinds_saved:
            sys_binds = [b for b in self._keybinds_all if b["source"] == "SYSTEM"]
            usr_binds = [b for b in self._keybinds_all if b["source"] == "USER"]
            KEYBINDS_SYSTEM_PATH.write_text(rebuild_keybind_file(self._keybinds_system_lines, sys_binds))
            KEYBINDS_USER_PATH.write_text(rebuild_keybind_file(self._keybinds_user_lines, usr_binds))
            self._keybinds_saved = deepcopy(self._keybinds_all)
            apply_hypr_reload()

        self._saved_config = deepcopy(self._config)
        self._saved_apps   = deepcopy(self._apps)
        self._saved_skwd_wall_config = deepcopy(self._skwd_wall_config)
        self._suppress_external_reload_until = time.time() + 1.2
        self._mark_saved()
        self._reload_banner.set_revealed(False)
        self._external_conflict_paths = []

        self._toast("Settings saved")

    def _on_discard(self, _widget):
        self._config = deepcopy(self._saved_config)
        self._apps   = deepcopy(self._saved_apps)
        self._skwd_wall_config = deepcopy(self._saved_skwd_wall_config)
        self._keybinds_all = deepcopy(self._keybinds_saved)
        self._selected_terminal = _read_userdefaults_terminal()
        self._selected_compositor = _read_compositor()
        self._selected_gpu_vendor = _read_gpu_vendor()
        self._selected_color_mode = str(get_nested(self._config, ["appearance", "colorMode"], _read_theme_mode()) or "dark")
        self._startup_apps = _parse_startup_apps()
        self._workspace_rules = _parse_workspace_rules()
        self._apply_color_mode_style()
        self._mark_saved()
        self._reload_banner.set_revealed(False)
        self._external_conflict_paths = []
        self._refresh_pages()

    def _on_defaults(self, _widget):
        self._config = deepcopy(self._defaults_config)
        self._apps   = deepcopy(self._defaults_apps)
        self._skwd_wall_config = deepcopy(self._defaults_skwd_wall_config)
        self._selected_terminal = _read_userdefaults_terminal()
        self._selected_compositor = _read_compositor()
        self._selected_gpu_vendor = _read_gpu_vendor()
        self._selected_color_mode = str(get_nested(self._config, ["appearance", "colorMode"], _read_theme_mode()) or "dark")
        self._startup_apps = _parse_startup_apps()
        self._workspace_rules = _parse_workspace_rules()
        self._apply_color_mode_style()
        self._apply_color_mode_style()
        self._mark_unsaved()
        self._refresh_pages()

    def _on_reload_external(self, _widget):
        self._reload_from_disk(self._external_conflict_paths)

    def _update_title(self):
        self.set_title("SdrxDots Settings*" if self._unsaved else "SdrxDots Settings")

    def _toast(self, text: str, timeout: int = 2):
        self._toast_overlay.add_toast(Adw.Toast(title=text, timeout=timeout))
