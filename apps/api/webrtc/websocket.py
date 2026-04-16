import json
from handlers import websockethandler as handler


class WSSignaling:
    def __init__(self, server, mode: str):
        self.server = server
        handler.reset(mode)
    
    async def handle_connection(self, websocket):
        await handler.add(websocket)
        
        try:
            async for message in websocket:
                msg = json.loads(message)
                
                if not msg:
                    continue
                
                print(msg)
                
                msg_type = msg.get("type")
                
                if msg_type == "connect":
                    await handler.on_connect(websocket, msg.get("connectionId"))
                elif msg_type == "disconnect":
                    await handler.on_disconnect(websocket, msg.get("connectionId"))
                elif msg_type == "offer":
                    await handler.on_offer(websocket, msg.get("data"))
                elif msg_type == "answer":
                    await handler.on_answer(websocket, msg.get("data"))
                elif msg_type == "candidate":
                    await handler.on_candidate(websocket, msg.get("data"))
        
        except Exception as e:
            print(f"WebSocket error: {e}")
        finally:
            await handler.remove(websocket)