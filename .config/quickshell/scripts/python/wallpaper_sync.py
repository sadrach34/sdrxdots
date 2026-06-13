#!/usr/bin/env python3
import json
import os
import subprocess
import sys
from pathlib import Path

HOME = Path.home()
CACHE_DIR = HOME / ".cache/skwd-wall"

def get_monitors():
    try:
        out = subprocess.check_output(["hyprctl", "monitors", "-j"])
        return [m["name"] for m in json.loads(out)]
    except Exception:
        # Fallback if hyprctl fails
        return []

def get_awww_state():
    state = {}
    try:
        out = subprocess.check_output(["awww", "query"], text=True)
        for line in out.splitlines():
            # Format: ": DP-1: 1920x1080, scale: 1, currently displaying: image: /path/to/wall.png"
            if "currently displaying: image:" in line:
                # Splitting by colon and spaces is a bit fragile, let's use regex or better split
                # ": DP-1: ..." -> parts[1] is " DP-1"
                parts = line.split(":")
                if len(parts) >= 2:
                    mon = parts[1].strip()
                    if "image:" in line:
                        path = line.split("image:")[1].strip()
                        state[mon] = path
    except Exception:
        pass
    return state

def is_video_running(mon):
    # Check for mpvpaper or linux-wallpaperengine for this monitor
    try:
        # mpvpaper DP-1 ...
        subprocess.check_call(["pgrep", "-f", f"mpvpaper.*{mon}"], stdout=subprocess.DEVNULL)
        return True
    except Exception:
        pass
    try:
        # linux-wallpaperengine ... --screen-root DP-1
        subprocess.check_call(["pgrep", "-f", f"linux-wallpaperengine.*--screen-root {mon}"], stdout=subprocess.DEVNULL)
        return True
    except Exception:
        pass
    return False

def sync():
    monitors = get_monitors()
    if not monitors:
        # Try to find state files if monitors couldn't be detected via hyprctl
        monitors = [f.stem[len("last-wallpaper-"):].replace("_", " ") 
                   for f in CACHE_DIR.glob("last-wallpaper-*.json")]

    awww_state = get_awww_state()
    
    for mon in monitors:
        safe_mon = mon.replace(" ", "_")
        state_file = CACHE_DIR / f"last-wallpaper-{safe_mon}.json"
        
        if not state_file.exists():
            # If no monitor-specific file, check global one if it's a single monitor setup
            if len(monitors) == 1:
                state_file = CACHE_DIR / "last-wallpaper.json"
            else:
                continue
            
        try:
            current_state = json.loads(state_file.read_text())
            st_type = current_state.get("type")
            
            needs_update = False
            new_state = current_state.copy()
            
            if st_type in ["video", "we"]:
                if not is_video_running(mon):
                    # Video/WE supposed to be running but isn't. Fallback to what awww says.
                    if mon in awww_state:
                        new_state = {"type": "static", "path": awww_state[mon]}
                        needs_update = True
                    else:
                        # If awww doesn't know either, we might just leave it or mark as unknown
                        pass
            elif st_type == "static":
                # Static supposed to be running. Check if awww changed externally.
                if mon in awww_state:
                    awww_path = awww_state[mon]
                    current_path = current_state.get("path")
                    # Use realpath to avoid symlink mismatches
                    if os.path.realpath(awww_path) != os.path.realpath(current_path):
                        new_state = {"type": "static", "path": awww_path}
                        needs_update = True
            
            if needs_update:
                # Update both monitor-specific and global if it was global
                state_file.write_text(json.dumps(new_state, indent=2))
                if state_file.name != "last-wallpaper.json" and len(monitors) == 1:
                    (CACHE_DIR / "last-wallpaper.json").write_text(json.dumps(new_state, indent=2))
                
                # Also update symlinks used by other scripts if necessary
                if new_state["type"] == "static":
                    wall_current = HOME / ".config/hypr/wallpaper_effects/.wallpaper_current"
                    try:
                        if os.path.exists(new_state["path"]):
                            if os.path.islink(wall_current):
                                os.unlink(wall_current)
                            os.symlink(new_state["path"], wall_current)
                    except Exception:
                        pass

        except Exception as e:
            # print(f"Error syncing {mon}: {e}", file=sys.stderr)
            pass

if __name__ == "__main__":
    sync()
