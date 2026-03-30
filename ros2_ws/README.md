# TCP-шлюз для ROS 2

## Сборка

docker build -t ros2-endpoint .

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
