#!/usr/bin/env python3
"""Verify that Gazebo's physical cylinder reached the A*-selected bin."""

import json
import math
from pathlib import Path
import subprocess
import sys


root = Path(__file__).resolve().parents[1]
report = json.loads((root / "generated" / "plan.json").read_text())
result = subprocess.run(
    ["gz", "topic", "-e", "-n", "1", "--json-output",
     "-t", "/world/default/pose/info"],
    text=True, capture_output=True, timeout=15, check=True,
)
poses = {item["name"]: item["position"] for item in json.loads(result.stdout)["pose"]}
object_position = poses["red_cylinder"]
bin_position = poses[f"bin_{report['selected_bin']}"]
distance_xy = math.hypot(
    object_position.get("x", 0) - bin_position.get("x", 0),
    object_position.get("y", 0) - bin_position.get("y", 0),
)
height_above_bin = object_position.get("z", 0) - bin_position.get("z", 0)
passed = distance_xy < 0.075 and 0.035 < height_above_bin < 0.17
summary = {
    "selected_bin": report["selected_bin"],
    "object_position_world": object_position,
    "bin_position_world": bin_position,
    "xy_distance_m": round(distance_xy, 4),
    "height_above_bin_m": round(height_above_bin, 4),
    "passed": passed,
}
(root / "generated" / "verification.json").write_text(
    json.dumps(summary, ensure_ascii=False, indent=2) + "\n"
)
print(json.dumps(summary, ensure_ascii=False, indent=2))
sys.exit(0 if passed else 1)
