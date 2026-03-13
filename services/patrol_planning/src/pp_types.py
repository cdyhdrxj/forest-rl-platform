from enum import IntEnum


class CellType(IntEnum):
    EMPTY = 0
    TREE = 1
    OBSTACLE = 2
    SWAMP = 3
    INTRUDER = 4

class AgentActions(IntEnum):
    UP = 0
    DOWN = 1
    LEFT = 2
    RIGHT = 3
    STAY = 4

class InputActions(IntEnum):
    UP = 0
    DOWN = 1
    LEFT = 2
    RIGHT = 3
    STAY = 4