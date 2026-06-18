#!/bin/bash
set -eo pipefail

source /opt/ros/humble/setup.bash

if [ -f /ros2_ws/install/setup.bash ]; then
    source /ros2_ws/install/setup.bash
fi

ENDPOINT_PID=""

cleanup() {
    echo "Останавливаем ROS 2 сервисы..."
    if [ -n "${ENDPOINT_PID}" ]; then
        kill "${ENDPOINT_PID}" 2>/dev/null || true
    fi
}

trap cleanup EXIT INT TERM

echo "Запуск ROS TCP Endpoint на порту 10000..."
ros2 run ros_tcp_endpoint default_server_endpoint --ros-args -p ROS_IP:=0.0.0.0 &
ENDPOINT_PID=$!
echo "ROS TCP Endpoint запущен (PID: ${ENDPOINT_PID})"

echo "Запуск rosbridge на порту 9090..."
ros2 launch rosbridge_server rosbridge_websocket_launch.xml
