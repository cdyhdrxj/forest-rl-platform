from __future__ import annotations

from packages.env_bridge import ObservationFrame, PolicyDecision, RobotCommand
from services.robot_control.policy_runner import CallablePolicyRunner
from services.robot_control.runtime import RobotControlRuntime
from services.robot_control.safety import (
    CompositeSafetySupervisor,
    EmergencyStopSafetySupervisor,
    VelocityLimitSafetySupervisor,
)


class FakeEnvironmentAdapter:
    def __init__(self, reset_info: dict | None = None) -> None:
        self.reset_info = dict(reset_info or {})
        self.reset_calls = 0
        self.step_commands: list[RobotCommand] = []

    def reset(self) -> ObservationFrame:
        self.reset_calls += 1
        return ObservationFrame(observation={"pose": [0.0, 0.0]}, info=dict(self.reset_info))

    def step(self, command: RobotCommand) -> ObservationFrame:
        self.step_commands.append(command)
        return ObservationFrame(
            observation={"pose": [1.0, 0.0]},
            reward=1.0,
            info={"bridge_command_reason": command.metadata.get("reason")},
        )


class RecordingRobotBridge:
    def __init__(self) -> None:
        self.commands: list[RobotCommand] = []
        self.stop_calls = 0

    def send_command(self, command: RobotCommand) -> None:
        self.commands.append(command)

    def stop(self) -> None:
        self.stop_calls += 1


def test_runtime_filters_policy_command_before_bridge_and_environment() -> None:
    environment = FakeEnvironmentAdapter()
    bridge = RecordingRobotBridge()
    policy = CallablePolicyRunner(
        lambda observation: PolicyDecision(
            command=RobotCommand(linear_velocity=2.5, angular_velocity=-1.5),
            raw_action=(2.5, -1.5),
        )
    )
    safety = CompositeSafetySupervisor(
        VelocityLimitSafetySupervisor(max_linear=0.7, max_angular=0.4),
    )
    runtime = RobotControlRuntime(
        environment_adapter=environment,
        policy_runner=policy,
        safety_supervisor=safety,
        robot_bridge=bridge,
    )

    initial = runtime.reset()
    assert initial.observation == {"pose": [0.0, 0.0]}
    assert bridge.stop_calls == 1

    step = runtime.step()

    assert step.tick_index == 1
    assert step.was_filtered is True
    assert step.safe_command.linear_velocity == 0.7
    assert step.safe_command.angular_velocity == -0.4
    assert step.safe_command.metadata["safety"] == "velocity_limit"
    assert bridge.commands == [step.safe_command]
    assert environment.step_commands == [step.safe_command]


def test_runtime_triggers_emergency_stop_on_collision_flag() -> None:
    environment = FakeEnvironmentAdapter(reset_info={"collision": True})
    bridge = RecordingRobotBridge()
    policy = CallablePolicyRunner(
        lambda observation: RobotCommand(linear_velocity=0.5, angular_velocity=0.2)
    )
    safety = CompositeSafetySupervisor(
        EmergencyStopSafetySupervisor(stop_flags=("collision",)),
        VelocityLimitSafetySupervisor(max_linear=1.0, max_angular=1.0),
    )
    runtime = RobotControlRuntime(
        environment_adapter=environment,
        policy_runner=policy,
        safety_supervisor=safety,
        robot_bridge=bridge,
    )

    runtime.reset()
    step = runtime.step()

    assert step.was_filtered is True
    assert step.safe_command.linear_velocity == 0.0
    assert step.safe_command.angular_velocity == 0.0
    assert step.safe_command.metadata["reason"] == "safety:collision"
    assert bridge.commands[-1] == step.safe_command
