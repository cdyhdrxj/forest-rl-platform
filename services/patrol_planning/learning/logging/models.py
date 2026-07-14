from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from pydantic import BaseModel, Field


class StepRecord(BaseModel):
    step: int
    action: int
    pos: Tuple[int, int]
    reward: float
    reward_components: Dict[str, float] = Field(default_factory=dict)
    events: List[str] = Field(default_factory=list)


class EpisodeRecord(BaseModel):
    episode: int
    steps: int
    terminated: bool
    truncated: bool
    total_reward: float
    total_damage: float
    catch_rate: float  # intruders caught / intruders scheduled (0.0 if none scheduled)
    catch_latency_mean: Optional[float] = None  # mean steps from spawn to catch (None if no catches)
    step_records: List[StepRecord] = Field(default_factory=list)
    metrics: Optional[Dict[str, float]] = None  # M_damage, M_move, M_idleness, idleness_max, Z
    idleness_percentiles: Optional[Dict[str, float]] = None  # p50, p90, p99 of staleness map
