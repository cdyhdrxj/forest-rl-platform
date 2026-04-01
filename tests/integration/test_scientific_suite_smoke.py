from __future__ import annotations

import json
import os
import sys
import types
from pathlib import Path

from jsonschema import Draft202012Validator


REPO_ROOT = Path(__file__).resolve().parents[2]


def _install_sb3_stub() -> None:
    if "stable_baselines3" in sys.modules:
        return

    sb3 = types.ModuleType("stable_baselines3")
    common = types.ModuleType("stable_baselines3.common")
    env_util = types.ModuleType("stable_baselines3.common.env_util")
    callbacks = types.ModuleType("stable_baselines3.common.callbacks")

    class _Algo:
        def __init__(self, *args, **kwargs):
            pass

        def learn(self, *args, **kwargs):
            return None

        def save(self, *args, **kwargs):
            return None

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

