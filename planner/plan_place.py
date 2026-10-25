#!/usr/bin/env python3
"""Choose a reachable UR3 drop bin with A* and write MTC parameters.

This is a high-level planner. MoveIt still computes and validates the arm's
joint-space trajectory; the A* grid represents clearance around the arm base.
"""

from __future__ import annotations

import argparse
import heapq
import json
import math
from pathlib import Path
import re


RESOLUTION = 0.05
X_MIN, X_MAX = -0.35, 0.55
Y_MIN, Y_MAX = -0.45, 0.45
PICK = (0.36, 0.0)
BINS = {
    "right": (-0.15, -0.25, 0.06),
    "left": (-0.15, 0.25, 0.06),
}
BASE_CLEARANCE = 0.13
STEPS = [
    (dx, dy, math.hypot(dx, dy))
    for dx in (-1, 0, 1)
    for dy in (-1, 0, 1)
    if dx or dy
]


def cell(point: tuple[float, float]) -> tuple[int, int]:
    return (
        round((point[0] - X_MIN) / RESOLUTION),
        round((point[1] - Y_MIN) / RESOLUTION),
    )


def xy(index: tuple[int, int]) -> tuple[float, float]:
    return (
        X_MIN + index[0] * RESOLUTION,
        Y_MIN + index[1] * RESOLUTION,
    )


def clear(index: tuple[int, int]) -> bool:
    x, y = xy(index)
    return (
        X_MIN <= x <= X_MAX
        and Y_MIN <= y <= Y_MAX
        and math.hypot(x, y) >= BASE_CLEARANCE
    )


def astar(start: tuple[float, float], goal: tuple[float, float]):
    origin, target = cell(start), cell(goal)
    if not clear(origin) or not clear(target):
        return None
    frontier = [(0.0, 0.0, origin)]
    best = {origin: 0.0}
    parent = {}
    while frontier:
        _, cost, current = heapq.heappop(frontier)
        if cost > best[current] + 1e-9:
            continue
        if current == target:
            route = [current]
            while route[-1] != origin:
                route.append(parent[route[-1]])
            route.reverse()
            return cost * RESOLUTION, [xy(index) for index in route]
        for dx, dy, step_cost in STEPS:
            neighbor = (current[0] + dx, current[1] + dy)
            if not clear(neighbor):
                continue
            # A diagonal may not cut across the circular base clearance.
            if dx and dy and not (clear((current[0] + dx, current[1]))
                                  and clear((current[0], current[1] + dy))):
                continue
            new_cost = cost + step_cost
            if new_cost + 1e-9 >= best.get(neighbor, math.inf):
                continue
            best[neighbor] = new_cost
            parent[neighbor] = current
            heuristic = math.dist(neighbor, target)
            heapq.heappush(frontier, (new_cost + heuristic, new_cost, neighbor))
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-yaml", type=Path, required=True)
    parser.add_argument("--output-yaml", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--block", choices=BINS, action="append", default=[])
    args = parser.parse_args()

    candidates = []
    for name, pose in BINS.items():
        if name in args.block:
            continue
        result = astar(PICK, pose[:2])
        if result:
            cost, route = result
            candidates.append((cost, name, pose, route))
    if not candidates:
        parser.error("No reachable, unblocked bin")
    cost, name, pose, route = min(candidates, key=lambda item: item[0])

    content = args.base_yaml.read_text()
    replacement = f"place_pose: [{pose[0]}, {pose[1]}, {pose[2]}, 0.0, 0.0, 0.0]"
    content, count = re.subn(r"(?m)^([ \t]*)place_pose: *\[[^\]]+\]",
                             lambda match: match.group(1) + replacement, content)
    if count != 1:
        raise ValueError(f"Expected one place_pose in {args.base_yaml}, found {count}")
    content, count = re.subn(r"(?m)^([ \t]*)force_fallback_scene: (?:true|false)",
                             r"\1force_fallback_scene: true", content)
    if count != 1:
        raise ValueError(f"Expected one force_fallback_scene in {args.base_yaml}, found {count}")
    args.output_yaml.parent.mkdir(parents=True, exist_ok=True)
    args.output_yaml.write_text(content)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps({
        "planner": "A* (8-connected grid)",
        "selected_bin": name,
        "place_pose": pose,
        "estimated_xy_route_m": round(cost, 3),
        "base_clearance_m": BASE_CLEARANCE,
        "route_xy": [[round(x, 3), round(y, 3)] for x, y in route],
        "blocked_bins": args.block,
    }, ensure_ascii=False, indent=2) + "\n")
    print(f"A*: selected {name} bin, estimated XY route {cost:.3f} m")
    print(f"MTC parameters: {args.output_yaml}")


if __name__ == "__main__":
    main()
