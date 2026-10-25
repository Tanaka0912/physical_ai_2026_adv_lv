#!/usr/bin/env python3
"""Make Gazebo's cylinder a visual marker driven by the object sync node.

MoveIt retains its own collision object for planning. The upstream Gazebo
cylinder cannot be grasped by the MTC virtual attachment and blocks the
gripper controller when it closes. A static, collision-free visual model
allows the Gazebo marker to follow that attachment without controller stalls.
"""

from pathlib import Path
import re
import sys


path = Path(sys.argv[1]) / "ur_gazebo/models/red_cylinder/model.sdf"
source = path.read_text()
modified = source.replace("<static>false</static>", "<static>true</static>")
modified, count = re.subn(
    r"\s*<collision name=\"collision\">.*?</collision>",
    "",
    modified,
    flags=re.DOTALL,
)
if count not in (0, 1):
    raise ValueError(f"Unexpected collision element count: {count}")
if "<static>true</static>" not in modified or "<visual name=\"visual\">" not in modified:
    raise ValueError(f"Unexpected marker SDF: {path}")
if modified != source:
    path.write_text(modified)
print(f"{path}: visual-only marker ready")
