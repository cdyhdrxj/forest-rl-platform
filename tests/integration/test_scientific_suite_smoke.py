from __future__ import annotations

import json
import os
import sys
import types
from pathlib import Path

import numpy as np
from jsonschema import Draft202012Validator


REPO_ROOT = Path(__file__).resolve().parents[2]


def _install_sb3_stub() -> None:
    sb3 = types.ModuleType("stable_baselines3")
    common = types.ModuleType("stable_baselines3.common")
    env_util = types.ModuleType("stable_baselines3.common.env_util")
    callbacks = types.ModuleType("stable_baselines3.common.callbacks")

    class _Algo:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs
            self.env = kwargs.get("env")
            if self.env is None and len(args) >= 2:
                self.env = args[1]
            self.loaded_path = None

        def learn(self, *args, **kwargs):
            return self

        def save(self, path, *args, **kwargs):
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            Path(path).write_text("stub-model", encoding="utf-8")
            self.loaded_path = str(path)
            return None

        @classmethod
        def load(cls, path, env=None, *args, **kwargs):
            model = cls("MlpPolicy", env, verbose=0, *args, **kwargs)
            model.loaded_path = str(path)
            return model

        def predict(self, observation, deterministic=True):
            return np.asarray([0.0, 1.0], dtype=np.float32), None

    class _Callback:
        def __init__(self, *args, **kwargs):
            pass

    env_util.make_vec_env = lambda factory, n_envs=1: factory()
    callbacks.BaseCallback = _Callback

    sb3.PPO = _Algo
    sb3.SAC = _Algo
    sb3.A2C = _Algo
    sb3.common = common
    common.env_util = env_util
    common.callbacks = callbacks

    sys.modules["stable_baselines3"] = sb3
    sys.modules["stable_baselines3.common"] = common
    sys.modules["stable_baselines3.common.env_util"] = env_util
    sys.modules["stable_baselines3.common.callbacks"] = callbacks

    trainer_module = sys.modules.get("apps.api.sb3.sb3_trainer")
    if trainer_module is not None:
        trainer_module.PPO = _Algo
        trainer_module.SAC = _Algo
        trainer_module.A2C = _Algo
        trainer_module.ALGORITHMS = {
            "ppo": _Algo,
            "sac": _Algo,
            "a2c": _Algo,
        }

    coverage_service_module = sys.modules.get("services.agrocare_coverage.service")
    if coverage_service_module is not None:
        coverage_service_module.make_vec_env = env_util.make_vec_env
        coverage_service_module.ALGORITHMS = {
            "ppo": _Algo,
            "sac": _Algo,
            "a2c": _Algo,
        }


def _load_schema(name: str) -> dict:
    path = REPO_ROOT / "contracts" / "v1" / name
    return json.loads(path.read_text(encoding="utf-8"))


def test_scientific_suite_smoke_run_exports_report(tmp_path):
    _install_sb3_stub()
    os.environ["DATABASE_URL"] = f"sqlite:///{(tmp_path / 'scientific.sqlite3').as_posix()}"

    from packages.db.session import get_engine, get_session_factory

    get_session_factory.cache_clear()
    get_engine.cache_clear()

    from experiments.scientific.models import ScientificSuiteConfig
    from experiments.scientific.orchestrator import ExperimentSuiteOrchestrator
    from packages.db.models.experiment_suite import ExperimentSuite
    from packages.db.models.experiment_suite_run import ExperimentSuiteRun
    from packages.db.session import db_session

    config = ScientificSuiteConfig.model_validate(
        {
            "suite_code": "trail-smoke-suite",
            "title": "Trail smoke suite",
            "route_key": "threed/trail",
            "report_dir": str(tmp_path / "reports"),
            "seed": 11,
            "scenarios": [
                {
                    "family": "smoke",
                    "split": "test",
                    "count": 1,
                    "generation_params": {
                        "preview_size": 10,
                        "tree_density": 0.25,
                        "terrain_hilliness": 0.2,
                        "max_steps": 8
                    },
                    "evaluation_params": {
                        "max_steps": 8,
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
                        "max_steps": 8,
                        "tick_sleep": 0.001
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
    )

    orchestrator = ExperimentSuiteOrchestrator(poll_interval=0.02, per_run_timeout_sec=5.0)
    result = orchestrator.run_suite(config)

    report_json_path = Path(result["report_json_path"])
    summary_csv_path = Path(result["summary_csv_path"])
    report_html_path = Path(result["report_html_path"])
    manifest_path = Path(result["manifest_path"])

    assert result["status"] == "finished"
    assert report_json_path.exists()
    assert summary_csv_path.exists()
    assert report_html_path.exists()
    assert manifest_path.exists()

    report_payload = json.loads(report_json_path.read_text(encoding="utf-8"))
    Draft202012Validator(_load_schema("scientific_report.schema.json")).validate(report_payload)

    with db_session() as db:
        suite = db.query(ExperimentSuite).filter(ExperimentSuite.code == config.suite_code).first()
        assert suite is not None
        assert suite.status == "finished"
        assert suite.manifest_uri == str(manifest_path)
        suite_runs = db.query(ExperimentSuiteRun).filter(ExperimentSuiteRun.suite_id == suite.id).all()
        assert len(suite_runs) == 1

    assert report_payload["overview"]["total_runs"] == 1
    assert report_payload["runs"][0]["trajectory_path"] is not None
    assert Path(report_payload["runs"][0]["trajectory_path"]).exists()


def test_scientific_suite_coverage_rl_protocol_smoke(tmp_path):
    _install_sb3_stub()
    os.environ["DATABASE_URL"] = f"sqlite:///{(tmp_path / 'scientific_rl.sqlite3').as_posix()}"

    from packages.db.session import get_engine, get_session_factory

    get_session_factory.cache_clear()
    get_engine.cache_clear()

    from experiments.scientific.models import ScientificSuiteConfig
    from experiments.scientific.orchestrator import ExperimentSuiteOrchestrator
    from packages.db.models.experiment_suite import ExperimentSuite
    from packages.db.models.experiment_suite_run import ExperimentSuiteRun
    from packages.db.session import db_session

    config = ScientificSuiteConfig.model_validate(
        {
            "suite_code": "coverage-rl-smoke-suite",
            "title": "Coverage RL protocol smoke suite",
            "route_key": "continuous/coverage",
            "report_dir": str(tmp_path / "reports"),
            "seed": 101,
            "scenarios": [
                {
                    "family": "S1",
                    "train_count": 2,
                    "val_count": 1,
                    "test_count": 1,
                    "generation_params": {
                        "grid_size": 16,
                        "row_count": 3,
                        "curvature_level": "low",
                        "obstacle_count": 0,
                        "max_steps": 6,
                    },
                    "evaluation_params": {
                        "max_steps": 6,
                        "tick_sleep": 0.0,
                    },
                }
            ],
            "methods": [
                {
                    "code": "sac",
                    "algorithm": "sac",
                    "kind": "rl",
                    "enabled": True,
                    "training": {
                        "repeats": 1,
                        "total_timesteps": 4,
                        "eval_every_steps": 1,
                        "early_stop_patience": 0,
                    },
                    "evaluation": {
                        "deterministic": True,
                        "eval_episodes": 1,
                        "selection_metric": "coverage_ratio_mean",
                        "selection_mode": "max",
                    },
                }
            ],
            "report": {
                "formats": ["json", "csv", "html"],
                "representative_runs_per_method": 1,
                "save_trajectory_plots": True,
                "save_distribution_plots": True,
            },
        }
    )

    orchestrator = ExperimentSuiteOrchestrator(poll_interval=0.02, per_run_timeout_sec=5.0)
    result = orchestrator.run_suite(config)

    report_json_path = Path(result["report_json_path"])
    manifest_path = Path(result["manifest_path"])

    assert result["status"] == "finished"
    assert report_json_path.exists()
    assert manifest_path.exists()

    report_payload = json.loads(report_json_path.read_text(encoding="utf-8"))
    Draft202012Validator(_load_schema("scientific_report.schema.json")).validate(report_payload)

    runs = report_payload["runs"]
    assert len(runs) == 5
    assert {row["protocol_phase"] for row in runs} >= {"train", "val_eval", "test_eval"}
    assert {row["dataset_split"] for row in runs} == {"train", "val", "test"}

    train_runs = [row for row in runs if row["role"] == "train"]
    eval_runs = [row for row in runs if row["role"] == "eval"]
    test_runs = [row for row in runs if row["dataset_split"] == "test"]

    assert len(train_runs) == 2
    assert len(eval_runs) == 3
    assert len(test_runs) == 1
    assert all(row["checkpoint_out_path"] for row in train_runs)
    assert any(row["checkpoint_in_path"] for row in eval_runs)
    assert test_runs[0]["checkpoint_in_path"] is not None
    assert test_runs[0]["source_train_run_id"] is not None

    checkpoint_paths = [
        path
        for row in train_runs
        for path in row.get("checkpoint_paths") or []
    ]
    assert checkpoint_paths
    assert all(Path(path).exists() for path in checkpoint_paths)

    aggregates = report_payload["aggregates"]
    assert any(item["role"] == "train" and item["dataset_split"] == "train" for item in aggregates)
    assert any(item["role"] == "eval" and item["dataset_split"] == "val" for item in aggregates)
    assert any(item["role"] == "eval" and item["dataset_split"] == "test" for item in aggregates)

    with db_session() as db:
        suite = db.query(ExperimentSuite).filter(ExperimentSuite.code == config.suite_code).first()
        assert suite is not None
        assert suite.status == "finished"
        suite_runs = db.query(ExperimentSuiteRun).filter(ExperimentSuiteRun.suite_id == suite.id).all()
        assert len(suite_runs) == 5
