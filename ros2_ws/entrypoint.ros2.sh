#!/bin/bash

# Активируем ROS 2
source /opt/ros/humble/setup.bash

# Активируем наше рабочее пространство
source /ros2_ws/install/setup.bash

# Запускаем endpoint
ros2 run ros_tcp_endpoint default_server_endpoint --ros-args -p ROS_IP:=0.0.0.0