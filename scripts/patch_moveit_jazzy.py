#!/usr/bin/env python3
"""Convert upstream MoveIt adapter settings to the Jazzy list format."""

from pathlib import Path
import sys


def convert(path: Path) -> None:
    lines = path.read_text().splitlines(keepends=True)
    result = []
    in_adapters = False
    changed = False
    for line in lines:
        if line.startswith("planning_plugin: "):
            result.append("planning_plugins:\n")
            result.append("  - " + line.removeprefix("planning_plugin: "))
            changed = True
        elif line.startswith(("request_adapters: >-", "response_adapters: >-")):
            result.append(line.replace(": >-", ":"))
            in_adapters = True
            changed = True
        elif in_adapters and line.startswith("  default_"):
            result.append("  - " + line[2:])
        else:
            in_adapters = False
            result.append(line)
    content = "".join(result)
    before, separator, after = content.partition("request_adapters:\n")
    if not separator:
        raise ValueError(f"Missing request_adapters in {path}")
    if path.name == "ompl_planning.yaml":
        _, separator, remainder = after.partition("planner_configs:\n")
        if not separator:
            raise ValueError(f"Missing planner_configs in {path}")
        adapters = (
            "request_adapters:\n"
            "  - default_planning_request_adapters/ResolveConstraintFrames\n"
            "  - default_planning_request_adapters/ValidateWorkspaceBounds\n"
            "  - default_planning_request_adapters/CheckStartStateBounds\n"
            "  - default_planning_request_adapters/CheckStartStateCollision\n"
            "response_adapters:\n"
            "  - default_planning_response_adapters/AddTimeOptimalParameterization\n"
            "  - default_planning_response_adapters/ValidateSolution\n"
            "  - default_planning_response_adapters/DisplayMotionPath\n"
        )
        content = before + adapters + "planner_configs:\n" + remainder
    else:
        _, separator, remainder = after.partition("default_planner_config:")
        if not separator:
            raise ValueError(f"Missing default_planner_config in {path}")
        adapters = (
            "request_adapters:\n"
            "  - default_planning_request_adapters/ValidateWorkspaceBounds\n"
            "  - default_planning_request_adapters/CheckStartStateBounds\n"
            "  - default_planning_request_adapters/CheckStartStateCollision\n\n"
        )
        content = before + adapters + "default_planner_config:" + remainder
    if content != path.read_text():
        path.write_text(content)
        changed = True
    print(f"{path}: {'converted' if changed else 'already compatible'}")


root = Path(sys.argv[1])
for name in (
    "ompl_planning.yaml",
    "pilz_industrial_motion_planner_planning.yaml",
):
    convert(root / "moveit_config" / "config" / name)
sensors = root / "moveit_config" / "config" / "sensors_3d.yaml"
if sensors.read_text() != "sensors: []\n":
    sensors.write_text("sensors: []\n")
    print(f"{sensors}: disabled point-cloud octomap for known-object demo")
