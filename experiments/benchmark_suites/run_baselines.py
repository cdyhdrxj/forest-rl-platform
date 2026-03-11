import matplotlib.pyplot as plt
import numpy as np
import time

from services.trail_planning.cost_map_builder import build_cost_map
from packages.baselines.astar import astar
from packages.baselines.dijkstra import dijkstra
from packages.baselines.rrt_star import rrt_star


def compute_path_cost(cost_map, path):

    cost = 0

    for node in path:
        cost += cost_map[node]

    return cost


def visualize(cost_map, path, title):

    plt.imshow(cost_map, cmap="viridis")

    if path is not None:

        xs = [p[0] for p in path]
        ys = [p[1] for p in path]

        plt.plot(ys, xs, color="red")

    plt.title(title)
    plt.colorbar()
    plt.show()


def run_algorithm(name, algo, cost_map, start, goal):

    t0 = time.perf_counter()

    path = algo(cost_map, start, goal)

    t1 = time.perf_counter()

    planning_time = t1 - t0

    if path is None:

        print(name, "path not found")
        return

    path_length = len(path)

    path_cost = compute_path_cost(cost_map, path)


    print(name)
    print("planning_time:", planning_time)
    print("path_length:", path_length)
    print("path_cost:", path_cost)

    visualize(cost_map, path, name)


def main():

    cost_map = build_cost_map()

    start = (0, 0)
    goal = (99, 99)

    run_algorithm("A*", astar, cost_map, start, goal)

    run_algorithm("Dijkstra", dijkstra, cost_map, start, goal)

    run_algorithm("RRT*", rrt_star, cost_map, start, goal)


if __name__ == "__main__":
    main()
