# Используем официальный образ ROS 2 Humble
FROM osrf/ros:humble-desktop

# Устанавливаем необходимые пакеты
RUN apt-get update && apt-get install -y \
    python3-pip \
    git \
    ros-humble-rosbridge-server \
    ros-humble-rosbridge-library \
    && rm -rf /var/lib/apt/lists/*

# Создаём рабочее пространство
WORKDIR /ros2_ws

# Копируем исходники ros_tcp_endpoint
COPY src/ src/

# Собираем пакет
RUN bash -c "source /opt/ros/humble/setup.bash && \
    colcon build --packages-select ros_tcp_endpoint forest_msgs"

# Копируем скрипт запуска
COPY entrypoint.ros2.sh /
RUN chmod +x /entrypoint.ros2.sh

# Открываем порты
EXPOSE 10000
EXPOSE 9090

# Запускаем всё
ENTRYPOINT ["/entrypoint.ros2.sh"]