import pytest
from unittest.mock import ANY, MagicMock, patch
from datetime import datetime
from apps.api.dispatcher import ExperimentDispatcher
from packages.db.models.enums import RunStatus
import asyncio
from packages.db.session import db_session

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
        default_algorithm="ppo",
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
        finished=False,
    )

    dispatcher = ExperimentDispatcher()
    dispatcher.routes = {"discrete/patrol": route}
    dispatcher.observer_poll_interval = 0.1
    dispatcher._store_session(session)  
    return dispatcher, session

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

def test_stop_preserves_running_status():
    """Кнопка "Стоп" не меняет статус (остаётся running)."""
    service = _make_fake_service(running=True, step=5)
    
    mock_run = MagicMock()
    mock_run.status = RunStatus.running
    
    with (patch("apps.api.dispatcher.db_session") as mock_db_session,
          patch("apps.api.dispatcher._get_service_checkpoint_path", return_value=None),
          patch("apps.api.dispatcher._save_model_artifact"),
          patch("apps.api.dispatcher.write_service_log"),
          patch("apps.api.dispatcher.ExperimentDispatcher._update_run_status")):
        
        dispatcher, session = _make_dispatcher_with_session(service)
        
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_run
        mock_db_session.return_value.__enter__.return_value = mock_db
        
        dispatcher.stop_run(42)
        
        assert mock_run.status == RunStatus.running

class _SelfStoppingService:
    last_error = None
    def __init__(self):
        self._last_checkpoint_path = None
    def start(self, params): pass
    def stop(self): pass
    def reset(self): pass
    def load_scenario(self, scenario, runtime_config): pass
    def get_state(self):
        return {"running": False, "step": 0, "episode": 0}


@pytest.mark.asyncio
class TestSelfCompletion:

    @pytest.fixture
    def dispatcher(self):
        return ExperimentDispatcher()

    async def test_self_completion_finishes_without_checkpoint(self, dispatcher):
        """Алгоритм завершился сам -> status=finished, finished_at, без model_checkpoint,
        авто-название не затёрто, finish_run не вызывался."""
        from packages.db.models.run import Run
        from packages.db.models.artifact import Artifact
        from packages.db.models.enums import ArtifactType

        route_key = "continuous/trail"
        params = {"algorithm": "ppo", "max_steps": 100}

        session = dispatcher.generate_and_load(route_key, params)
        run_id = session.run_id

        with db_session() as db:
            original_title = db.query(Run).filter(Run.id == run_id).first().title

        session.service = _SelfStoppingService()
        dispatcher._store_session(session)

        dispatcher.start_run(run_id, params)

        for _ in range(50):
            if session.observer is None or not session.observer.is_alive():
                break
            await asyncio.sleep(0.1)
        assert session.observer is None or not session.observer.is_alive()

        with db_session() as db:
            run = db.query(Run).filter(Run.id == run_id).first()
            assert run.status == RunStatus.finished
            assert run.finished_at is not None
            assert run.title == original_title 
            checkpoint = (
                db.query(Artifact)
                .filter(
                    Artifact.run_id == run_id,
                    Artifact.artifact_type == ArtifactType.model_checkpoint,
                )
                .first()
            )
            assert checkpoint is None  

@pytest.mark.xfail(
    reason="Прямая финализация finish_run в БД не доведена; снять метку, когда тест зелёный",
    strict=False,
)
def test_finish_run_finalizes_db():
    """Явный finish_run проставляет status=finished и finished_at в БД."""
    from packages.db.models.run import Run

    dispatcher = ExperimentDispatcher()
    session = dispatcher.generate_and_load("continuous/trail", {"algorithm": "ppo", "max_steps": 100})
    run_id = session.run_id

    dispatcher.finish_run(run_id)

    with db_session() as db:
        run = db.query(Run).filter(Run.id == run_id).first()
        assert run.status == RunStatus.finished
        assert run.finished_at is not None

def test_load_run_not_found():
    """Загрузка несуществующего run_id вызывает KeyError."""
    dispatcher = ExperimentDispatcher()
    with pytest.raises(KeyError):
        dispatcher.load_run(999999)

def test_has_route_known_and_unknown():
    """has_route отличает зарегистрированный маршрут от неизвестного."""
    dispatcher = ExperimentDispatcher()
    assert dispatcher.has_route("continuous/trail") is True
    assert dispatcher.has_route("unknown/route") is False

def test_dispose_run_removes_session():
    """dispose_run удаляет сессию из памяти диспетчера."""
    dispatcher = ExperimentDispatcher()
    session = dispatcher.generate_and_load("continuous/trail", {"algorithm": "ppo"})
    run_id = session.run_id
    
    assert run_id in dispatcher._sessions
    
    dispatcher.dispose_run(run_id)

    assert run_id not in dispatcher._sessions