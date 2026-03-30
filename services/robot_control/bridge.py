from __future__ import annotations

from packages.env_bridge.models import RobotCommand


class NullRobotBridge:
    """No-op bridge useful for tests, dry-runs and local composition."""

    def __init__(self) -> None:
        self.last_command = RobotCommand.stop(reason="bridge_init")

    def send_command(self, command: RobotCommand) -> None:
        self.last_command = command

    def stop(self) -> None:
        self.last_command = RobotCommand.stop(reason="bridge_stop")
