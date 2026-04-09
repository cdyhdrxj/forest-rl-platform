from __future__ import annotations

from collections.abc import Callable

from packages.env_bridge.models import ObservationFrame, PolicyDecision, RobotCommand


class CallablePolicyRunner:
    """Wrap a callable policy into the runtime policy runner contract."""

    def __init__(
        self,
        policy_fn: Callable[[ObservationFrame], PolicyDecision | RobotCommand],
    ) -> None:
        self.policy_fn = policy_fn

    def reset(self) -> None:
        return None

    def predict(self, observation: ObservationFrame) -> PolicyDecision:
        result = self.policy_fn(observation)
        if isinstance(result, PolicyDecision):
            return result
        if isinstance(result, RobotCommand):
            return PolicyDecision(command=result, raw_action=result)
        raise TypeError(
            "policy_fn must return PolicyDecision or RobotCommand, "
            f"got {type(result).__name__}",
        )
