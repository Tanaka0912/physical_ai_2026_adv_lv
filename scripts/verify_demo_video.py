#!/usr/bin/env python3
"""Check final MP4 metadata and export representative frames for visual QA."""

import json
from pathlib import Path
import subprocess

import cv2


root = Path(__file__).resolve().parents[1]
video = root / "output/PAI_pick_and_place_demo.mp4"
probe = subprocess.run(
    ["ffprobe", "-v", "error", "-show_entries",
     "format=duration,size:stream=codec_name,width,height,r_frame_rate,pix_fmt",
     "-of", "json", str(video)],
    capture_output=True, text=True, check=True,
)
metadata = json.loads(probe.stdout)
stream = next(item for item in metadata["streams"] if item["codec_name"] == "h264")
duration = float(metadata["format"]["duration"])
assert 60 <= duration <= 180, duration
assert (stream["width"], stream["height"]) == (1280, 720)
assert stream["pix_fmt"] == "yuv420p"

preview_dir = root / "generated/video_qa"
preview_dir.mkdir(parents=True, exist_ok=True)
capture = cv2.VideoCapture(str(video))
assert capture.isOpened()
samples = (3, 11, 24, int(duration * 0.45), int(duration * 0.57),
           int(duration * 0.69), int(duration - 15), int(duration - 4))
for second in samples:
    capture.set(cv2.CAP_PROP_POS_MSEC, second * 1000)
    ok, frame = capture.read()
    assert ok, second
    assert cv2.imwrite(str(preview_dir / f"frame_{second:03}.png"), frame)
capture.release()
print(json.dumps({
    "path": str(video),
    "duration_seconds": duration,
    "codec": stream["codec_name"],
    "resolution": [stream["width"], stream["height"]],
    "fps": stream["r_frame_rate"],
    "pixel_format": stream["pix_fmt"],
    "size_bytes": int(metadata["format"]["size"]),
    "qa_frames": samples,
}, indent=2))
