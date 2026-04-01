from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from apps.api.run_exports import build_run_result_payload, export_run_bundle
from apps.api.run_render import render_run_svg
from experiments.scientific.models import ScientificSuiteConfig
from experiments.scientific.stats import maybe_max, maybe_mean, maybe_median, maybe_min, maybe_std
from packages.db.models.experiment_suite import ExperimentSuite
from packages.db.models.experiment_suite_run import ExperimentSuiteRun
from packages.db.session import db_session


def build_suite_report(
    suite_id: int,
    config: ScientificSuiteConfig,
    report_dir: Path,
    *,
    suite_status: str | None = None,
    suite_finished_at: datetime | None = None,
) -> dict[str, Any]:
    report_dir.mkdir(parents=True, exist_ok=True)
    plots_dir = report_dir / "plots"
    trajectories_dir = report_dir / "trajectories"
    plots_dir.mkdir(parents=True, exist_ok=True)
    trajectories_dir.mkdir(parents=True, exist_ok=True)

    with db_session() as db:
        suite = db.query(ExperimentSuite).filter(ExperimentSuite.id == int(suite_id)).first()
        if suite is None:
            raise KeyError(f"Experiment suite '{suite_id}' not found")

        suite_runs = (
            db.query(ExperimentSuiteRun)
            .filter(ExperimentSuiteRun.suite_id == int(suite_id))
            .order_by(
                ExperimentSuiteRun.scenario_family.asc(),
                ExperimentSuiteRun.dataset_split.asc(),
                ExperimentSuiteRun.method_code.asc(),
                ExperimentSuiteRun.replicate_index.asc(),
                ExperimentSuiteRun.run_id.asc(),
            )
            .all()
        )

    run_rows = [_build_run_row(current) for current in suite_runs]
    aggregates = _aggregate_runs(run_rows)
    plots = []
    trajectories = []

    if config.report.save_distribution_plots:
        plots.extend(_render_plot_set(aggregates, plots_dir))
    if config.report.save_trajectory_plots:
        trajectories.extend(
            _render_representative_runs(
                run_rows,
                trajectories_dir,
                per_method=config.report.representative_runs_per_method,
            )
        )

    report_payload = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "suite": {
            "suite_id": int(suite.id),
            "suite_code": suite.code,
            "title": suite.title,
            "route_key": suite.route_key,
            "mode": suite.mode,
            "status": suite_status or suite.status,
            "started_at": _iso(suite.started_at),
            "finished_at": _iso(suite_finished_at or suite.finished_at),
        },
        "config": config.model_dump(mode="json"),
        "overview": {
            "total_runs": len(run_rows),
            "methods": sorted({row["method_code"] for row in run_rows}),
            "scenario_families": sorted({row["scenario_family"] for row in run_rows}),
            "splits": sorted({row["dataset_split"] for row in run_rows}),
            "status_counts": _status_counts(run_rows),
        },
        "aggregates": aggregates,
        "runs": run_rows,
        "artifacts": {
            "plots": [_relative_name(path, report_dir) for path in plots],
            "trajectories": [_relative_name(path, report_dir) for path in trajectories],
        },
    }

    enabled_formats = set(config.report.formats)

    manifest_payload = {
        "suite_id": int(suite.id),
        "suite_code": suite.code,
        "report_dir": str(report_dir),
        "report_files": {
            "report_json": str(report_dir / "report.json") if "json" in enabled_formats else None,
            "summary_csv": str(report_dir / "summary.csv") if "csv" in enabled_formats else None,
            "report_html": str(report_dir / "report.html") if "html" in enabled_formats else None,
        },
        "runs": [
            {
                "run_id": row["run_id"],
                "method_code": row["method_code"],
                "scenario_family": row["scenario_family"],
                "dataset_split": row["dataset_split"],
                "run_result_path": row.get("run_result_path"),
                "trajectory_path": row.get("trajectory_path"),
            }
            for row in run_rows
        ],
    }

    report_json_path = report_dir / "report.json"
    summary_csv_path = report_dir / "summary.csv"
    report_html_path = report_dir / "report.html"
    manifest_path = report_dir / "suite_manifest.json"

    if "json" in enabled_formats:
        _write_json(report_json_path, report_payload)
    if "csv" in enabled_formats:
        _write_summary_csv(summary_csv_path, run_rows)
    if "html" in enabled_formats:
        _write_html(report_html_path, report_payload)
    _write_json(manifest_path, manifest_payload)

    return {
        "summary": {
            "total_runs": len(run_rows),
            "status_counts": _status_counts(run_rows),
            "methods": aggregates,
        },
        "report_json_path": str(report_json_path) if "json" in enabled_formats else None,
        "summary_csv_path": str(summary_csv_path) if "csv" in enabled_formats else None,
        "report_html_path": str(report_html_path) if "html" in enabled_formats else None,
        "manifest_path": str(manifest_path),
        "plot_paths": [str(path) for path in plots],
        "trajectory_paths": [str(path) for path in trajectories],
    }


def _build_run_row(suite_run: ExperimentSuiteRun) -> dict[str, Any]:
    bundle = export_run_bundle(int(suite_run.run_id))
    run_result = build_run_result_payload(int(suite_run.run_id))
    row = {
        "run_id": int(suite_run.run_id),
        "scenario_family": suite_run.scenario_family,
        "dataset_split": suite_run.dataset_split,
        "method_code": suite_run.method_code,
        "replicate_index": suite_run.replicate_index,
        "role": suite_run.role,
        "train_seed": suite_run.train_seed,
        "eval_seed": suite_run.eval_seed,
        "group_key": suite_run.group_key,
        "status": run_result.get("status"),
        "algorithm_code": run_result.get("algorithm_code"),
        "success": run_result.get("success"),
        "duration_sec": run_result.get("duration_sec"),
        "episodes_count": run_result.get("episodes_count"),
        "episode_success_rate": run_result.get("episode_success_rate"),
        "episode_reward_mean": run_result.get("episode_reward_mean"),
        "episode_reward_median": run_result.get("episode_reward_median"),
        "episode_steps_mean": run_result.get("episode_steps_mean"),
        "coverage_ratio_mean": run_result.get("coverage_ratio_mean"),
        "missed_area_ratio": run_result.get("missed_area_ratio"),
        "return_to_start_success": run_result.get("return_to_start_success"),
        "return_error": run_result.get("return_error"),
        "path_length": run_result.get("path_length"),
        "task_time_sec": run_result.get("task_time_sec"),
        "transition_count": run_result.get("transition_count"),
        "repeat_coverage_ratio": run_result.get("repeat_coverage_ratio"),
        "angular_work_rad": run_result.get("angular_work_rad"),
        "compute_time_sec": run_result.get("compute_time_sec"),
        "run_result_path": bundle.get("run_result_path"),
        "metrics_export_path": bundle.get("metrics_path"),
        "episode_log_path": bundle.get("episode_log_path"),
        "trajectory_path": None,
        "config_json": run_result.get("config_json") or {},
    }
    return row


def _aggregate_runs(run_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_method: dict[str, list[dict[str, Any]]] = {}
    for row in run_rows:
        by_method.setdefault(row["method_code"], []).append(row)

    aggregates = []
    for method_code, rows in sorted(by_method.items()):
        finished_rows = [row for row in rows if row.get("status") == "finished"]
        aggregates.append(
            {
                "method_code": method_code,
                "runs_count": len(rows),
                "finished_runs_count": len(finished_rows),
                "scenario_families": sorted({row["scenario_family"] for row in rows}),
                "splits": sorted({row["dataset_split"] for row in rows}),
                "duration_sec_mean": maybe_mean(row.get("duration_sec") for row in rows),
                "duration_sec_std": maybe_std(row.get("duration_sec") for row in rows),
                "episode_success_rate_mean": maybe_mean(row.get("episode_success_rate") for row in rows),
                "episode_reward_mean": maybe_mean(row.get("episode_reward_mean") for row in rows),
                "episode_reward_median": maybe_median(row.get("episode_reward_mean") for row in rows),
                "episode_reward_min": maybe_min(row.get("episode_reward_mean") for row in rows),
                "episode_reward_max": maybe_max(row.get("episode_reward_mean") for row in rows),
                "coverage_ratio_mean": maybe_mean(row.get("coverage_ratio_mean") for row in rows),
                "missed_area_ratio_mean": maybe_mean(row.get("missed_area_ratio") for row in rows),
                "return_error_mean": maybe_mean(row.get("return_error") for row in rows),
                "path_length_mean": maybe_mean(row.get("path_length") for row in rows),
                "task_time_sec_mean": maybe_mean(row.get("task_time_sec") for row in rows),
                "transition_count_mean": maybe_mean(row.get("transition_count") for row in rows),
                "repeat_coverage_ratio_mean": maybe_mean(row.get("repeat_coverage_ratio") for row in rows),
                "angular_work_rad_mean": maybe_mean(row.get("angular_work_rad") for row in rows),
                "compute_time_sec_mean": maybe_mean(row.get("compute_time_sec") for row in rows),
                "episode_steps_mean": maybe_mean(row.get("episode_steps_mean") for row in rows),
                "status_counts": _status_counts(rows),
            }
        )
    return aggregates


def _render_plot_set(aggregates: list[dict[str, Any]], plots_dir: Path) -> list[Path]:
    paths: list[Path] = []

    reward_values = [
        (item["method_code"], item.get("episode_reward_mean"))
        for item in aggregates
    ]
    if any(value is not None for _, value in reward_values):
        reward_path = plots_dir / "reward_by_method.svg"
        _write_bar_chart_svg(
            reward_path,
            title="Mean Reward by Method",
            y_label="reward",
            values=reward_values,
        )
        paths.append(reward_path)

    success_values = [
        (item["method_code"], item.get("episode_success_rate_mean"))
        for item in aggregates
    ]
    if any(value is not None for _, value in success_values):
        success_path = plots_dir / "success_rate_by_method.svg"
        _write_bar_chart_svg(
            success_path,
            title="Episode Success Rate by Method",
            y_label="ratio",
            values=success_values,
        )
        paths.append(success_path)

    return paths


def _render_representative_runs(
    run_rows: list[dict[str, Any]],
    trajectories_dir: Path,
    *,
    per_method: int,
) -> list[Path]:
    if per_method <= 0:
        return []

    selected_paths: list[Path] = []
    by_method: dict[str, list[dict[str, Any]]] = {}
    for row in run_rows:
        by_method.setdefault(row["method_code"], []).append(row)

    for method_code, rows in sorted(by_method.items()):
        ranked = sorted(
            rows,
            key=lambda row: (
                0 if row.get("status") == "finished" else 1,
                -(row.get("episode_success_rate") or 0.0),
                -(row.get("episode_reward_mean") or 0.0),
                row.get("run_id") or 0,
            ),
        )
        for row in ranked[:per_method]:
            output_dir = trajectories_dir / (
                f"{row['scenario_family']}_{row['dataset_split']}_{method_code}_run_{row['run_id']}"
            )
            try:
                output_path = render_run_svg(int(row["run_id"]), output_dir=output_dir)
            except KeyError:
                row["trajectory_path"] = None
                continue
            row["trajectory_path"] = str(output_path)
            selected_paths.append(output_path)

    return selected_paths


def _write_summary_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "run_id",
        "scenario_family",
        "dataset_split",
        "method_code",
        "replicate_index",
        "role",
        "train_seed",
        "eval_seed",
        "group_key",
        "status",
        "algorithm_code",
        "success",
        "duration_sec",
        "episodes_count",
        "episode_success_rate",
        "episode_reward_mean",
        "episode_reward_median",
        "episode_steps_mean",
        "coverage_ratio_mean",
        "missed_area_ratio",
        "return_to_start_success",
        "return_error",
        "path_length",
        "task_time_sec",
        "transition_count",
        "repeat_coverage_ratio",
        "angular_work_rad",
        "compute_time_sec",
        "run_result_path",
        "metrics_export_path",
        "episode_log_path",
        "trajectory_path",
    ]

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field) for field in fieldnames})


def _write_html(path: Path, report_payload: dict[str, Any]) -> None:
    overview = report_payload["overview"]
    suite = report_payload["suite"]
    aggregate_rows = report_payload["aggregates"]
    run_rows = report_payload["runs"]
    artifact_paths = report_payload["artifacts"]

    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>{_escape(suite["title"])}</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f7fafc;
      --panel: #ffffff;
      --text: #102a43;
      --muted: #627d98;
      --line: #d9e2ec;
      --accent: #1d4ed8;
      --accent-soft: #dbeafe;
    }}
    body {{
      margin: 0;
      padding: 32px;
      background: linear-gradient(180deg, #eef2ff 0%, var(--bg) 36%, #f8fafc 100%);
      color: var(--text);
      font: 15px/1.5 Georgia, "Times New Roman", serif;
    }}
    h1, h2 {{
      margin: 0 0 12px;
    }}
    .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 16px;
      padding: 20px 22px;
      margin-bottom: 18px;
      box-shadow: 0 12px 34px rgba(15, 23, 42, 0.06);
    }}
    .meta {{
      color: var(--muted);
      margin-top: 6px;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
    }}
    th, td {{
      text-align: left;
      border-bottom: 1px solid var(--line);
      padding: 8px 10px;
      vertical-align: top;
    }}
    th {{
      background: #f8fafc;
      font-weight: 700;
    }}
    .chips span {{
      display: inline-block;
      margin: 0 8px 8px 0;
      padding: 6px 10px;
      border-radius: 999px;
      background: var(--accent-soft);
      color: var(--accent);
      font-size: 13px;
    }}
    a {{
      color: var(--accent);
      text-decoration: none;
    }}
  </style>
</head>
<body>
  <section class="panel">
    <h1>{_escape(suite["title"])}</h1>
    <div class="meta">suite_code={_escape(suite["suite_code"])} | route_key={_escape(suite["route_key"])} | status={_escape(suite["status"])}</div>
    <div class="meta">generated_at={_escape(report_payload["generated_at"])}</div>
  </section>
  <section class="panel">
    <h2>Overview</h2>
    <div class="chips">
      <span>total_runs={overview["total_runs"]}</span>
      <span>methods={len(overview["methods"])}</span>
      <span>families={len(overview["scenario_families"])}</span>
      <span>splits={", ".join(overview["splits"])}</span>
    </div>
    {_rows_to_html_table(report_payload["aggregates"])}
  </section>
  <section class="panel">
    <h2>Runs</h2>
    {_rows_to_html_table(run_rows)}
  </section>
  <section class="panel">
    <h2>Artifacts</h2>
    <div class="chips">
      {"".join(f'<span><a href="{_escape(path)}">{_escape(path)}</a></span>' for path in artifact_paths["plots"] + artifact_paths["trajectories"])}
    </div>
  </section>
</body>
</html>"""
    path.write_text(html, encoding="utf-8")


def _write_bar_chart_svg(
    path: Path,
    *,
    title: str,
    y_label: str,
    values: list[tuple[str, float | None]],
) -> None:
    filtered = [(label, float(value)) for label, value in values if value is not None]
    if not filtered:
        return

    width = 720
    height = 360
    left = 56
    baseline = 300
    bar_width = max(36, int((width - left - 32) / max(len(filtered), 1) * 0.6))
    gap = max(18, int((width - left - 32) / max(len(filtered), 1) * 0.4))
    max_value = max(value for _, value in filtered) or 1.0

    bars = []
    for index, (label, value) in enumerate(filtered):
        bar_height = (value / max_value) * 220 if max_value else 0.0
        x = left + index * (bar_width + gap)
        y = baseline - bar_height
        bars.append(
            f'<rect x="{x}" y="{y:.2f}" width="{bar_width}" height="{bar_height:.2f}" rx="8" fill="#2563eb" opacity="0.88" />'
        )
        bars.append(
            f'<text x="{x + bar_width / 2:.2f}" y="{baseline + 18}" text-anchor="middle" font-size="12" fill="#334155">{_escape(label)}</text>'
        )
        bars.append(
            f'<text x="{x + bar_width / 2:.2f}" y="{y - 8:.2f}" text-anchor="middle" font-size="12" fill="#0f172a">{value:.3f}</text>'
        )

    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
        '<rect width="100%" height="100%" fill="#ffffff" />'
        f'<text x="24" y="28" font-size="18" font-weight="700" fill="#0f172a">{_escape(title)}</text>'
        f'<text x="16" y="172" transform="rotate(-90 16 172)" font-size="12" fill="#64748b">{_escape(y_label)}</text>'
        f'<line x1="{left}" y1="60" x2="{left}" y2="{baseline}" stroke="#cbd5e1" stroke-width="1" />'
        f'<line x1="{left}" y1="{baseline}" x2="{width - 24}" y2="{baseline}" stroke="#cbd5e1" stroke-width="1" />'
        f'{"".join(bars)}'
        "</svg>"
    )
    path.write_text(svg, encoding="utf-8")


def _rows_to_html_table(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "<p>No rows collected.</p>"

    keys = list(rows[0].keys())
    header = "".join(f"<th>{_escape(key)}</th>" for key in keys)
    body = []
    for row in rows:
        cells = []
        for key in keys:
            value = row.get(key)
            if isinstance(value, list):
                value = ", ".join(str(item) for item in value)
            elif isinstance(value, dict):
                value = json.dumps(value, ensure_ascii=False)
            cells.append(f"<td>{_escape(value)}</td>")
        body.append(f"<tr>{''.join(cells)}</tr>")
    return f"<table><thead><tr>{header}</tr></thead><tbody>{''.join(body)}</tbody></table>"


def _status_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        key = str(row.get("status") or "unknown")
        counts[key] = counts.get(key, 0) + 1
    return counts


def _relative_name(path: Path, root: Path) -> str:
    return str(path.relative_to(root))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


def _escape(value: Any) -> str:
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
