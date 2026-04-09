from __future__ import annotations

from collections.abc import Iterable

from packages.env_bridge.models import ObservationFrame, RobotCommand


class PassthroughSafetySupervisor:
    """Leave policy commands unchanged."""

    def reset(self) -> None:
        return None

    def apply(self, command: RobotCommand, observation: ObservationFrame) -> RobotCommand:
        return command


class VelocityLimitSafetySupervisor:
    """Clamp continuous velocity commands to configured limits."""

    def __init__(self, *, max_linear: float, max_angular: float) -> None:
        self.max_linear = float(max_linear)
        self.max_angular = float(max_angular)

    def reset(self) -> None:
        return None

    def apply(self, command: RobotCommand, observation: ObservationFrame) -> RobotCommand:
        linear = command.linear_velocity
        angular = command.angular_velocity
        metadata = dict(command.metadata)
        filtered = False

        if linear is not None:
            clamped_linear = max(-self.max_linear, min(self.max_linear, float(linear)))
            filtered = filtered or clamped_linear != linear
            linear = clamped_linear

        if angular is not None:
            clamped_angular = max(-self.max_angular, min(self.max_angular, float(angular)))
            filtered = filtered or clamped_angular != angular
            angular = clamped_angular

        if filtered:
            metadata["safety"] = "velocity_limit"

        return RobotCommand(
            linear_velocity=linear,
            angular_velocity=angular,
            discrete_action=command.discrete_action,
            metadata=metadata,
        )


class EmergencyStopSafetySupervisor:
    """Replace commands with stop commands when safety flags appear."""

    def __init__(self, stop_flags: Iterable[str] = ("collision", "emergency_stop")) -> None:
        self.stop_flags = tuple(stop_flags)

    def reset(self) -> None:
        return None

    def apply(self, command: RobotCommand, observation: ObservationFrame) -> RobotCommand:
        info = observation.info or {}
        for flag in self.stop_flags:
            if info.get(flag):
                return RobotCommand.stop(reason=f"safety:{flag}")
        return command


class CompositeSafetySupervisor:
    """Apply multiple safety supervisors in order."""

    def __init__(self, *supervisors) -> None:
        self.supervisors = tuple(supervisors)

    def reset(self) -> None:
        for supervisor in self.supervisors:
            supervisor.reset()

    def apply(self, command: RobotCommand, observation: ObservationFrame) -> RobotCommand:
        current = command
        for supervisor in self.supervisors:
            current = supervisor.apply(current, observation)
        return current
