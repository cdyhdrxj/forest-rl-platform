import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime


def _make_fake_service(running: bool = False, step: int = 10):
    service = MagicMock()
    service.get_state.return_value = {"running": running, "step": step, "episode": 1}
    service.last_error = None
    return service


def _make_dispatcher_with_session(service, training_params=None):
    from apps.api.dispatcher import ExperimentDispatcher, RunSession, RuntimeRoute
    from services.scenario_generator.models import EnvironmentKind, TaskKind
    from packages.db.models.enums import ProjectMode

    route = RuntimeRoute(
        route_key="discrete/patrol",
        environment_kind=EnvironmentKind.GRID,
        task_kind=TaskKind.PATROL,
        project_mode=ProjectMode.patrol,
        training_mode="patrol",
        service_factory=lambda: service,
        request_builder=MagicMock(),
        runtime_config_builder=MagicMock(),
    )

    stored_scenario = MagicMock()
    stored_scenario.manifest_path.__str__ = lambda s: "/tmp/manifest.json"
    stored_scenario.preview_path.__str__ = lambda s: "/tmp/preview.json"
    stored_scenario.scenario.validation_passed = True
    stored_scenario.scenario.validation_messages = []
    stored_scenario.scenario.validation_report.to_payload.return_value = {}

    session = RunSession(
        run_id=42,
        scenario_version_id=1,
        route=route,
        stored_scenario=stored_scenario,
        service=service,
        training_params=dict(training_params or {"algorithm": "ppo"}),
        observer=None,
        validation_report={},
    )

    dispatcher = ExperimentDispatcher.__new__(ExperimentDispatcher)
    dispatcher._sessions = {42: session}
    dispatcher._lock = __import__("threading").RLock()
    dispatcher.observer_poll_interval = 0.1

    return dispatcher, session


def test_finish_phase_without_observer():
    """finish_run без observer -> execution_phase = finished"""
    service = _make_fake_service(running=False, step=10)

    with (patch("apps.api.dispatcher.db_session"),
          patch("apps.api.dispatcher._get_service_checkpoint_path", return_value=None),
          patch("apps.api.dispatcher._save_model_artifact"),
          patch("apps.api.dispatcher.write_service_log"),
          patch("apps.api.dispatcher.ExperimentDispatcher._update_run_status")):

        dispatcher, session = _make_dispatcher_with_session(service)
        assert session.observer is None

        dispatcher.finish_run(42)
        state = dispatcher.get_state("discrete/patrol", 42)
        assert state["execution_phase"] == "finished"


def test_finish_stops_running_service():
    """finish_run останавливает работающий сервис"""
    service = _make_fake_service(running=True, step=5)

    def stop_side_effect():
        service.get_state.return_value = {**service.get_state.return_value, "running": False}
    service.stop.side_effect = stop_side_effect

    with (patch("apps.api.dispatcher.db_session"),
          patch("apps.api.dispatcher._get_service_checkpoint_path", return_value=None),
          patch("apps.api.dispatcher._save_model_artifact"),
          patch("apps.api.dispatcher.write_service_log"),
          patch("apps.api.dispatcher.ExperimentDispatcher._update_run_status")):

        dispatcher, session = _make_dispatcher_with_session(service)
        dispatcher.finish_run(42)
        service.stop.assert_called_once()
        state = dispatcher.get_state("discrete/patrol", 42)
        assert state["execution_phase"] == "finished"


def test_finish_phase_never_running():
    """После finish_run execution_phase не может быть running"""
    service = _make_fake_service(running=True, step=20)

    with (patch("apps.api.dispatcher.db_session"),
          patch("apps.api.dispatcher._get_service_checkpoint_path", return_value=None),
          patch("apps.api.dispatcher._save_model_artifact"),
          patch("apps.api.dispatcher.write_service_log"),
          patch("apps.api.dispatcher.ExperimentDispatcher._update_run_status")):

        dispatcher, session = _make_dispatcher_with_session(service)
        dispatcher.finish_run(42)
        state = dispatcher.get_state("discrete/patrol", 42)
        assert state["execution_phase"] != "running"