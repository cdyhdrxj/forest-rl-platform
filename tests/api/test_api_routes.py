import sys
from unittest.mock import MagicMock, patch

import pytest

sys.modules.setdefault("roslibpy", MagicMock())
sys.modules.setdefault("services.ros_2", MagicMock())
sys.modules.setdefault("services.ros_2.ros_api_connection", MagicMock())
sys.modules["webrtc_routes"] = MagicMock() 
from fastapi.testclient import TestClient

from apps.api.app import app

client = TestClient(app)


def test_health():
    """GET /api/health -> 200 и status=ok."""
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_list_runs_ok():
    """GET /api/runs возвращает страницу со списком и метаданными пагинации."""
    r = client.get("/api/runs?page=1&page_size=10")
    assert r.status_code == 200
    body = r.json()
    assert "items" in body
    assert "total" in body
    assert body["page"] == 1
    assert body["page_size"] == 10


def test_get_run_not_found():
    """GET /api/runs/{id} для несуществующего запуска -> 404."""
    r = client.get("/api/runs/999999")
    assert r.status_code == 404


def test_rename_run_empty_title_rejected():
    """PATCH /api/runs/{id} с пустым названием -> 422."""
    r = client.patch("/api/runs/999999", json={"title": "   "})
    assert r.status_code == 422


def test_rename_missing_run_not_found():
    """PATCH /api/runs/{id} с валидным названием, но несуществующим run -> 404."""
    r = client.patch("/api/runs/999999", json={"title": "Некоторое название"})
    assert r.status_code == 404


def test_checkpoint_absent_for_missing_run():
    """GET /api/runs/{id}/checkpoint -> available=False, когда чекпоинта нет."""
    r = client.get("/api/runs/999999/checkpoint")
    assert r.status_code == 200
    assert r.json()["available"] is False


def test_replay_not_found():
    """GET /api/runs/{id}/replay для несуществующего запуска -> 404."""
    r = client.get("/api/runs/999999/replay")
    assert r.status_code == 404


def test_known_ws_route_accepts():
    """WebSocket по зарегистрированному маршруту принимается и шлёт состояние."""
    with client.websocket_connect("/continuous/trail") as ws:
        # send_loop пушит состояние сразу после accept
        state = ws.receive_json()
        assert "running" in state

def test_rename_run_duplicate_title():
    """PATCH /api/runs/{id} с названием, которое уже существует -> 409."""
    from fastapi import status
    
    with patch("apps.api.app.db_session") as mock_db_session:
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = MagicMock(id=1, title="Существующее название")
        mock_db_session.return_value.__enter__.return_value = mock_db
        
        r = client.patch("/api/runs/2", json={"title": "Существующее название"})
        assert r.status_code == status.HTTP_409_CONFLICT
        assert "title already exists" in r.text