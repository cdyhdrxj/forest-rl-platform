from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from apps.api.websocket_manager import handle_ws
from services.trail_camar.service  import CamarService
from services.patrol_planning.service.service import GridWorldService

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_camar_trail = CamarService()
_patrol_discrete = GridWorldService()

# _discrete_trail = DiscreteService()

@app.websocket("/continuous/trail")
async def ws_continuous(websocket: WebSocket):
    await handle_ws(websocket, _camar_trail)

# @app.websocket("/continuous/patrol")
# async def ws_continuous(websocket: WebSocket):
#     await handle_ws(websocket, _camar)

@app.websocket("/discrete/patrol")
async def ws_discrete_patrol(websocket: WebSocket):
    await handle_ws(websocket, _patrol_discrete)

# @app.websocket("/discrete/trail")
# async def ws_discrete_trail(websocket: WebSocket):
#     await handle_ws(websocket, _discrete_trail)

# @app.websocket("/threed/patrol")
# async def ws_threed(websocket: WebSocket):
#     await handle_ws(websocket, _threed_patrol)

# @app.websocket("/threed/trail")
# async def ws_threed(websocket: WebSocket):
#     await handle_ws(websocket, _threed)