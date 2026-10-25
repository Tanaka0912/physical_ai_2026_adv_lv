#!/usr/bin/env bash
set -eo pipefail

WS=/root/UR3_ROS2_PICK_AND_PLACE
source /opt/ros/jazzy/setup.bash
source "$WS/install/setup.bash"
set -u
export USE_GAZEBO_GUI=false
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
export GZ_SIM_RESOURCE_PATH="$WS/ur_gazebo/models:${GZ_SIM_RESOURCE_PATH:-}"
cd "$WS"
exec timeout --signal=INT --kill-after=15s 600s bash ur_mtc_pick_place_demo/scripts/robot.sh
