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


def test_dispatcher_runs_three_d_flow_and_persists_runtime(tmp_path):
    _install_sb3_stub()
    os.environ["DATABASE_URL"] = f"sqlite:///{(tmp_path / 'dispatcher.sqlite3').as_posix()}"

    from packages.db.session import get_engine, get_session_factory

    get_session_factory.cache_clear()
    get_engine.cache_clear()

    from apps.api.dispatcher import ExperimentDispatcher
    from packages.db.models.episode import Episode
    from packages.db.models.metric_series import MetricSeries
    from packages.db.models.replay import Replay
    from packages.db.models.run import Run
    from packages.db.models.service_log import ServiceLog
    from packages.db.models.enums import RunStatus
    from packages.db.session import db_session

    dispatcher = ExperimentDispatcher(observer_poll_interval=0.02)
    session = dispatcher.generate_and_load(
        "threed/trail",
        {
            "seed": 19,
            "preview_size": 12,
            "tree_density": 0.3,
            "terrain_hilliness": 0.4,
            "max_steps": 18,
        },
    )

    preview_state = dispatcher.get_state("threed/trail", session.run_id)
    assert preview_state["scenario_loaded"] is True
    assert preview_state["execution_phase"] == "preview"
    assert preview_state["validation_passed"] is True

    dispatcher.start_run(session.run_id, {"max_steps": 18, "tick_sleep": 0.001})

    deadline = time.time() + 2.0
    state = preview_state
    while time.time() < deadline:
        state = dispatcher.get_state("threed/trail", session.run_id)
        if state["execution_phase"] in {"finished", "failed"}:
            break
        time.sleep(0.02)

    assert state["execution_phase"] == "finished"
    assert int(state["step"]) > 0

    with db_session() as db:
        run = db.query(Run).filter(Run.id == session.run_id).first()
        assert run is not None
        assert run.status == RunStatus.finished
        assert db.query(Episode).filter(Episode.run_id == session.run_id).count() >= 1
        assert db.query(MetricSeries).filter(MetricSeries.run_id == session.run_id).count() >= 1
        assert db.query(Replay).filter(Replay.run_id == session.run_id).count() >= 1
        assert db.query(ServiceLog).filter(ServiceLog.run_id == session.run_id).count() >= 1


def test_dispatcher_restarts_three_d_run_without_duplicate_episode_indices(tmp_path):
    _install_sb3_stub()
    os.environ["DATABASE_URL"] = f"sqlite:///{(tmp_path / 'dispatcher_restart.sqlite3').as_posix()}"

    from packages.db.session import get_engine, get_session_factory

    get_session_factory.cache_clear()
    get_engine.cache_clear()

    from apps.api.dispatcher import ExperimentDispatcher
    from packages.db.models.episode import Episode
    from packages.db.models.run import Run
    from packages.db.models.service_log import ServiceLog
    from packages.db.models.enums import RunStatus
    from packages.db.session import db_session

    dispatcher = ExperimentDispatcher(observer_poll_interval=0.02)
    session = dispatcher.generate_and_load(
        "threed/trail",
        {
            "seed": 23,
            "preview_size": 10,
            "tree_density": 0.25,
            "terrain_hilliness": 0.2,
            "max_steps": 8,
        },
    )

    def wait_until_finished() -> dict:
        deadline = time.time() + 2.0
        current = dispatcher.get_state("threed/trail", session.run_id)
        while time.time() < deadline:
            current = dispatcher.get_state("threed/trail", session.run_id)
            if current["execution_phase"] in {"finished", "failed"}:
                return current
            time.sleep(0.02)
        return current

    dispatcher.start_run(session.run_id, {"max_steps": 8, "tick_sleep": 0.001})
    first_state = wait_until_finished()
    assert first_state["execution_phase"] == "finished"
    first_episode_count = int(first_state["episode"])
    assert first_episode_count > 0

    dispatcher.start_run(session.run_id, {"max_steps": 8, "tick_sleep": 0.001})
    second_state = wait_until_finished()
    assert second_state["execution_phase"] == "finished"
    assert int(second_state["episode"]) > 0

    with db_session() as db:
        run = db.query(Run).filter(Run.id == session.run_id).first()
        assert run is not None
        assert run.status == RunStatus.finished

        episodes = (
            db.query(Episode)
            .filter(Episode.run_id == session.run_id)
            .order_by(Episode.episode_index.asc())
            .all()
        )
        episode_indices = [episode.episode_index for episode in episodes]
        assert episode_indices
        assert episode_indices == list(range(1, len(episode_indices) + 1))
        assert episode_indices[-1] > first_episode_count

        observer_errors = (
            db.query(ServiceLog)
            .filter(ServiceLog.run_id == session.run_id, ServiceLog.service_name == "runtime_observer")
            .all()
        )
        duplicate_messages = [
            log for log in observer_errors
            if log.level == "error"
            and "duplicate key value violates unique constraint" in (
                f"{log.message or ''} {(log.payload_json or {}).get('error', '')}"
            )
        ]
        assert not duplicate_messages
