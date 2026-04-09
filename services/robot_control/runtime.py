from __future__ import annotations

from dataclasses import dataclass

from packages.env_bridge import (
    EnvironmentAdapter,
    ObservationFrame,
    PolicyDecision,
    PolicyRunner,
    RobotBridge,
    RobotCommand,
    SafetySupervisor,
)


@dataclass(slots=True)
class RobotControlStep:
    tick_index: int
    observation: ObservationFrame
    policy_decision: PolicyDecision
    safe_command: RobotCommand
    was_filtered: bool


class RobotControlRuntime:
    """Compose runtime execution from policy, safety and transport roles."""

    def __init__(
        self,
        *,
        environment_adapter: EnvironmentAdapter,
        policy_runner: PolicyRunner,
        safety_supervisor: SafetySupervisor,
        robot_bridge: RobotBridge,
    ) -> None:
        self.environment_adapter = environment_adapter
        self.policy_runner = policy_runner
        self.safety_supervisor = safety_supervisor
        self.robot_bridge = robot_bridge
        self._last_observation: ObservationFrame | None = None
        self._tick_index = 0

    @property
    def last_observation(self) -> ObservationFrame | None:
        return self._last_observation

    def reset(self) -> ObservationFrame:
        self.policy_runner.reset()
        self.safety_supervisor.reset()
        self.robot_bridge.stop()
        self._tick_index = 0
        self._last_observation = self.environment_adapter.reset()
        return self._last_observation

    def step(self) -> RobotControlStep:
        if self._last_observation is None:
            self.reset()

        assert self._last_observation is not None
        decision = self.policy_runner.predict(self._last_observation)
        safe_command = self.safety_supervisor.apply(decision.command, self._last_observation)
        self.robot_bridge.send_command(safe_command)

        next_observation = self.environment_adapter.step(safe_command)
        self._tick_index += 1
        was_filtered = safe_command != decision.command
        self._last_observation = next_observation

        return RobotControlStep(
            tick_index=self._tick_index,
            observation=next_observation,
            policy_decision=decision,
            safe_command=safe_command,
            was_filtered=was_filtered,
        )

    def stop(self) -> None:
        self.robot_bridge.stop()
