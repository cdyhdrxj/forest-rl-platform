import asyncio

import orjson
from fastapi import WebSocket, WebSocketDisconnect

from apps.api.dispatcher import ExperimentDispatcher


async def handle_ws(websocket: WebSocket, dispatcher: ExperimentDispatcher, route_key: str) -> None:
    """Управление экспериментами через WebSocket."""

    await websocket.accept()
    active_run_id: int | None = None

    _last_logged_run_id = [None]

    async def send_loop():
        interval = 0.1
        while True:
            try:
                state = dispatcher.get_state(route_key, active_run_id)
                if active_run_id != _last_logged_run_id[0]:
                    _last_logged_run_id[0] = active_run_id
                await websocket.send_text(orjson.dumps(state).decode())
                # Adaptive interval: fast when visualizing (canvas animation),
                # slow when training without visualization (chart-only updates),
                # normal when idle/preview
                if state.get("running"):
                    interval = 0.05 if state.get("visualize") else 0.5
                else:
                    interval = 0.1
            except Exception as e:
                print(f"Error in send_loop: {e}")
                interval = 0.1
            await asyncio.sleep(interval)

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
                    resume = params.get("resume", False) 
                    if active_run_id is not None:
                        dispatcher.start_run(active_run_id, params, resume=resume)
                    else:
                        session = dispatcher.generate_and_load(route_key, params)
                        active_run_id = session.run_id
                        dispatcher.start_run(active_run_id, params, resume=False)

                elif action == "start_eval":
                    source_run_id = data.get("source_run_id")
                    resume = params.get("resume", False)

                    if not source_run_id:
                        raise ValueError("start_eval requires source_run_id")

                    checkpoint_path = dispatcher.get_model_checkpoint_path(int(source_run_id))
                    if not checkpoint_path:
                        raise FileNotFoundError(...)

                    if active_run_id is not None:
                        eval_params = {
                            **params,
                            "execution_role": "eval",
                            "load_checkpoint_path": checkpoint_path,
                            "deterministic": params.get("deterministic", True),
                            "resume": resume,
                        }
                        dispatcher.start_run(active_run_id, eval_params, resume=resume)
                    else:
                        session = dispatcher.generate_and_load(route_key, params)
                        active_run_id = session.run_id
                        eval_params = {
                            **params,
                            "execution_role": "eval",
                            "load_checkpoint_path": checkpoint_path,
                            "deterministic": params.get("deterministic", True),
                            "resume": False,
                        }
                        dispatcher.start_run(active_run_id, eval_params, resume=False)

                elif action == "stop" and active_run_id is not None:
                    dispatcher.stop_run(active_run_id)

                elif action == "finish" and active_run_id is not None:
                    dispatcher.finish_run(active_run_id)
                    active_run_id = None

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
            dispatcher.dispose_run(active_run_id)
    finally:
        task.cancel()
