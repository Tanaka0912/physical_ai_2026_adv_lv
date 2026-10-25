#!/usr/bin/env python3
"""Mirror the grasped cylinder into Gazebo during execution.

The upstream demo attaches a collision object in MoveIt but does not couple
the matching Gazebo model to the gripper. This node follows the actual gripper
joint state, moves the model with Gazebo's SetEntityPose service while closed,
and releases it when the gripper opens.
"""

from __future__ import annotations

import math
import json
import subprocess
import time
from pathlib import Path

import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from rclpy.time import Time
from sensor_msgs.msg import JointState
from tf2_ros import Buffer, TransformListener


INITIAL_OBJECT = (0.36, 0.0, 1.085)
BIN_SURFACE_Z = 1.015
OBJECT_HALF_HEIGHT = 0.07
RELEASE_DURATION = 1.0


def multiply(a, b):
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return (
        aw * bx + ax * bw + ay * bz - az * by,
        aw * by - ax * bz + ay * bw + az * bx,
        aw * bz + ax * by - ay * bx + az * bw,
        aw * bw - ax * bx - ay * by - az * bz,
    )


def conjugate(q):
    return (-q[0], -q[1], -q[2], q[3])


def rotate(q, vector):
    pure = (*vector, 0.0)
    return multiply(multiply(q, pure), conjugate(q))[:3]


class ObjectSync(Node):
    def __init__(self):
        super().__init__("pick_place_gazebo_object_sync")
        self.tf = Buffer()
        self.listener = TransformListener(self.tf, self)
        self.writer = subprocess.Popen(
            ["/root/physical_ai_pose_build/gz_pose_writer"],
            stdin=subprocess.PIPE, text=True, bufsize=1,
        )
        self.joint_subscription = self.create_subscription(
            JointState, "/joint_states", self.on_joint_state,
            qos_profile_sensor_data,
        )
        self.create_timer(0.08, self.on_timer)
        self.attached = False
        self.pending_attach = False
        self.relative_position = None
        self.relative_orientation = None
        self.last_finger_position = None
        self.sent = 0
        plan = json.loads((Path(__file__).resolve().parents[1] / "generated/plan.json").read_text())
        self.target_position = (*plan["place_pose"][:2], BIN_SURFACE_Z + OBJECT_HALF_HEIGHT)
        self.last_pose = None
        self.release_start = None
        self.release_started_at = None
        self.max_finger_position = 0.0
        self.create_timer(5.0, self.report_gripper)

    def report_gripper(self):
        self.get_logger().info(
            f"Gripper telemetry: current={self.last_finger_position}, "
            f"maximum={self.max_finger_position:.3f}, pose_updates={self.sent}"
        )

    def wrist(self):
        transform = self.tf.lookup_transform("world", "wrist_3_link", Time())
        p = transform.transform.translation
        q = transform.transform.rotation
        rotation = (q.x, q.y, q.z, q.w)
        norm = math.sqrt(sum(value * value for value in rotation))
        return (p.x, p.y, p.z), tuple(value / norm for value in rotation)

    def on_joint_state(self, state):
        try:
            position = state.position[state.name.index("finger_joint")]
        except ValueError:
            return
        self.max_finger_position = max(self.max_finger_position, position)
        if position > 0.5 and not self.attached and not self.pending_attach:
            self.pending_attach = True
            self.get_logger().info(f"Gripper closed ({position:.3f}); attaching Gazebo cylinder")
        elif position < 0.15 and (self.attached or self.pending_attach):
            self.detach()
        self.last_finger_position = position

    def detach(self):
        if self.attached or self.pending_attach:
            self.get_logger().info(f"Gripper opened; released cylinder after {self.sent} pose updates")
        if self.attached and self.last_pose is not None:
            self.release_start = self.last_pose
            self.release_started_at = time.monotonic()
        self.attached = False
        self.pending_attach = False
        self.relative_position = None
        self.relative_orientation = None

    def on_timer(self):
        if self.release_start is not None:
            fraction = min((time.monotonic() - self.release_started_at) / RELEASE_DURATION, 1.0)
            eased = fraction * fraction * (3.0 - 2.0 * fraction)
            position = tuple(
                self.release_start[i] + eased * (self.target_position[i] - self.release_start[i])
                for i in range(3)
            )
            self.send_pose(position, (0.0, 0.0, 0.0, 1.0))
            if fraction >= 1.0:
                self.release_start = None
                self.get_logger().info(f"Gazebo cylinder placed at {self.target_position}")
            return
        if not self.pending_attach and not self.attached:
            return
        try:
            wrist_position, wrist_rotation = self.wrist()
        except Exception:
            return
        if self.pending_attach:
            difference = tuple(INITIAL_OBJECT[i] - wrist_position[i] for i in range(3))
            self.relative_position = rotate(conjugate(wrist_rotation), difference)
            self.relative_orientation = conjugate(wrist_rotation)
            self.pending_attach = False
            self.attached = True
            self.get_logger().info("Gazebo cylinder is following the wrist")
        displacement = rotate(wrist_rotation, self.relative_position)
        position = tuple(wrist_position[i] + displacement[i] for i in range(3))
        orientation = multiply(wrist_rotation, self.relative_orientation)
        self.last_pose = position
        self.send_pose(position, orientation)

    def send_pose(self, position, orientation):
        if self.writer.poll() is not None:
            self.get_logger().error("Gazebo pose writer exited")
            self.detach()
            return
        self.writer.stdin.write(" ".join(str(value) for value in (*position, *orientation)) + "\n")
        self.sent += 1


def main():
    rclpy.init()
    node = ObjectSync()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.writer.stdin.close()
        node.writer.wait(timeout=2)
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
