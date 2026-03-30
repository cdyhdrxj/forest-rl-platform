from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ObservationFrame:
    """Unified observation payload for both training and runtime loops."""

    observation: Any
    reward: float = 0.0
    terminated: bool = False
    truncated: bool = False
    info: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class RobotCommand:
    """Internal command representation before transport-specific conversion."""

    linear_velocity: float | None = None
    angular_velocity: float | None = None
    discrete_action: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def stop(cls, *, reason: str = "stop") -> "RobotCommand":
        return cls(
            linear_velocity=0.0,
            angular_velocity=0.0,
            metadata={"stop": True, "reason": reason},
        )


@dataclass(slots=True)
class PolicyDecision:
    """Policy output with optional raw action payload for logging/debugging."""

    command: RobotCommand
    raw_action: Any = None
    metadata: dict[str, Any] = field(default_factory=dict)
