import numpy as np
import random


import numpy as np

def sample_spawn_times(K, T, tau_min, tau_max, t0=0):
    """
    Генерирует моменты появления нарушителей.
    Интервалы задаются между появлениями.
    """

    times = []
    current_time = t0

    for _ in range(K):
        upper = min(tau_max, T - current_time)

        # если больше нельзя разместить интервал
        if upper < tau_min:
            break

        tau_k = np.random.randint(tau_min, upper + 1)
        current_time += tau_k
        times.append(current_time)

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

def generate_intruder_schedule(intruders, T, tau_min, tau_max, random):
    """
    intruders - список нарушителей
    tau_min - минимальное значение интервала
    tau_max - максимальное значение интервала
    T - время патрулирования

    Возвращает словарь:
    {idx: (t_k, (x, y))}
    """

    K = len(intruders)

    times = []
    
    # моменты появления
    if random:
        times = sample_spawn_times(K, T, tau_min, tau_max)
    else:
        for i in intruders:
            times.append(i.incoming_moment)
        

    schedule = {}

    # связываем индекс нарушителя с его временем
    for idx, t in enumerate(times):
        schedule[t] = [idx, (-1, -1)]  # позиция вычисляется позже

    return schedule