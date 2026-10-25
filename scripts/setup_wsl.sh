#!/usr/bin/env bash
set -eo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WS=/root/UR3_ROS2_PICK_AND_PLACE
UPSTREAM_COMMIT=5e481d01492860dcef61992edfbe9f14ba98616d

if [[ "$(id -u)" != 0 ]]; then
    echo "Run as root in Ubuntu 24.04 WSL." >&2
    exit 1
fi

bash "$ROOT/scripts/setup_ros_repository.sh"
DEBIAN_FRONTEND=noninteractive apt-get install -y \
    git ffmpeg python3-pil python3-colcon-common-extensions python3-rosdep python3-opencv \
    ros-jazzy-ros-base ros-jazzy-ros-gz ros-jazzy-moveit \
    ros-jazzy-ur-simulation-gz ros-jazzy-gz-ros2-control \
    ros-jazzy-ros2-control ros-jazzy-ros2-controllers \
    ros-jazzy-gz-ros2-control-demos \
    ros-jazzy-moveit-task-constructor-core \
    ros-jazzy-moveit-task-constructor-capabilities \
    ros-jazzy-moveit-ros-perception \
    ros-jazzy-moveit-resources-panda-moveit-config \
    ros-jazzy-moveit-resources-fanuc-moveit-config \
    ros-jazzy-py-binding-tools ros-jazzy-parallel-gripper-controller \
    ros-jazzy-pcl-conversions ros-jazzy-pcl-ros ros-jazzy-cv-bridge \
    libpcl-dev liburdfdom-tools libmongoclient-dev

if [[ ! -d "$WS/.git" ]]; then
    git clone https://github.com/darshmenon/UR3_ROS2_PICK_AND_PLACE.git "$WS"
fi
if [[ "$(git -C "$WS" rev-parse HEAD)" != "$UPSTREAM_COMMIT" ]]; then
    echo "Upstream checkout differs from pinned commit $UPSTREAM_COMMIT." >&2
    echo "Use a clean checkout at $WS." >&2
    exit 1
fi

for patch in mtc_jazzy_api.patch robot_params.patch; do
    if ! git -C "$WS" apply --reverse --check "$ROOT/patches/$patch" 2>/dev/null; then
        git -C "$WS" apply "$ROOT/patches/$patch"
    fi
done
python3 "$ROOT/scripts/patch_moveit_jazzy.py" "$WS"
python3 "$ROOT/scripts/patch_gazebo_marker.py" "$WS"
python3 "$ROOT/scripts/patch_gazebo_overview_camera.py" "$WS"

rosdep init 2>/dev/null || true
rosdep update
source /opt/ros/jazzy/setup.bash
cmake -S "$ROOT/planner" -B /root/physical_ai_pose_build -DCMAKE_BUILD_TYPE=Release
cmake --build /root/physical_ai_pose_build -j1
cd "$WS"
export CMAKE_BUILD_PARALLEL_LEVEL=1 MAKEFLAGS=-j1
colcon build --symlink-install --executor sequential \
    --allow-overriding ur_description \
    --packages-select warehouse_ros_mongo ur_description robotiq_description \
        onrobot_description robotiq_2f_85_gripper_visualization \
        moveit_config ur_interfaces ur_gazebo \
    --cmake-args -DCMAKE_BUILD_TYPE=Debug -DCMAKE_CXX_FLAGS_DEBUG=-O0 -DBUILD_TESTING=OFF
source install/setup.bash
colcon build --symlink-install --executor sequential \
    --packages-select ur_mtc_pick_place_demo \
    --cmake-args -DCMAKE_BUILD_TYPE=Debug -DCMAKE_CXX_FLAGS_DEBUG=-O0 -DBUILD_TESTING=OFF
echo "Setup complete. Run: bash $ROOT/scripts/run_planned.sh"
