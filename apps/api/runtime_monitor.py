from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import func

from packages.db.models.artifact import Artifact
from packages.db.models.episode import Episode
from packages.db.models.episode_event import EpisodeEvent
from packages.db.models.metric_point import MetricPoint
from packages.db.models.metric_series import MetricSeries
from packages.db.models.replay import Replay
from packages.db.models.run import Run
from packages.db.models.service_log import ServiceLog
from packages.db.models.enums import ArtifactType, EventType, RunStatus
from packages.db.session import db_session
from services.scenario_generator.models import TaskKind


def get_runtime_storage_root() -> Path:
    repo_root = Path(__file__).resolve().parents[2]
    root = repo_root / "data" / "runs"
    root.mkdir(parents=True, exist_ok=True)
    return root


def write_service_log(
    *,
    service_name: str,
    level: str,
    message: str,
    run_id: int | None = None,
    payload_json: dict[str, Any] | None = None,
) -> None:
    with db_session() as db:
        db.add(
            ServiceLog(
                run_id=run_id,
                service_name=service_name,
                level=level,
                message=message,
                payload_json=dict(payload_json or {}) or None,
            )
        )


@dataclass(slots=True)
class _SeriesHandle:
    series_id: int
    next_point_index: int


class RunObserver:
    def __init__(
        self,
        *,
        run_id: int,
        route_key: str,
        task_kind: TaskKind,
        service: Any,
        poll_interval: float = 0.25,
    ) -> None:
        self.run_id = int(run_id)
        self.route_key = route_key
        self.task_kind = task_kind
        self.service = service
        self.poll_interval = float(poll_interval)

        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._series_handles: dict[str, _SeriesHandle] = {}
        self._last_state: dict[str, Any] | None = None
        self._running_seen = False
        self._finalized = False
        self._requested_status: RunStatus | None = None
        self._requested_message: str | None = None
        self.final_status: RunStatus | None = None

        self._episode_offset = 0
        self._baseline_local_episode = 0
        self._last_completed_local_episode = 0
        self._episode_boundary_step = 0
        self._episode_boundary_goal_count = 0
        self._episode_boundary_collision_count = 0

        timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%S%f")
        run_dir = get_runtime_storage_root() / f"run_{self.run_id}"
        run_dir.mkdir(parents=True, exist_ok=True)
        self._replay_path = run_dir / f"replay_{timestamp}.jsonl"
        self._replay_path.touch(exist_ok=True)

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return

        initial_state = dict(self.service.get_state())
        self._running_seen = bool(initial_state.get("running"))
        self._bootstrap_from_db(initial_state)
        self._register_replay_artifacts()
        write_service_log(
            run_id=self.run_id,
            service_name="runtime_observer",
            level="info",
            message="Runtime observer started",
            payload_json={"route_key": self.route_key, "replay_uri": str(self._replay_path)},
        )
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self, *, final_status: RunStatus | None = None, message: str | None = None) -> None:
        self._requested_status = final_status
        self._requested_message = message
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=max(1.0, self.poll_interval * 5))

    def is_alive(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def _bootstrap_from_db(self, initial_state: dict[str, Any]) -> None:
        with db_session() as db:
            max_episode_index = (
                db.query(func.max(Episode.episode_index))
                .filter(Episode.run_id == self.run_id)
                .scalar()
            )
            self._episode_offset = int(max_episode_index or 0)
        self._baseline_local_episode = int(initial_state.get("episode") or 0)
        self._last_completed_local_episode = self._baseline_local_episode
        self._episode_boundary_step = int(initial_state.get("step") or 0)
        self._episode_boundary_goal_count = int(initial_state.get("goal_count") or 0)
        self._episode_boundary_collision_count = int(initial_state.get("collision_count") or 0)

    def _register_replay_artifacts(self) -> None:
        replay_name = self._replay_path.name
        with db_session() as db:
            db.add(
                Replay(
                    run_id=self.run_id,
                    name=replay_name,
                    storage_uri=str(self._replay_path),
                    format="jsonl",
                )
            )
            db.add(
                Artifact(
                    run_id=self.run_id,
                    artifact_type=ArtifactType.replay,
                    name=replay_name,
                    storage_uri=str(self._replay_path),
                    mime_type="application/x-ndjson",
                    size_bytes=0,
                )
            )

    def _loop(self) -> None:
        try:
            while True:
                state = dict(self.service.get_state())
                self._running_seen = self._running_seen or bool(state.get("running"))
                self._persist_state(state)
                self._last_state = state

                if self._stop_event.wait(self.poll_interval):
                    break
                if self._running_seen and not bool(state.get("running")):
                    break
        except Exception as exc:
            write_service_log(
                run_id=self.run_id,
                service_name="runtime_observer",
                level="error",
                message="Runtime observer failed",
                payload_json={"error": str(exc)},
            )
            self._requested_status = RunStatus.failed
            self._requested_message = str(exc)
        finally:
            final_state = dict(self.service.get_state())
            self._persist_state(final_state)
            self._finalize(final_state)

    def _persist_state(self, state: dict[str, Any]) -> None:
        self._append_replay_line(state)

        direct_events = []
        if hasattr(self.service, "drain_runtime_events"):
            direct_events = list(self.service.drain_runtime_events() or [])

        with db_session() as db:
            self._persist_metrics(db, state)
            self._persist_completed_episode_if_needed(db, state)
            self._persist_events(db, state, direct_events)

    def _append_replay_line(self, state: dict[str, Any]) -> None:
        snapshot = {
            "timestamp": datetime.utcnow().isoformat(),
            "route_key": self.route_key,
            "state": _sanitize_value(state),
        }
        with self._replay_path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(snapshot, ensure_ascii=False))
            stream.write("\n")

    def _persist_metrics(self, db, state: dict[str, Any]) -> None:
        metric_specs = {
            "step": ("steps", "snapshot", "dispatcher"),
            "total_reward": ("reward", "snapshot", "dispatcher"),
            "goal_count": ("count", "snapshot", "dispatcher"),
            "collision_count": ("count", "snapshot", "dispatcher"),
            "coverage_ratio": ("ratio", "snapshot", "dispatcher"),
            "missed_area_ratio": ("ratio", "snapshot", "dispatcher"),
            "return_error": ("distance", "snapshot", "dispatcher"),
            "path_length": ("distance", "snapshot", "dispatcher"),
            "task_time_sec": ("seconds", "snapshot", "dispatcher"),
            "transition_count": ("count", "snapshot", "dispatcher"),
            "repeat_coverage_ratio": ("ratio", "snapshot", "dispatcher"),
            "angular_work_rad": ("radians", "snapshot", "dispatcher"),
            "compute_time_sec": ("seconds", "snapshot", "dispatcher"),
            "remaining_seedlings": ("count", "snapshot", "dispatcher"),
            "intruders_remaining": ("count", "snapshot", "dispatcher"),
            "remaining_rows": ("count", "snapshot", "dispatcher"),
        }

        local_episode = int(state.get("episode") or 0)
        episode_index = self._global_episode_index(
            local_episode,
            include_pending=bool(state.get("step") or 0) > self._episode_boundary_step and not bool(state.get("new_episode")),
        )
        for metric_name, (unit, aggregation, source) in metric_specs.items():
            value = state.get(metric_name)
            if isinstance(value, bool) or value is None:
                continue
            if not isinstance(value, (int, float)):
                continue
            handle = self._ensure_series_handle(
                db,
                name=metric_name,
                unit=unit,
                aggregation=aggregation,
                source=source,
            )
            db.add(
                MetricPoint(
                    metric_series_id=handle.series_id,
                    point_index=handle.next_point_index,
                    train_step=int(state.get("step") or 0),
                    episode_index=episode_index if episode_index is not None and episode_index > 0 else None,
                    wall_time_sec=time.time(),
                    value=float(value),
                )
            )
            handle.next_point_index += 1

    def _persist_completed_episode_if_needed(self, db, state: dict[str, Any]) -> None:
        observed_completed = int(state.get("episode") or 0)
        if observed_completed <= self._last_completed_local_episode:
            return

        persisted_index = self._global_episode_index(observed_completed)
        self._upsert_episode(
            db,
            episode_index=persisted_index,
            state=state,
            complete=True,
            terminated_by="completed",
        )
        self._episode_boundary_step = int(state.get("step") or 0)
        self._episode_boundary_goal_count = int(state.get("goal_count") or 0)
        self._episode_boundary_collision_count = int(state.get("collision_count") or 0)
        self._last_completed_local_episode = observed_completed

    def _persist_events(self, db, state: dict[str, Any], direct_events: list[dict[str, Any]]) -> None:
        if direct_events:
            for event in direct_events:
                episode = self._ensure_event_episode(db, state, completed_this_tick=bool(state.get("new_episode")))
                payload_json = dict(event.get("payload_json") or {})
                position = list(event.get("position") or [])
                db.add(
                    EpisodeEvent(
                        episode_id=episode.id,
                        step_index=int(event.get("step_index") or state.get("step") or 0),
                        sim_time_sec=float(time.time()),
                        event_type=EventType(str(event["event_type"])),
                        x=float(position[0]) if len(position) >= 1 else None,
                        y=float(position[1]) if len(position) >= 2 else None,
                        payload_json=payload_json or None,
                    )
                )
            return

        inferred = self._infer_events(state)
        for event_type, payload_json in inferred:
            episode = self._ensure_event_episode(db, state, completed_this_tick=bool(state.get("new_episode")))
            agent_pos = list((state.get("agent_pos") or [[None, None]])[0])
            db.add(
                EpisodeEvent(
                    episode_id=episode.id,
                    step_index=int(state.get("step") or 0),
                    sim_time_sec=float(time.time()),
                    event_type=event_type,
                    x=float(agent_pos[0]) if len(agent_pos) >= 1 and agent_pos[0] is not None else None,
                    y=float(agent_pos[1]) if len(agent_pos) >= 2 and agent_pos[1] is not None else None,
                    payload_json=payload_json or None,
                )
            )

    def _infer_events(self, state: dict[str, Any]) -> list[tuple[EventType, dict[str, Any] | None]]:
        if self._last_state is None:
            return []

        events: list[tuple[EventType, dict[str, Any] | None]] = []
        current_collisions = int(state.get("collision_count") or 0)
        previous_collisions = int(self._last_state.get("collision_count") or 0)
        for _ in range(max(0, current_collisions - previous_collisions)):
            events.append((EventType.collision_impassable, None))

        if self.task_kind is TaskKind.TRAIL:
            current_goals = int(state.get("goal_count") or 0)
            previous_goals = int(self._last_state.get("goal_count") or 0)
            for _ in range(max(0, current_goals - previous_goals)):
                events.append((EventType.goal_reached, None))
        elif self.task_kind is TaskKind.COVERAGE:
            current_goals = int(state.get("goal_count") or 0)
            previous_goals = int(self._last_state.get("goal_count") or 0)
            for _ in range(max(0, current_goals - previous_goals)):
                events.append((EventType.goal_reached, {"kind": "row_completed"}))
        elif self.task_kind is TaskKind.PATROL:
            previous_targets = len(self._last_state.get("goal_pos") or [])
            current_targets = len(state.get("goal_pos") or [])
            for _ in range(max(0, current_targets - previous_targets)):
                events.append((EventType.intruder_appeared, None))
            for _ in range(max(0, previous_targets - current_targets)):
                events.append((EventType.intruder_caught, None))

        return events

    def _ensure_event_episode(self, db, state: dict[str, Any], *, completed_this_tick: bool) -> Episode:
        local_completed = int(state.get("episode") or 0)
        episode_index = self._global_episode_index(
            local_completed,
            include_pending=not completed_this_tick,
        )
        if episode_index is None:
            episode_index = self._global_episode_index(local_completed, include_pending=True)
        episode = (
            db.query(Episode)
            .filter(Episode.run_id == self.run_id, Episode.episode_index == episode_index)
            .first()
        )
        if episode is None:
            episode = Episode(run_id=self.run_id, episode_index=episode_index)
            db.add(episode)
            db.flush()
        return episode

    def _upsert_episode(
        self,
        db,
        *,
        episode_index: int,
        state: dict[str, Any],
        complete: bool,
        terminated_by: str,
    ) -> None:
        episode = (
            db.query(Episode)
            .filter(Episode.run_id == self.run_id, Episode.episode_index == episode_index)
            .first()
        )
        if episode is None:
            episode = Episode(run_id=self.run_id, episode_index=episode_index)
            db.add(episode)

        current_step = int(state.get("step") or 0)
        current_goal_count = int(state.get("goal_count") or 0)
        current_collision_count = int(state.get("collision_count") or 0)
        steps_delta = max(0, current_step - self._episode_boundary_step)
        goal_delta = max(0, current_goal_count - self._episode_boundary_goal_count)
        collision_delta = max(0, current_collision_count - self._episode_boundary_collision_count)

        reward_key = "last_episode_reward" if complete else "total_reward"
        episode.reward_total = float(state.get(reward_key) or 0.0)
        episode.steps_count = steps_delta
        episode.duration_sec = _optional_float(state.get("task_time_sec"))
        episode.collisions_count = collision_delta
        episode.coverage_ratio = _optional_float(state.get("coverage_ratio"))
        episode.path_length = _optional_float(state.get("path_length")) or float(steps_delta)
        episode.path_cost = float(collision_delta)
        episode.avg_detection_delay = None
        episode.total_damage = None
        episode.terminated_by = terminated_by
        episode.success = _episode_success(self.task_kind, state, goal_delta)

    def _ensure_series_handle(
        self,
        db,
        *,
        name: str,
        unit: str,
        aggregation: str,
        source: str,
    ) -> _SeriesHandle:
        cache_key = f"{name}:{aggregation}"
        handle = self._series_handles.get(cache_key)
        if handle is not None:
            return handle

        series = (
            db.query(MetricSeries)
            .filter(
                MetricSeries.run_id == self.run_id,
                MetricSeries.name == name,
                MetricSeries.aggregation == aggregation,
            )
            .first()
        )
        if series is None:
            series = MetricSeries(
                run_id=self.run_id,
                name=name,
                unit=unit,
                aggregation=aggregation,
                source=source,
                description=f"Dispatcher snapshot series for {name}",
            )
            db.add(series)
            db.flush()

        max_point_index = (
            db.query(func.max(MetricPoint.point_index))
            .filter(MetricPoint.metric_series_id == series.id)
            .scalar()
        )
        handle = _SeriesHandle(series_id=int(series.id), next_point_index=int(max_point_index or -1) + 1)
        self._series_handles[cache_key] = handle
        return handle

    def _finalize(self, state: dict[str, Any]) -> None:
        if self._finalized:
            return

        status = self._requested_status
        if status is None:
            last_error = getattr(self.service, "last_error", None)
            if last_error:
                status = RunStatus.failed
            elif self._running_seen:
                status = RunStatus.finished

        if status in {RunStatus.cancelled, RunStatus.finished, RunStatus.failed}:
            with db_session() as db:
                if self._has_partial_episode(state):
                    partial_index = self._global_episode_index(
                        int(state.get("episode") or 0),
                        include_pending=True,
                    )
                    self._upsert_episode(
                        db,
                        episode_index=partial_index,
                        state=state,
                        complete=False,
                        terminated_by=status.value,
                    )

                run = db.query(Run).filter(Run.id == self.run_id).first()
                if run is not None:
                    run.status = status
                    if run.started_at is None and self._running_seen:
                        run.started_at = datetime.utcnow()
                    run.finished_at = datetime.utcnow()

                replay_artifact = (
                    db.query(Artifact)
                    .filter(
                        Artifact.run_id == self.run_id,
                        Artifact.artifact_type == ArtifactType.replay,
                        Artifact.storage_uri == str(self._replay_path),
                    )
                    .first()
                )
                if replay_artifact is not None and self._replay_path.exists():
                    replay_artifact.size_bytes = self._replay_path.stat().st_size

            write_service_log(
                run_id=self.run_id,
                service_name="runtime_observer",
                level="info" if status is not RunStatus.failed else "error",
                message=self._requested_message or f"Run finalized with status '{status.value}'",
                payload_json={"status": status.value, "route_key": self.route_key},
            )
        self.final_status = status

        self._finalized = True

    def _has_partial_episode(self, state: dict[str, Any]) -> bool:
        current_step = int(state.get("step") or 0)
        if current_step <= self._episode_boundary_step:
            return False
        if bool(state.get("new_episode")):
            return False
        return current_step > 0

    def _global_episode_index(self, local_episode: int, *, include_pending: bool = False) -> int | None:
        completed_delta = max(0, int(local_episode) - self._baseline_local_episode)
        if include_pending:
            return self._episode_offset + completed_delta + 1
        if completed_delta <= 0:
            return None
        return self._episode_offset + completed_delta


def _episode_success(task_kind: TaskKind, state: dict[str, Any], goal_delta: int) -> bool | None:
    if task_kind is TaskKind.REFORESTATION:
        coverage = _optional_float(state.get("coverage_ratio"))
        return None if coverage is None else coverage > 0.0
    if task_kind is TaskKind.COVERAGE:
        success = state.get("success")
        if success is not None:
            return bool(success)
        coverage = _optional_float(state.get("coverage_ratio"))
        return None if coverage is None else coverage >= 0.999 and bool(state.get("return_to_start_success"))
    if task_kind is TaskKind.PATROL:
        return len(state.get("goal_pos") or []) == 0 or goal_delta > 0
    return goal_delta > 0


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _sanitize_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_sanitize_value(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if hasattr(value, "tolist"):
        try:
            return value.tolist()
        except Exception:
            return str(value)
    return value
