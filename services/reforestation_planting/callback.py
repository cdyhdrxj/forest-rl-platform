import time

from stable_baselines3.common.callbacks import BaseCallback

from services.reforestation_planting.models import PlantingTrainState


class PlantingCallback(BaseCallback):
    def __init__(self, state: PlantingTrainState):
        super().__init__()
        self.state = state

    def _on_step(self) -> bool:
        if not self.state["running"]:
            return False
        time.sleep(0.01)
        return True
