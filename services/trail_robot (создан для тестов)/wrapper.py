import gymnasium as gym
from gymnasium import spaces
import numpy as np
import roslibpy
import time
import threading
import urllib.parse
from typing import Optional

class TrailRobotGymWrapper(gym.Env):
    """
    Обёртка для робота через rosbridge (WebSocket)
    Полностью совместима с Stable Baselines 3
    """
    
    metadata = {"render_modes": ["human", "rgb_array"], "render_fps": 10}
    
    def __init__(self, 
                 ros_url: str = "ws://localhost:9090",
                 goal_topic: str = "/goal_pose",
                 max_steps: int = 500,
                 goal_reward: float = 10.0,
                 collision_penalty: float = 5.0,
                 step_penalty: float = 0.01,
                 goal_distance_threshold: float = 0.5,
                 render_mode: Optional[str] = None):
        
        super().__init__()
        
        # Параметры
        self.ros_url = ros_url
        self.goal_topic = goal_topic
        self.max_steps = max_steps
        self.goal_reward = goal_reward
        self.collision_penalty = collision_penalty
        self.step_penalty = step_penalty
        self.goal_distance_threshold = goal_distance_threshold
        self.render_mode = render_mode
        
        # Данные для обучения
        self.last_scan_sectors = np.zeros(9, dtype=np.float32)
        self.last_position = np.array([0.0, 0.0], dtype=np.float32)
        
        # 🎯 Данные о цели
        self.goal_position = np.array([0.0, 0.0], dtype=np.float32)
        self.goal_received = False
        self.distance_to_goal = 0.0
        self.prev_distance = 0.0
        
        self.last_reward = 0.0
        self.collision = False
        self.goal_reached = False
        self.current_step = 0
        
        # Данные для визуализации
        self.last_scan_raw = None
        self.trajectory = []
        
        self.goal_count = 0
        self.collision_count = 0
        
        # ⚡ ПАРАМЕТРЫ УСКОРЕНИЯ
        self.action_repeat = 20  # повторять действие 20 раз
        self.speed_multiplier = 4.0  # умножитель скорости
        
        # ROS соединение
        self.client = None
        self.cmd_vel = None
        self.scan_sub = None
        self.odom_sub = None
        self.goal_sub = None
        self.connected = False
        self.lock = threading.Lock()
        
        # Пространство действий
        self.action_space = spaces.Box(
            low=np.array([-1.0, -1.0], dtype=np.float32),
            high=np.array([1.0, 1.0], dtype=np.float32),
            dtype=np.float32
        )
        
        # Пространство наблюдений (13: лидар 9 + позиция 2 + цель 2)
        self.observation_space = spaces.Box(
            low=-np.inf,
            high=np.inf,
            shape=(13,),
            dtype=np.float32
        )
        
        self._connect_ros()
    
    def _connect_ros(self):
        """Подключение к rosbridge"""
        print(f"🔄 Подключение к {self.ros_url}...")
        
        parsed = urllib.parse.urlparse(self.ros_url)
        host = parsed.hostname or 'localhost'
        port = parsed.port or 9090
        
        self.client = roslibpy.Ros(host=host, port=port)
        self.client.on_error = self._on_error
        self.client.run()
        
        timeout = 5
        start = time.time()
        while time.time() - start < timeout:
            if self.client.is_connected:
                self.connected = True
                print(f"✅ Подключено к ROS bridge!")
                
                self.cmd_vel = roslibpy.Topic(self.client, '/cmd_vel', 'geometry_msgs/msg/Twist')
                
                print(f"🔄 Подписка на /freight/base_scan")
                self.scan_sub = roslibpy.Topic(self.client, '/freight/base_scan', 'sensor_msgs/msg/LaserScan')
                self.scan_sub.subscribe(self._scan_callback)
                
                print(f"🔄 Подписка на /model_pose")
                self.odom_sub = roslibpy.Topic(self.client, '/model_pose', 'geometry_msgs/msg/PoseStamped')
                self.odom_sub.subscribe(self._odom_callback)
                
                print(f"🔄 Подписка на цель: {self.goal_topic}")
                self.goal_sub = roslibpy.Topic(self.client, self.goal_topic, 'geometry_msgs/msg/PoseStamped')
                self.goal_sub.subscribe(self._goal_callback)

                break
            time.sleep(0.0001)  # минимальная задержка
    
    def _on_error(self, error):
        print(f"❌ Ошибка ROS: {error}")
        with self.lock:
            self.connected = False
    
    def _scan_callback(self, msg):
        with self.lock:
            self.last_scan_raw = msg['ranges']
            ranges = np.array(msg['ranges'])
            ranges = np.clip(ranges, 0, 10)
            ranges = np.nan_to_num(ranges, nan=10.0, posinf=10.0, neginf=0.0)
            
            if len(ranges) > 0:
                sectors = np.array_split(ranges, 9)
                self.last_scan_sectors = np.array([np.min(s) for s in sectors], dtype=np.float32)
                
                if np.min(self.last_scan_sectors) < 0.3:
                    self.collision = True
    
    def _odom_callback(self, msg):
        with self.lock:
            try:
                self.last_position = np.array([
                    msg['pose']['position']['x'],
                    msg['pose']['position']['y']
                ], dtype=np.float32)
                
                self.trajectory.append(self.last_position.copy())
                if len(self.trajectory) > 100:
                    self.trajectory.pop(0)
                    
            except Exception as e:
                print(f"❌ Ошибка в odom: {e}")
    
    def _goal_callback(self, msg):
        with self.lock:
            try:
                self.goal_position = np.array([
                    msg['pose']['position']['x'],
                    msg['pose']['position']['y']
                ], dtype=np.float32)
                self.goal_received = True
            except Exception as e:
                print(f"❌ Ошибка обработки цели: {e}")
    
    def _send_action(self, action):
        """Отправка команды роботу с увеличенной скоростью"""
        if not self.connected or not self.cmd_vel:
            return False
        
        try:
            # ⚡ УВЕЛИЧИВАЕМ СКОРОСТЬ
            linear_x = float(action[0] * 0.5 * self.speed_multiplier)
            angular_z = float(action[1] * 1.0 * self.speed_multiplier)
            
            msg = {
                'linear': {'x': linear_x, 'y': 0.0, 'z': 0.0},
                'angular': {'x': 0.0, 'y': 0.0, 'z': angular_z}
            }
            
            self.cmd_vel.publish(roslibpy.Message(msg))
            return True
        except Exception as e:
            print(f"Ошибка отправки команды: {e}")
            return False
    
    def _get_obs(self):
        with self.lock:
            lidar = self.last_scan_sectors.copy()
            position = self.last_position.copy()
            
            if self.goal_received:
                goal = self.goal_position.copy()
                self.distance_to_goal = np.linalg.norm(position - goal)
            else:
                goal = np.array([0.0, 0.0], dtype=np.float32)
                self.distance_to_goal = float('inf')
        
        return np.concatenate([lidar, position, goal]).astype(np.float32)
    
    def _compute_reward(self, obs, action):
        """Расчёт награды"""
        position = obs[9:11]
        goal = obs[11:13]
        
        if not self.goal_received:
            return -self.step_penalty
        
        dist_to_goal = np.linalg.norm(position - goal)
        
        # Базовая награда
        reward = -dist_to_goal * 0.1
        
        # Штраф за коллизию
        if self.collision:
            reward -= self.collision_penalty
            self.collision_count += 1
        
        # Штраф за шаг
        reward -= self.step_penalty
        
        # Бонус за цель
        if dist_to_goal < self.goal_distance_threshold:
            reward += self.goal_reward
            self.goal_count += 1
            self.goal_reached = True
        
        return float(reward)
    
    def _is_done(self, obs):
        """Проверка завершения эпизода"""
        if self.goal_reached:
            return True
        
        if self.current_step >= self.max_steps:
            return True
        
        return False
    
    def reset(self, seed=None, options=None):
        """Сброс среды"""
        super().reset(seed=seed)
        
        self.current_step = 0
        self.collision = False
        self.goal_reached = False
        self.trajectory = []
        
        # ⚡ МГНОВЕННАЯ ТЕЛЕПОРТАЦИЯ
        self.reset_robot()
        
        # ⚡ МГНОВЕННАЯ ЦЕЛЬ (без ожидания из Unity)
        angle = np.random.uniform(0, 2*np.pi)
        distance = np.random.uniform(3.0, 7.0)
        self.goal_position = np.array([
            distance * np.cos(angle),
            distance * np.sin(angle)
        ], dtype=np.float32)
        self.goal_received = True
        
        self._send_action([0.0, 0.0])
        self.prev_distance = np.linalg.norm(self.last_position - self.goal_position)
        
        obs = self._get_obs()
        return obs, {"goal": self.goal_position.tolist()}
    
    def step(self, action):
        """Шаг среды"""
        self.current_step += 1
        
        for i in range(self.action_repeat):
            self._send_action(action)
            if i % 5 == 0:
                time.sleep(0.001)
        
        obs = self._get_obs()
        reward = self._compute_reward(obs, action)
        self.last_reward = reward
        
        terminated = self._is_done(obs)
        truncated = False
        
        # 👇 СОЗДАЕМ info
        info = {
            "collision": self.collision,
            "goal_reached": self.goal_reached,
            "position": self.last_position.copy(),
            "goal_position": self.goal_position.copy() if self.goal_received else None,
            "distance_to_goal": float(self.distance_to_goal) if self.goal_received else -1,
            "min_lidar": float(np.min(obs[:9])) if len(obs) >= 9 else 0
        }
        
        return obs, reward, terminated, truncated, info
        
    def reset_robot(self):
        """Публикует команду ресета в топик"""
        if not self.connected:
            return False
        
        try:
            reset_pub = roslibpy.Topic(self.client, '/reset_robot', 'std_msgs/msg/Empty')
            reset_pub.publish(roslibpy.Message({}))
            reset_pub.unadvertise()
            return True
        except Exception as e:
            print(f"❌ Ошибка ресета: {e}")
            return False
    
    def get_scan_for_web(self):
        with self.lock:
            if self.last_scan_raw is not None and len(self.last_scan_raw) > 0:
                step = max(1, len(self.last_scan_raw) // 36)
                return self.last_scan_raw[::step][:36]
            return []
    
    def get_status(self):
        status = {
            "connected": self.connected,
            "position": self.last_position.tolist() if hasattr(self.last_position, 'tolist') else self.last_position,
            "collision": self.collision,
            "step": self.current_step,
            "scan": self.get_scan_for_web(),
            "trajectory": self.trajectory[-50:] if self.trajectory else [],
            "goal_position": self.goal_position.tolist(),
            "distance_to_goal": float(self.distance_to_goal)
        }
        return status
    
    def close(self):
        if self.client and self.client.is_connected:
            self.client.terminate()