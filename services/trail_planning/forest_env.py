import time
import numpy as np
import gymnasium as gym
from gymnasium import spaces
import subprocess
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from sensor_msgs.msg import Imu, PointCloud2
import math
from lidar_processor import LiDARProcessor
from imu_processor import IMUProcessor
import pose_reader

# ограничение скоростей для стабильного обучения
V_MAX = 0.8
W_MAX = 1.2


class ForestEnv(gym.Env):

    def __init__(self):
        super().__init__()

        rclpy.init(args=None)
        self.node = Node("forest_env_node")

        self.cmd_pub = self.node.create_publisher(
            Twist,
            "/robot/robotnik_base_control/cmd_vel_unstamped",
            10
        )

        self.lidar_processor = LiDARProcessor(n_horiz=60, n_vert=2)
        self.imu_processor = IMUProcessor()

        self.last_cloud = None
        self.last_imu = None

        self.node.create_subscription(
            PointCloud2,
            "/robot/top_laser/points",
            self._lidar_callback,
            10
        )

        self.node.create_subscription(
            Imu,
            "/robot/imu/data",
            self._imu_callback,
            10
        )

        self.start_pose = np.array([0.0, 0.0, 0.0])
        self.dt = 0.15
        self.max_steps = 200
        self.current_step = 0
        self.prev_distance = None

        # action: [forward_speed , turn_speed]
        self.action_space = spaces.Box(
            low=np.array([0.0, -1.0]),
            high=np.array([1.0, 1.0]),
            dtype=np.float32
        )

        # position + goal + heading + lidar + imu
        obs_dim = 3 + 3 + 1 + 120 + 4
        self.observation_space = spaces.Box(
            low=-np.inf,
            high=np.inf,
            shape=(obs_dim,),
            dtype=np.float32
        )

    def _lidar_callback(self, msg):
        self.last_cloud = msg

    def _imu_callback(self, msg):
        self.last_imu = msg

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.current_step = 0

        # Случайная цель на карте (20x20)
        while True:
            goal_x = np.random.uniform(-9.5, 9.5)
            goal_y = np.random.uniform(-9.5, 9.5)
            dist = np.linalg.norm(np.array([goal_x, goal_y]) - self.start_pose[:2])
            if 3.0 <= dist <= 12.0:
                break

        self.goal = np.array([goal_x, goal_y, 0.0])

        while self.last_cloud is None or self.last_imu is None:
            rclpy.spin_once(self.node, timeout_sec=0.1)

        while pose_reader.get_pose() is None:
            rclpy.spin_once(self.node, timeout_sec=0.1)

        self._send_command([0.0, 0.0])
        time.sleep(0.2)

        start_x, start_y, start_yaw = self.start_pose
        qz = np.sin(start_yaw / 2)
        qw = np.cos(start_yaw / 2)

        cmd = f"""
gz service -s /world/rl_forest/set_pose \
--reqtype gz.msgs.Pose \
--reptype gz.msgs.Boolean \
--req 'name: "robot"
position {{ x: {start_x} y: {start_y} z: 0.2 }}
orientation {{ z: {qz} w: {qw} }}'
"""
        subprocess.run(cmd, shell=True)
        time.sleep(1.0)

        obs = self._get_observation()
        self.prev_distance = self._distance_to_goal(obs)
        return obs, {}

    def step(self, action):
        action = np.clip(action, [0.0, -1.0], [1.0, 1.0])
        self.current_step += 1

        start_time = time.time()
        while time.time() - start_time < self.dt:
            self._send_command(action)
            rclpy.spin_once(self.node, timeout_sec=0.01)

        obs = self._get_observation()
        reward = self._compute_reward(obs, action)
        done = self._is_done(obs)

        # ВЫВОД 
        pose = pose_reader.get_pose()
        if pose is not None:
            x, y, z = pose["x"], pose["y"], pose["z"]
            x, y, z = round(x, 3), round(y, 3), round(z, 3)
            distance = round(self._distance_to_goal(obs), 3)
            print(f"pos: x={x}, y={y}, z={z} | distance={distance} | action=[{round(action[0],3)}, {round(action[1],3)}] | reward={round(reward,3)}")

        return obs, reward, done, False, {}

    def _send_command(self, action):
        msg = Twist()
        msg.linear.x = float(action[0] * V_MAX)
        msg.angular.z = float(action[1] * W_MAX)
        self.cmd_pub.publish(msg)

    def _get_observation(self):
        pose = pose_reader.get_pose()
        if pose is None:
            return np.zeros(self.observation_space.shape[0], dtype=np.float32)

        position = np.array([pose["x"], pose["y"], pose["z"]])
        dx = self.goal[0] - position[0]
        dy = self.goal[1] - position[1]

        goal_angle = np.arctan2(dy, dx)
        # Вычисляем yaw из кватерниона
        ox, oy, oz, ow = pose['ox'], pose['oy'], pose['oz'], pose['ow']
        yaw = math.atan2(2*(ow*oz + ox*oy), 1 - 2*(oy*oy + oz*oz))

        # Вектор к цели
        dx = self.goal[0] - position[0]
        dy = self.goal[1] - position[1]
        goal_angle = math.atan2(dy, dx)

        # Ошибка угла [-pi, pi]
        heading_error = goal_angle - yaw
        heading_error = np.arctan2(np.sin(heading_error), np.cos(heading_error))
        
        lidar = self.lidar_processor.process_pointcloud2(self.last_cloud)
        imu = self.imu_processor.process_imu(self.last_imu)

        return np.concatenate([position, self.goal, [heading_error], lidar, imu]).astype(np.float32)

    def _distance_to_goal(self, obs):
        return np.linalg.norm(obs[0:2] - obs[3:5])

    def _compute_reward(self, obs, action):
        distance = self._distance_to_goal(obs)
        progress = self.prev_distance - distance
        self.prev_distance = distance

        reward = 0.0
        reward += 40 * progress        # приближение к цели
        reward -= 0.01                 # штраф за шаг
        reward -= 0.03 * abs(action[0]) # штраф за скорость
        reward -= 0.08 * abs(action[1]) # штраф за вращение
        if distance < 0.5:
            reward += 120              # бонус за достижение цели
        return reward

    def _is_done(self, obs):
        if self._distance_to_goal(obs) < 0.5:
            return True
        if self.current_step >= self.max_steps:
            return True
        return False
