# robot_adapter/robot_adapter/unity_env.py

import rclpy
import numpy as np
from rclpy.node import Node
from sensor_msgs.msg import LaserScan
from geometry_msgs.msg import Twist
import gymnasium as gym
from gymnasium import spaces

class UnityRobotEnv(gym.Env):
    """
    Среда для Stable Baselines3, которая общается с Unity через ROS2
    """
    
    def __init__(self, ros_node=None):
        super().__init__()
        
        # Если ROS нода не передана, создаём свою
        if ros_node is None:
            rclpy.init()
            self.ros_node = UnityROSNode()
        else:
            self.ros_node = ros_node
        
        # Действия: [линейная скорость, угловая скорость]
        self.action_space = spaces.Box(
            low=np.array([-0.5, -1.0]),
            high=np.array([0.5, 1.0]),
            dtype=np.float32
        )
        
        # Наблюдение: 9 секторов лидара + 2 координаты
        self.observation_space = spaces.Box(
            low=-10, high=10, 
            shape=(11,),  # 9 секторов + x + y
            dtype=np.float32
        )
        
        self.max_steps = 500
        self.step_count = 0
    
    def reset(self, seed=None):
        """Начать новый эпизод"""
        self.step_count = 0
        
        # Останавливаем робота
        cmd = Twist()
        self.ros_node.cmd_pub.publish(cmd)
        
        # Ждём обновления
        import time
        time.sleep(0.5)
        
        return self._get_obs(), {}
    
    def step(self, action):
        """
        Выполнить действие и вернуть результат
        action: [linear_x, angular_z]
        """
        # 1. Отправляем команду роботу
        cmd = Twist()
        cmd.linear.x = float(action[0])
        cmd.angular.z = float(action[1])
        self.ros_node.cmd_pub.publish(cmd)
        
        # 2. Ждём (0.1 сек = частота лидара)
        import time
        time.sleep(0.1)
        
        # 3. Получаем новые наблюдения
        obs = self._get_obs()
        
        # 4. Считаем награду
        min_dist = min(obs[:9])  # минимальное расстояние до препятствия
        if min_dist < 0.3:
            reward = -10.0  # врезался
            done = True
        else:
            # Награда за движение вперёд + штраф за близость к стенам
            reward = float(action[0]) - (0.5 / (min_dist + 0.1))
            done = self.step_count >= self.max_steps
        
        self.step_count += 1
        
        return obs, reward, done, False, {}
    
    def _get_obs(self):
        """Собирает наблюдения из ROS2"""
        scan = self.ros_node.get_scan_sectors()
        position = [self.ros_node.current_x, self.ros_node.current_y]
        return np.array(scan + position, dtype=np.float32)

class UnityROSNode(Node):
    """ROS2 нода для общения с Unity"""
    
    def __init__(self):
        super().__init__('unity_env_node')
        
        # Подписчики
        self.scan_sub = self.create_subscription(
            LaserScan, '/scan', self.scan_callback, 10)
        
        self.odom_sub = self.create_subscription(
            Odometry, '/odom', self.odom_callback, 10)
        
        # Издатель команд
        self.cmd_pub = self.create_publisher(Twist, '/cmd_vel', 10)
        
        # Данные
        self.last_scan = None
        self.current_x = 0.0
        self.current_y = 0.0
        
        self.get_logger().info('✅ UnityROSNode запущен')
    
    def scan_callback(self, msg):
        self.last_scan = msg
    
    def odom_callback(self, msg):
        self.current_x = msg.pose.pose.position.x
        self.current_y = msg.pose.pose.position.y
    
    def get_scan_sectors(self, num_sectors=9):
        """Разбивает лидар на секторы"""
        if self.last_scan is None:
            return [0.0] * num_sectors
        
        ranges = np.array(self.last_scan.ranges)
        ranges = np.clip(ranges, 0, 10)
        sectors = np.array_split(ranges, num_sectors)
        return [float(np.min(s)) for s in sectors]