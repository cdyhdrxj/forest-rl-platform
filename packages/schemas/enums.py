from enum import Enum

class ProjectMode(str, Enum):
    trail = "trail"
    robot = "robot"
    patrol = "patrol"
    fast_grid = "fast_grid"

class RunStatus(str, Enum):
    created = "created"
    queued = "queued"
    running = "running"
    finished = "finished"
    failed = "failed"
    cancelled = "cancelled"

class AlgorithmFamily(str, Enum):
    tabular = "tabular"
    dqn = "dqn"
    actor_critic = "actor_critic"
    classic_planner = "classic_planner"
    patrol_heuristic = "patrol_heuristic"
    hybrid = "hybrid"

class ArtifactType(str, Enum):
    world_file = "world_file"
    scenario_preview = "scenario_preview"
    config = "config"
    log = "log"
    replay = "replay"
    model_checkpoint = "model_checkpoint"
    metric_export = "metric_export"
    report = "report"
    plot = "plot"
    map_layer = "map_layer"

class EventType(str, Enum):
    collision = "collision"
    collision_passable = "collision_passable"
    collision_impassable = "collision_impassable"
    goal_reached = "goal_reached"
    flip = "flip"
    intruder_appeared = "intruder_appeared"
    intruder_detected = "intruder_detected"
    intruder_caught = "intruder_caught"
    timeout = "timeout"
    deadlock = "deadlock"
    fire_started = "fire_started"
    fire_detected = "fire_detected"
    fire_missed = "fire_missed"
    # Legacy values are kept to preserve compatibility with existing rows and integrations.
    violator_started = "violator_started"
    violator_detected = "violator_detected"
    violator_intercepted = "violator_intercepted"
    patrol_zone_visited = "patrol_zone_visited"
