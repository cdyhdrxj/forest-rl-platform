import numpy as np
from collections import deque
from math import sqrt

OBSTACLE = 10
MAX_SWAMP = OBSTACLE - 1
STEPS = [(-1, 0), (1, 0), (0, -1), (0, 1)]

def generate_environment(n, m, p_walk, p_obstacle, number_mud, seed):
    rng = np.random.default_rng(seed=seed)

    # Находится ли точка внутри сетки
    def in_grid(i, j):
        return 0 <= i < n and 0 <= j < m

    # Возвращает манхеттенское расстояние между (i1, j1) и (i2, j2)
    def dist(i1, j1, i2, j2):
        return abs(i1 - i2) + abs(j1 - j2)

    def random_point():
        return (rng.integers(low=0, high=n), rng.integers(low=0, high=m))

    grid = [[-1] * m for _ in range(n)]
    start = random_point()
    finish = random_point()

    # --- Генерация случайного пути между стартом и финишем ---

    i, j = start
    fi, fj = finish

    while (i, j) != (fi, fj):
        grid[i][j] = 0
        # С вероятностью p_walk делаем шаг в случайную сторону (выбор стороны равновероятен)
        if rng.uniform() < p_walk:
            di, dj = STEPS[rng.integers(low=0, high=4)]
            ni, nj = i + di, j + dj
            if in_grid(ni, nj):
                i, j = ni, nj
        # С вероятностью 1 - p_walk - шаг в направлении финиша
        else:
            options = []
            for di, dj in STEPS:
                ni, nj = i + di, j + dj
                if in_grid(ni, nj) and dist(ni, nj, fi, fj) < dist(i, j, fi, fj):
                    options.append((ni, nj))

            i, j = rng.choice(options)

    grid[fi][fj] = 0

    # --- Генерация препятствий ---

    for i in range(n):
        for j in range(m):
            # Нельзя поставить препятствие на пути из старта в финиш
            # В остальных клетках - с вероятностью p_obstacle
            if grid[i][j] == -1 and rng.uniform() < p_obstacle:
                grid[i][j] = OBSTACLE

    # --- Генерация труднопроходимых поверхностей ---

    for _ in range(number_mud):
        # Случайная точка - центр "болота"
        ci, cj = random_point()

        strength = rng.integers(low=1, high=MAX_SWAMP+1)
        if grid[ci][cj] != OBSTACLE:
            grid[ci][cj] = strength

        queue = deque()
        queue.append((ci, cj, strength))

        # Будем распространять болото в ширину наподобие BFS
        while queue:
            i, j, s = queue.popleft()

            for di, dj in STEPS:
                ni, nj = i + di, j + dj
                # Вероятность распространения болота в соседную клетку
                p_mud = sqrt(s / 10)
                if in_grid(ni, nj) and grid[ni][nj] < 1 and rng.uniform() < p_mud:
                    # Проходимость соседней точки либо такая же, либо на 1 меньше
                    ns = grid[ni][nj] = rng.integers(low=max(1, s-1), high=s+1)
                    queue.append((ni, nj, ns))

    # --- В остальных точках - проходимая поверхность ---

    for i in range(n):
        for j in range(m):
            if grid[i][j] == -1:
                grid[i][j] = 0

    return grid, start, finish


# Случайно сгенерированная среда
class Environment:
    def __init__(self, n, m, p_walk, p_obstacle, number_mud, step_reward, finish_reward, seed):
        self.n = n
        self.m = m
        self.grid, self.start, self.finish = generate_environment(n, m, p_walk, p_obstacle, number_mud, seed)
        self.agent_position = self.start
        self.step_reward = step_reward
        self.finish_reward = finish_reward
        self.seed = seed
        self.rng = np.random.default_rng(seed=seed)

    # Является ли состояние терминальным
    @staticmethod
    def is_terminal(state):
        di, dj, _, _, _, _, _ = state
        return di == 0 and dj == 0


    # Возвращает состояние по клетке, в которой находится агент
    def get_state(self):
        i, j = self.agent_position
        fi, fj = self.finish

        # Возвращает знак x
        def sign(x):
            if x == 0:
                return 0
            return 1 if x > 0 else -1

        # Возвращает значение для клетки (x, y):
        # 0 - пустая клетка, 1 - труднопроходимая поверхность, 2 - препятствие или стена
        def cell(x, y):
            if not (0 <= x < self.n and 0 <= y < self.m):
                return 2
            val = self.grid[x][y]
            if val == 0:
                return 0
            if val == OBSTACLE:
                return 2
            return 1

        return (
            sign(i - fi),
            sign(j - fj),
            cell(i, j),
            cell(i-1, j),
            cell(i+1, j),
            cell(i, j-1),
            cell(i, j+1)
        )


    # Шаг агента - возвращает следующее состояние, вознаграждение
    def step(self, move):
        i, j = self.agent_position

        di, dj = {
            0: (-1, 0),  # наверх
            1: (1, 0),   # вниз
            2: (0, -1),  # влево
            3: (0, 1)    # вправо
        }[move]

        ni, nj = i + di, j + dj

        # Ушли за границы, не двигаемся с места
        if not (0 <= ni < self.n and 0 <= nj < self.m):
            reward = self.step_reward
            return self.get_state(), reward

        # Новое состояние
        if self.grid[ni][nj] != OBSTACLE:
            p_move = 1 - self.grid[i][j] / 10
            moved = self.rng.uniform() < p_move

            self.agent_position = (ni, nj) if moved else (i, j)

        reward = self.step_reward

        if self.agent_position == self.finish:
            reward = self.finish_reward

        return self.get_state(), reward


class EnvParams:
    def __init__(self, n_range, m_range, p_walk_range, p_obstacle_range, mud_range, step_reward, finish_reward, seed):
        self.n_range = n_range
        self.m_range = m_range
        self.p_walk_range = p_walk_range
        self.p_obstacle_range = p_obstacle_range
        self.mud_range = mud_range
        self.step_reward = step_reward
        self.finish_reward = finish_reward
        self.seed = seed
        self.rng = np.random.default_rng(seed)

    def sample_env(self):
        n = self.rng.integers(low=self.n_range[0], high=self.n_range[1]+1)
        m = self.rng.integers(low=self.m_range[0], high=self.m_range[1]+1)
        p_walk = self.rng.uniform(*self.p_walk_range)
        p_obstacle = self.rng.uniform(*self.p_obstacle_range)
        number_mud = self.rng.integers(low=self.mud_range[0], high=self.mud_range[1]+1)
        seed = int(self.rng.integers(low=0, high=2**31))
        return Environment(n, m, p_walk, p_obstacle, number_mud, self.step_reward, self.finish_reward, seed)
