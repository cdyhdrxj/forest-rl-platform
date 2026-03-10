import time
import numpy as np
import gymnasium as gym
from gymnasium import spaces
import subprocess
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from sensor_msgs.msg import Imu, PointCloud2

from lidar_processor import LiDARProcessor
from imu_processor import IMUProcessor
from obstacle_classifier import ObstacleClassifier
import pose_reader


V_MAX = 3.5  # максимальная линейная скорость
W_MAX = 2.0  # максимальная угловая скорость

class ForestEnv(gym.Env):

    def __init__(self):
        super().__init__()

        rclpy.init(args=None)
        self.node = Node("forest_env_node")

        self.cmd_pub = self.node.create_publisher(
            Twist,
            '/robot/robotnik_base_control/cmd_vel_unstamped',
            10
        )

        self.lidar_processor = LiDARProcessor(n_horiz=60, n_vert=2)
        self.imu_processor = IMUProcessor()
        self.detector = ObstacleClassifier()

        self.last_cloud = None
        self.last_imu = None

        self.node.create_subscription(
            PointCloud2,
            '/robot/top_laser/points',
            self._lidar_callback,
            10
        )

        self.node.create_subscription(
            Imu,
            '/robot/imu/data',
            self._imu_callback,
            10
        )

        self.start_pose = np.array([0.0, 0.0, 0.0])
        #self.goal = np.array([-2.0, 0.0, 0.0])  # ближе

        self.dt = 0.15
        self.max_steps = 400
        self.current_step = 0

        self.prev_distance = None

        self.action_space = spaces.Box(
            low=np.array([-1.0, -1.0]),
            high=np.array([1.0, 1.0]),
            dtype=np.float32
        )

        obs_dim = 3 + 3 + 120 + 4

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

        while True:
            goal_xy = np.random.uniform(-1.5, 1.5, size=2)
            dist = np.linalg.norm(goal_xy - self.start_pose[:2])
            if 1.0 <= dist <= 1.5:
                break

        self.goal = np.array([goal_xy[0], goal_xy[1], 0.0])

        
        while self.last_cloud is None or self.last_imu is None:
            rclpy.spin_once(self.node, timeout_sec=0.1)

        while pose_reader.get_pose() is None:
            rclpy.spin_once(self.node, timeout_sec=0.1)

        self._send_command([0.0, 0.0])
        time.sleep(0.2)

        start_x, start_y, start_yaw = self.start_pose
        qz = np.sin(start_yaw / 2.0)
        qw = np.cos(start_yaw / 2.0)

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
        self.current_step += 1

        start_time = time.time()
        while time.time() - start_time < self.dt:
            self._send_command(action)
            rclpy.spin_once(self.node, timeout_sec=0.01)

        obs = self._get_observation()

        pose = pose_reader.get_pose()
        self.detector.update_lidar(obs[6:126])
        status = self.detector.classify(pose)
        
        reward = self._compute_reward(obs, status)
        done = self._is_done(obs, status)
        print("pose:", pose)
        print("action:", action)
        print("reward:", reward)
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

        position = np.array([pose['x'], pose['y'], pose['z']])
        lidar = self.lidar_processor.process_pointcloud2(self.last_cloud)
        imu = self.imu_processor.process_imu(self.last_imu)

        return np.concatenate([position, self.goal, lidar, imu]).astype(np.float32)

    def _distance_to_goal(self, obs):
        return np.linalg.norm(obs[0:2] - obs[3:5])

    '''def _compute_reward(self, obs, status):
        distance = self._distance_to_goal(obs)
        progress = self.prev_distance - distance
        self.prev_distance = distance

        reward = 30.0 * progress
        reward -= 0.01

        if status == "TREE":
            reward -= 20

        if "TILTED" in status or "UPSIDE" in status:
            reward -= 100

        if distance < 0.5:
            reward += 800

        return reward
    '''
    def _compute_reward(self, obs, status):
        distance = self._distance_to_goal(obs)
        progress = self.prev_distance - distance
        self.prev_distance = distance
        print("dist:",distance)
        reward = 400.0 * progress      # штраф за продвижение к цели
        reward -= 0.02                 # штраф за шаг
        reward -= 0.05 * obs[129]   # штраф за кручение

        if distance < 0.5:
            reward += 500.0

        return reward


    def _is_done(self, obs, status):
        if self._distance_to_goal(obs) < 0.5:
            return True
        '''if status == "TREE":
            return True'''
        if self.current_step >= self.max_steps:
            return True
        return False
