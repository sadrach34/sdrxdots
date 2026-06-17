#!/usr/bin/env python3
import json
import os
import subprocess
import re
from pathlib import Path

HOME = Path.home()
CACHE_DIR = HOME / ".cache/skwd-wall"

def get_monitors():
    try:
        out = subprocess.check_output(["hyprctl", "monitors", "-j"])
        return [m["name"] for m in json.loads(out)]
    except Exception:
        return []

def get_running_video_wallpapers():
    # monitor -> path
    video_walls = {}
    try:
        # Check mpvpaper
        ps = subprocess.check_output(["ps", "aux"], text=True)
        for line in ps.splitlines():
            if "mpvpaper" in line and not "grep" in line:
                # Basic parsing for mpvpaper: mpvpaper [options] monitor path
                # Example: mpvpaper -o loop --mute=yes HDMI-A-1 /path/to/wall.mp4
                # We look for the last part which is usually the path, 
                # and the monitor name which is usually before it.
                parts = line.split()
                # Find the monitor name in the command line
                monitors = get_monitors()
                for mon in monitors:
                    if mon in parts:
                        # The path is usually the last argument
                        path = parts[-1]
                        if os.path.exists(path) and (path.endswith(".mp4") or path.endswith(".mkv") or path.endswith(".webm")):
                            video_walls[mon] = path
            
            if "linux-wallpaperengine" in line and not "grep" in line:
                # Example: linux-wallpaperengine ... --screen-root DP-1 ... ID
                match_mon = re.search(r"--screen-root\s+([^\s]+)", line)
                if match_mon:
                    mon = match_mon.group(1).strip('"').strip("'")
                    # For WE, the last arg is usually the ID
                    parts = line.split()
                    we_id = parts[-1]
                    if we_id.isdigit():
                        video_walls[mon] = ("we", we_id)
    except Exception:
        pass
    return video_walls

def get_awww_state():
    state = {}
    try:
        out = subprocess.check_output(["awww", "query"], text=True)
        for line in out.splitlines():
            if "currently displaying: image:" in line:
                parts = line.split(":")
                if len(parts) >= 2:
                    mon = parts[1].strip()
                    path = line.split("image:")[1].strip()
                    state[mon] = path
    except Exception:
        pass
    return state

def sync():
    monitors = get_monitors()
    video_walls = get_running_video_wallpapers()
    awww_state = get_awww_state()
    
    for mon in monitors:
        safe_mon = mon.replace(" ", "_")
        state_file = CACHE_DIR / f"last-wallpaper-{safe_mon}.json"
        
        needs_update = False
        new_state = {}

        # 1. Check if a video/WE is actually running for this monitor
        if mon in video_walls:
            val = video_walls[mon]
            if isinstance(val, tuple) and val[0] == "we":
                new_state = {"type": "we", "we_id": val[1]}
            else:
                new_state = {"type": "video", "path": val}
            needs_update = True
        # 2. If no video, check what awww (static) is displaying
        elif mon in awww_state:
            new_state = {"type": "static", "path": awww_state[mon]}
            needs_update = True
        
        if needs_update:
            # Check if current state file matches
            current_state = {}
            if state_file.exists():
                try:
                    current_state = json.loads(state_file.read_text())
                except: pass
            
            # Simple deep compare
            if json.dumps(new_state, sort_keys=True) != json.dumps(current_state, sort_keys=True):
                state_file.write_text(json.dumps(new_state, indent=2))
                
                # Update global if single monitor
                if len(monitors) == 1:
                    (CACHE_DIR / "last-wallpaper.json").write_text(json.dumps(new_state, indent=2))
                
                # Update .wallpaper_current symlink for static walls
                if new_state.get("type") == "static":
                    wall_current = HOME / ".config/hypr/wallpaper_effects/.wallpaper_current"
                    try:
                        path = new_state.get("path")
                        if path and os.path.exists(path):
                            if os.path.islink(wall_current): os.unlink(wall_current)
                            os.symlink(path, wall_current)
                    except: pass

if __name__ == "__main__":
    sync()
