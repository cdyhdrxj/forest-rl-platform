import sys
import pytest
import numpy as np
from unittest.mock import MagicMock

sys.modules.setdefault("roslibpy", MagicMock())
sys.modules.setdefault("services.ros_2", MagicMock())
sys.modules.setdefault("services.ros_2.ros_api_connection", MagicMock())

from services.scenario_generator import builtin
builtin.resolve_coverage_family_params = lambda family, params: params

from apps.api.dispatcher import ExperimentDispatcher
from packages.db.session import db_session


ROUTE = "continuous/trail"
BASE_PARAMS = {
    "algorithm": "ppo",
    "grid_size": 10,
    "obstacle_density": 0.2,
    "max_steps": 100,
}


def _preview_of(session) -> dict:
    return session.stored_scenario.scenario.preview_payload


def _as_sorted_array(points) -> np.ndarray:
    """Список координат -> отсортированный массив (сравнение без учёта порядка точек)."""
    arr = np.asarray(points, dtype=np.float64)
    if arr.size == 0:
        return arr.reshape(0, 0)
    order = np.lexsort(arr.T[::-1])
    return arr[order]


@pytest.fixture
def dispatcher():
    return ExperimentDispatcher()


class TestCamarIntegration:

    def test_generate_populates_preview(self, dispatcher):
        """generate строит превью с координатами агента, цели и препятствий."""
        session = dispatcher.generate_and_load(ROUTE, BASE_PARAMS)
        preview = _preview_of(session)

        assert len(preview["agent_pos"]) > 0, "agent_pos не заполнен"
        assert len(preview["goal_pos"]) > 0, "goal_pos не заполнен"
        assert len(preview["landmark_pos"]) > 0, "landmark_pos не заполнен"
        assert len(preview["agent_pos"][0]) == 2
        assert len(preview["goal_pos"][0]) == 2

    def test_state_has_coords_before_start(self, dispatcher):
        """Координаты доступны в get_state до старта обучения (режим превью)."""
        session = dispatcher.generate_and_load(ROUTE, BASE_PARAMS)
        state = dispatcher.get_state(ROUTE, session.run_id)

        assert len(state["agent_pos"]) > 0
        assert len(state["goal_pos"]) > 0
        assert state["running"] is False

    def test_same_seed_same_map(self, dispatcher):
        """Один seed -> одинаковая карта (детерминизм генерации)."""
        params = {**BASE_PARAMS, "seed": 123}
        p1 = _preview_of(dispatcher.generate_and_load(ROUTE, params))
        p2 = _preview_of(dispatcher.generate_and_load(ROUTE, params))

        assert np.array_equal(_as_sorted_array(p1["landmark_pos"]),
                              _as_sorted_array(p2["landmark_pos"]))
        assert np.array_equal(_as_sorted_array(p1["agent_pos"]),
                              _as_sorted_array(p2["agent_pos"]))

    def test_different_seed_different_map(self, dispatcher):
        """Разный seed -> разная карта."""
        p1 = _preview_of(dispatcher.generate_and_load(ROUTE, {**BASE_PARAMS, "seed": 1}))
        p2 = _preview_of(dispatcher.generate_and_load(ROUTE, {**BASE_PARAMS, "seed": 2}))

        same = np.array_equal(_as_sorted_array(p1["landmark_pos"]),
                              _as_sorted_array(p2["landmark_pos"]))
        assert not same, "разные seed дали одинаковую карту"

    def test_reset_keeps_same_map(self, dispatcher):
        """reset возвращает ту же карту, а не генерирует новую."""
        session = dispatcher.generate_and_load(ROUTE, BASE_PARAMS)
        run_id = session.run_id

        before = dispatcher.get_state(ROUTE, run_id)["landmark_pos"]
        dispatcher.reset_run(run_id)
        after = dispatcher.get_state(ROUTE, run_id)["landmark_pos"]

        assert np.array_equal(_as_sorted_array(before), _as_sorted_array(after)), \
            "reset сменил карту"

    def test_scenario_persisted_and_reloadable(self, dispatcher):
        """Сценарий сохраняется в БД и перечитывается с теми же координатами."""
        session = dispatcher.generate_and_load(ROUTE, BASE_PARAMS)
        run_id = session.run_id
        original = _preview_of(session)

        reloaded = dispatcher.load_run(run_id)
        restored = _preview_of(reloaded)

        assert np.array_equal(_as_sorted_array(original["agent_pos"]),
                              _as_sorted_array(restored["agent_pos"]))
        assert np.array_equal(_as_sorted_array(original["landmark_pos"]),
                              _as_sorted_array(restored["landmark_pos"]))

    def test_preview_matches_runtime_reset(self, dispatcher):
        """Превью совпадает с реальным reset среды (сверка координат препятствий)."""
        from services.trail_camar.wrapper import CamarGymWrapper

        session = dispatcher.generate_and_load(ROUTE, {**BASE_PARAMS, "seed": 7})
        preview = _preview_of(session)

        wrapper_kwargs = session.stored_scenario.scenario.runtime_context["continuous_2d"]["wrapper_kwargs"]
        filtered = {k: v for k, v in wrapper_kwargs.items() if k in CamarGymWrapper._KNOWN_PARAMS}

        env = CamarGymWrapper(**filtered)
        env.reset()
        runtime = env.get_render_state()

        # препятствия определяются только seed и должны совпасть
        assert np.allclose(_as_sorted_array(preview["landmark_pos"]),
                           _as_sorted_array(runtime["landmark_pos"])), \
            "превью и реальный reset среды дали разные препятствия"