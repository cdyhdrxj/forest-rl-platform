# Симулятор Unity

## Сборка

docker build -t unity-forest-simulator:latest .

## Сеть

docker network create ros-unity-net

## Имя ROS 2 шлюза

ros2-endpoint

## Запуск

docker run -it --rm \
  --name unity-sim \
  --network ros-unity-net \
  -e DISPLAY=host.docker.internal:0.0 \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  -v $(pwd)/logs:/linux_build/logs \
  unity-forest-simulator
