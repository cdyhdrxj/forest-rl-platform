# webrtc_routes.py
import os
import json
from pathlib import Path
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from webrtc.handlers.websockethandler import WebSocketHandler
import logging

logger = logging.getLogger(__name__)

class ServerConfig:
    def __init__(self, mode: str = "public", logging_level: str = "dev", socket_type: str = "websocket"):
        self.mode = mode
        self.logging = logging_level
        self.type = socket_type

def setup_webrtc_routes(app: FastAPI, config: ServerConfig = None):
    
    if config is None:
        config = ServerConfig()
    
    WebSocketHandler.reset(config.mode)
    
    @app.middleware("http")
    async def log_webrtc_requests(request: Request, call_next):
        if request.url.path in ["/ws", "/signaling", "/webrtc/config"] or request.url.path.startswith(("/client/", "/multiplay/")):
            logger.info(f"🌐 WebRTC {request.method} {request.url.path} from {request.client.host}")
        response = await call_next(request)
        return response
    
    @app.get("/webrtc/config")
    async def get_webrtc_config():
        return JSONResponse({
            "useWebSocket": config.type == "websocket",
            "startupMode": config.mode,
            "logging": config.logging
        })

    @app.websocket("/ws")
    async def websocket_ws(websocket: WebSocket):
        logger.info(f"WebRTC WebSocket /ws from {websocket.client.host}:{websocket.client.port}")
        await WebSocketHandler.handle_connection(websocket)

    @app.websocket("/signaling")
    async def websocket_signaling(websocket: WebSocket):
        logger.info(f"WebRTC Signaling /signaling from {websocket.client.host}:{websocket.client.port}")
        await WebSocketHandler.handle_connection(websocket)
    
    logger.info("WebRTC routes added to existing FastAPI app")
    return app