from __future__ import annotations

from typing import Protocol

from packages.env_bridge.models import ObservationFrame, PolicyDecision, RobotCommand


class EnvironmentAdapter(Protocol):
    """Training or runtime environment adapter with a reset/step contract."""

    def reset(self) -> ObservationFrame:
        ...

    def step(self, command: RobotCommand) -> ObservationFrame:
        ...


class PolicyRunner(Protocol):
    """Runtime policy executor used outside the training loop."""

    def reset(self) -> None:
        ...

    def predict(self, observation: ObservationFrame) -> PolicyDecision:
        ...


class SafetySupervisor(Protocol):
    """Command filter applied between policy inference and robot transport."""

    def reset(self) -> None:
        ...

    def apply(self, command: RobotCommand, observation: ObservationFrame) -> RobotCommand:
        ...


class RobotBridge(Protocol):
    """Transport bridge that publishes commands to ROS or another backend."""

    def send_command(self, command: RobotCommand) -> None:
        ...

    def stop(self) -> None:
        ...
