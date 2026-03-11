import numpy as np


def build_cost_map(size=(100,100), seed=50):

    np.random.seed(seed)

    cost_map = np.random.uniform(1, 4, size)

    # случайные препятствия
    for _ in range(200):

        x = np.random.randint(0, size[0])
        y = np.random.randint(0, size[1])

        cost_map[x,y] = np.inf

    return cost_map
