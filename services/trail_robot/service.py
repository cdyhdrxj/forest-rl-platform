from apps.api.sb3.sb3_trainer import SB3Trainer
from services.trail_robot.wrapper import TrailRobotGymWrapper
from services.trail_robot.callback import TrailRobotCallback

class TrailRobotService(SB3Trainer):
    def __init__(self):
        self.env = None
        self.model = None
        self.training_state = self._make_state()
        self.loaded_wrapper_kwargs = {}
        # Не создаём env здесь — дождёмся load_scenario
    
    def _build_env(self, params):
        """Создаём среду с параметрами из конфига"""
        kwargs = dict(self.loaded_wrapper_kwargs or {})
        kwargs["ros_url"] = "ws://ros2:9090"
        return TrailRobotGymWrapper(**kwargs)
    
    def _make_callback(self):
        return TrailRobotCallback(self.training_state)
    
    def get_state(self):
        """Возвращаем состояние для фронтенда — ВАЖНО: agent_pos = [[x,y]]"""
        if self.env:
            status = self.env.get_status() if hasattr(self.env, 'get_status') else {}
            agent_pos_raw = status.get("position", [0, 0])[:2] if status.get("position") else [0, 0]
            
            self.training_state.update({
                "agent_pos": [agent_pos_raw],  # ← list of lists для runtime_monitor
                "is_collision": status.get("collision", False),
                "connected": status.get("connected", False),
                "goal_pos": status.get("goal_position", [0, 0]),
                "trajectory": status.get("trajectory", []),
                "goal_count": getattr(self.env, 'goal_count', 0),
                "collision_count": getattr(self.env, 'collision_count', 0),
                "hp": getattr(self.env, 'hp', 100.0),
                "mode": "trail"
            })
        return self.training_state
    
    @staticmethod
    def _make_state():
        return {
            "running": False, "episode": 0, "step": 0,
            "total_reward": 0, "last_episode_reward": 0,
            "agent_pos": [[0, 0]], "is_collision": False,
            "goal_pos": [0, 0], "trajectory": [],
            "goal_count": 0, "collision_count": 0,
            "hp": 100.0, "mode": "trail"
        }
    
    def load_scenario(self, scenario, runtime_config=None):
        """Читаем конфиг и настраиваем награды"""
        cfg = runtime_config or {}
        target_cfg = cfg.get("target_config", {})
        robot_cfg = cfg.get("robot_config", {})
        
        # Тип робота из конфига
        robot_type = int(robot_cfg.get("type", 0))
        
        # Параметры наград — из конфига или стандартные
        self.loaded_wrapper_kwargs = {
            "goal_reward": float(cfg.get("goal_reward", 80.0)),
            "collision_penalty": float(cfg.get("collision_penalty", 12.0)),
            "step_penalty": float(cfg.get("step_penalty", 0.01)),
            "max_steps": int(cfg.get("max_steps", 500)),
            "goal_distance_threshold": float(target_cfg.get("radius", 0.5)),
            "progress_weight": float(cfg.get("progress_weight", 40.0)),
            "angle_penalty": float(cfg.get("angle_penalty", 3.0)),
            "bush_reward": float(cfg.get("bush_reward", 0.01)),
            "flip_penalty": float(cfg.get("flip_penalty", 50.0)),
            "robot_type": robot_type,
        }

        # Создаём среду с параметрами
        #self.env = self._build_env({})
        #return self.env
    
    def start(self, params): super().start(params)
    def stop(self): super().stop()
    def reset(self): super().reset()
    def _reset_counters(self): pass