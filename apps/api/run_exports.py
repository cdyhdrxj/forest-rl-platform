from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from statistics import mean, median
from typing import Any

from packages.db.models.artifact import Artifact
from packages.db.models.episode import Episode
from packages.db.models.metric_series import MetricSeries
from packages.db.models.replay import Replay
from packages.db.models.run import Run
from packages.db.models.enums import ArtifactType
from packages.db.session import db_session


def export_run_bundle(run_id: int, output_dir: Path | None = None) -> dict[str, str]:
    payload = build_run_result_payload(run_id)
    if output_dir is None:
        output_dir = get_run_export_dir(run_id)
    output_dir.mkdir(parents=True, exist_ok=True)

    metrics_payload = build_metrics_export_payload(run_id)
    episodes_payload = build_episode_log_payload(run_id)

    metrics_path = output_dir / "metrics_export.json"
    episodes_path = output_dir / "episode_log.json"
    summary_path = output_dir / "run_result.json"

    _write_json(metrics_path, metrics_payload)
    _write_json(episodes_path, episodes_payload)
    _write_json(summary_path, payload)

    with db_session() as db:
        _upsert_artifact(
            db,
            run_id=run_id,
            artifact_type=ArtifactType.metric_export,
            name=metrics_path.name,
            storage_uri=str(metrics_path),
            mime_type="application/json",
        )
        _upsert_artifact(
            db,
            run_id=run_id,
            artifact_type=ArtifactType.report,
            name=episodes_path.name,
            storage_uri=str(episodes_path),
            mime_type="application/json",
        )
        _upsert_artifact(
            db,
            run_id=run_id,
            artifact_type=ArtifactType.report,
            name=summary_path.name,
            storage_uri=str(summary_path),
            mime_type="application/json",
        )

    return {
        "metrics_path": str(metrics_path),
        "episode_log_path": str(episodes_path),
        "run_result_path": str(summary_path),
    }


def get_run_export_dir(run_id: int) -> Path:
    repo_root = Path(__file__).resolve().parents[2]
    path = repo_root / "data" / "runs" / f"run_{int(run_id)}" / "exports"
    path.mkdir(parents=True, exist_ok=True)
    return path


def build_metrics_export_payload(run_id: int) -> dict[str, Any]:
    with db_session() as db:
        run = db.query(Run).filter(Run.id == int(run_id)).first()
        if run is None:
            raise KeyError(f"Run '{run_id}' not found")

        series_rows = (
            db.query(MetricSeries)
            .filter(MetricSeries.run_id == int(run_id))
            .order_by(MetricSeries.id.asc())
            .all()
        )

        series_payload = []
        for series in series_rows:
            points = sorted(series.points, key=lambda point: point.point_index)
            series_payload.append(
                {
                    "name": series.name,
                    "unit": series.unit,
                    "aggregation": series.aggregation,
                    "source": series.source,
                    "description": series.description,
                    "points": [
                        {
                            "point_index": point.point_index,
                            "train_step": point.train_step,
                            "episode_index": point.episode_index,
                            "wall_time_sec": point.wall_time_sec,
                            "value": point.value,
                            "created_at": _iso(point.created_at),
                        }
                        for point in points
                    ],
                }
            )

        return {
            "run_id": int(run.id),
            "route_key": str((run.config_json or {}).get("route_key") or ""),
            "exported_at": datetime.utcnow().isoformat() + "Z",
            "series": series_payload,
        }


def build_episode_log_payload(run_id: int) -> dict[str, Any]:
    with db_session() as db:
        run = db.query(Run).filter(Run.id == int(run_id)).first()
        if run is None:
            raise KeyError(f"Run '{run_id}' not found")

        episodes = (
            db.query(Episode)
            .filter(Episode.run_id == int(run_id))
            .order_by(Episode.episode_index.asc())
            .all()
        )

        return {
            "run_id": int(run.id),
            "route_key": str((run.config_json or {}).get("route_key") or ""),
            "exported_at": datetime.utcnow().isoformat() + "Z",
            "episodes": [
                {
                    "episode_index": episode.episode_index,
                    "success": episode.success,
                    "terminated_by": episode.terminated_by,
                    "reward_total": episode.reward_total,
                    "steps_count": episode.steps_count,
                    "duration_sec": episode.duration_sec,
                    "path_length": episode.path_length,
                    "path_cost": episode.path_cost,
                    "collisions_count": episode.collisions_count,
                    "coverage_ratio": episode.coverage_ratio,
                    "avg_detection_delay": episode.avg_detection_delay,
                    "total_damage": episode.total_damage,
                    "created_at": _iso(episode.created_at),
                    "events": [
                        {
                            "step_index": event.step_index,
                            "sim_time_sec": event.sim_time_sec,
                            "event_type": event.event_type.value if hasattr(event.event_type, "value") else str(event.event_type),
                            "x": event.x,
                            "y": event.y,
                            "z": event.z,
                            "intruder_id": _event_intruder_id(event),
                            "payload_json": event.payload_json,
                            "created_at": _iso(event.created_at),
                        }
                        for event in sorted(episode.events, key=lambda current: (current.step_index or 0, current.id or 0))
                    ],
                }
                for episode in episodes
            ],
        }


def build_run_result_payload(run_id: int) -> dict[str, Any]:
    with db_session() as db:
        run = db.query(Run).filter(Run.id == int(run_id)).first()
        if run is None:
            raise KeyError(f"Run '{run_id}' not found")

        episodes = (
            db.query(Episode)
            .filter(Episode.run_id == int(run_id))
            .order_by(Episode.episode_index.asc())
            .all()
        )
        replay = (
            db.query(Replay)
            .filter(Replay.run_id == int(run_id))
            .order_by(Replay.created_at.desc(), Replay.id.desc())
            .first()
        )

        rewards = [episode.reward_total for episode in episodes if episode.reward_total is not None]
        steps = [episode.steps_count for episode in episodes if episode.steps_count is not None]
        coverage_values = [episode.coverage_ratio for episode in episodes if episode.coverage_ratio is not None]
        success_flags = [episode.success for episode in episodes if episode.success is not None]
        last_snapshot = read_last_replay_snapshot(Path(replay.storage_uri)) if replay is not None else None

        duration_sec = None
        if run.started_at is not None and run.finished_at is not None:
            duration_sec = max(0.0, (run.finished_at - run.started_at).total_seconds())

        return {
            "run_id": int(run.id),
            "route_key": str((run.config_json or {}).get("route_key") or ""),
            "status": run.status.value if hasattr(run.status, "value") else str(run.status),
            "algorithm_code": getattr(run.algorithm, "code", None),
            "title": run.title,
            "seed": run.seed,
            "started_at": _iso(run.started_at),
            "finished_at": _iso(run.finished_at),
            "duration_sec": duration_sec,
            "episodes_count": len(episodes),
            "episode_success_rate": _ratio(success_flags),
            "episode_reward_mean": mean(rewards) if rewards else None,
            "episode_reward_median": median(rewards) if rewards else None,
            "episode_steps_mean": mean(steps) if steps else None,
            "coverage_ratio_mean": mean(coverage_values) if coverage_values else None,
            "success": (last_snapshot.get("state") or {}).get("success") if isinstance(last_snapshot, dict) else None,
            "missed_area_ratio": (last_snapshot.get("state") or {}).get("missed_area_ratio") if isinstance(last_snapshot, dict) else None,
            "return_to_start_success": (last_snapshot.get("state") or {}).get("return_to_start_success") if isinstance(last_snapshot, dict) else None,
            "return_error": (last_snapshot.get("state") or {}).get("return_error") if isinstance(last_snapshot, dict) else None,
            "path_length": (last_snapshot.get("state") or {}).get("path_length") if isinstance(last_snapshot, dict) else None,
            "task_time_sec": (last_snapshot.get("state") or {}).get("task_time_sec") if isinstance(last_snapshot, dict) else None,
            "transition_count": (last_snapshot.get("state") or {}).get("transition_count") if isinstance(last_snapshot, dict) else None,
            "repeat_coverage_ratio": (last_snapshot.get("state") or {}).get("repeat_coverage_ratio") if isinstance(last_snapshot, dict) else None,
            "angular_work_rad": (last_snapshot.get("state") or {}).get("angular_work_rad") if isinstance(last_snapshot, dict) else None,
            "compute_time_sec": (last_snapshot.get("state") or {}).get("compute_time_sec") if isinstance(last_snapshot, dict) else None,
            "final_state": last_snapshot.get("state") if isinstance(last_snapshot, dict) else None,
            "replay_path": replay.storage_uri if replay is not None else None,
            "config_json": run.config_json,
        }


def read_last_replay_snapshot(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    last_line = ""
    with path.open("r", encoding="utf-8") as stream:
        for line in stream:
            stripped = line.strip()
            if stripped:
                last_line = stripped
    if not last_line:
        return None
    return json.loads(last_line)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _ratio(values: list[bool]) -> float | None:
    if not values:
        return None
    return sum(1 for value in values if value) / len(values)


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


def _event_intruder_id(event) -> int | None:
    payload_json = dict(event.payload_json or {})
    intruder_id = payload_json.get("intruder_id")
    if intruder_id is None:
        return None
    try:
        return int(intruder_id)
    except (TypeError, ValueError):
        return None


def _upsert_artifact(
    db,
    *,
    run_id: int,
    artifact_type: ArtifactType,
    name: str,
    storage_uri: str,
    mime_type: str,
) -> None:
    artifact = (
        db.query(Artifact)
        .filter(
            Artifact.run_id == int(run_id),
            Artifact.storage_uri == storage_uri,
        )
        .first()
    )
    size_bytes = Path(storage_uri).stat().st_size if Path(storage_uri).exists() else None
    if artifact is None:
        db.add(
            Artifact(
                run_id=int(run_id),
                artifact_type=artifact_type,
                name=name,
                storage_uri=storage_uri,
                mime_type=mime_type,
                size_bytes=size_bytes,
            )
        )
        return

    artifact.artifact_type = artifact_type
    artifact.name = name
    artifact.mime_type = mime_type
    artifact.size_bytes = size_bytes
