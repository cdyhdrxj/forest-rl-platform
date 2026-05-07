import time
from stable_baselines3.common.callbacks import BaseCallback
from services.patrol_planning.service.models import GridWorldTrainState

TRAJECTORY_MAX_LEN = 200


class GridWorldCallback(BaseCallback):
    """Запись в GridWorldTrainState параметров среды во время обучения"""

    def __init__(self, state: GridWorldTrainState):
        super().__init__()
        self.state = state
        self.episode_reward = 0.0
        self.sent_terrain = False

    def _on_step(self) -> bool:
        if not self.state["running"]:
            return False

        # Задержка скорости обучения
        time.sleep(0.50)
        
        #Всё пишется внутри среды в соответствующую модель.

        return True