import json
import logging
from datetime import datetime
from typing import Dict, Set, Optional, List
from fastapi import WebSocket
import asyncio

logger = logging.getLogger(__name__)

class Offer:
    def __init__(self, sdp: str, datetime: int, polite: bool = False):
        self.sdp = sdp
        self.datetime = datetime
        self.polite = polite
    
    def to_dict(self):
        return {"sdp": self.sdp, "datetime": self.datetime, "polite": self.polite}

class Answer:
    def __init__(self, sdp: str, datetime: int):
        self.sdp = sdp
        self.datetime = datetime
    
    def to_dict(self):
        return {"sdp": self.sdp, "datetime": self.datetime}

class Candidate:
    def __init__(self, candidate: str, sdpMLineIndex: int, sdpMid: str, datetime: int):
        self.candidate = candidate
        self.sdpMLineIndex = sdpMLineIndex
        self.sdpMid = sdpMid
        self.datetime = datetime
    
    def to_dict(self):
        return {
            "candidate": self.candidate,
            "sdpMLineIndex": self.sdpMLineIndex,
            "sdpMid": self.sdpMid,
            "datetime": self.datetime
        }

class WebSocketHandler:
    is_private: bool = False
    clients: Dict[WebSocket, Set[str]] = {}
    connection_pair: Dict[str, List[Optional[WebSocket]]] = {}
    
    @classmethod
    def reset(cls, mode: str):
        cls.is_private = (mode == "private")
        cls.clients.clear()
        cls.connection_pair.clear()
        logger.info(f"WebSocketHandler reset with mode: {mode}")
    
    @classmethod
    def get_or_create_connection_ids(cls, session: WebSocket) -> Set[str]:
        if session not in cls.clients:
            cls.clients[session] = set()
        return cls.clients[session]
    
    @classmethod
    def add(cls, ws: WebSocket):
        cls.clients[ws] = set()
        logger.info(f"Added new WebSocket session")
    
    @classmethod
    def remove(cls, ws: WebSocket):
        if ws not in cls.clients:
            return
        
        connection_ids = cls.clients[ws]
        for connection_id in connection_ids:
            if connection_id in cls.connection_pair:
                pair = cls.connection_pair[connection_id]
                other = pair[1] if pair[0] == ws else pair[0]
                if other:
                    try:
                        asyncio.create_task(other.send_text(json.dumps({
                            "type": "disconnect",
                            "connectionId": connection_id
                        })))
                    except:
                        pass
                del cls.connection_pair[connection_id]
        
        del cls.clients[ws]
        logger.info(f"Removed WebSocket session")
    
    @classmethod
    async def handle_connection(cls, websocket: WebSocket):
        await websocket.accept()
        cls.add(websocket)
        
        client_ip = websocket.client.host if websocket.client else "unknown"
        logger.info(f"WebSocket connected from {client_ip}")
        
        try:
            async for message in websocket.iter_text():
                try:
                    data = json.loads(message)
                    msg_type = data.get("type")
                    
                    logger.debug(f"Received {msg_type}: {message[:200]}...")
                    
                    if msg_type == "connect":
                        await cls.on_connect(websocket, data)
                    elif msg_type == "disconnect":
                        await cls.on_disconnect(websocket, data)
                    elif msg_type == "offer":
                        await cls.on_offer(websocket, data)
                    elif msg_type == "answer":
                        await cls.on_answer(websocket, data)
                    elif msg_type == "candidate":
                        await cls.on_candidate(websocket, data)
                    else:
                        logger.warning(f"Unknown message type: {msg_type}")
                        
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON: {message}")
                except Exception as e:
                    logger.error(f"Error processing message: {e}", exc_info=True)
                    
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
        finally:
            cls.remove(websocket)
    
    @classmethod
    async def on_connect(cls, ws: WebSocket, data: dict):
        # Поддерживаем оба варианта: connectionId и connectionId внутри data
        connection_id = data.get("connectionId")
        if not connection_id:
            logger.error(f"Missing connectionId in connect message: {data}")
            return
        
        polite = True
        
        if cls.is_private:
            if connection_id in cls.connection_pair:
                pair = cls.connection_pair[connection_id]
                if pair[0] is not None and pair[1] is not None:
                    await ws.send_text(json.dumps({
                        "type": "error",
                        "message": f"{connection_id}: This connection id is already used."
                    }))
                    return
                elif pair[0] is not None:
                    cls.connection_pair[connection_id] = [pair[0], ws]
            else:
                cls.connection_pair[connection_id] = [ws, None]
                polite = False
        
        connection_ids = cls.get_or_create_connection_ids(ws)
        connection_ids.add(connection_id)
        
        await ws.send_text(json.dumps({
            "type": "connect",
            "connectionId": connection_id,
            "polite": polite
        }))
        
        logger.info(f"Connect: {connection_id}, polite: {polite}")
    
    @classmethod
    async def on_disconnect(cls, ws: WebSocket, data: dict):
        connection_id = data.get("connectionId")
        if not connection_id:
            logger.error(f"Missing connectionId in disconnect message")
            return
        
        if ws in cls.clients:
            cls.clients[ws].discard(connection_id)
        
        if connection_id in cls.connection_pair:
            pair = cls.connection_pair[connection_id]
            other = pair[1] if pair[0] == ws else pair[0]
            if other:
                await other.send_text(json.dumps({
                    "type": "disconnect",
                    "connectionId": connection_id
                }))
            del cls.connection_pair[connection_id]
        
        await ws.send_text(json.dumps({
            "type": "disconnect",
            "connectionId": connection_id
        }))
        
        logger.info(f"Disconnect: {connection_id}")
    
    @classmethod
    async def on_offer(cls, ws: WebSocket, data: dict):
        # Клиент отправляет: {type: "offer", from: connectionId, data: {sdp, connectionId}}
        connection_id = data.get("from") or data.get("connectionId")
        
        # SDP может быть в data.sdp или на верхнем уровне
        sdp = None
        if "data" in data and isinstance(data["data"], dict):
            sdp = data["data"].get("sdp")
        if not sdp:
            sdp = data.get("sdp")
        
        if not connection_id or not sdp:
            logger.error(f"Missing connectionId or sdp in offer: {data.keys()}")
            return
        
        new_offer = Offer(sdp=sdp, datetime=int(datetime.now().timestamp()), polite=False)
        
        if cls.is_private:
            if connection_id in cls.connection_pair:
                pair = cls.connection_pair[connection_id]
                other = pair[1] if pair[0] == ws else pair[0]
                if other:
                    new_offer.polite = True
                    await other.send_text(json.dumps({
                        "from": connection_id,
                        "to": "",
                        "type": "offer",
                        "data": new_offer.to_dict()
                    }))
            return
        
        cls.connection_pair[connection_id] = [ws, None]
        
        # Отправляем всем кроме отправителя
        for client in cls.clients:
            if client != ws:
                try:
                    await client.send_text(json.dumps({
                        "from": connection_id,
                        "to": "",
                        "type": "offer",
                        "data": new_offer.to_dict()
                    }))
                except:
                    pass
        
        logger.info(f"Offer from {connection_id}")
    
    @classmethod
    async def on_answer(cls, ws: WebSocket, data: dict):
        connection_id = data.get("from") or data.get("connectionId")
        
        sdp = None
        if "data" in data and isinstance(data["data"], dict):
            sdp = data["data"].get("sdp")
        if not sdp:
            sdp = data.get("sdp")
        
        if not connection_id or not sdp:
            logger.error(f"Missing connectionId or sdp in answer")
            return
        
        connection_ids = cls.get_or_create_connection_ids(ws)
        connection_ids.add(connection_id)
        
        new_answer = Answer(sdp=sdp, datetime=int(datetime.now().timestamp()))
        
        if connection_id not in cls.connection_pair:
            return
        
        pair = cls.connection_pair[connection_id]
        other = pair[1] if pair[0] == ws else pair[0]
        
        if not cls.is_private:
            cls.connection_pair[connection_id] = [other, ws]
        
        if other:
            await other.send_text(json.dumps({
                "from": connection_id,
                "to": "",
                "type": "answer",
                "data": new_answer.to_dict()
            }))
        
        logger.info(f"Answer from {connection_id}")
    
    @classmethod
    async def on_candidate(cls, ws: WebSocket, data: dict):
        connection_id = data.get("from") or data.get("connectionId")
        
        # Извлекаем данные кандидата
        cand_data = data.get("data", data)
        
        candidate_str = cand_data.get("candidate")
        sdp_mline_index = cand_data.get("sdpMLineIndex")
        sdp_mid = cand_data.get("sdpMid")
        
        if not connection_id or not candidate_str:
            logger.error(f"Missing required fields in candidate")
            return
        
        candidate = Candidate(
            candidate=candidate_str,
            sdpMLineIndex=sdp_mline_index or 0,
            sdpMid=sdp_mid or "",
            datetime=int(datetime.now().timestamp())
        )
        
        if cls.is_private:
            if connection_id in cls.connection_pair:
                pair = cls.connection_pair[connection_id]
                other = pair[1] if pair[0] == ws else pair[0]
                if other:
                    await other.send_text(json.dumps({
                        "from": connection_id,
                        "to": "",
                        "type": "candidate",
                        "data": candidate.to_dict()
                    }))
            return
        
        # Отправляем всем кроме отправителя
        for client in cls.clients:
            if client != ws:
                try:
                    await client.send_text(json.dumps({
                        "from": connection_id,
                        "to": "",
                        "type": "candidate",
                        "data": candidate.to_dict()
                    }))
                except:
                    pass
        
        logger.debug(f"Candidate from {connection_id}")