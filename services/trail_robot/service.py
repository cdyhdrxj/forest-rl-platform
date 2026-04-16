# services/trail_robot/service.py
from apps.api.sb3.sb3_trainer import SB3Trainer
from services.trail_robot.wrapper import TrailRobotGymWrapper
from services.trail_robot.callback import TrailRobotCallback

class TrailRobotService(SB3Trainer):
    def __init__(self):
        self.env = None
        self.model = None
        self.training_state = self._make_state()
        self.env = self._build_env({})
    
    def _build_env(self, params):
        return TrailRobotGymWrapper(ros_url="ws://localhost:9090")
    
    def _make_callback(self):
        return TrailRobotCallback(self.training_state)
    
    def get_state(self):
        if self.env:
            status = self.env.get_status() if hasattr(self.env, 'get_status') else {}
            self.training_state.update({
                "agent_pos": status.get("position", [0,0]),
                "is_collision": status.get("collision", False),
                "connected": status.get("connected", False)
            })
        return self.training_state
    
    @staticmethod
    def _make_state():
        return {
            "running": False, "episode": 0, "step": 0,
            "total_reward": 0, "last_episode_reward": 0,
            "agent_pos": [0,0], "is_collision": False
        }
    
    def start(self, params): super().start(params)
    def stop(self): super().stop()
    def reset(self): super().reset()
    def _reset_counters(self): pass