import sys
import asyncio
import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from apps.api.websocket_manager import handle_ws

sys.modules['roslibpy'] = MagicMock()
sys.modules['services.ros_2'] = MagicMock()
sys.modules['services.ros_2.ros_api_connection'] = MagicMock()

from services.scenario_generator import builtin
builtin.resolve_coverage_family_params = lambda family, params: params

from apps.api.dispatcher import ExperimentDispatcher
from packages.db.models.enums import RunStatus
from packages.db.session import db_session


class MockWebSocket:
    def __init__(self):
        self.sent_messages = []
        self.received_messages = []
        self.accepted = False
        self.closed = False
        
    async def accept(self):
        self.accepted = True
        
    async def receive_json(self):
        if not self.received_messages:
            await asyncio.sleep(0.1)
            raise Exception("No more messages")
        return self.received_messages.pop(0)
    
    async def send_text(self, message):
        self.sent_messages.append(json.loads(message))
        
    async def close(self):
        self.closed = True


@pytest.mark.asyncio
class TestResume:
    
    @pytest.fixture
    def dispatcher(self):
        return ExperimentDispatcher()
    
    @pytest.fixture
    def mock_websocket(self):
        return MockWebSocket()
    
    async def test_resume_preserves_state(self, dispatcher):
        """Resume не сбрасывает счётчики."""
        from services.trail_camar.service import CamarService
        
        route_key = "continuous/trail"
        params = {"algorithm": "ppo", "max_steps": 100}
        
        session = dispatcher.generate_and_load(route_key, params)
        run_id = session.run_id
        
        real_service = CamarService()
        real_service.load_scenario(
            session.stored_scenario.scenario,
            session.stored_scenario.runtime_config
        )
        
        real_service.training_state["step"] = 50
        real_service.training_state["total_reward"] = 123.5
        real_service.training_state["episode"] = 3
        
        session.service = real_service
        dispatcher._store_session(session)
        
        dispatcher.start_run(run_id, {"resume": True}, resume=True)
        
        state = dispatcher.get_state(route_key, run_id)
        assert state.get("step") == 50
        assert state.get("total_reward") == 123.5
        assert state.get("episode") == 3

    async def test_new_start_resets_state(self, dispatcher):
        """Новый старт (без resume) сбрасывает счётчики."""
        from services.trail_camar.service import CamarService
        
        route_key = "continuous/trail"
        params = {"algorithm": "ppo", "max_steps": 100}
        
        session = dispatcher.generate_and_load(route_key, params)
        run_id = session.run_id
        
        real_service = CamarService()
        real_service.load_scenario(
            session.stored_scenario.scenario,
            session.stored_scenario.runtime_config
        )
        
        real_service.training_state["step"] = 50
        real_service.training_state["total_reward"] = 123.5
        
        session.service = real_service
        dispatcher._store_session(session)
        
        dispatcher.start_run(run_id, {"resume": False}, resume=False)
        
        state = dispatcher.get_state(route_key, run_id)
        assert state.get("step") == 0
        assert state.get("total_reward") == 0

    async def test_stop_then_resume_continues(self, dispatcher):
        """Цикл start / stop / resume: обучение продолжается."""
        from services.trail_camar.service import CamarService
        
        route_key = "continuous/trail"
        params = {"algorithm": "ppo", "max_steps": 100}
        
        session = dispatcher.generate_and_load(route_key, params)
        run_id = session.run_id
        
        real_service = CamarService()
        real_service.load_scenario(
            session.stored_scenario.scenario,
            session.stored_scenario.runtime_config
        )
        
        session.service = real_service
        dispatcher._store_session(session)
        
        dispatcher.start_run(run_id, {})
        real_service.training_state["step"] = 75
        
        dispatcher.stop_run(run_id)
        state_after_stop = dispatcher.get_state(route_key, run_id)
        assert state_after_stop.get("step") == 75
        
        dispatcher.start_run(run_id, {"resume": True}, resume=True)
        state_after_resume = dispatcher.get_state(route_key, run_id)
        assert state_after_resume.get("step") >= 75

    async def test_resume_flag_in_websocket(self, dispatcher):
        """WebSocket передаёт resume флаг в start."""
        class MockWebSocket:
            def __init__(self):
                self.sent = []
                self.accepted = False
                self.counter = 0
                
            async def accept(self):
                self.accepted = True
                
            async def receive_json(self):
                self.counter += 1
                if self.counter == 1:
                    return {"action": "start", "params": {"resume": True, "algorithm": "ppo"}}
                else:
                    raise Exception("No more messages")
                
            async def send_text(self, message):
                self.sent.append(json.loads(message))
                
            async def close(self):
                pass
        
        ws = MockWebSocket()
        
        with patch.object(dispatcher, 'start_run') as mock_start_run:
            try:
                await handle_ws(ws, dispatcher, "continuous/trail")
            except Exception:
                pass
            assert mock_start_run.called

    async def test_resume_flag_in_dispatcher(self, dispatcher):
        """Dispatcher передаёт resume флаг в сервис."""
        route_key = "continuous/trail"
        params = {"algorithm": "ppo"}
        
        session = dispatcher.generate_and_load(route_key, params)
        run_id = session.run_id
        
        mock_service = MagicMock()
        mock_service.get_state.return_value = {"running": False, "step": 0}
        session.service = mock_service
        dispatcher._store_session(session)
        
        dispatcher.start_run(run_id, {"resume": True}, resume=True)
        call_args = mock_service.start.call_args
        params_passed = call_args[0][0]
        assert params_passed.get("resume") == True
        
        dispatcher.start_run(run_id, {"resume": False}, resume=False)
        call_args = mock_service.start.call_args
        params_passed = call_args[0][0]
        assert params_passed.get("resume") == False