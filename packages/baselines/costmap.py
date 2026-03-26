import numpy as np

def build_cost_map(elevation, obstacles, reward_config):
    h, w = elevation.shape
    cost_map = np.zeros((h, w), dtype=np.float32)

    for i in range(h):
        for j in range(w):

            cost = 0.0

            # ШАГ
            cost += reward_config["W_STEP"]

            # ВЫСОТА
            if i > 0:
                slope = abs(elevation[i, j] - elevation[i-1, j])
                cost += reward_config["W_HEIGHT"] * slope

            # ПРЕПЯТСТВИЯ
            if obstacles[i, j] == 1:  # куст
                cost += reward_config["W_COLLISION_BUSH"]

            elif obstacles[i, j] == 2:  # дерево
                return_block = reward_config["W_COLLISION_TREE"]
                cost = return_block + 1e5

            cost_map[i, j] = cost

    return cost_map
