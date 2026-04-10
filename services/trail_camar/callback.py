import time
from stable_baselines3.common.callbacks import BaseCallback

TRAJECTORY_MAX_LEN = 200


class CamarCallback(BaseCallback):
    """Запись в training_state параметров среды во время обучения"""

    def __init__(self, state: dict):
        super().__init__()
        self.state = state
        self.episode_reward = 0.0
        self.sent_terrain = False

    def _on_step(self) -> bool:
        if not self.state["running"]:
            return False
        
        # Задержка скорости обучения
        time.sleep(0.01)

        # Получение состояния среды
        render = self.training_env.env_method("get_render_state")[0]
        infos = self.locals["infos"][0]

        on_goal = infos.get("on_goal", False)
        is_collision = infos.get("is_collision", False)

        # Обновление счётчиков событий
        if is_collision:
            self.state["collision_count"] += 1
        if on_goal:
            self.state["goal_count"] += 1

        # Обновление позиций для отрисовки
        self.state["agent_pos"] = render.get("agent_pos", [])
        self.state["goal_pos"] = render.get("goal_pos", [])
        self.state["landmark_pos"] = render.get("landmark_pos", [])
        self.state["is_collision"] = is_collision

        # Запись точки траектории 
        if render.get("agent_pos") and self.state.get("mode") == "trail":
            traj = self.state["trajectory"]
            traj.append(render["agent_pos"][0])

        # Накопление награды за эпизод
        reward = self.locals["rewards"][0]
        self.episode_reward += float(reward)
        self.state["step"] += 1
        self.state["total_reward"] = self.episode_reward
        self.state["new_episode"] = False

        # Отправка карты рельефа
        if not self.sent_terrain:
            terrain = self.training_env.env_method("get_terrain_map")[0]
            if terrain is not None:
                self.state["terrain_map"] = terrain
                self.sent_terrain = True

        # Обработка конца эпизода
        if self.locals["dones"][0]:
            self.state["episode"] += 1
            self.state["new_episode"] = True
            self.state["last_episode_reward"] = self.episode_reward
            self.episode_reward = 0.0
            self.state["trajectory"] = []

        return True