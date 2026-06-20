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
        out = subprocess.check_output(["hyprctl", "monitors", "-j"], text=True)
        return [m["name"] for m in json.loads(out)]
    except Exception:
        return []

def get_running_video_wallpapers():
    # monitor -> state_dict or path
    video_walls = {}
    monitors = get_monitors()
    
    # Use pgrep -af for reliable command line retrieval
    try:
        ps_out = subprocess.check_output(["ps", "auxw"], text=True)
        lines = ps_out.splitlines()
        
        # Check mpvpaper
        for line in lines:
            if "mpvpaper" in line and not "grep" in line:
                for mon in monitors:
                    # Look for monitor name with spaces around it or at start/end of a part
                    if re.search(rf"\s+{re.escape(mon)}(\s+|$)", line):
                        # Extract path: it's usually at the end, but can have spaces.
                        # mpvpaper [args] monitor path
                        # We try to find the part after the monitor name
                        parts = re.split(rf"\s+{re.escape(mon)}\s+", line)
                        if len(parts) > 1:
                            path = parts[-1].split(" </dev/null")[0].strip()
                            if os.path.exists(path):
                                # Check if it's a WE workshop video
                                we_match = re.search(r"workshop/content/431960/(\d+)", path)
                                if we_match:
                                    video_walls[mon] = {"type": "we", "we_id": we_match.group(1)}
                                else:
                                    video_walls[mon] = {"type": "video", "path": path}
            
            # Check linux-wallpaperengine
            if "linux-wallpaperengine" in line and not "grep" in line:
                match_mon = re.search(r"--screen-root\s+([^\s]+)", line)
                if match_mon:
                    mon = match_mon.group(1).strip('"').strip("'")
                    # ID is usually the last argument
                    parts = line.split()
                    we_id = parts[-1]
                    if we_id.isdigit():
                        video_walls[mon] = {"type": "we", "we_id": we_id}
    except Exception as e:
        print(f"Error detection: {e}")
        pass
    return video_walls

def get_awww_state():
    state = {}
    try:
        # awww query output format:
        # : DP-1: 1920x1080, scale: 1, currently displaying: image: /path/to/wall.webp
        out = subprocess.check_output(["awww", "query"], text=True)
        for line in out.splitlines():
            if "currently displaying: image:" in line:
                # Split by colons and handle the leading colon if present
                line_parts = line.strip().split(":")
                # After strip() and split(':'), we might have:
                # ['', ' DP-1', ' 1920x1080, scale', ' 1, currently displaying', ' image', ' /path/to/wall.webp']
                # OR if no leading colon:
                # ['DP-1', ' 1920x1080, scale', ' 1, currently displaying', ' image', ' /path/to/wall.webp']
                
                mon = ""
                if line_parts[0] == "" and len(line_parts) > 1:
                    mon = line_parts[1].strip()
                else:
                    mon = line_parts[0].strip()
                
                if mon:
                    path_parts = line.split("image:")
                    if len(path_parts) > 1:
                        path = path_parts[1].strip()
                        state[mon] = path
    except Exception:
        pass
    return state

def sync():
    monitors = get_monitors()
    video_walls = get_running_video_wallpapers()
    awww_state = get_awww_state()
    
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR, exist_ok=True)
    
    for mon in monitors:
        safe_mon = mon.replace(" ", "_")
        state_file = CACHE_DIR / f"last-wallpaper-{safe_mon}.json"
        
        needs_update = False
        new_state = {}

        # 1. Check if a video/WE is actually running for this monitor
        if mon in video_walls:
            new_state = video_walls[mon]
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
                
                # Update global if single monitor or this is the focused monitor?
                # For now, let's keep the single monitor logic or update global with focused monitor
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
