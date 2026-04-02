from __future__ import annotations
import math
from collections import deque
import numpy as np


def cell_passable(env, x: int, y: int) -> bool:

    n = env.grid_world_size

    if not (0 <= x < n and 0 <= y < n):
        return False

    passability = env.word_layers.get("passability")

    if passability is not None and passability[x][y] == 0.0:
        return False

    if env.word_layers["intruders"][x][y] != 0.0:
        return False

    return True


def pick_initial_target(env):

    value = env.word_layers["value"]
    intruders = env.word_layers["intruders"]
    passability = env.word_layers.get("passability")

    mask = (value > 0) & (intruders == 0)

    if passability is not None:
        mask &= (passability > 0)

    candidates = np.argwhere(mask)

    if len(candidates) == 0:
        return None

    rng = getattr(env, "np_random", np.random.default_rng())
    idx = rng.integers(len(candidates))

    return tuple(int(v) for v in candidates[idx])


def find_nearest_valuable(env, x: int, y: int):

    value = env.word_layers["value"]
    intruders = env.word_layers["intruders"]
    passability = env.word_layers.get("passability")

    mask = (value > 0) & (intruders == 0)

    if passability is not None:
        mask &= (passability > 0)

    candidates = np.argwhere(mask)

    if len(candidates) == 0:
        return None

    dists = (
        np.abs(candidates[:, 0] - x) +
        np.abs(candidates[:, 1] - y)
    )

    idx = int(np.argmin(dists))

    return tuple(int(v) for v in candidates[idx])


def find_exit_cell(env, x: int, y: int):

    n = env.grid_world_size

    border = (
        [(bx, 0)   for bx in range(n)] +
        [(bx, n-1) for bx in range(n)] +
        [(0, by)   for by in range(1, n-1)] +
        [(n-1, by) for by in range(1, n-1)]
    )

    best = None
    best_dist = math.inf

    for bx, by in border:
        d = abs(x - bx) + abs(y - by)
        if d < best_dist:
            best_dist = d
            best = (bx, by)

    return best


def bfs(env, start, goal):

    n = env.grid_world_size
    intruders = env.word_layers["intruders"]
    passability = env.word_layers.get("passability")

    queue   = deque([(start, [start])])
    visited = {start}

    while queue:

        (cx, cy), path = queue.popleft()

        if (cx, cy) == goal:
            return path

        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:

            nx, ny = cx + dx, cy + dy

            if not (0 <= nx < n and 0 <= ny < n):
                continue

            if (nx, ny) in visited:
                continue

            if passability is not None and passability[nx][ny] == 0.0:
                continue

            if (nx, ny) != goal and intruders[nx][ny] != 0.0:
                continue

            visited.add((nx, ny))
            queue.append(((nx, ny), path + [(nx, ny)]))

    return []
