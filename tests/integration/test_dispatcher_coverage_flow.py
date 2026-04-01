from __future__ import annotations

import os
import sys
import time
import types


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


def test_dispatcher_runs_continuous_coverage_baseline_and_persists_runtime(tmp_path):
    _install_sb3_stub()
    os.environ["DATABASE_URL"] = f"sqlite:///{(tmp_path / 'coverage.sqlite3').as_posix()}"

    from packages.db.session import get_engine, get_session_factory

    get_session_factory.cache_clear()
    get_engine.cache_clear()

    from apps.api.dispatcher import ExperimentDispatcher
    from packages.db.models.episode import Episode
    from packages.db.models.metric_series import MetricSeries
    from packages.db.models.replay import Replay
    from packages.db.models.run import Run
    from packages.db.models.enums import RunStatus
    from packages.db.session import db_session

    dispatcher = ExperimentDispatcher(observer_poll_interval=0.02)
    session = dispatcher.generate_and_load(
        "continuous/coverage",
        {
            "seed": 17,
            "grid_size": 24,
            "row_count": 6,
            "curvature_level": "medium",
            "gap_probability": 0.1,
            "obstacle_count": 1,
            "max_steps": 10,
            "algorithm": "greedy_nearest",
        },
    )

    preview_state = dispatcher.get_state("continuous/coverage", session.run_id)
    assert preview_state["scenario_loaded"] is True
    assert preview_state["execution_phase"] == "preview"
    assert preview_state["validation_passed"] is True
    assert preview_state["route_key"] == "continuous/coverage"

    dispatcher.start_run(
        session.run_id,
        {
            "algorithm": "greedy_nearest",
            "max_steps": 10,
            "tick_sleep": 0.001,
        },
    )

    deadline = time.time() + 3.0
    state = preview_state
    while time.time() < deadline:
        state = dispatcher.get_state("continuous/coverage", session.run_id)
        if state["execution_phase"] in {"finished", "failed"}:
            break
        time.sleep(0.02)

    assert state["execution_phase"] == "finished"
    assert "coverage_ratio" in state
    assert "path_length" in state
    assert "return_error" in state

    with db_session() as db:
        run = db.query(Run).filter(Run.id == session.run_id).first()
        assert run is not None
        assert run.status == RunStatus.finished
        assert db.query(Episode).filter(Episode.run_id == session.run_id).count() >= 1
        assert db.query(MetricSeries).filter(MetricSeries.run_id == session.run_id).count() >= 1
        assert db.query(Replay).filter(Replay.run_id == session.run_id).count() >= 1

