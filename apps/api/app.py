from fastapi import FastAPI, WebSocket
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from apps.api.dispatcher import ExperimentDispatcher
from apps.api.websocket_manager import handle_ws
from webrtc_routes import setup_webrtc_routes, ServerConfig
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_dispatcher = ExperimentDispatcher()

# _discrete_trail = DiscreteService()

@app.websocket("/continuous/trail")
async def ws_continuous(websocket: WebSocket):
    await handle_ws(websocket, _dispatcher, "continuous/trail")

@app.websocket("/continuous/coverage")
async def ws_continuous_coverage(websocket: WebSocket):
    await handle_ws(websocket, _dispatcher, "continuous/coverage")

# @app.websocket("/continuous/patrol")
# async def ws_continuous(websocket: WebSocket):
#     await handle_ws(websocket, _camar)

@app.websocket("/discrete/patrol")
async def ws_discrete_patrol(websocket: WebSocket):
    await handle_ws(websocket, _dispatcher, "discrete/patrol")

@app.websocket("/discrete/reforestation")
async def ws_discrete_reforestation(websocket: WebSocket):
    await handle_ws(websocket, _dispatcher, "discrete/reforestation")

# @app.websocket("/discrete/trail")
# async def ws_discrete_trail(websocket: WebSocket):
#     await handle_ws(websocket, _discrete_trail)

@app.websocket("/threed/patrol")
async def ws_threed_patrol(websocket: WebSocket):
    await handle_ws(websocket, _dispatcher, "threed/patrol")

@app.websocket("/threed/trail")
async def ws_threed_trail(websocket: WebSocket):
    await handle_ws(websocket, _dispatcher, "threed/trail")

# --- WEBRTC ---

webrtc_config = ServerConfig(mode="public", logging_level="dev", socket_type="websocket")
setup_webrtc_routes(app, webrtc_config)

@app.get("/api/health")
async def health_check():
    return JSONResponse({"status": "ok", "message": "Server is running"})