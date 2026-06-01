import gymnasium as gym
from gymnasium import spaces
import numpy as np
import roslibpy
import time
import threading
import urllib.parse
from typing import Optional
import math
from services.trail_robot.lidar_processor import LidarProcessor

class TrailRobotGymWrapper(gym.Env):
    """
    Обёртка для робота через rosbridge (WebSocket)
    Полностью совместима с Stable Baselines 3
    """
    
    metadata = {"render_modes": ["human", "rgb_array"], "render_fps": 10}
    
    def __init__(self, 
                 ros_url: str = "ws://ros2:9090",
                 goal_topic: str = "/goal_pose",
                 max_steps: int = 500,
                 goal_reward: float = 80.0,
                 collision_penalty: float = 12.0,
                 step_penalty: float = 0.01,
                 goal_distance_threshold: float = 0.5,
                 progress_weight: float = 40.0,
                 angle_penalty: float = 3.0,
                 bush_reward: float = 0.01,
                 flip_penalty: float = 50.0,
                 robot_type: int = 1,
                 render_mode: Optional[str] = None):
        
        super().__init__()
        self.robot_type = robot_type
        # Параметры
        self.ros_url = ros_url
        self.goal_topic = goal_topic
        self.max_steps = max_steps
        self.goal_reward = goal_reward
        self.collision_penalty = collision_penalty
        self.step_penalty = step_penalty
        self.goal_distance_threshold = goal_distance_threshold
        self.render_mode = render_mode
        self.progress_weight = progress_weight
        self.angle_penalty = angle_penalty
        self.bush_reward = bush_reward
        self.flip_penalty = flip_penalty
        self.last_yaw = 0.0

        # Данные для обучения
        #self.last_scan_sectors = np.zeros(9, dtype=np.float32)
        self.last_position = np.array([0.0, 0.0, 0.0], dtype=np.float32)
        self.goal_position = np.array([0.0, 0.0, 0.0], dtype=np.float32)
        self.lidar_processor = LidarProcessor(degrees_per_sector=5, max_range=5.0)
        self.n_lidar_sectors = self.lidar_processor.n_sectors  # 36 секторов
        self.last_scan_sectors = np.zeros(self.n_lidar_sectors, dtype=np.float32)

        # Данные о цели
        self.goal_received = False
        self.distance_to_goal = 0.0
        self.prev_distance = 0.0
        
        self.hp = 100.0
        self.last_event_type = 0
        self.last_reward = 0.0
        self.collision = False
        self.goal_reached = False
        self.current_step = 0
        
        # Данные для визуализации
        self.last_scan_raw = None
        self.trajectory = []
        
        self.goal_count = 0
        self.collision_count = 0
        
        # 🆕 Переменные для событий из /env/events
        self.collision_from_event = False
        self.goal_from_event = False
        self.intruder_from_event = False
        self.last_event_time = 0
        self.event_cooldown = 0.5
        
        # Параметры ускорения
        self.action_repeat = 20
        self.speed_multiplier = 4.0
        
        # ROS соединение
        self.client = None
        self.cmd_vel = None
        self.scan_sub = None
        self.odom_sub = None
        self.goal_sub = None
        self.event_sub = None
        self.connected = False
        self.lock = threading.Lock()
        
        # Пространство действий
        self.action_space = spaces.Box(
            low=np.array([-1.0, -1.0], dtype=np.float32),
            high=np.array([1.0, 1.0], dtype=np.float32),
            dtype=np.float32
        )
        
        # Пространство наблюдений(координаты(2), цель(2), угол(2), лидар(n))
        self.observation_space = spaces.Box(
            low=-np.inf,
            high=np.inf,
            shape=(self.n_lidar_sectors + 8,),
            dtype=np.float32
        )
        
        self._connect_ros()
    
    def _connect_ros(self):
        """Подключение к rosbridge через общий объект ros"""
        from services.ros_2.ros_api_connection import ros
        
        print(f"🔄 Подключение к ROS через общий клиент...")
        
        if not ros.connected:
            print("❌ ROS не подключен")
            return
        
        self.client = ros.client
        self.connected = True
        print(f"✅ Подключено к ROS bridge!")

        prefix = f"robot_{self.robot_type}"
        # Издатель команд
        self.cmd_vel = roslibpy.Topic(self.client, f'/{prefix}/cmd_vel', 'geometry_msgs/msg/Twist')
        
        # Подписка на лидар
        print(f"🔄 Подписка на /robot_1/scan")
        self.scan_sub = roslibpy.Topic(self.client, f'/{prefix}/scan', 'sensor_msgs/msg/LaserScan')
        self.scan_sub.subscribe(self._scan_callback)
        
        # Подписка на одометрию
        print(f"🔄 Подписка на /robot_1/odom")
        self.odom_sub = roslibpy.Topic(self.client, f'/{prefix}/odom', 'nav_msgs/msg/Odometry')
        self.odom_sub.subscribe(self._odom_callback)
        
        # Подписка на цель
        print(f"🔄 Подписка на цель: {self.goal_topic}")
        self.goal_sub = roslibpy.Topic(self.client, self.goal_topic, 'geometry_msgs/msg/PoseStamped')
        self.goal_sub.subscribe(self._goal_callback)
        
        # Подписка на события
        print(f"🔄 Подписка на /env/events")
        self.event_sub = roslibpy.Topic(self.client, '/env/events', 'forest_msgs/Event')
        self.event_sub.subscribe(self._event_callback)

    def _on_error(self, error):
        print(f"❌ Ошибка ROS: {error}")
        with self.lock:
            self.connected = False
    
    def _scan_callback(self, msg):
        with self.lock:
            self.last_scan_raw = msg['ranges']
            self.last_scan_sectors = self.lidar_processor.process(msg['ranges'])
            if self.lidar_processor.get_min(self.last_scan_sectors) < 0.3:
                self.collision = True
    
    def _odom_callback(self, msg):
        with self.lock:
            try:
                self.last_position = np.array([
                    msg['pose']['pose']['position']['x'],
                    msg['pose']['pose']['position']['y'],
                    msg['pose']['pose']['position']['z']
                ], dtype=np.float32)
                
                # Yaw из кватерниона
                qz = msg['pose']['pose']['orientation']['z']
                qw = msg['pose']['pose']['orientation']['w']
                self.last_yaw = math.atan2(2 * qw * qz, 1 - 2 * qz * qz)

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
                    msg['pose']['position']['y'],
                    msg['pose']['position']['z']  
                ], dtype=np.float32)
                self.goal_received = True
            except Exception as e:
                print(f"❌ Ошибка обработки цели: {e}")
    
    def _event_callback(self, msg):
        """
        Обработка событий из Unity
        Типы событий:
        0 = GOAL - достижение цели
        1 = FLIP - переворот
        2 = COLLISION_PASSABLE - столкновение с проходимым
        3 = COLLISION_IMPASSABLE - столкновение с непроходимым
        4 = INTRUDER_APPEARED - появился нарушитель
        5 = INTRUDER_DETECTED - обнаружен нарушитель
        6 = INTRUDER_CAUGHT - пойман нарушитель
        """
        with self.lock:
            self.last_event_type = event_type
            event_type = msg.get('event_type', 0)
            robot_id = msg.get('robot_id', 0)
            position = msg.get('position') or {}
            x = position.get('x', 0)
            y = position.get('y', 0)
            intruder_id = msg.get('intruder_id', -1)
            
            # Проверяем, что событие для нашего робота (если robot_id не 0)
            if robot_id != 0 and robot_id != 1:  # robot_1
                return
            
            current_time = time.time()
            if current_time - self.last_event_time < self.event_cooldown:
                return
            self.last_event_time = current_time
            
            if event_type == 0:  # GOAL
                print(f"🏆 СОБЫТИЕ: Достигнута цель! (x={x}, y={y})")
                self.goal_from_event = True
                
            elif event_type == 1:  # FLIP
                print(f"⚠️ СОБЫТИЕ: Робот перевернулся!")
                self.collision_from_event = True
                
            elif event_type == 2:  # COLLISION_PASSABLE
                print(f"🌿 СОБЫТИЕ: Столкновение с проходимым объектом")
                self.collision_from_event = True
                
            elif event_type == 3:  # COLLISION_IMPASSABLE
                print(f"🌲 СОБЫТИЕ: Столкновение с непроходимым объектом!")
                self.collision_from_event = True
                
            elif event_type == 4:  # INTRUDER_APPEARED
                print(f"🦹 СОБЫТИЕ: Появился нарушитель!")
                
            elif event_type == 5:  # INTRUDER_DETECTED
                print(f"🔍 СОБЫТИЕ: Нарушитель обнаружен!")
                
            elif event_type == 6:  # INTRUDER_CAUGHT
                print(f"✅ СОБЫТИЕ: Нарушитель пойман! intruder_id={intruder_id}")
                self.intruder_from_event = True
    
    def _send_action(self, action):
        """Отправка команды роботу"""
        if not self.connected or not self.cmd_vel:
            return False
        
        try:
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
                
                dx = goal[0] - position[0]
                dy = goal[1] - position[1]
                desired_angle = math.atan2(dy, dx)
                heading_error = math.atan2(
                    math.sin(desired_angle - self.last_yaw),
                    math.cos(desired_angle - self.last_yaw)
                )
                angle_features = np.array([math.sin(heading_error), math.cos(heading_error)], dtype=np.float32)
            else:
                goal = np.array([0.0, 0.0, 0.0], dtype=np.float32)
                angle_features = np.array([0.0, 0.0], dtype=np.float32)
                self.distance_to_goal = float('inf')
        
        return np.concatenate([position, goal, angle_features, lidar]).astype(np.float32)
    
    def _compute_reward(self, obs, action):
        """Расчёт награды: прогресс, столкновения, HP, переворот"""
        n = self.n_lidar_sectors
        position = obs[0:3]
        goal = obs[3:6]

        
        if not self.goal_received:
            return -self.step_penalty
        
        dist_to_goal = np.linalg.norm(position - goal)
        progress = self.prev_distance - dist_to_goal
        self.prev_distance = dist_to_goal
        
        prev_hp = self.hp
        reward = 0.0
        
        # Базовые
        reward -= self.step_penalty                          
        reward -= self.angle_penalty * abs(float(action[1])) 
        reward += self.progress_weight * progress           
        
        # Столкновения
        if self.collision_from_event:
            if self.last_event_type == 2:  # COLLISION_PASSABLE (куст)
                reward += self.bush_reward * max(progress, 0)  # W_BUSH = 0.01
            elif self.last_event_type == 3:  # COLLISION_IMPASSABLE (дерево)
                velocity = abs(float(action[0]) * 0.5 * self.speed_multiplier)
                damage = self.collision_penalty * velocity   
                self.hp -= damage
            elif self.last_event_type == 1:  # FLIP (переворот)
                reward -= self.flip_penalty                   
            
            self.collision_count += 1
            self.collision_from_event = False
        
        # Штраф за потерю HP
        hp_loss = prev_hp - self.hp
        reward -= 1.0 * hp_loss
        
        # Достижение цели
        if self.goal_from_event or dist_to_goal < self.goal_distance_threshold:
            reward += self.goal_reward                       
            self.goal_count += 1
            self.goal_reached = True
            self.goal_from_event = False
        
        return float(reward)
    
    def _is_done(self, obs):
        """Проверка завершения эпизода"""
        if self.goal_reached: return True
        if self.current_step >= self.max_steps: return True 
        if self.hp <= 0.0: return True          #  Исчерпан ресурс
        if self.last_event_type == 1: return True  #  FLIP (переворот)
        return False
    
    def reset_environment(self):
        """
        Вызывает сервис /env/reset для полного сброса среды
        """
        if not self.connected:
            print("❌ Не подключено к ROS, не могу вызвать сервис /env/reset")
            return False
        
        try:
            reset_service = roslibpy.Service(self.client, '/env/reset', 'std_srvs/Trigger')
            request = roslibpy.ServiceRequest()
            response = reset_service.call(request)
            
            if response and response.get('success', False):
                print(f"✅ Среда сброшена: {response.get('message', '')}")
                return True
            else:
                print(f"⚠️ Ошибка сервиса: {response.get('message', 'Unknown')}")
                return False
                
        except Exception as e:
            print(f"❌ Исключение при вызове /env/reset: {e}")
            return False
    
    def reset(self, seed=None, options=None):
        """Сброс среды"""
        super().reset(seed=seed)
        
        # Сбрасываем флаги событий
        self.collision_from_event = False
        self.goal_from_event = False
        self.intruder_from_event = False
        self.hp = 100.0
        # Вызываем сервис /env/reset
        self.reset_environment()
        
        # Сбрасываем внутренние счётчики
        self.current_step = 0
        self.collision = False
        self.goal_reached = False
        self.trajectory = []
        
        if not self.goal_received:
            time.sleep(0.5)
        if not self.goal_received:
            angle = np.random.uniform(0, 2*np.pi)
            distance = np.random.uniform(3.0, 7.0)
            self.goal_position = np.array([
                distance * np.cos(angle),
                distance * np.sin(angle),
                np.random.uniform(0, 2.0)  
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

        position = self.last_position.copy()
        goal = self.goal_position.copy() if self.goal_received else None
        lidar = self.last_scan_sectors.copy()
            
            # Физические команды (после масштабирования)
        cmd_linear = float(action[0] * 0.5 * self.speed_multiplier)
        cmd_angular = float(action[1] * 1.0 * self.speed_multiplier)
            
        print(f"\n[STEP {self.current_step:4d}] " + "-"*60)
        print(f"  Робот:  pos=({position[0]:6.2f}, {position[1]:6.2f}, {position[2]:6.2f}) м")
        if goal is not None:
            print(f"  Цель:   pos=({goal[0]:6.2f}, {goal[1]:6.2f}, {goal[2]:6.2f}) м | dist={np.linalg.norm(position[:2]-goal[:2]):5.2f} м")
        print(f"  Команда: v={cmd_linear:5.2f} м/с, ω={cmd_angular:5.2f} рад/с")
        print(f"  Reward: {reward:7.3f} | HP: {self.hp:5.1f}")
        print(f"  LiDAR: {np.array2string(lidar, precision=2, separator=', ', suppress_small=True)}")
        if self.collision_from_event:
            print(f"  СОБЫТИЕ: event_type={self.last_event_type}")
        print("-"*60)
        
        info = {
            "collision": self.collision,
            "goal_reached": self.goal_reached,
            "position": self.last_position.copy(),
            "goal_position": self.goal_position.copy() if self.goal_received else None,
            "distance_to_goal": float(self.distance_to_goal) if self.goal_received else -1,
            "min_lidar": float(np.min(obs[:9])) if len(obs) >= 9 else 0
        }
        
        return obs, reward, terminated, truncated, info
    
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
