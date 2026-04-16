import asyncio

import orjson
from fastapi import WebSocket, WebSocketDisconnect

from apps.api.dispatcher import ExperimentDispatcher


async def handle_ws(websocket: WebSocket, dispatcher: ExperimentDispatcher, route_key: str) -> None:
    """Управление экспериментами через WebSocket."""

    await websocket.accept()
    active_run_id: int | None = None

    async def send_loop():
        while True:
            try:
                state = dispatcher.get_state(route_key, active_run_id)
                await websocket.send_text(orjson.dumps(state).decode())
                await asyncio.sleep(0.1)
            except Exception as e:
                print(f"Error: {e}")
                break

    task = asyncio.create_task(send_loop())

    try:
        while True:
            data = await websocket.receive_json()
            action = data.get("action")
            params = data.get("params", {})
            
            try:
                if action == "generate":
                    if active_run_id is not None:
                        dispatcher.dispose_run(active_run_id)
                    session = dispatcher.generate_and_load(route_key, params)
                    active_run_id = session.run_id
                    
                elif action == "load":
                    if active_run_id is not None:
                        dispatcher.dispose_run(active_run_id)
                    if data.get("run_id") is not None:
                        session = dispatcher.load_run(int(data["run_id"]))
                        active_run_id = session.run_id
                    elif data.get("scenario_version_id") is not None:
                        session = dispatcher.load_scenario_version(
                            route_key,
                            int(data["scenario_version_id"]),
                            params,
                        )
                        active_run_id = session.run_id
                    
                elif action == "start":
                    if active_run_id is None:
                        session = dispatcher.generate_and_load(route_key, params)
                        active_run_id = session.run_id
                    dispatcher.start_run(active_run_id, params)
                    
                elif action == "stop" and active_run_id is not None:
                    dispatcher.stop_run(active_run_id)
                    
                elif action == "reset" and active_run_id is not None:
                    dispatcher.reset_run(active_run_id)
                    
                elif action == "dispose" and active_run_id is not None:
                    dispatcher.dispose_run(active_run_id)
                    active_run_id = None
                    
            except Exception as exc:
                print(f"Error in action {action}: {exc}")
                import traceback
                traceback.print_exc()
                state = dispatcher.get_state(route_key, active_run_id)
                state["error"] = str(exc)
                await websocket.send_text(orjson.dumps(state).decode())
                
    except WebSocketDisconnect:
        print(f"WebSocket disconnected for {route_key}")
        if active_run_id is not None:
            dispatcher.stop_run(active_run_id)
            dispatcher.dispose_run(active_run_id)
    finally:
        task.cancel()