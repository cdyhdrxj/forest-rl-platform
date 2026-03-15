# ROS 2 TCP ENDPOINT

# Build

docker build -t ros2-endpoint .

# Network

docker network create ros-unity-net

# Run

docker run --rm -it \
  --name ros2-endpoint \
  --network ros-unity-net \
  -p 10000:10000 \
  ros2-endpoint

# ROS 2 Activation

source /opt/ros/humble/setup.bash