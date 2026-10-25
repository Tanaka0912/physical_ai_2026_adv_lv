#!/usr/bin/env bash
set -eo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WS=/root/UR3_ROS2_PICK_AND_PLACE
python3 "$ROOT/planner/plan_place.py" \
    --base-yaml "$WS/ur_mtc_pick_place_demo/config/mtc_node_params.yaml" \
    --output-yaml "$ROOT/generated/mtc_node_params.yaml" \
    --report "$ROOT/generated/plan.json" \
    "$@"
export MTC_NODE_PARAMS_FILE="$ROOT/generated/mtc_node_params.yaml"
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-113}"
export ROS_LOCALHOST_ONLY=1
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
mkdir -p "$ROOT/logs"
SYNC_PID=
BASE_PID=
cleanup() {
    if [[ -n "$SYNC_PID" ]]; then kill "$SYNC_PID" 2>/dev/null || true; fi
    if [[ -n "$BASE_PID" ]]; then
        kill -INT "$BASE_PID" 2>/dev/null || true
        wait "$BASE_PID" 2>/dev/null || true
    fi
}
trap cleanup EXIT INT TERM
bash "$ROOT/scripts/run_baseline.sh" > "$ROOT/logs/baseline.log" 2>&1 &
BASE_PID=$!
# A subscriber started before Gazebo's DDS participant can remain undiscovered
# on this WSL Fast DDS setup. Start the synchronizer after live joint states exist.
for attempt in $(seq 1 180); do
    if grep -q 'Ready at attempt' "$ROOT/logs/baseline.log"; then break; fi
    if ! kill -0 "$BASE_PID" 2>/dev/null; then
        echo "Baseline launch exited before Gazebo was ready" >&2
        exit 1
    fi
    sleep 0.5
done
if ! grep -q 'Ready at attempt' "$ROOT/logs/baseline.log"; then
    echo "Timed out waiting for Gazebo and controllers" >&2
    exit 1
fi
python3 "$ROOT/planner/sync_gazebo_object.py" \
    > "$ROOT/logs/object_sync.log" 2>&1 &
SYNC_PID=$!
for attempt in $(seq 1 1200); do
    if grep -q 'Task execution failed\|Task planning failed' "$ROOT/logs/baseline.log"; then
        echo "MTC planning or execution failed; inspect $ROOT/logs/baseline.log" >&2
        exit 1
    fi
    if grep -q 'Task executed successfully' "$ROOT/logs/baseline.log" && \
       grep -q 'Gazebo cylinder placed at' "$ROOT/logs/object_sync.log"; then
        python3 "$ROOT/scripts/verify_result.py"
        exit 0
    fi
    if ! kill -0 "$BASE_PID" 2>/dev/null; then
        echo "Simulation exited before placement verification" >&2
        exit 1
    fi
    sleep 0.5
done
echo "Timed out waiting for pick and place completion" >&2
exit 1
