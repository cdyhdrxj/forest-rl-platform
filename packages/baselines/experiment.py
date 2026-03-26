import numpy as np
import time

from scenario_loader import load_layers
from costmap import build_cost_map
from planners import astar, dijkstra, rrt_star
from metrics import compute_path_cost, compute_length, compute_success


def random_point(cost_map):
    h, w = cost_map.shape
    return (np.random.randint(0, h), np.random.randint(0, w))


def run_single_episode(scenario, reward_config, episode_idx):

    elevation, obstacles = load_layers(scenario)
    cost_map = build_cost_map(elevation, obstacles, reward_config)

    start = random_point(cost_map)
    goal = random_point(cost_map)

    results = {}

    for name, planner in {
        "astar": astar,
        "dijkstra": dijkstra,
        "rrt": rrt_star
    }.items():

        t0 = time.time()
        path = planner(cost_map, start, goal)
        duration = time.time() - t0

        results[name] = {
            "path_length": compute_length(path),
            "path_cost": compute_path_cost(path, cost_map),
            "success": compute_success(path, goal),
            "duration_sec": duration
        }

    # RL потом сюда
    # results["rl"] = ...

    return results
