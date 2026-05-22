import pytest
import asyncio
from pathlib import Path
from unittest.mock import patch

from apps.api.dispatcher import ExperimentDispatcher
from packages.db.models.enums import RunStatus
from packages.db.session import db_session


@pytest.mark.asyncio
class TestCheckpoint:
    
    @pytest.fixture
    def dispatcher(self):
        return ExperimentDispatcher()
    
    async def test_stop_saves_checkpoint(self, dispatcher, tmp_path):
        """Тест: При нажатии кнопки "Стоп" чекпоинт сохраняется в БД."""
        
        route_key = "continuous/trail"
        params = {"algorithm": "ppo", "max_steps": 100}
        
        session = dispatcher.generate_and_load(route_key, params)
        run_id = session.run_id
        
        mock_checkpoint = tmp_path / "model.zip"
        mock_checkpoint.write_text("mock")
        
        with patch('apps.api.dispatcher._get_service_checkpoint_path', return_value=str(mock_checkpoint)):
            dispatcher.stop_run(run_id)
        
        from packages.db.models.artifact import Artifact
        from packages.db.models.enums import ArtifactType
        with db_session() as db:
            artifact = (
                db.query(Artifact)
                .filter(
                    Artifact.run_id == run_id,
                    Artifact.artifact_type == ArtifactType.model_checkpoint,
                )
                .first()
            )
            assert artifact is not None
            assert artifact.storage_uri == str(mock_checkpoint)
    
    async def test_disconnect_saves_checkpoint(self, dispatcher, tmp_path):
        """Тест: При разрыве соединения (закрытии страницы) чекпоинт сохраняется."""
        
        route_key = "continuous/trail"
        params = {"algorithm": "ppo", "max_steps": 100}
        
        session = dispatcher.generate_and_load(route_key, params)
        run_id = session.run_id
        
        mock_checkpoint = tmp_path / "model.zip"
        mock_checkpoint.write_text("mock")
        
        with patch('apps.api.dispatcher._get_service_checkpoint_path', return_value=str(mock_checkpoint)):
            dispatcher.dispose_run(run_id)
        
        from packages.db.models.artifact import Artifact
        from packages.db.models.enums import ArtifactType
        with db_session() as db:
            artifact = (
                db.query(Artifact)
                .filter(
                    Artifact.run_id == run_id,
                    Artifact.artifact_type == ArtifactType.model_checkpoint,
                )
                .first()
            )
            assert artifact is not None
    
    async def test_stop_does_not_change_status(self, dispatcher):
        """Тест: Кнопка "Стоп" не меняет статус Run (остаётся running)."""
        
        route_key = "continuous/trail"
        params = {"algorithm": "ppo", "max_steps": 100}
        
        session = dispatcher.generate_and_load(route_key, params)
        run_id = session.run_id
        
        dispatcher.start_run(run_id, params)
        dispatcher.stop_run(run_id)
        
        with db_session() as db:
            from packages.db.models.run import Run
            run = db.query(Run).filter(Run.id == run_id).first()
            assert run.status == RunStatus.running
    
    async def test_dispose_sets_cancelled(self, dispatcher):
        """Тест: При разрыве соединения (закрытии страницы) статус Run становится cancelled."""
        
        route_key = "continuous/trail"
        params = {"algorithm": "ppo", "max_steps": 100}
        
        session = dispatcher.generate_and_load(route_key, params)
        run_id = session.run_id
        
        dispatcher.dispose_run(run_id)
        
        with db_session() as db:
            from packages.db.models.run import Run
            run = db.query(Run).filter(Run.id == run_id).first()
            assert run.status == RunStatus.cancelled
    
    async def test_get_checkpoint_path(self, dispatcher, tmp_path):
        """Тест: get_model_checkpoint_path возвращает правильный путь к чекпоинту."""
        
        route_key = "continuous/trail"
        params = {"algorithm": "ppo", "max_steps": 100}
        
        session = dispatcher.generate_and_load(route_key, params)
        run_id = session.run_id
        
        mock_checkpoint = tmp_path / "model.zip"
        mock_checkpoint.write_text("mock")
        
        with patch('apps.api.dispatcher._get_service_checkpoint_path', return_value=str(mock_checkpoint)):
            dispatcher.stop_run(run_id)
        
        path = dispatcher.get_model_checkpoint_path(run_id)
        assert path == str(mock_checkpoint)