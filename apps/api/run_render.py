from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from apps.api.run_exports import build_run_result_payload, read_last_replay_snapshot
from packages.db.models.artifact import Artifact
from packages.db.models.enums import ArtifactType
from packages.db.session import db_session


CANVAS_SIZE = 520


def render_run_svg(run_id: int, output_dir: Path | None = None) -> Path:
    payload = build_run_result_payload(run_id)
    replay_path = payload.get("replay_path")
    if replay_path is None:
        raise KeyError(f"Run '{run_id}' has no replay path")

    if output_dir is None:
        output_dir = Path(replay_path).resolve().parent / "exports"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "trajectory.svg"

    snapshot = read_last_replay_snapshot(Path(replay_path)) or {}
    state = dict(snapshot.get("state") or {})
    points = _extract_points(state, Path(replay_path))

    svg = _build_svg_document(payload, state, points)
    output_path.write_text(svg, encoding="utf-8")

    with db_session() as db:
        artifact = (
            db.query(Artifact)
            .filter(Artifact.run_id == int(run_id), Artifact.storage_uri == str(output_path))
            .first()
        )
        size_bytes = output_path.stat().st_size
        if artifact is None:
            db.add(
                Artifact(
                    run_id=int(run_id),
                    artifact_type=ArtifactType.plot,
                    name=output_path.name,
                    storage_uri=str(output_path),
                    mime_type="image/svg+xml",
                    size_bytes=size_bytes,
                )
            )
        else:
            artifact.artifact_type = ArtifactType.plot
            artifact.name = output_path.name
            artifact.mime_type = "image/svg+xml"
            artifact.size_bytes = size_bytes

    return output_path


def _extract_points(state: dict[str, Any], replay_path: Path) -> list[tuple[float, float]]:
    trajectory = state.get("trajectory") or []
    points: list[tuple[float, float]] = []
    for point in trajectory:
        if isinstance(point, (list, tuple)) and len(point) >= 2:
            points.append((float(point[0]), float(point[1])))

    if points:
        return points

    with replay_path.open("r", encoding="utf-8") as stream:
        for line in stream:
            line = line.strip()
            if not line:
                continue
            payload = json.loads(line)
            agent_pos = list((payload.get("state") or {}).get("agent_pos") or [])
            if agent_pos and isinstance(agent_pos[0], (list, tuple)) and len(agent_pos[0]) >= 2:
                points.append((float(agent_pos[0][0]), float(agent_pos[0][1])))
    return points


def _build_svg_document(run_payload: dict[str, Any], state: dict[str, Any], points: list[tuple[float, float]]) -> str:
    terrain_map = state.get("terrain_map") if isinstance(state.get("terrain_map"), list) else None
    rows = len(terrain_map or [])
    cols = len(terrain_map[0]) if rows else 0

    grid_markup = []
    if rows and cols:
        cell_w = CANVAS_SIZE / max(cols, 1)
        cell_h = CANVAS_SIZE / max(rows, 1)
        for y in range(rows):
            for x in range(cols):
                value = float((terrain_map[y] or [0])[x] or 0.0)
                fill = "#f8fafc" if value <= 0.5 else "rgba(156,163,175,0.65)"
                grid_markup.append(
                    f'<rect x="{x * cell_w:.2f}" y="{y * cell_h:.2f}" width="{cell_w:.2f}" height="{cell_h:.2f}" fill="{fill}" stroke="#e5e7eb" stroke-width="1" />'
                )

    overlay_markup = []
    if rows and cols and points:
        cell_w = CANVAS_SIZE / max(cols, 1)
        cell_h = CANVAS_SIZE / max(rows, 1)
        svg_points = " ".join(
            f"{point[1] * cell_w + cell_w / 2:.2f},{point[0] * cell_h + cell_h / 2:.2f}"
            for point in points
        )
        overlay_markup.append(
            f'<polyline points="{svg_points}" fill="none" stroke="#2563eb" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" opacity="0.85" />'
        )
        start = points[0]
        end = points[-1]
        overlay_markup.append(
            f'<circle cx="{start[1] * cell_w + cell_w / 2:.2f}" cy="{start[0] * cell_h + cell_h / 2:.2f}" r="5" fill="#16a34a" />'
        )
        overlay_markup.append(
            f'<circle cx="{end[1] * cell_w + cell_w / 2:.2f}" cy="{end[0] * cell_h + cell_h / 2:.2f}" r="6" fill="#dc2626" />'
        )
    elif points:
        xs = [point[1] for point in points]
        ys = [point[0] for point in points]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        span_x = max(1.0, max_x - min_x)
        span_y = max(1.0, max_y - min_y)
        svg_points = " ".join(
            f"{20 + (point[1] - min_x) / span_x * (CANVAS_SIZE - 40):.2f},{20 + (point[0] - min_y) / span_y * (CANVAS_SIZE - 40):.2f}"
            for point in points
        )
        overlay_markup.append(
            f'<polyline points="{svg_points}" fill="none" stroke="#2563eb" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" opacity="0.85" />'
        )

    final_state = dict(run_payload.get("final_state") or {})
    summary_lines = [
        f"run_id={run_payload.get('run_id')}",
        f"status={run_payload.get('status')}",
        f"episodes={run_payload.get('episodes_count')}",
        f"step={final_state.get('step')}",
        f"reward={final_state.get('total_reward')}",
        f"goal_count={final_state.get('goal_count')}",
        f"collision_count={final_state.get('collision_count')}",
        f"coverage={final_state.get('coverage_ratio')}",
    ]
    summary_markup = "".join(
        f'<text x="560" y="{40 + index * 24}" font-size="14" fill="#0f172a">{_escape(line)}</text>'
        for index, line in enumerate(summary_lines)
    )

    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="860" height="560" viewBox="0 0 860 560">'
        '<rect width="860" height="560" fill="#ffffff" />'
        '<text x="24" y="28" font-size="18" font-weight="700" fill="#0f172a">Run trajectory</text>'
        '<g transform="translate(20,40)">'
        f'<rect x="0" y="0" width="{CANVAS_SIZE}" height="{CANVAS_SIZE}" fill="#f8fafc" stroke="#cbd5e1" stroke-width="1" />'
        f'{"".join(grid_markup)}'
        f'{"".join(overlay_markup)}'
        '</g>'
        f"{summary_markup}"
        "</svg>"
    )


def _escape(value: Any) -> str:
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
