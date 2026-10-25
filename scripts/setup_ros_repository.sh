#!/usr/bin/env bash
set -euo pipefail

if [[ "$(id -u)" != 0 ]]; then
  echo "Run as root inside Ubuntu 24.04 WSL." >&2
  exit 1
fi

source /etc/os-release
if [[ "$ID" != ubuntu || "$VERSION_ID" != 24.04 ]]; then
  echo "This setup is for Ubuntu 24.04; found $PRETTY_NAME." >&2
  exit 1
fi

apt-get update
apt-get install -y curl ca-certificates gnupg
curl -fsSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.asc \
  -o /usr/share/keyrings/ros-archive-keyring.asc
printf 'deb [arch=amd64 signed-by=/usr/share/keyrings/ros-archive-keyring.asc] http://packages.ros.org/ros2/ubuntu noble main\n' \
  > /etc/apt/sources.list.d/ros2.list
apt-get update
