#!/usr/bin/env bash
set -eo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TAKE="${1:?Usage: record_take.sh TAKE_NAME [run_planned.sh options]}"
shift
if [[ ! "$TAKE" =~ ^[a-z0-9_]+$ ]]; then
    echo "TAKE_NAME must contain only lower-case letters, digits or underscores" >&2
    exit 2
fi

source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=113 ROS_LOCALHOST_ONLY=1 RMW_IMPLEMENTATION=rmw_fastrtps_cpp
mkdir -p "$ROOT/video/raw" "$ROOT/logs"
: > "$ROOT/logs/baseline.log"
WS=/root/UR3_ROS2_PICK_AND_PLACE
python3 "$ROOT/scripts/toggle_head_camera_for_video.py" disable "$WS"
python3 "$ROOT/scripts/set_video_camera_pose.py" "$TAKE" "$WS"

BRIDGE_PID=
CAPTURE_PID=
RUN_PID=
cleanup() {
    if [[ -n "$BRIDGE_PID" ]]; then kill "$BRIDGE_PID" 2>/dev/null || true; fi
    if [[ -n "$CAPTURE_PID" ]]; then kill "$CAPTURE_PID" 2>/dev/null || true; fi
    if [[ -n "$RUN_PID" ]]; then kill -INT "$RUN_PID" 2>/dev/null || true; fi
    python3 "$ROOT/scripts/set_video_camera_pose.py" restore "$WS"
    python3 "$ROOT/scripts/toggle_head_camera_for_video.py" restore "$WS"
}
trap cleanup EXIT INT TERM

bash "$ROOT/scripts/run_planned.sh" "$@" > "$ROOT/logs/take_${TAKE}_runner.log" 2>&1 &
RUN_PID=$!
for attempt in $(seq 1 180); do
    if grep -q 'Ready at attempt' "$ROOT/logs/baseline.log"; then break; fi
    if ! kill -0 "$RUN_PID" 2>/dev/null; then
        echo "Simulation exited before ready" >&2
        exit 1
    fi
    sleep 0.5
done
if ! grep -q 'Ready at attempt' "$ROOT/logs/baseline.log"; then
    echo "Gazebo readiness timed out" >&2
    exit 1
fi

ros2 run ros_gz_image image_bridge /demo/overview/image \
    > "$ROOT/logs/take_${TAKE}_bridge.log" 2>&1 &
BRIDGE_PID=$!
sleep 3
python3 "$ROOT/scripts/capture_camera.py" \
    --topic /demo/overview/image \
    --mp4 "$ROOT/video/raw/${TAKE}.mp4" --duration 130 --fps 10 \
    > "$ROOT/logs/take_${TAKE}_capture.log" 2>&1 &
CAPTURE_PID=$!

wait "$RUN_PID"
RUN_PID=
wait "$CAPTURE_PID"
CAPTURE_PID=
cp "$ROOT/logs/baseline.log" "$ROOT/video/raw/${TAKE}_baseline.log"
cp "$ROOT/logs/object_sync.log" "$ROOT/video/raw/${TAKE}_object_sync.log"
cp "$ROOT/generated/plan.json" "$ROOT/video/raw/${TAKE}_plan.json"
cp "$ROOT/generated/verification.json" "$ROOT/video/raw/${TAKE}_verification.json"
echo "Recorded and verified $TAKE"
