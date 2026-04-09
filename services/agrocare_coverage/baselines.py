from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from services.agrocare_coverage.environment import CoveragePlanningEnv


def encode_row_action(env: "CoveragePlanningEnv", row_index: int, direction: int) -> np.ndarray:
    row_count = max(1, int(env.row_count))
    normalized_row = -1.0 + (2.0 * float(row_index) / max(1, row_count - 1))
    normalized_direction = 1.0 if int(direction) >= 0 else -1.0
    return np.asarray([normalized_row, normalized_direction], dtype=np.float32)


def choose_greedy_nearest_action(env: "CoveragePlanningEnv") -> np.ndarray:
    best_score = None
    best_choice = None
    for row_index in env.get_candidate_row_indices():
        for direction in (-1, 1):
            estimate = env.estimate_row_transition_cost(row_index, direction)
            if estimate is None:
                continue
            score = estimate["transition_length"] + 0.25 * estimate["row_length"]
            if best_score is None or score < best_score:
                best_score = score
                best_choice = (row_index, direction)

    if best_choice is None:
        return encode_row_action(env, 0, 1)
    return encode_row_action(env, best_choice[0], best_choice[1])


def choose_greedy_two_step_action(env: "CoveragePlanningEnv") -> np.ndarray:
    best_score = None
    best_choice = None
    for row_index in env.get_candidate_row_indices():
        for direction in (-1, 1):
            estimate = env.estimate_row_transition_cost(row_index, direction)
            if estimate is None:
                continue

            future_score = env.estimate_future_row_cost(
                current_row_index=row_index,
                end_position=estimate["end_position"],
            )
            score = estimate["transition_length"] + estimate["row_length"] + 0.7 * future_score
            if best_score is None or score < best_score:
                best_score = score
                best_choice = (row_index, direction)

    if best_choice is None:
        return encode_row_action(env, 0, 1)
    return encode_row_action(env, best_choice[0], best_choice[1])

