# Используем официальный образ ROS 2 Humble
FROM osrf/ros:humble-desktop

RUN apt-get update && apt-get install -y \
    python3-pip \
    git \
    ros-humble-rosbridge-server \
    ros-humble-rosbridge-library \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /ros2_ws

# Копируем исходники ros_tcp_endpoint
COPY src/ ./src/

# Собираем пакет
RUN bash -c "source /opt/ros/humble/setup.bash && \
    colcon build --packages-select ros_tcp_endpoint forest_msgs"

COPY entrypoint.ros2.sh /
RUN sed -i 's/\r$//' /entrypoint.ros2.sh && chmod +x /entrypoint.ros2.sh

EXPOSE 10000
EXPOSE 9090

# Запуск
ENTRYPOINT ["/entrypoint.ros2.sh"]
