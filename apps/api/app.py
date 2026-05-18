from fastapi import FastAPI, WebSocket
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from apps.api import dispatcher
from apps.api.dispatcher import ExperimentDispatcher
from apps.api.websocket_manager import handle_ws
from webrtc_routes import setup_webrtc_routes, ServerConfig
import logging
import json
from pathlib import Path
from fastapi import Query
from pydantic import BaseModel
from packages.db.models.run import Run
from packages.db.models.replay import Replay
from packages.db.models.artifact import Artifact         
from packages.db.models.enums import ArtifactType  
from packages.db.session import db_session
from sqlalchemy import desc

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])

_dispatcher = ExperimentDispatcher()


@app.websocket("/continuous/trail")
async def ws_continuous(websocket: WebSocket):
    await handle_ws(websocket, _dispatcher, "continuous/trail")

@app.websocket("/continuous/coverage")
async def ws_continuous_coverage(websocket: WebSocket):
    await handle_ws(websocket, _dispatcher, "continuous/coverage")

@app.websocket("/discrete/patrol")
async def ws_discrete_patrol(websocket: WebSocket):
    await handle_ws(websocket, _dispatcher, "discrete/patrol")

@app.websocket("/discrete/reforestation")
async def ws_discrete_reforestation(websocket: WebSocket):
    await handle_ws(websocket, _dispatcher, "discrete/reforestation")

@app.websocket("/threed/patrol")
async def ws_threed_patrol(websocket: WebSocket):
    await handle_ws(websocket, _dispatcher, "threed/patrol")

@app.websocket("/threed/trail")
async def ws_threed_trail(websocket: WebSocket):
    await handle_ws(websocket, _dispatcher, "threed/trail")


webrtc_config = ServerConfig(mode="public", logging_level="dev", socket_type="websocket")
setup_webrtc_routes(app, webrtc_config)


@app.get("/api/health")
async def health_check():
    return JSONResponse({"status": "ok", "message": "Server is running"})


class RunTitleBody(BaseModel):
    title: str


def _run_to_dict(run: Run) -> dict:
    has_checkpoint = False
    with db_session() as db:
        checkpoint = db.query(Artifact).filter(
            Artifact.run_id == run.id,
            Artifact.artifact_type == ArtifactType.model_checkpoint,
        ).first()
        has_checkpoint = checkpoint is not None
    
    return {
        "id": run.id,
        "title": run.title,
        "status": run.status.value if hasattr(run.status, "value") else str(run.status),
        "route_key": (run.config_json or {}).get("route_key"),
        "scenario_version_id": run.scenario_version_id,
        "created_at": run.created_at.isoformat() if run.created_at else None,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
        "has_checkpoint": has_checkpoint,  
    }



@app.get("/api/runs")
async def list_runs(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    search: str = Query("", alias="search"),
):
    with db_session() as db:
        q = db.query(Run)
        if search:
            q = q.filter(Run.title.ilike(f"%{search}%"))
        total = q.count()
        runs = q.order_by(desc(Run.created_at)).offset((page-1)*page_size).limit(page_size).all()
        items = [_run_to_dict(r) for r in runs]
    return JSONResponse({"items": items, "total": total, "page": page, "page_size": page_size})


@app.get("/api/runs/{run_id}")
async def get_run(run_id: int):
    with db_session() as db:
        run = db.query(Run).filter(Run.id == run_id).first()
        if run is None:
            return JSONResponse({"detail": "not found"}, status_code=404)
        data = _run_to_dict(run)
        data["config_json"] = run.config_json
        return JSONResponse(data)


@app.get("/api/runs/{run_id}/replay")
async def get_replay_frames(run_id: int):
    with db_session() as db:
        replay = (
            db.query(Replay)
            .filter(Replay.run_id == run_id)
            .order_by(Replay.created_at.desc(), Replay.id.desc())
            .first()
        )
        if replay is None:
            return JSONResponse({"detail": "replay not found"}, status_code=404)
        replay_path = Path(replay.storage_uri)

    if not replay_path.exists():
        return JSONResponse({"detail": "replay file missing"}, status_code=404)

    frames = []
    with replay_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    frames.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

    return JSONResponse({"run_id": run_id, "frames": frames, "total": len(frames)})


@app.patch("/api/runs/{run_id}")
async def rename_run(run_id: int, body: RunTitleBody):
    title = body.title.strip()
    if not title:
        return JSONResponse({"detail": "title required"}, status_code=422)
    with db_session() as db:
        conflict = db.query(Run).filter(Run.title == title, Run.id != run_id).first()
        if conflict:
            return JSONResponse({"detail": "title already exists"}, status_code=409)
        run = db.query(Run).filter(Run.id == run_id).first()
        if run is None:
            return JSONResponse({"detail": "not found"}, status_code=404)
        run.title = title
    return JSONResponse({"id": run_id, "title": title})

@app.get("/api/runs/{run_id}/checkpoint")
async def get_run_checkpoint(run_id: int):
    """
    Проверка сохранённого чекпоинта модели для этого run.
    """
    path = _dispatcher.get_model_checkpoint_path(run_id)
    if path is None:
        return JSONResponse({"available": False, "checkpoint_path": None})
    from pathlib import Path
    p = Path(path)
    return JSONResponse({
        "available": p.exists(),
        "checkpoint_path": path,
        "size_bytes": p.stat().st_size if p.exists() else 0,
    })
 