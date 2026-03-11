import heapq
import numpy as np


def heuristic(a, b):
    return np.linalg.norm(np.array(a) - np.array(b))


def get_neighbors(node, grid):
    x, y = node
    neighbors = []

    directions = [
        (1,0), (-1,0),
        (0,1), (0,-1),
        (1,1), (1,-1),
        (-1,1), (-1,-1)
    ]

    for dx, dy in directions:
        nx = x + dx
        ny = y + dy

        if 0 <= nx < grid.shape[0] and 0 <= ny < grid.shape[1]:
            if grid[nx,ny] != np.inf:
                neighbors.append((nx,ny))

    return neighbors


def reconstruct_path(came_from, current):
    path = [current]

    while current in came_from:
        current = came_from[current]
        path.append(current)

    path.reverse()
    return path


def astar(cost_map, start, goal):

    open_set = []
    heapq.heappush(open_set, (0, start))

    came_from = {}

    g_score = {start: 0}
    f_score = {start: heuristic(start, goal)}

    while open_set:

        _, current = heapq.heappop(open_set)

        if current == goal:
            return reconstruct_path(came_from, current)

        for neighbor in get_neighbors(current, cost_map):

            tentative_g = g_score[current] + cost_map[neighbor]

            if neighbor not in g_score or tentative_g < g_score[neighbor]:

                came_from[neighbor] = current
                g_score[neighbor] = tentative_g

                f_score[neighbor] = tentative_g + heuristic(neighbor, goal)

                heapq.heappush(open_set, (f_score[neighbor], neighbor))

    return None
