from fastapi import WebSocketDisconnect
import pytest
import asyncio
import json
from unittest.mock import MagicMock, patch, AsyncMock
import orjson

import sys
sys.modules['apps.api.dispatcher'] = MagicMock()

from apps.api.websocket_manager import handle_ws

class MockWebSocket:
    def __init__(self, messages: list):
        self._incoming = iter(messages)
        self.sent = []

    async def accept(self): pass

    async def receive_json(self):
        try:
            return next(self._incoming)
        except StopIteration:
            raise Exception("no more messages")

    async def send_text(self, text: str):
        self.sent.append(json.loads(text))


@pytest.mark.asyncio
async def test_error_on_generate_fail():
    """Ошибка generate попадает в поле error."""
    dispatcher = MagicMock()
    dispatcher.get_state.return_value = {
        "running": False,
        "execution_phase": "idle",
        "error": None,
    }
    dispatcher.generate_and_load.side_effect = ValueError("grid_size must be positive")

    ws = MockWebSocket([{"action": "generate", "params": {"grid_size": -1}}])

    with pytest.raises(Exception):
        await handle_ws(ws, dispatcher, "discrete/reforestation")

    error_frames = [m for m in ws.sent if m.get("error")]
    assert error_frames
    assert "grid_size" in error_frames[0]["error"]

@pytest.mark.asyncio
async def test_start_without_prior_generate_auto_generates():
    """При start без предварительного generate менеджер генерирует сценарий сам."""
    dispatcher = MagicMock()
    dispatcher.get_state.return_value = {
        "running": False,
        "execution_phase": "idle",
        "error": None,
    }
    dispatcher.generate_and_load.return_value = MagicMock(run_id=1)

    ws = MockWebSocket([{"action": "start", "params": {"algorithm": "ppo"}}])

    with pytest.raises(Exception):
        await handle_ws(ws, dispatcher, "discrete/reforestation")

    dispatcher.generate_and_load.assert_called_once()
    dispatcher.start_run.assert_called_once()


@pytest.mark.asyncio
async def test_error_on_load_missing_run():
    """Ошибка загрузки несуществующего run."""
    dispatcher = MagicMock()
    dispatcher.get_state.return_value = {
        "running": False,
        "execution_phase": "idle",
        "error": None,
    }
    dispatcher.load_run.side_effect = KeyError("Run '999999' not found")

    ws = MockWebSocket([{"action": "load", "run_id": 999999}])

    with pytest.raises(Exception):
        await handle_ws(ws, dispatcher, "discrete/reforestation")

    error_frames = [m for m in ws.sent if m.get("error")]
    assert error_frames
    assert "999999" in error_frames[0]["error"]


@pytest.mark.asyncio
async def test_normal_state_no_error():
    """В нормальном состоянии error = null."""
    dispatcher = MagicMock()
    dispatcher.get_state.return_value = {
        "running": False,
        "execution_phase": "idle",
        "error": None,
    }
    ws = MockWebSocket([])

    with pytest.raises(Exception):
        await handle_ws(ws, dispatcher, "discrete/reforestation")

    if ws.sent:
        assert ws.sent[0].get("error") is None

@pytest.mark.asyncio
async def test_start_eval_requires_source_run_id():
    """start_eval без source_run_id -> ошибка в поле error."""
    dispatcher = MagicMock()
    dispatcher.get_state.return_value = {"running": False, "execution_phase": "idle", "error": None}

    ws = MockWebSocket([{"action": "start_eval", "params": {}}])

    with pytest.raises(Exception):
        await handle_ws(ws, dispatcher, "continuous/trail")

    error_frames = [m for m in ws.sent if m.get("error")]
    assert error_frames
    assert "source_run_id" in error_frames[0]["error"]


@pytest.mark.asyncio
async def test_start_eval_missing_checkpoint():
    """start_eval без сохранённого чекпоинта -> ошибка."""
    dispatcher = MagicMock()
    dispatcher.get_state.return_value = {"running": False, "execution_phase": "idle", "error": None}
    dispatcher.get_model_checkpoint_path.return_value = None

    ws = MockWebSocket([{"action": "start_eval", "source_run_id": 5, "params": {}}])

    with pytest.raises(Exception):
        await handle_ws(ws, dispatcher, "continuous/trail")

    error_frames = [m for m in ws.sent if m.get("error")]
    assert error_frames
    dispatcher.get_model_checkpoint_path.assert_called_once_with(5)

@pytest.mark.asyncio
async def test_websocket_disconnect_calls_dispose():
    dispatcher = MagicMock()

    ws = MagicMock()
    ws.accept = AsyncMock()

    session_mock = MagicMock()
    session_mock.run_id = 42

    ws.receive_json = AsyncMock(side_effect=[
        {"action": "generate", "params": {}},   
        WebSocketDisconnect()                   
    ])

    dispatcher.generate_and_load.return_value = session_mock

    await handle_ws(ws, dispatcher, "continuous/trail")

    dispatcher.dispose_run.assert_called_once_with(42)