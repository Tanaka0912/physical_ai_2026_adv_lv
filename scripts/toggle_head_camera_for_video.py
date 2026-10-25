#!/usr/bin/env python3
"""Temporarily disable the unused RGBD sensor while recording overview video."""

from pathlib import Path
import re
import sys


root = Path(__file__).resolve().parents[1]
target = Path(sys.argv[2]) / "ur_description/urdf/intel_rgbd_cam_d435.urdf.xacro"
backup = root / "video/raw/head_camera_xacro_backup"
mode = sys.argv[1]
if mode == "disable":
    if backup.exists():
        target.write_bytes(backup.read_bytes())
    source = target.read_text()
    replacement, count = re.subn(
        r"\n<gazebo reference=\"\$\{prefix\}camera_head_link\">.*?</gazebo>",
        "\n<!-- RGBD sensor disabled temporarily for overview video recording. -->",
        source,
        flags=re.DOTALL,
    )
    if count != 1:
        raise ValueError(f"Expected one camera sensor block, found {count}")
    backup.parent.mkdir(parents=True, exist_ok=True)
    backup.write_text(source)
    target.write_text(replacement)
elif mode == "restore":
    if backup.exists():
        target.write_bytes(backup.read_bytes())
        backup.unlink()
else:
    raise ValueError("Mode must be disable or restore")
print(f"Head camera: {mode}")
