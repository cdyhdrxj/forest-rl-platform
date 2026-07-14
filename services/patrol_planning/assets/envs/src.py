import numpy as np
import random


def sample_spawn_times(T: int, tau_min: int, tau_max: int, K: int) -> list:
    """Генерирует времена спавна в [1, T) с интервалами tau_min..tau_max.

    K < 0 — без ограничений (до конца горизонта).
    K == 0 — пустой список.
    K > 0 — не более K времён.
    """
    if K == 0:
        return []

    times = []
    t = np.random.randint(tau_min, tau_max + 1)
    while t < T:
        times.append(t)
        if K > 0 and len(times) >= K:
            break
        t += np.random.randint(tau_min, tau_max + 1)
    return times

def get_valid_spawn_cells(env, mu_min = 0.5):
    """
    Возвращает множество допустимых граничных клеток:
    μ_ij >= μ_min и клетка не занята
    """
    u = env.world_layers["passability"]
    intr = env.world_layers["intruders"]

    rows, cols = len(u), len(u[0])
    border = get_border_positions(rows, cols)

    valid = []

    for x, y in border:
        if u[x][y] >= mu_min and intr[x][y] == 0:
            valid.append((x, y))

    return valid

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

def sample_spawn_cell(env, mu_min):
    """
    v_ij ~ U(V_start)
    """
    valid = get_valid_spawn_cells(env, mu_min)

    if not valid:
        return None

    return random.choice(valid)

def generate_intruder_schedule(intruders_start, T: int, tau_min: int, tau_max: int, K: int = -1) -> dict:
    """Генерирует расписание спавна нарушителей.

    Аргументы:
        intruders_start — пул шаблонов нарушителей (циклически используется).
        T               — длина эпизода.
        tau_min/tau_max — диапазон интервалов между появлениями.
        K               — макс. число спавнов: -1 = без ограничений, 0 = нет, >0 = не более K.

    Возвращает: {time_step: [intruder_index, (-1, -1)]}
    Позиция (-1, -1) — placeholder; реальная позиция выбирается в step() через sample_spawn_cell.
    """
    if not intruders_start or K == 0:
        return {}

    times = sample_spawn_times(T, tau_min, tau_max, K)
    n = len(intruders_start)
    return {t: [i % n, (-1, -1)] for i, t in enumerate(times)}