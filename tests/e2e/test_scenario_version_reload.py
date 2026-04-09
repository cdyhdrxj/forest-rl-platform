from __future__ import annotations

import os
import sys
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


def test_scenario_version_can_be_reloaded_into_new_run(tmp_path):
    _install_sb3_stub()
    os.environ["DATABASE_URL"] = f"sqlite:///{(tmp_path / 'reload.sqlite3').as_posix()}"

    from packages.db.session import get_engine, get_session_factory

    get_session_factory.cache_clear()
    get_engine.cache_clear()

    from apps.api.dispatcher import ExperimentDispatcher

    dispatcher = ExperimentDispatcher(observer_poll_interval=0.02)
    original = dispatcher.generate_and_load(
        "threed/patrol",
        {
            "seed": 23,
            "preview_size": 14,
            "intruder_count": 2,
            "tree_density": 0.28,
        },
    )

    reloaded = dispatcher.load_scenario_version("threed/patrol", original.scenario_version_id)
    state = dispatcher.get_state("threed/patrol", reloaded.run_id)

    assert reloaded.run_id != original.run_id
    assert state["scenario_version_id"] == original.scenario_version_id
    assert state["scenario_loaded"] is True
    assert state["execution_phase"] == "preview"
    assert len(state["goal_pos"]) == 2
