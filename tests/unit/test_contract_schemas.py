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


def test_scientific_suite_config_conforms_to_contract():
    payload = {
        "suite_code": "trail-smoke-suite",
        "title": "Three-D Trail Scientific Smoke Suite",
        "route_key": "threed/trail",
        "task_kind": "trail",
        "environment_kind": "simulator_3d",
        "report_dir": "data/scientific/suites",
        "seed": 101,
        "scenarios": [
            {
                "family": "smoke",
                "split": "test",
                "count": 1,
                "generation_params": {
                    "preview_size": 12,
                    "tree_density": 0.25
                },
                "evaluation_params": {
                    "max_steps": 12,
                    "tick_sleep": 0.001
                }
            }
        ],
        "methods": [
            {
                "code": "ppo",
                "algorithm": "ppo",
                "enabled": True,
                "repeats": 1,
                "start_params": {
                    "max_steps": 12
                },
                "role": "eval"
            }
        ],
        "report": {
            "formats": ["json", "csv", "html"],
            "representative_runs_per_method": 1,
            "save_trajectory_plots": True,
            "save_distribution_plots": True
        }
    }

    _assert_valid("scientific_suite.schema.json", payload)


def test_scientific_suite_paper_config_conforms_to_contract():
    payload = {
        "suite_code": "agrocare-paper-v1",
        "title": "Agrocare coverage benchmark S1-S4",
        "route_key": "continuous/coverage",
        "task_kind": "coverage",
        "environment_kind": "continuous_2d",
        "report_dir": "data/scientific/suites",
        "seed": 20260401,
        "scenarios": [
            {
                "family": "S1",
                "train_count": 300,
                "val_count": 100,
                "test_count": 150,
                "generation_params": {
                    "row_count_range": [8, 12],
                    "curvature_level": "low",
                    "obstacle_count_range": [0, 0]
                }
            }
        ],
        "methods": [
            {
                "code": "greedy_nearest",
                "algorithm": "greedy_nearest",
                "kind": "baseline",
                "enabled": True,
                "start_params": {
                    "tick_sleep": 0.0
                }
            },
            {
                "code": "sac",
                "algorithm": "sac",
                "kind": "rl",
                "enabled": True,
                "training": {
                    "repeats": 5,
                    "total_timesteps": 500000
                },
                "evaluation": {
                    "deterministic": True
                }
            }
        ],
        "report": {
            "formats": ["json", "csv", "html"],
            "representative_runs_per_method": 3,
            "save_trajectory_plots": True,
            "save_distribution_plots": True
        }
    }

    _assert_valid("scientific_suite.schema.json", payload)


def test_scientific_report_payload_conforms_to_contract():
    payload = {
        "generated_at": "2026-04-01T18:00:00Z",
        "suite": {
            "suite_id": 1,
            "suite_code": "trail-smoke-suite",
            "title": "Three-D Trail Scientific Smoke Suite",
            "route_key": "threed/trail",
            "mode": "trail",
            "status": "finished",
            "started_at": "2026-04-01T18:00:00Z",
            "finished_at": "2026-04-01T18:00:10Z"
        },
        "config": {
            "suite_code": "trail-smoke-suite"
        },
        "overview": {
            "total_runs": 1,
            "methods": ["ppo"],
            "scenario_families": ["smoke"],
            "splits": ["test"],
            "status_counts": {
                "finished": 1
            }
        },
        "aggregates": [
            {
                "method_code": "ppo",
                "role": "eval",
                "dataset_split": "test",
                "runs_count": 1,
                "finished_runs_count": 1,
                "scenario_families": ["smoke"],
                "splits": ["test"],
                "duration_sec_mean": 1.2,
                "duration_sec_std": 0.0,
                "episode_success_rate_mean": 1.0,
                "episode_reward_mean": 10.0,
                "episode_reward_median": 10.0,
                "episode_reward_min": 10.0,
                "episode_reward_max": 10.0,
                "coverage_ratio_mean": 0.75,
                "episode_steps_mean": 8.0,
                "status_counts": {
                    "finished": 1
                }
            }
        ],
        "runs": [
            {
                "run_id": 12,
                "scenario_family": "smoke",
                "dataset_split": "test",
                "method_code": "ppo",
                "replicate_index": 1,
                "role": "eval",
                "train_seed": 1101,
                "eval_seed": 1001101,
                "group_key": "smoke:test:sv4:ppo:r1",
                "status": "finished",
                "algorithm_code": "ppo_trail",
                "duration_sec": 1.2,
                "episodes_count": 1,
                "episode_success_rate": 1.0,
                "episode_reward_mean": 10.0,
                "episode_reward_median": 10.0,
                "episode_steps_mean": 8.0,
                "coverage_ratio_mean": 0.75,
                "protocol_phase": "test_eval",
                "checkpoint_in_path": "data/scientific/suites/trail-smoke-suite/checkpoints/smoke/ppo/best.zip",
                "checkpoint_out_path": None,
                "source_train_run_id": 10,
                "checkpoint_paths": [
                    "data/scientific/suites/trail-smoke-suite/checkpoints/smoke/ppo/best.zip"
                ],
                "run_result_path": "data/runs/run_12/exports/run_result.json",
                "metrics_export_path": "data/runs/run_12/exports/metrics_export.json",
                "episode_log_path": "data/runs/run_12/exports/episode_log.json",
                "trajectory_path": "data/scientific/suites/trail-smoke-suite/trajectories/run_12/trajectory.svg",
                "config_json": {
                    "route_key": "threed/trail"
                }
            }
        ],
        "artifacts": {
            "plots": [
                "plots/reward_by_method.svg"
            ],
            "trajectories": [
                "trajectories/smoke_test_ppo_run_12/trajectory.svg"
            ]
        }
    }

    _assert_valid("scientific_report.schema.json", payload)


def test_replay_payload_with_coverage_state_conforms_to_contract():
    payload = {
        "timestamp": "2026-04-01T18:00:00Z",
        "route_key": "continuous/coverage",
        "state": {
            "running": False,
            "mode": "coverage",
            "episode": 1,
            "step": 8,
            "total_reward": 0.0,
            "last_episode_reward": 12.5,
            "new_episode": True,
            "agent_pos": [[5.0, 0.0]],
            "goal_pos": [],
            "landmark_pos": [[3.0, 4.0]],
            "trajectory": [[5.0, 0.0], [5.0, 1.0]],
            "goal_count": 6,
            "collision_count": 0,
            "terrain_map": [[0.0, 1.0], [0.0, 0.0]],
            "coverage_ratio": 1.0,
            "missed_area_ratio": 0.0,
            "return_to_start_success": True,
            "return_error": 0.0,
            "path_length": 42.0,
            "task_time_sec": 1.3,
            "transition_count": 5,
            "repeat_coverage_ratio": 0.1,
            "angular_work_rad": 3.14,
            "compute_time_sec": 0.05,
            "remaining_rows": 0,
            "success": True,
            "coverage_target_map": [[1.0, 0.0], [0.0, 1.0]],
            "covered_map": [[1.0, 0.0], [0.0, 1.0]]
        }
    }

    _assert_valid("replay.schema.json", payload)
