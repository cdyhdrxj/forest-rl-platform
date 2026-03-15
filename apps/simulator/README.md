# Unity Simulator

# Build

docker build -t unity-forest-simulator:latest .

# Network

docker network create ros-unity-net

# ROS 2 IP

ros2-endpoint

# Run

docker run -it --rm \
  --name unity-sim \
  --network ros-unity-net \
  -e DISPLAY=host.docker.internal:0.0 \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  -v $(pwd)/logs:/linux_build/logs \
  unity-forest-simulator