# services/trail_robot/callback.py
from stable_baselines3.common.callbacks import BaseCallback

class TrailRobotCallback(BaseCallback):
    def __init__(self, training_state):
        super().__init__()
        self.training_state = training_state
        self.episode_reward = 0.0
    
    def _on_step(self):
        if not self.training_state.get("running", False):
            return False
        
        # Обновляем шаг
        self.training_state["step"] = self.num_timesteps
        
        # Награда
        reward = self.locals["rewards"][0]
        self.episode_reward += float(reward)
        
        # Инфо из среды
        if self.locals["infos"] and "position" in self.locals["infos"][0]:
            info = self.locals["infos"][0]
            self.training_state["agent_pos"] = info["position"].tolist()
            self.training_state["is_collision"] = info.get("collision", False)
        
        # Конец эпизода
        if self.locals["dones"][0]:
            self.training_state["episode"] += 1
            self.training_state["last_episode_reward"] = self.episode_reward
            self.training_state["total_reward"] += self.episode_reward
            self.episode_reward = 0
        
        return True