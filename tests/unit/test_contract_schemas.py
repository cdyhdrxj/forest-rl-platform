from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator


REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACTS_ROOT = REPO_ROOT / "contracts" / "v1"


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _load_schema(name: str) -> dict:
    return _load_json(CONTRACTS_ROOT / name)


def _assert_valid(schema_name: str, payload) -> None:
    schema = _load_schema(schema_name)
    Draft202012Validator(schema).validate(payload)


def test_synthetic_scenario_and_preview_payloads_conform_to_contracts():
    preview_payload = {
        "environment_kind": "grid",
        "task_kind": "patrol",
        "preview_payload": {
            "terrain_map": [[0.0, 1.0], [1.0, 0.0]],
            "agent_pos": [[1.0, 1.0]],
            "goal_pos": [[2.0, 2.0]],
            "landmark_pos": [],
        },
        "validation_passed": True,
        "validation_messages": [],
        "validation_report": {
            "passed": True,
            "issues": [],
        },
    }
    manifest_payload = {
        "environment_kind": "grid",
        "task_kind": "patrol",
        "seed": 17,
        "generator_name": "unit",
        "generator_version": "v1",
        "effective_params": {"grid_size": 4, "terrain_hilliness": 0.4},
        "preview_payload": dict(preview_payload["preview_payload"]),
        "runtime_context": {"patrol": {"agent_pos": [1, 1], "intruder_positions": [[2, 2]]}},
        "validation_messages": [],
        "validation_passed": True,
        "validation_report": {
            "passed": True,
            "issues": [],
        },
        "request": {
            "environment_kind": "grid",
            "task_kind": "patrol",
            "seed": 17,
            "terrain_params": {"grid_size": 4},
            "forest_params": {"terrain_hilliness": 0.4},
            "task_params": {"intruder_count": 1},
            "visualization_options": {"show_preview": True},
            "metadata": {"source": "contract-test"},
        },
        "runtime_config": {"seed": 17, "grid_size": 4},
        "layers": [
            {
                "name": "terrain",
                "layer_type": "terrain",
                "file_uri": "/tmp/terrain.npy",
                "file_format": "npy",
                "description": "Synthetic terrain layer",
            }
        ],
        "preview_uri": "/tmp/preview.json",
    }

    _assert_valid("scenario.schema.json", manifest_payload)
    _assert_valid("preview.schema.json", preview_payload)


def test_real_persisted_scenario_samples_conform_to_contracts():
    scenario_paths = sorted((REPO_ROOT / "data" / "scenarios" / "generated").glob("**/scenario.json"))
    preview_paths = sorted((REPO_ROOT / "data" / "scenarios" / "generated").glob("**/preview.json"))

    if not scenario_paths or not preview_paths:
        pytest.skip("No persisted scenario samples found under data/scenarios/generated")

    for path in scenario_paths[:3]:
        _assert_valid("scenario.schema.json", _load_json(path))

    for path in preview_paths[:3]:
        _assert_valid("preview.schema.json", _load_json(path))


def test_real_replay_sample_lines_conform_to_contract():
    replay_paths = sorted((REPO_ROOT / "data" / "runs").glob("**/replay_*.jsonl"))
    if not replay_paths:
        pytest.skip("No replay samples found under data/runs")

    checked = 0
    for replay_path in replay_paths[:2]:
        with replay_path.open("r", encoding="utf-8") as stream:
            for line in stream:
                line = line.strip()
                if not line:
                    continue
                _assert_valid("replay.schema.json", json.loads(line))
                checked += 1
                if checked >= 4:
                    break
        if checked >= 4:
            break

    assert checked > 0


def test_metrics_export_payload_conforms_to_contract():
    payload = {
        "run_id": 12,
        "route_key": "threed/trail",
        "exported_at": "2026-03-30T12:00:00Z",
        "series": [
            {
                "name": "step",
                "unit": "steps",
                "aggregation": "snapshot",
                "source": "dispatcher",
                "description": "Dispatcher snapshot series for step",
                "points": [
                    {
                        "point_index": 0,
                        "train_step": 0,
                        "episode_index": None,
                        "wall_time_sec": 1710000000.0,
                        "value": 0.0,
                        "created_at": "2026-03-30T12:00:00Z",
                    },
                    {
                        "point_index": 1,
                        "train_step": 1,
                        "episode_index": 1,
                        "wall_time_sec": 1710000001.0,
                        "value": 1.0,
                        "created_at": "2026-03-30T12:00:01Z",
                    },
                ],
            }
        ],
    }

    _assert_valid("metrics.schema.json", payload)


def test_episode_log_payload_conforms_to_contract():
    payload = {
        "run_id": 7,
        "route_key": "threed/patrol",
        "exported_at": "2026-03-30T12:00:00Z",
        "episodes": [
            {
                "episode_index": 1,
                "success": True,
                "terminated_by": "finished",
                "reward_total": 5.0,
                "steps_count": 20,
                "duration_sec": 1.5,
                "path_length": 20.0,
                "path_cost": 1.0,
                "collisions_count": 1,
                "coverage_ratio": 0.75,
                "avg_detection_delay": 0.2,
                "total_damage": 0.0,
                "created_at": "2026-03-30T12:00:00Z",
                "events": [
                    {
                        "step_index": 5,
                        "sim_time_sec": 1710000000.5,
                        "event_type": "intruder_appeared",
                        "x": 3.0,
                        "y": 4.0,
                        "z": None,
                        "intruder_id": 1,
                        "payload_json": {"intruder_id": 1},
                        "created_at": "2026-03-30T12:00:00Z",
                    },
                    {
                        "step_index": 20,
                        "sim_time_sec": 1710000001.5,
                        "event_type": "intruder_caught",
                        "x": 3.0,
                        "y": 4.0,
                        "z": None,
                        "intruder_id": 1,
                        "payload_json": {"intruder_id": 1},
                        "created_at": "2026-03-30T12:00:01Z",
                    },
                ],
            }
        ],
    }

    _assert_valid("episode_log.schema.json", payload)
