import asyncio
import orjson
from fastapi import WebSocket, WebSocketDisconnect

async def handle_ws(websocket: WebSocket, service) -> None:
    """ 
    Управление WebSocket соединением.

    Требует от подключенного модуля (service) реализации методов:
      - start(params) — запустить обучение с параметрами от фронта
      - stop()        — остановить обучение
      - reset()       — сбросить среду и модель
      - get_state()   — вернуть текущее состояние обучения (dict)
    """

    await websocket.accept()

    async def send_loop():
        while True:
            try:
                await websocket.send_text(
                    orjson.dumps((service.get_state())).decode()
                )
                await asyncio.sleep(0.05)
            except Exception:
                break

    task = asyncio.create_task(send_loop())

    try:
        while True:
            data = await websocket.receive_json()
            action = data.get("action")
            if action == "start":
                service.start(data.get("params", {}))
            elif action == "stop":
                service.stop()
            elif action == "reset":
                service.reset()
    except WebSocketDisconnect:
        pass
    finally:
        task.cancel()
        if service.get_state().get("running"):
            service.stop()