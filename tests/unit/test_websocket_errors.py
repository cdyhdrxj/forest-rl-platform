import pytest
import asyncio
import json
from unittest.mock import MagicMock, patch, AsyncMock
import orjson

import sys
sys.modules['apps.api.dispatcher'] = MagicMock()

from apps.api.websocket_manager import handle_ws


class MockWebSocket:
    """Минимальная заглушка WebSocket."""
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
async def test_error_field_set_on_generate_failure():
    """При ошибке generate поле error должно быть заполнено."""
    dispatcher = MagicMock()
    dispatcher.get_state.return_value = {
        "running": False,
        "execution_phase": "idle",
        "error": None,
    }
    dispatcher.generate_and_load.side_effect = ValueError(
        "grid_size must be positive"
    )

    ws = MockWebSocket([{"action": "generate", "params": {"grid_size": -1}}])

    with pytest.raises(Exception):  
        await handle_ws(ws, dispatcher, "discrete/reforestation")

    error_frames = [m for m in ws.sent if m.get("error")]
    assert error_frames, "Ожидался хотя бы один снимок с полем error"
    assert "grid_size" in error_frames[0]["error"]


@pytest.mark.asyncio
async def test_error_field_set_on_load_missing_run():
    """При загрузке несуществующего run_id поле error заполняется."""
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
async def test_normal_state_has_no_error():
    """В нормальном состоянии поле error равно null."""
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