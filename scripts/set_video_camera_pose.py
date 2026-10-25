#!/usr/bin/env python3
"""Choose an overview angle that reveals the selected destination bin."""

from pathlib import Path
import re
import sys


root = Path(__file__).resolve().parents[1]
mode = sys.argv[1]
path = Path(sys.argv[2]) / "ur_gazebo/worlds/pick_and_place_demo.world"
backup = root / "video/raw/overview_world_backup"
if mode in ("right", "left"):
    if backup.exists():
        path.write_bytes(backup.read_bytes())
    source = path.read_text()
    backup.parent.mkdir(parents=True, exist_ok=True)
    backup.write_text(source)
    pose = ("0.85 -1.25 1.95 0 0.53 2.17" if mode == "right"
            else "0.85 1.25 1.95 0 0.53 -2.17")
    pattern = r'(<model name="demo_overview_camera">\s*<static>true</static>\s*)<pose>[^<]+</pose>'
    result, count = re.subn(pattern, rf"\g<1><pose>{pose}</pose>", source)
    if count != 1:
        raise ValueError(f"Expected one overview camera model, found {count}")
    path.write_text(result)
elif mode == "restore":
    if backup.exists():
        path.write_bytes(backup.read_bytes())
        backup.unlink()
else:
    raise ValueError("Mode must be left, right or restore")
print(f"Overview camera: {mode}")
