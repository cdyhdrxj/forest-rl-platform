#!/bin/bash

# Активируем ROS 2
source /opt/ros/humble/setup.bash

# Активируем наше рабочее пространство
if [ -f /ros2_ws/install/setup.bash ]; then
    source /ros2_ws/install/setup.bash
fi

# Функция для остановки всех процессов
cleanup() {
    echo "🛑 Останавливаем сервисы..."
    kill $ENDPOINT_PID 2>/dev/null
    exit 0
}

# Перехватываем Ctrl+C
trap cleanup INT TERM

# Запускаем ROS TCP Endpoint для Unity в фоне
echo "🚀 Запуск ROS TCP Endpoint на порту 10000..."
ros2 run ros_tcp_endpoint default_server_endpoint --ros-args -p ROS_IP:=0.0.0.0 &
ENDPOINT_PID=$!
echo "✅ ROS TCP Endpoint запущен (PID: $ENDPOINT_PID)"

# Запускаем rosbridge для веба (блокирует выполнение)
echo "🚀 Запуск rosbridge на порту 9090..."
ros2 launch rosbridge_server rosbridge_websocket_launch.xml