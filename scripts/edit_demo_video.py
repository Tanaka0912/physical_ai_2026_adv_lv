#!/usr/bin/env python3
"""Assemble verified Gazebo takes into a captioned 1-3 minute demo video."""

from __future__ import annotations

import json
import math
from pathlib import Path
import re

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "video/raw"
OUTPUT = ROOT / "output"
SIZE = (1280, 720)
FPS = 20
FONT_PATH = "/mnt/c/Windows/Fonts/meiryo.ttc"
FONT_BIG = ImageFont.truetype(FONT_PATH, 58)
FONT_TITLE = ImageFont.truetype(FONT_PATH, 35)
FONT_MEDIUM = ImageFont.truetype(FONT_PATH, 26)
FONT_SMALL = ImageFont.truetype(FONT_PATH, 20)
FONT_TINY = ImageFont.truetype(FONT_PATH, 16)
BG = (13, 22, 34)
PANEL = (23, 38, 55)
WHITE = (239, 246, 251)
MUTED = (159, 179, 194)
CYAN = (77, 210, 225)
ORANGE = (255, 145, 83)
COLORS = {"right": (76, 211, 159), "left": (111, 165, 255)}
LABELS = {"right": "右ビン", "left": "左ビン"}


def text(draw, xy, value, font=FONT_MEDIUM, fill=WHITE):
    draw.text(xy, value, font=font, fill=fill)


def background():
    image = Image.new("RGB", SIZE, BG)
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, SIZE[0], 7), fill=CYAN)
    return image, draw


def route_map(draw, plan, box):
    x0, y0, width, height = box
    draw.rounded_rectangle((x0, y0, x0 + width, y0 + height), radius=15,
                           fill=(16, 29, 43), outline=(48, 74, 91), width=2)
    margin = 17
    xmin, xmax, ymin, ymax = -0.35, 0.55, -0.45, 0.45

    def point(x, y):
        return (
            int(x0 + margin + (x - xmin) / (xmax - xmin) * (width - 2 * margin)),
            int(y0 + margin + (ymax - y) / (ymax - ymin) * (height - 2 * margin)),
        )

    for step in range(1, 8):
        gx = x0 + margin + step * (width - 2 * margin) / 8
        gy = y0 + margin + step * (height - 2 * margin) / 8
        draw.line((gx, y0 + margin, gx, y0 + height - margin), fill=(33, 52, 67))
        draw.line((x0 + margin, gy, x0 + width - margin, gy), fill=(33, 52, 67))
    base = point(0, 0)
    radius = int(plan["base_clearance_m"] / (xmax - xmin) * (width - 2 * margin))
    draw.ellipse((base[0] - radius, base[1] - radius,
                  base[0] + radius, base[1] + radius),
                 fill=(49, 57, 68), outline=(107, 117, 128), width=2)
    route = [point(*xy) for xy in plan["route_xy"]]
    if len(route) > 1:
        draw.line(route, fill=CYAN, width=5, joint="curve")
    for name, y in (("right", -0.25), ("left", 0.25)):
        bx, by = point(-0.15, y)
        color = COLORS[name]
        draw.rounded_rectangle((bx - 8, by - 8, bx + 8, by + 8), radius=3,
                               fill=color if plan["selected_bin"] == name else (75, 91, 105))
    px, py = point(0.36, 0.0)
    draw.ellipse((px - 8, py - 8, px + 8, py + 8), fill=ORANGE)


def center_text(draw, y, value, font, fill=WHITE):
    bounds = draw.textbbox((0, 0), value, font=font)
    x = (SIZE[0] - (bounds[2] - bounds[0])) // 2
    text(draw, (x, y), value, font, fill)


def title_frame():
    image, draw = background()
    center_text(draw, 142, "PAI 最終課題", FONT_TITLE, CYAN)
    center_text(draw, 228, "UR3 Pick & Place", FONT_BIG)
    center_text(draw, 333, "A* で配置先を選び、左右のビンへ搬送", FONT_TITLE)
    center_text(draw, 500, "ROS 2 Jazzy  /  Gazebo Harmonic  /  MoveIt Task Constructor", FONT_SMALL, MUTED)
    center_text(draw, 543, "追加学習・外部 API なし  |  等速再生", FONT_SMALL, MUTED)
    return image


def plan_frame(plan, name):
    image, draw = background()
    color = COLORS[name]
    text(draw, (72, 56), "A* 配置先計画", FONT_TITLE, CYAN)
    if name == "right":
        text(draw, (72, 123), "通常条件", FONT_MEDIUM, MUTED)
    else:
        text(draw, (72, 123), "条件変更: 右ビンを使用不可", FONT_MEDIUM, MUTED)
    text(draw, (72, 199), LABELS[name] + "を選択", FONT_BIG, color)
    text(draw, (72, 315), f"推定 XY 経路長  {plan['estimated_xy_route_m']:.3f} m", FONT_MEDIUM)
    text(draw, (72, 362), "アーム基部の占有領域を避けて探索", FONT_MEDIUM, MUTED)
    text(draw, (72, 575), "A* は配置先を決定。関節軌道は MoveIt が計画・検証します。", FONT_SMALL, MUTED)
    route_map(draw, plan, (809, 146, 360, 360))
    return image


def clip_template(plan, name, status):
    image, draw = background()
    draw.rounded_rectangle((28, 84, 992, 628), radius=13, fill=(4, 10, 16))
    draw.rounded_rectangle((1007, 84, 1252, 628), radius=13, fill=PANEL)
    text(draw, (32, 25), "UR3 Pick & Place  |  Gazebo 実行映像", FONT_MEDIUM)
    text(draw, (1023, 103), "TARGET", FONT_SMALL, MUTED)
    text(draw, (1023, 142), LABELS[name], FONT_TITLE, COLORS[name])
    text(draw, (1023, 208), "A* ROUTE", FONT_TINY, MUTED)
    route_map(draw, plan, (1021, 243, 217, 217))
    text(draw, (1023, 485), f"{plan['estimated_xy_route_m']:.3f} m", FONT_MEDIUM)
    text(draw, (1023, 540), "推論のみ", FONT_SMALL, CYAN)
    text(draw, (1023, 570), "ローカル実行", FONT_SMALL, CYAN)
    draw.rounded_rectangle((28, 647, 1252, 702), radius=10, fill=PANEL)
    text(draw, (48, 660), status, FONT_MEDIUM)
    return np.asarray(image)[:, :, ::-1].copy()


def final_frame(right, left):
    image, draw = background()
    center_text(draw, 78, "実行結果", FONT_BIG)
    draw.rounded_rectangle((145, 202, 1135, 498), radius=20, fill=PANEL)
    text(draw, (201, 239), "配置先", FONT_MEDIUM, MUTED)
    text(draw, (485, 239), "MTC 実行", FONT_MEDIUM, MUTED)
    text(draw, (778, 239), "Gazebo 座標", FONT_MEDIUM, MUTED)
    for row, (name, result) in enumerate((("right", right), ("left", left))):
        y = 314 + row * 87
        text(draw, (201, y), LABELS[name], FONT_TITLE, COLORS[name])
        text(draw, (507, y), "成功", FONT_TITLE, COLORS[name])
        text(draw, (777, y), f"XY {result['xy_distance_m'] * 100:.1f} cm", FONT_MEDIUM, COLORS[name])
    center_text(draw, 539, "円柱中心の高さ: ビン基準 7 cm", FONT_MEDIUM)
    center_text(draw, 608, "Gazebo 円柱は MoveIt の把持を可視化したマーカーです。", FONT_SMALL, MUTED)
    return image


def event_time(path, phrase):
    for line in path.read_text().splitlines():
        if phrase in line:
            match = re.search(r"\[(\d{10}\.\d+)\]", line)
            if match:
                return float(match.group(1))
    raise ValueError(f"Event {phrase!r} missing from {path}")


def write_still(writer, image, seconds):
    frame = cv2.cvtColor(np.asarray(image), cv2.COLOR_RGB2BGR)
    for _ in range(round(seconds * FPS)):
        writer.write(frame)


def write_clip(writer, name, plan):
    source = RAW / f"{name}.mp4"
    metadata = json.loads(source.with_suffix(".json").read_text())
    baseline = RAW / f"{name}_baseline.log"
    sync = RAW / f"{name}_object_sync.log"
    start_epoch = event_time(baseline, "Task planning succeeded") - 2.0
    end_epoch = event_time(baseline, "Task executed successfully") + 2.0
    close_epoch = event_time(sync, "Gripper closed")
    open_epoch = event_time(sync, "Gripper opened")
    start_seconds = max(0.0, start_epoch - metadata["start_wall_time"])
    end_seconds = min(metadata["frames_written"] / metadata["fps"],
                      end_epoch - metadata["start_wall_time"])
    if end_seconds - start_seconds < 22:
        raise ValueError(f"Recording did not cover the complete {name} task")
    templates = {
        "approach": clip_template(plan, name, "01  ピック位置へ接近"),
        "carry": clip_template(plan, name, "02  円柱を把持して搬送"),
        "place": clip_template(plan, name, f"03  {LABELS[name]}へ配置"),
    }
    capture = cv2.VideoCapture(str(source))
    if not capture.isOpened():
        raise RuntimeError(f"Cannot read {source}")
    first_index = int(math.floor(start_seconds * metadata["fps"]))
    capture.set(cv2.CAP_PROP_POS_FRAMES, first_index)
    current_index = first_index - 1
    camera_frame = None
    count = round((end_seconds - start_seconds) * FPS)
    try:
        for output_index in range(count):
            t = start_seconds + output_index / FPS
            wanted_index = int(t * metadata["fps"])
            while current_index < wanted_index:
                ok, camera_frame = capture.read()
                if not ok:
                    raise RuntimeError(f"Raw recording ended early: {source}")
                current_index += 1
            wall = metadata["start_wall_time"] + t
            stage = "approach" if wall < close_epoch else "carry" if wall < open_epoch else "place"
            frame = templates[stage].copy()
            frame[86:626, 30:990] = camera_frame
            writer.write(frame)
    finally:
        capture.release()
    return count / FPS


def main():
    plans = {name: json.loads((RAW / f"{name}_plan.json").read_text())
             for name in ("right", "left")}
    results = {name: json.loads((RAW / f"{name}_verification.json").read_text())
               for name in ("right", "left")}
    if any(not result["passed"] for result in results.values()):
        raise ValueError("Both simulation runs must pass before editing the video")
    OUTPUT.mkdir(exist_ok=True)
    destination = OUTPUT / "pick_and_place_demo_intermediate.mp4"
    writer = cv2.VideoWriter(str(destination), cv2.VideoWriter_fourcc(*"mp4v"), FPS, SIZE)
    if not writer.isOpened():
        raise RuntimeError("OpenCV cannot create the intermediate MP4")
    seconds = 0.0
    try:
        write_still(writer, title_frame(), 8)
        seconds += 8
        for name in ("right", "left"):
            write_still(writer, plan_frame(plans[name], name), 6)
            seconds += 6
            seconds += write_clip(writer, name, plans[name])
        write_still(writer, final_frame(results["right"], results["left"]), 10)
        seconds += 10
    finally:
        writer.release()
    if not 60 <= seconds <= 180:
        raise ValueError(f"Demo length {seconds:.1f}s violates the 1-3 minute requirement")
    print(f"Intermediate video: {destination} ({seconds:.1f} seconds)")


if __name__ == "__main__":
    main()
