from __future__ import annotations

import json
import os
import threading
import time
from typing import Any

from packages.schemas.enums import EventType
from packages.schemas.event_mapping import map_ros_event_type
from services.scenario_generator.models import GeneratedScenario
from services.ros_2.ros_api_connection import ros


class Simulator3DService:
    """Lightweight descriptor-driven runtime for 3D scenarios."""

    def __init__(self) -> None:
        self.loaded_scenario: GeneratedScenario | None = None
        self.loaded_runtime_config: dict[str, Any] | None = None
        self.last_error: str | None = None
        self._state = self._make_state()
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._event_lock = threading.Lock()
        self._pending_events: list[dict[str, Any]] = []

    def start(self, params: dict[str, Any]) -> None:
        if self._state["running"]:
            return
        if self.loaded_scenario is None:
            raise RuntimeError("Simulator3DService.start() requires a scenario loaded by the dispatcher")

        self.last_error = None
        if int(self._state.get("step") or 0) > 0 or int(self._state.get("episode") or 0) > 0:
            self._state = self._make_state()
            self._state["mode"] = self.loaded_scenario.task_kind.value
            self._apply_preview_state(self.loaded_scenario)
        self._stop_event.clear()
        self._state["running"] = True
        self._state["mode"] = self.loaded_scenario.task_kind.value
        self._pending_events.clear()
        runtime_mode = self._resolve_runtime_mode(params)
        self._state["runtime_mode"] = runtime_mode

        if runtime_mode == "sync_step":
            try:
                ros.call_service("/env/reset", "std_srvs/srv/Trigger", {})
            except Exception as exc:
                self.last_error = f"3D sync runtime reset failed: {exc}"
                self._state["running"] = False
                return

        target = self._loop if runtime_mode == "synthetic" else self._sync_step_loop
        self._thread = threading.Thread(target=target, args=(dict(params),), daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        self._state["running"] = False
        if self._thread is not None and self._thread.is_alive() and self._thread is not threading.current_thread():
            self._thread.join(timeout=1.0)

    def reset(self) -> None:
        self.stop()
        self._state = self._make_state()
        if self.loaded_scenario is not None:
            self._apply_preview_state(self.loaded_scenario)

    def load_scenario(self, scenario: GeneratedScenario, runtime_config: dict[str, Any] | None = None) -> None:
        self.stop()
        self.loaded_scenario = scenario
        self.loaded_runtime_config = dict(runtime_config or {})
        self._state = self._make_state()
        self._state["mode"] = scenario.task_kind.value
        self._apply_preview_state(scenario)

        map_config = self.loaded_runtime_config.get("map_config", {})

        robot_config = self.loaded_runtime_config.get("robot_config", {})

        robots_ros_request = {
            "positions_x": [float(robot_config.get("position_x", 0.0))],
            "positions_y": [float(robot_config.get("position_y", 0.0))],
            "positions_z": [float(robot_config.get("position_z", 0.0))],
            "rotations_y": [float(robot_config.get("rotation_y", 0.0))],
            "type": [int(robot_config.get("robot_type", robot_config.get("type", 0)))],
        }

        target_config = self.loaded_runtime_config.get("target_config", {})

        threading.Thread(
            target=self._init_ros_scene,
            args=(map_config, robots_ros_request, target_config),
            daemon=True,
        ).start()

    def _init_ros_scene(
        self,
        map_config: dict[str, Any],
        robots_ros_request: dict[str, Any],
        target_config: dict[str, Any],
    ) -> None:
        for config, service, service_type in (
            (map_config, "/env/generate", "forest_msgs/srv/SetTerrainParams"),
            (robots_ros_request, "/env/set_robots", "forest_msgs/srv/SetRobots"),
            (target_config, "/env/set_goal", "forest_msgs/srv/SetGoal"),
        ):
            self._call_ros_init(config, service, service_type)

    def _call_ros_init(self, config: dict[str, Any] | None, service, service_type) -> None:
        try:
            if not config:
                return

            response = ros.call_service_dict(service, service_type, config)

        except Exception as e:
            self.last_error = f"ROS init failed: {e}"

    def validate_scenario(self, scenario: GeneratedScenario, runtime_config: dict[str, Any] | None = None) -> list[str]:
        messages: list[str] = []
        if scenario.environment_kind.value != "simulator_3d":
            messages.append("3D runtime can load only simulator_3d scenarios")
        sim_ctx = scenario.runtime_context.get("simulator_3d")
        if not isinstance(sim_ctx, dict):
            messages.append("3D runtime requires simulator_3d runtime context")
        elif "world_descriptor" not in sim_ctx:
            messages.append("3D runtime requires a world descriptor")

        if scenario.task_kind.value == "patrol":
            patrol = scenario.runtime_context.get("patrol")
            if not isinstance(patrol, dict):
                messages.append("3D patrol runtime requires patrol runtime context")
            elif not patrol.get("intruder_positions"):
                messages.append("3D patrol runtime requires at least one intruder")

        return messages

    def get_state(self) -> dict[str, Any]:
        return dict(self._state)

    def drain_runtime_events(self) -> list[dict[str, Any]]:
        with self._event_lock:
            events = list(self._pending_events)
            self._pending_events.clear()
        return events

    def _loop(self, params: dict[str, Any]) -> None:
        max_steps = int(params.get("max_steps") or self._state.get("max_steps") or 120)
        step_sleep = float(params.get("tick_sleep") or 0.05)
        intruders = list(self._state.get("goal_pos") or [])
        intruder_announced = False
        preview_payload = self.loaded_scenario.preview_payload if self.loaded_scenario is not None else {}
        start_pos = list(preview_payload.get("agent_pos") or [[0.0, 0.0]])[0]
        goal_pos = list(preview_payload.get("goal_pos") or [])

        try:
            while not self._stop_event.is_set() and self._state["step"] < max_steps:
                self._state["step"] += 1
                self._state["new_episode"] = False
                self._state["is_collision"] = False

                if self._state["mode"] == "trail":
                    self._advance_trail(goal_pos)
                else:
                    if not intruder_announced and intruders:
                        intruder_announced = True
                        for index, intruder_pos in enumerate(intruders, start=1):
                            self._push_event(
                                EventType.intruder_appeared.value,
                                step_index=self._state["step"],
                                position=intruder_pos,
                                intruder_id=index,
                            )

                    if intruders and self._state["step"] % 20 == 0:
                        intruder = intruders.pop(0)
                        self._state["goal_pos"] = list(intruders)
                        self._state["intruders_remaining"] = len(intruders)
                        self._state["goal_count"] += 1
                        self._state["total_reward"] += 3.0
                        self._push_event(
                            EventType.intruder_caught.value,
                            step_index=self._state["step"],
                            position=intruder,
                            intruder_id=self._state["goal_count"],
                        )
                        if not intruders:
                            self._finish_episode(start_pos)

                if self._state["step"] % 15 == 0:
                    self._state["collision_count"] += 1
                    self._state["is_collision"] = True
                    self._state["total_reward"] -= 0.5
                    agent_pos = (self._state.get("agent_pos") or [[0.0, 0.0]])[0]
                    self._push_event(
                        EventType.collision_impassable.value,
                        step_index=self._state["step"],
                        position=agent_pos,
                    )

                time.sleep(step_sleep)
        except Exception as exc:
            self.last_error = str(exc)
        finally:
            self._state["running"] = False

    def _sync_step_loop(self, params: dict[str, Any]) -> None:
        max_steps = int(params.get("max_steps") or self._state.get("max_steps") or 120)
        step_sleep = float(params.get("tick_sleep") or 0.05)
        dt = float(params.get("dt") or params.get("step_dt") or step_sleep)

        try:
            while not self._stop_event.is_set() and self._state["step"] < max_steps:
                response = ros.call_service_dict(
                    "/env/step",
                    "forest_msgs/srv/Step",
                    {
                        "actions": list(params.get("actions") or []),
                        "dt": dt,
                    },
                )
                self._state["step"] += 1
                self._state["new_episode"] = False
                self._apply_step_response(response)

                if bool(response.get("terminated")) or bool(response.get("truncated")):
                    self._finish_episode((self._state.get("agent_pos") or [[0.0, 0.0]])[0])
                    break

                time.sleep(step_sleep)
        except Exception as exc:
            self.last_error = (
                "3D sync runtime failed. The selected runtime mode requires "
                f"/env/step forest_msgs/srv/Step: {exc}"
            )
        finally:
            self._state["running"] = False

    def _apply_step_response(self, response: dict[str, Any]) -> None:
        if not bool(response.get("success", True)):
            message = str(response.get("message") or "unknown /env/step failure")
            raise RuntimeError(message)

        reward = float(response.get("reward") or 0.0)
        self._state["total_reward"] += reward
        self._state["last_step_reward"] = reward
        self._state["terminated"] = bool(response.get("terminated"))
        self._state["truncated"] = bool(response.get("truncated"))

        observation = self._decode_json_field(response.get("observation_json"), "observation_json")
        info = self._decode_json_field(response.get("info_json"), "info_json")
        self._state["last_observation"] = observation
        self._state["last_info"] = info

        if isinstance(observation, dict):
            for key in ("agent_pos", "goal_pos", "landmark_pos", "terrain_map"):
                if key in observation:
                    self._state[key] = observation[key]
            if "trajectory" in observation:
                self._state["trajectory"] = observation["trajectory"]

        for event in response.get("events") or []:
            self._push_ros_event(event)

    def _push_ros_event(self, event: dict[str, Any]) -> None:
        event_type = map_ros_event_type(int(event.get("event_type") or 0)).value
        position = event.get("position") or {}
        intruder_id = int(event.get("intruder_id", -1))
        event_position = [float(position.get("x", 0.0)), float(position.get("y", 0.0))]
        self._push_event(
            event_type,
            step_index=int(self._state.get("step") or 0),
            position=event_position,
            intruder_id=intruder_id if intruder_id >= 0 else None,
        )

        if event_type == EventType.goal_reached.value:
            self._state["goal_count"] += 1
        elif event_type in {EventType.collision_passable.value, EventType.collision_impassable.value}:
            self._state["collision_count"] += 1
            self._state["is_collision"] = True
        elif event_type == EventType.intruder_caught.value:
            self._state["goal_count"] += 1
            self._state["intruders_remaining"] = max(0, int(self._state.get("intruders_remaining") or 0) - 1)

    @staticmethod
    def _decode_json_field(value: Any, field_name: str) -> dict[str, Any]:
        if value in (None, ""):
            return {}
        if isinstance(value, dict):
            return dict(value)
        try:
            decoded = json.loads(str(value))
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Invalid {field_name}: {exc}") from exc
        if not isinstance(decoded, dict):
            raise RuntimeError(f"{field_name} must decode to a JSON object")
        return decoded

    @staticmethod
    def _resolve_runtime_mode(params: dict[str, Any]) -> str:
        value = params.get("synthetic")
        if value is None:
            value = os.getenv("SIMULATOR_3D_SYNTHETIC")
        if isinstance(value, str):
            synthetic = value.strip().lower() in {"1", "true", "yes", "on"}
        else:
            synthetic = bool(value)
        return "synthetic" if synthetic else "sync_step"

    def _advance_trail(self, goal_pos: list[list[float]]) -> None:
        agent = list((self._state.get("agent_pos") or [[0.0, 0.0]])[0])
        goal = list(goal_pos[0]) if goal_pos else agent
        dx = 0.0 if agent[0] == goal[0] else (1.0 if goal[0] > agent[0] else -1.0)
        dy = 0.0 if agent[1] == goal[1] else (1.0 if goal[1] > agent[1] else -1.0)
        agent[0] += dx
        agent[1] += dy
        self._state["agent_pos"] = [[float(agent[0]), float(agent[1])]]
        self._state["trajectory"].append([float(agent[0]), float(agent[1])])
        self._state["total_reward"] += 0.1

        if [float(agent[0]), float(agent[1])] == [float(goal[0]), float(goal[1])]:
            self._state["goal_count"] += 1
            self._state["total_reward"] += 5.0
            self._push_event(
                EventType.goal_reached.value,
                step_index=self._state["step"],
                position=goal,
            )
            self._finish_episode(goal)

    def _finish_episode(self, reset_pos: list[float]) -> None:
        self._state["episode"] += 1
        self._state["new_episode"] = True
        self._state["last_episode_reward"] = float(self._state["total_reward"])
        self._state["total_reward"] = 0.0
        self._state["trajectory"] = []
        self._state["agent_pos"] = [[float(reset_pos[0]), float(reset_pos[1])]]

    def _apply_preview_state(self, scenario: GeneratedScenario) -> None:
        preview = scenario.preview_payload
        sim_ctx = dict(scenario.runtime_context.get("simulator_3d") or {})
        descriptor = dict(sim_ctx.get("world_descriptor") or {})
        terrain = scenario.get_layer_data("terrain_preview")

        self._state.update(
            {
                "running": False,
                "agent_pos": list(preview.get("agent_pos") or []),
                "goal_pos": list(preview.get("goal_pos") or []),
                "landmark_pos": list(preview.get("landmark_pos") or []),
                "trajectory": [],
                "is_collision": False,
                "new_episode": False,
                "terrain_map": terrain.tolist() if terrain is not None else preview.get("terrain_map"),
                "world_descriptor": descriptor,
                "max_steps": int(descriptor.get("max_steps") or descriptor.get("task_params", {}).get("max_steps") or 120),
                "intruders_remaining": len(preview.get("goal_pos") or []),
            }
        )

    def _push_event(
        self,
        event_type: str,
        *,
        step_index: int,
        position: list[float] | tuple[float, float] | None = None,
        intruder_id: int | None = None,
    ) -> None:
        payload: dict[str, Any] = {"event_type": event_type, "step_index": int(step_index)}
        if position is not None:
            payload["position"] = [float(position[0]), float(position[1])]
        if intruder_id is not None:
            payload["payload_json"] = {"intruder_id": int(intruder_id)}
        with self._event_lock:
            self._pending_events.append(payload)

    @staticmethod
    def _make_state() -> dict[str, Any]:
        return {
            "running": False,
            "mode": "trail",
            "episode": 0,
            "step": 0,
            "total_reward": 0.0,
            "last_episode_reward": 0.0,
            "new_episode": False,
            "agent_pos": [],
            "goal_pos": [],
            "landmark_pos": [],
            "is_collision": False,
            "goal_count": 0,
            "collision_count": 0,
            "trajectory": [],
            "terrain_map": None,
            "world_descriptor": {},
            "max_steps": 120,
            "intruders_remaining": 0,
            "runtime_mode": "sync_step",
            "last_step_reward": 0.0,
            "terminated": False,
            "truncated": False,
            "last_observation": {},
            "last_info": {},
        }
