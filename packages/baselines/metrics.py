import numpy as np

def compute_path_cost(path, cost_map):
    return float(sum(cost_map[x, y] for x, y in path))


def compute_length(path):
    return len(path)


def compute_success(path, goal):
    return path[-1] == goal
