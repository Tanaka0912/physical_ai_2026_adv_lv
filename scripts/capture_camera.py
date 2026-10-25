#!/usr/bin/env python3
"""Capture Gazebo's ROS camera stream as a PNG preview or MP4."""

import argparse
import json
import time
from pathlib import Path

import cv2
from cv_bridge import CvBridge
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image


class CameraCapture(Node):
    def __init__(self, args):
        super().__init__("pick_place_camera_capture")
        self.args = args
        self.bridge = CvBridge()
        self.frame = None
        self.frames_received = 0
        self.subscription = self.create_subscription(
            Image, args.topic, self.on_image, qos_profile_sensor_data
        )

    def on_image(self, msg):
        self.frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
        self.frames_received += 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--topic", default="/camera_head/color/image_raw")
    parser.add_argument("--preview", type=Path)
    parser.add_argument("--mp4", type=Path)
    parser.add_argument("--duration", type=float, default=120.0)
    parser.add_argument("--fps", type=float, default=10.0)
    args = parser.parse_args()
    if not args.preview and not args.mp4:
        parser.error("Choose --preview or --mp4")

    rclpy.init()
    node = CameraCapture(args)
    try:
        deadline = time.monotonic() + 30.0
        while node.frame is None and time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=0.1)
        if node.frame is None:
            raise RuntimeError(f"No camera frames received on {args.topic}")
        if args.preview:
            args.preview.parent.mkdir(parents=True, exist_ok=True)
            if not cv2.imwrite(str(args.preview), node.frame):
                raise RuntimeError(f"Cannot write {args.preview}")
            print(f"Preview: {args.preview}, {node.frame.shape}")
        if args.mp4:
            args.mp4.parent.mkdir(parents=True, exist_ok=True)
            height, width = node.frame.shape[:2]
            writer = cv2.VideoWriter(
                str(args.mp4), cv2.VideoWriter_fourcc(*"mp4v"), args.fps,
                (width, height),
            )
            if not writer.isOpened():
                raise RuntimeError("OpenCV cannot open MP4 video writer")
            try:
                wall_start = time.time()
                start = time.monotonic()
                frame_number = 0
                while time.monotonic() - start < args.duration:
                    target = start + frame_number / args.fps
                    while time.monotonic() < target:
                        rclpy.spin_once(node, timeout_sec=min(0.05, target - time.monotonic()))
                    writer.write(node.frame)
                    frame_number += 1
                metadata = {
                    "topic": args.topic,
                    "start_wall_time": wall_start,
                    "end_wall_time": time.time(),
                    "fps": args.fps,
                    "frames_written": frame_number,
                    "frames_received": node.frames_received,
                    "width": width,
                    "height": height,
                }
                args.mp4.with_suffix(".json").write_text(json.dumps(metadata, indent=2) + "\n")
                print(f"Video: {args.mp4}, {frame_number} frames, received {node.frames_received} images")
            finally:
                writer.release()
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
