from __future__ import annotations
import math
from collections import deque
import numpy as np


def cell_passable(env, x: int, y: int) -> bool:

    n = env.grid_world_size

    if not (0 <= x < n and 0 <= y < n):
        return False

    passability = env.world_layers.get("passability")

    if passability is not None and passability[x][y] == 0.0:
        return False

    if env.world_layers["intruders"][x][y] != 0.0:
        return False

    return True


def pick_initial_target(env):

    value = env.world_layers["value"]
    intruders = env.world_layers["intruders"]
    passability = env.world_layers.get("passability")

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

    value = env.world_layers["value"]
    intruders = env.world_layers["intruders"]
    passability = env.world_layers.get("passability")

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
    intruders = env.world_layers["intruders"]
    passability = env.world_layers.get("passability")

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

# A*, ищущий путь до цели 
def target2path(env, start, goal, pass_mltply = 10):

    u = env.world_layers["passability"]
    a = env.agent
    i = env.world_layers['intruders']
    
    rows, cols = len(u), len(u[0])

    # эвристика
    def h(cell):
        return (abs(cell[0] - goal[0]) + abs(cell[1] - goal[1])) + (1- u[cell[0]][cell[1]])*pass_mltply

    open_list = [start]
    came_from = {}
    g_score = {start: 0}
    closed = set()

    directions = [(-1,0), (1,0), (0,-1), (0,1)]

    while open_list:
        current = min(open_list, key=lambda c: g_score[c] + h(c))
        open_list.remove(current)

        if current == goal:
            # восстановление пути
            path = [current]
            while current in came_from:
                current = came_from[current]
                path.append(current)
            path.reverse()

            cost = g_score[goal] + h(goal)   # ← стоимость с эвристикой
            return path, cost

        closed.add(current)

        for dx, dy in directions:
            neighbor = (current[0]+dx, current[1]+dy)

            if not (0 <= neighbor[0] < rows and 0 <= neighbor[1] < cols):
                continue

            if u[neighbor[0]][neighbor[1]] == 0:
                continue

            if neighbor != goal:
                if i[neighbor[0]][neighbor[1]] == 1:
                    continue

                if neighbor[0] == a.x and neighbor[1] == a.y:
                    continue

            if neighbor in closed:
                continue

            tentative_g = g_score[current] + 1

            if neighbor not in g_score or tentative_g < g_score[neighbor]:
                g_score[neighbor] = tentative_g
                came_from[neighbor] = current
                if neighbor not in open_list:
                    open_list.append(neighbor)

    return None, float("inf")

def get_neighbors_radius_1(pos, rows, cols):
    """
    pos: (x, y)
    rows, cols: размеры карты
    return: список соседних клеток в радиусе 1
    """
    x, y = pos
    neighbors = []

    for dx in [-1, 0, 1]:
        for dy in [-1, 0, 1]:
            nx = x + dx
            ny = y + dy

            # пропускаем саму клетку
            # if dx == 0 and dy == 0:
            #     continue

            # проверка границ
            if 0 <= nx < rows and 0 <= ny < cols:
                neighbors.append((nx, ny))

    return neighbors

def get_border_positions(rows, cols):
    border = []

    # левая и правая границы
    for x in range(rows):
        border.append((x, 0))
        border.append((x, cols - 1))

    # верхняя и нижняя границы
    for y in range(cols):
        border.append((0, y))
        border.append((rows - 1, y))

    # убираем дубликаты углов
    border = list(set(border))

    return border

# class Agent:
#     def __init__(self, x, y):
#         self.x = x
#         self.y = y


# class Env:
#     def __init__(self):
#         self.world_layers = {
#             # 1 = можно идти, 0 = стена
#             "passability": np.array([
#     [0.8621479,  0.44488984, 0.6262721,  0.8822823,  0.0,        0.6765684,  0.114948705, 0.5430609],
#     [0.6101762,  0.12423932, 0.26696867, 0.5138896,  0.9412351,  0.0,        0.10441818,  0.80823064],
#     [0.12189217, 0.4326768,  0.5934967,  0.22954984, 0.56678814, 0.26824993, 0.33429992,  0.4699934],
#     [0.54779005, 0.20281328, 0.57758516, 0.26335886, 0.3913955,  0.34717393, 0.0,         0.37257412],
#     [0.0,        0.5562958,  0.63317525, 0.0,        0.87725616, 0.0,        0.0,         0.9150069],
#     [0.21617368, 0.598346,   0.9910849,  0.9074836,  0.87830377, 0.61706173, 0.17243142,  0.0],
#     [0.704682,   0.5999211,  0.56317705, 0.14194463, 0.14995259, 0.70917314, 0.18224716,  0.8903187],
#     [0.0,        0.5701598,  0.0,        0.46995604, 0.33834448, 0.9461003,  0.536121,    0.47560766],
#         ]),
#             # 0 = пусто, 1 = нарушитель
#             "intruders": np.zeros((8, 8), dtype=int)
#         }

#         # агент (его нельзя пересекать)
#         self.agent = Agent(0, 4)
        


# env = Env()

# start = (0, 0)
# goal = (5,5)

# path = target2path(env, start, goal)

# print(path)