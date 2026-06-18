# TCP-шлюз для ROS 2

## Сборка

docker build --no-cache -t ros2-endpoint .

## Сеть

docker network create ros-unity-net

## Запуск

docker run --rm -it \
  --name ros2-endpoint \
  --network ros-unity-net \
  -p 10000:10000 \
  -p 9090:9090 \
  ros2-endpoint

## Активация ROS 2

source /opt/ros/humble/setup.bash
source /ros2_ws/install/setup.bash

ros2 service call /env/generate forest_msgs/srv/SetTerrainParams "{uniform_scale: 0.1, mesh_height_multiplayer: 10.0, noise_scale: 60.0, seed: 15, octaves: 4, persistance: 0.5, lacunarity: 2.0, offset_x: 0.0, offset_y: 0.0, max_view_dst: 500,  noise_normalize_mode: 0}"

ros2 topic pub --once /robot_0/cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.2, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}"