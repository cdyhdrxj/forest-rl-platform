import numpy as np
import random
import math

# Node
class Node:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.parent = None
        self.cost = 0  # суммарная стоимость пути до этого узла

#  Distance
def distance(n1, n2):
    # чисто геометрическое расстояние (для steer и проверки цели)
    return math.hypot(n2.x - n1.x, n2.y - n1.y)

#  Nearest
def nearest(tree, rnd):
    return min(tree, key=lambda node: distance(node, rnd))

# Steer
def steer(from_node, to_node, step_size):
    theta = math.atan2(to_node.y - from_node.y, to_node.x - from_node.x)
    new_x = from_node.x + step_size * math.cos(theta)
    new_y = from_node.y + step_size * math.sin(theta)
    return Node(new_x, new_y)

# Collision
def collision(node, cost_map):
    x, y = int(node.x), int(node.y)
    if x < 0 or y < 0 or x >= cost_map.shape[0] or y >= cost_map.shape[1]:
        return True
    if cost_map[x, y] == np.inf:
        return True
    return False

#  Near
def near(tree, new_node, radius):
    neighbors = []
    for node in tree:
        if distance(node, new_node) <= radius:
            neighbors.append(node)
    return neighbors

#  Reconstruct Path
def reconstruct_path(node):
    path = []
    while node is not None:
        path.append((int(node.x), int(node.y)))
        node = node.parent
    path.reverse()
    return path

#  RRT*
def rrt_star(cost_map, start, goal,
             max_iter=10000,
             step_size=5,
             radius=10,
             seed=42):
    random.seed(seed)
    start_node = Node(start[0], start[1])
    goal_node = Node(goal[0], goal[1])
    tree = [start_node]

    for _ in range(max_iter):
        # случайная точка
        rand_x = random.randint(0, cost_map.shape[0]-1)
        rand_y = random.randint(0, cost_map.shape[1]-1)
        rnd = Node(rand_x, rand_y)

        nearest_node = nearest(tree, rnd)
        new_node = steer(nearest_node, rnd, step_size)

        if collision(new_node, cost_map):
            continue

        # поиск соседей для ребалансировки
        neighbors = near(tree, new_node, radius)

        # выбор лучшего родителя
        best_parent = nearest_node
        best_cost = nearest_node.cost + cost_map[int(new_node.x), int(new_node.y)]

        for node in neighbors:
            cost = node.cost + cost_map[int(new_node.x), int(new_node.y)]
            if cost < best_cost:
                best_parent = node
                best_cost = cost

        new_node.parent = best_parent
        new_node.cost = best_cost
        tree.append(new_node)

        # ребалансировка соседей
        for node in neighbors:
            cost_through_new = new_node.cost + cost_map[int(node.x), int(node.y)]
            if cost_through_new < node.cost:
                node.parent = new_node
                node.cost = cost_through_new

        # проверка достижения цели (по геометрии)
        if distance(new_node, goal_node) < step_size:
            goal_node.parent = new_node
            goal_node.cost = new_node.cost + cost_map[int(goal_node.x), int(goal_node.y)]
            return reconstruct_path(goal_node)

    # путь не найден
    return None
