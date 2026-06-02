from config_panel_constants import *

_LAST_WAYBAR_LOG_POS = 0
_LAST_WAYBAR_STYLE = ""


# ── Keybind helpers ───────────────────────────────────────────────────────────

def _auto_description(dispatcher: str, arg: str) -> str:
    d = (dispatcher or "").lower().strip()
    a = (arg or "").strip()
    if d == "exec":
        if "kitty" in a or "$term" in a: return "Open terminal"
        if "firefox" in a: return "Open Firefox"
        if "screenshot" in a or "ScreenShot" in a: return "Screenshot"
        if "windowswitcher" in a: return "Window switcher"
        if "applauncher" in a: return "App launcher"
        if "config toggle" in a: return "Config panel"
        return "Run command"
    if d == "killactive": return "Close window"
    if d == "workspace": return "Switch workspace"
    if d == "movefocus": return "Move focus"
    if d == "fullscreen": return "Toggle fullscreen"
    if d == "togglefloating": return "Toggle floating"
    return dispatcher or "Custom bind"

def _split_spec(spec: str) -> list[str]:
    out, current = [], ""
    for ch in spec:
        if ch == "," and len(out) < 3:
            out.append(current.strip())
            current = ""
        else:
            current += ch
    out.append(current.strip())
    return out

def _is_bind_line(line: str) -> bool:
    return bool(re.match(r'^(#\s*)?(bind[a-z]*)\s*=\s*', line.strip(), re.I))

def _parse_keybinds(text: str, source_tag: str) -> list[dict]:
    binds = []
    for i, original in enumerate(text.splitlines()):
        trimmed = original.strip()
        if not trimmed:
            continue
        commented = trimmed.startswith("#")
        parse = re.sub(r'^#\s*', '', trimmed) if commented else trimmed
        m = re.match(r'^(bind[a-z]*)\s*=\s*(.+)$', parse, re.I)
        if not m:
            continue
        bind_type, spec = m.group(1), m.group(2)
        description = ""
        if "#" in spec:
            idx = spec.index("#")
            description = spec[idx+1:].strip()
            spec = spec[:idx].strip()
        parts = _split_spec(spec)
        if len(parts) < 3:
            continue
        mods, key, dispatcher = parts[0], parts[1], parts[2]
        arg = ", ".join(parts[3:]) if len(parts) > 3 else ""
        binds.append({
            "uid": f"{source_tag}:{i}",
            "source": source_tag,
            "line_index": i,
            "enabled": not commented,
            "type": bind_type,
            "mods": mods.strip(),
            "key": key.strip(),
            "dispatcher": dispatcher.strip(),
            "arg": arg.strip(),
            "description": description or _auto_description(dispatcher, arg),
        })
    return binds

def _compose_bind_line(bind: dict) -> str:
    line = f"{bind['type']} = {bind['mods']}, {bind['key']}, {bind['dispatcher']}"
    if bind["arg"]:
        line += f", {bind['arg']}"
    if bind["description"]:
        line += f" # {bind['description']}"
    return ("# " if not bind["enabled"] else "") + line

def rebuild_keybind_file(original_lines: list[str], binds: list[dict]) -> str:
    keep = [l for l in original_lines if not _is_bind_line(l)]
    while keep and not keep[-1].strip():
        keep.pop()
    bind_lines = [_compose_bind_line(b) for b in binds]
    if bind_lines and keep:
        keep.append("")
    return "\n".join(keep + bind_lines) + "\n"


# ── Apply side effects ────────────────────────────────────────────────────────

def _run(cmd, shell=False):
    try:
        subprocess.Popen(cmd, shell=shell, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass

def _run_wait(cmd, shell=False):
    try:
        subprocess.run(cmd, shell=shell, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass

def _is_waybar_running() -> bool:
    try:
        return subprocess.run(
            ["pgrep", "-x", "waybar"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        ).returncode == 0
    except Exception:
        return False

def _start_waybar_checked(
    cfg_path: str,
    style_path: str,
    timeout_sec: float = 5.0,
    stable_sec: float = 1.8,
) -> bool:
    global _LAST_WAYBAR_LOG_POS, _LAST_WAYBAR_STYLE
    try:
        WAYBAR_STARTUP_LOG.parent.mkdir(parents=True, exist_ok=True)
        try:
            _LAST_WAYBAR_LOG_POS = WAYBAR_STARTUP_LOG.stat().st_size
        except Exception:
            _LAST_WAYBAR_LOG_POS = 0
        _LAST_WAYBAR_STYLE = style_path
        with WAYBAR_STARTUP_LOG.open("a", encoding="utf-8") as logf:
            proc = subprocess.Popen(
                ["waybar", "-c", cfg_path, "-s", style_path],
                stdout=logf,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
    except Exception:
        return False

    start_ts = time.time()
    first_seen_ts = None
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        running = _is_waybar_running()

        # Some environments can make the parent process exit while Waybar keeps
        # running in a child/session. Only fail when BOTH are not alive.
        if proc.poll() is not None and not running:
            return False

        if running and first_seen_ts is None:
            first_seen_ts = time.time()

        # Require the process to remain alive for a short grace period.
        if running and first_seen_ts is not None and (time.time() - first_seen_ts) >= stable_sec:
            return True

        # Hard guard: if process never appeared quickly enough, fail fast.
        if first_seen_ts is None and (time.time() - start_ts) > timeout_sec:
            return False

        time.sleep(0.1)
    return _is_waybar_running() and proc.poll() is None

def _waybar_last_error_summary(max_lines: int = 160, style_path: str = "") -> str:
    try:
        if not WAYBAR_STARTUP_LOG.exists():
            return ""

        start_pos = _LAST_WAYBAR_LOG_POS if _LAST_WAYBAR_LOG_POS >= 0 else 0
        with WAYBAR_STARTUP_LOG.open("rb") as fh:
            fh.seek(start_pos)
            chunk = fh.read()
        text = chunk.decode("utf-8", errors="ignore")
        lines = text.splitlines()
        tail = lines[-max_lines:] if len(lines) > max_lines else lines

        style_hint = Path(style_path or _LAST_WAYBAR_STYLE).name.strip().lower()

        if style_hint:
            for line in reversed(tail):
                line_s = line.strip()
                if "[error]" in line_s and style_hint in line_s.lower():
                    msg = line_s.split("[error]", 1)[-1].strip()
                    return msg[:180]

        for line in reversed(tail):
            line_s = line.strip()
            if "[error]" in line_s:
                # Keep the part after [error] when present.
                msg = line_s.split("[error]", 1)[-1].strip()
                return msg[:180]
        return ""
    except Exception:
        return ""

def apply_waybar(enabled: bool, cfg_path: str, style_path: str, restart: bool = False):
    if enabled:
        if restart:
            # Stop must be synchronous; async pkill can kill the new process.
            _run_wait("pkill -x waybar || true", shell=True)
            return _start_waybar_checked(cfg_path, style_path)
        else:
            if _is_waybar_running():
                return True
            return _start_waybar_checked(cfg_path, style_path)
    else:
        _run_wait("pkill -x waybar || true", shell=True)
        return True

def sync_waybar_links(cfg_path: str, style_path: str):
    _run(f"ln -sf {json.dumps(cfg_path)} {json.dumps(str(WAYBAR_CONFIG_LINK))}", shell=True)
    _run(f"ln -sf {json.dumps(style_path)} {json.dumps(str(WAYBAR_STYLE_LINK))}", shell=True)

def apply_power_profile():
    if POWER_SCRIPT.exists():
        _run([str(POWER_SCRIPT)])

def _visual_toggles_from_config(config: dict) -> dict:
    return {
        "disableBorders": bool(get_nested(config, ["optimization", "toggles", "disableBorders"], False)),
        "disableTransparency": bool(get_nested(config, ["optimization", "toggles", "disableTransparency"], False)),
        "disableAnimations": bool(get_nested(config, ["optimization", "toggles", "disableAnimations"], False)),
        "disableBlur": bool(get_nested(config, ["optimization", "toggles", "disableBlur"], False)),
        "disableShadows": bool(get_nested(config, ["optimization", "toggles", "disableShadows"], False)),
        "disableRounding": bool(get_nested(config, ["optimization", "toggles", "disableRounding"], False)),
        "disableGaps": bool(get_nested(config, ["optimization", "toggles", "disableGaps"], False)),
        "disableDimInactive": bool(get_nested(config, ["optimization", "toggles", "disableDimInactive"], False)),
    }


def apply_visual_toggles(config: dict):
    toggles = _visual_toggles_from_config(config)

    animations_enabled = 0 if toggles["disableAnimations"] else 1
    blur_enabled = 0 if toggles["disableBlur"] else 1
    shadow_enabled = 0 if toggles["disableShadows"] else 1
    dim_inactive = 0 if toggles["disableDimInactive"] else 1
    inactive_opacity = 1.0 if toggles["disableTransparency"] else 0.9
    gaps_in = 0 if toggles["disableGaps"] else 2
    gaps_out = 0 if toggles["disableGaps"] else 4
    border_size = 0 if toggles["disableBorders"] else 2
    rounding = 0 if toggles["disableRounding"] else 10

    batch = (
        f"keyword animations:enabled {animations_enabled};"
        f"keyword decoration:blur:enabled {blur_enabled};"
        f"keyword decoration:shadow:enabled {shadow_enabled};"
        f"keyword decoration:dim_inactive {dim_inactive};"
        "keyword decoration:active_opacity 1.0;"
        f"keyword decoration:inactive_opacity {inactive_opacity};"
        f"keyword general:gaps_in {gaps_in};"
        f"keyword general:gaps_out {gaps_out};"
        f"keyword general:border_size {border_size};"
        f"keyword decoration:rounding {rounding}"
    )
    _run(["hyprctl", "--batch", batch])


def _snapshot_component_state(config: dict) -> dict:
    return {
        "barEnabled": bool(get_nested(config, ["components", "bar", "enabled"], True)),
        "appLauncher": bool(get_nested(config, ["components", "appLauncher"], True)),
        "windowSwitcher": bool(get_nested(config, ["components", "windowSwitcher"], True)),
        "notifications": bool(get_nested(config, ["components", "notifications"], True)),
        "lockscreen": bool(get_nested(config, ["components", "lockscreen"], False)),
        "smartHome": bool(get_nested(config, ["components", "smartHome"], False)),
        "powerMenu": bool(get_nested(config, ["components", "powerMenu", "enabled"], True)),
        "wallpaperSelector": bool(get_nested(config, ["components", "wallpaperSelector", "enabled"], True)),
    }


def _apply_optimization_component_mode(config: dict, enabled: bool) -> bool:
    changed = False
    saved_state = get_nested(config, ["optimization", "restoreState"], None)

    if enabled:
        if not isinstance(saved_state, dict):
            set_nested(config, ["optimization", "restoreState"], _snapshot_component_state(config))
            changed = True

        desired = {
            ("components", "bar", "enabled"): False,
            ("components", "appLauncher"): False,
            ("components", "windowSwitcher"): False,
            ("components", "notifications"): False,
            ("components", "lockscreen"): False,
            ("components", "smartHome"): False,
            ("components", "powerMenu", "enabled"): False,
            ("components", "wallpaperSelector", "enabled"): True,
        }
        for key_path, value in desired.items():
            current = get_nested(config, list(key_path), None)
            if current != value:
                set_nested(config, list(key_path), value)
                changed = True
        return changed

    if isinstance(saved_state, dict):
        restore_map = {
            ("components", "bar", "enabled"): bool(saved_state.get("barEnabled", True)),
            ("components", "appLauncher"): bool(saved_state.get("appLauncher", True)),
            ("components", "windowSwitcher"): bool(saved_state.get("windowSwitcher", True)),
            ("components", "notifications"): bool(saved_state.get("notifications", True)),
            ("components", "lockscreen"): bool(saved_state.get("lockscreen", False)),
            ("components", "smartHome"): bool(saved_state.get("smartHome", False)),
            ("components", "powerMenu", "enabled"): bool(saved_state.get("powerMenu", True)),
            ("components", "wallpaperSelector", "enabled"): bool(saved_state.get("wallpaperSelector", True)),
        }
        for key_path, value in restore_map.items():
            current = get_nested(config, list(key_path), None)
            if current != value:
                set_nested(config, list(key_path), value)
                changed = True
        set_nested(config, ["optimization", "restoreState"], None)
        changed = True

    return changed


def apply_hypr_reload():
    _run(["hyprctl", "reload"])

def _replace_timeout_in_listener_block(block: str, seconds: int) -> str:
    return re.sub(
        r'(?m)^(\s*timeout\s*=\s*)\d+(\s*(?:#.*)?)$',
        rf'\g<1>{int(seconds)}\2',
        block,
        count=1,
    )

def sync_hypridle_conf(warn_seconds: int, lock_seconds: int, ignore_dbus_inhibit: bool) -> bool:
    if not HYPRIDLE_CONF_PATH.exists():
        return False

    text = HYPRIDLE_CONF_PATH.read_text()
    changed = False

    listener_re = re.compile(r'(?ms)^\s*listener\s*\{.*?^\s*\}')
    state = {"warn": False, "lock": False}

    def repl(match):
        nonlocal changed
        block = match.group(0)
        lowered = block.lower()

        if ("on-timeout" in lowered and "notify-send" in lowered and not state["warn"]):
            state["warn"] = True
            new_block = _replace_timeout_in_listener_block(block, warn_seconds)
            if new_block != block:
                changed = True
            return new_block

        if ("on-timeout" in lowered and "loginctl lock-session" in lowered and not state["lock"]):
            state["lock"] = True
            new_block = _replace_timeout_in_listener_block(block, lock_seconds)
            if new_block != block:
                changed = True
            return new_block

        return block

    text_after_listeners = listener_re.sub(repl, text)

    ignore_re = re.compile(r'(?m)^(\s*ignore_dbus_inhibit\s*=\s*)(true|false)(\s*(?:#.*)?)$')
    ignore_value = "true" if ignore_dbus_inhibit else "false"
    text_after_ignore, ignore_count = ignore_re.subn(rf'\1{ignore_value}\3', text_after_listeners, count=1)
    if ignore_count > 0 and text_after_ignore != text_after_listeners:
        changed = True

    if changed:
        HYPRIDLE_CONF_PATH.write_text(text_after_ignore)

    return changed

def apply_hypridle_enabled(enabled: bool):
    _run_wait("pkill -x hypridle || true", shell=True)
    if enabled:
        _run(["hypridle"])

def _read_text(path: Path) -> str:
    try:
        return path.read_text()
    except Exception:
        return ""

def _write_text(path: Path, text: str):
    path.write_text(text if text.endswith("\n") else text + "\n")

def _detect_terminals() -> list[str]:
    detected = []
    for terminal in KNOWN_TERMINALS:
        if subprocess.run(["bash", "-lc", f"command -v {terminal} >/dev/null 2>&1"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
            detected.append(terminal)
    if "kitty" not in detected:
        detected.insert(0, "kitty")
    return detected

def _sync_userdefaults_terminal(terminal: str) -> bool:
    text = _read_text(USER_DEFAULTS_PATH)
    if not text:
        return False
    current = _read_userdefaults_terminal()
    if current == terminal:
        return False
    new_text, count = re.subn(r'(?m)^(\$term\s*=\s*).*$' , rf'\1{terminal}', text, count=1)
    if count:
        _write_text(USER_DEFAULTS_PATH, new_text)
        return True
    return False

def _read_userdefaults_terminal() -> str:
    text = _read_text(USER_DEFAULTS_PATH)
    match = re.search(r'(?m)^\$term\s*=\s*(.+?)\s*$', text)
    return match.group(1).strip() if match else "kitty"

def _read_compositor() -> str:
    value = get_nested(load_json(CONFIG_PATH), ["compositor"], "hyprland")
    return str(value or "hyprland")

def _read_theme_mode() -> str:
    try:
        value = THEME_MODE_PATH.read_text().strip().lower()
        return value if value in {"dark", "light"} else "dark"
    except Exception:
        return "dark"

def _sync_theme_mode(mode: str) -> bool:
    mode = (mode or "dark").strip().lower()
    if mode not in {"dark", "light"}:
        mode = "dark"
    current = _read_theme_mode()
    THEME_MODE_PATH.parent.mkdir(parents=True, exist_ok=True)
    if current == mode:
        THEME_MODE_PATH.write_text(mode + "\n")
        return False
    opposite = "light" if mode == "dark" else "dark"
    THEME_MODE_PATH.write_text(opposite + "\n")
    script = HOME / ".config/hypr/scripts/DarkLight.sh"
    if script.exists():
        _run([str(script)])
        return True
    THEME_MODE_PATH.write_text(mode + "\n")
    return False

def _read_gpu_vendor() -> str:
    text = _read_text(ENV_VARIABLES_PATH).lower()
    if "nvidia" in text:
        return "nvidia"
    if "amdgpu" in text or "amd" in text:
        return "amd"
    if "iHD".lower() in text or "intel" in text:
        return "intel"
    return "auto"

def _sync_envariables_gpu(vendor: str) -> bool:
    text = _read_text(ENV_VARIABLES_PATH)
    if not text:
        return False
    if _read_gpu_vendor() == vendor:
        return False

    lines = text.splitlines()
    preserved = []
    for line in lines:
        if any(key in line for key in ["LIBVA_DRIVER_NAME", "__GLX_VENDOR_LIBRARY_NAME", "NVD_BACKEND", "VDPAU_DRIVER", "GBM_BACKEND", "WLR_RENDERER_ALLOW_SOFTWARE"]):
            continue
        preserved.append(line)

    additions = GPU_PRESET_ENV.get(vendor, GPU_PRESET_ENV["auto"])
    if additions:
        preserved.append("")
        preserved.extend(additions)

    _write_text(ENV_VARIABLES_PATH, "\n".join(preserved))
    return True

def _parse_startup_apps() -> list[dict]:
    text = _read_text(STARTUP_APPS_PATH)
    apps = []
    system_tokens = [
        "dbus-update-activation-environment",
        "systemctl --user import-environment",
        "xdg-desktop-portal-hyprland",
        "xdg-desktop-portal-gtk",
        "Polkit.sh",
        "PortalRestart.sh",
        "StartQuickshell.sh",
        "PowerProfileAuto.sh",
        "waybar",
        "hypridle",
        "wl-paste",
        "pkill firefox",
    ]
    for idx, line in enumerate(text.splitlines()):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if not stripped.startswith("exec-once"):
            continue
        cmd = stripped.split("=", 1)[1].strip() if "=" in stripped else ""
        if not cmd:
            continue
        is_system = any(token in cmd for token in system_tokens)
        apps.append({"index": idx, "cmd": cmd, "enabled": True, "system": is_system})
    return apps

def _sync_startup_apps(apps: list[dict]) -> bool:
    text = _read_text(STARTUP_APPS_PATH)
    if not text:
        return False
    out_lines = text.splitlines()
    changed = False
    for app in apps:
        idx = app.get("index")
        if idx is None or idx < 0 or idx >= len(out_lines):
            continue
        prefix = "" if app.get("enabled", True) else "# "
        new_line = f"{prefix}exec-once = {app['cmd']}"
        if out_lines[idx] != new_line:
            out_lines[idx] = new_line
            changed = True
    if changed:
        _write_text(STARTUP_APPS_PATH, "\n".join(out_lines))
    return changed

def _parse_workspace_rules() -> list[dict]:
    text = _read_text(WINDOW_RULES_PATH)
    rules = []
    for idx, line in enumerate(text.splitlines()):
        stripped = line.strip()
        if not stripped.startswith("windowrule"):
            continue
        if "workspace" not in stripped or "match:class" not in stripped and "match:tag" not in stripped:
            continue
        match = re.search(r'workspace\s+([^,\s]+)(?:\s+(silent))?,\s*match:(?:class|tag)\s+(.+)$', stripped)
        if not match:
            continue
        workspace = match.group(1).strip()
        modifier = match.group(2).strip() if match.group(2) else ""
        selector = match.group(3).strip()
        rules.append({"index": idx, "workspace": workspace, "modifier": modifier, "selector": selector, "line": line})
    return rules

def _sync_workspace_rules(rules: list[dict]) -> bool:
    text = _read_text(WINDOW_RULES_PATH)
    if not text:
        return False
    out_lines = text.splitlines()
    changed = False
    for rule in rules:
        idx = rule.get("index")
        if idx is None or idx < 0 or idx >= len(out_lines):
            continue
        line = out_lines[idx]
        workspace = str(rule.get("workspace", "1")).strip() or "1"
        modifier = str(rule.get("modifier", "")).strip()
        selector = str(rule.get("selector", "")).strip()
        if not selector:
            continue
        if "match:tag" in line:
            suffix = f" {modifier}" if modifier else ""
            new_line = re.sub(r'workspace\s+[^,]+,\s*match:tag\s+.+$', f'workspace {workspace}{suffix}, match:tag {selector}', line)
        else:
            suffix = f" {modifier}" if modifier else ""
            new_line = re.sub(r'workspace\s+[^,]+,\s*match:class\s+.+$', f'workspace {workspace}{suffix}, match:class {selector}', line)
        if new_line != line:
            out_lines[idx] = new_line
            changed = True
    if changed:
        _write_text(WINDOW_RULES_PATH, "\n".join(out_lines))
    return changed
