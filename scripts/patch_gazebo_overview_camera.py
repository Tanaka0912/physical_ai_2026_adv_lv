#!/usr/bin/env python3
"""Add a fixed overview camera for recording the pick and place task."""

from pathlib import Path
import sys


path = Path(sys.argv[1]) / "ur_gazebo/worlds/pick_and_place_demo.world"
source = path.read_text()
if '<model name="demo_overview_camera">' not in source:
    camera = """
    <!-- Fixed camera used only to document the robot demonstration. -->
    <model name="demo_overview_camera">
      <static>true</static>
      <pose>0.85 -1.25 1.95 0 0.53 2.17</pose>
      <link name="camera_link">
        <sensor name="overview" type="camera">
          <always_on>true</always_on>
          <update_rate>10</update_rate>
          <topic>/demo/overview/image</topic>
          <camera>
            <horizontal_fov>1.30</horizontal_fov>
            <image>
              <width>960</width>
              <height>540</height>
              <format>R8G8B8</format>
            </image>
            <clip><near>0.05</near><far>10</far></clip>
          </camera>
        </sensor>
      </link>
    </model>
"""
    if source.count("  </world>") != 1:
        raise ValueError(f"Unexpected SDF world structure: {path}")
    path.write_text(source.replace("  </world>", camera + "  </world>"))
print(f"{path}: overview camera ready")
