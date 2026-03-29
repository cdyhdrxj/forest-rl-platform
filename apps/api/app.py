from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from apps.api.dispatcher import ExperimentDispatcher
from apps.api.websocket_manager import handle_ws

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
