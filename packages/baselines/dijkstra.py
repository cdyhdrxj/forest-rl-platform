import heapq
import numpy as np


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


def dijkstra(cost_map, start, goal):

    queue = []
    heapq.heappush(queue, (0, start))

    came_from = {}
    cost_so_far = {start: 0}

    while queue:

        current_cost, current = heapq.heappop(queue)

        if current == goal:
            return reconstruct_path(came_from, current)

        for neighbor in get_neighbors(current, cost_map):

            new_cost = cost_so_far[current] + cost_map[neighbor]

            if neighbor not in cost_so_far or new_cost < cost_so_far[neighbor]:

                cost_so_far[neighbor] = new_cost
                came_from[neighbor] = current

                heapq.heappush(queue, (new_cost, neighbor))

    return None
