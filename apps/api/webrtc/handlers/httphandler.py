# class/httphandler.py
import uuid
from typing import Dict, Set, List, Optional, Tuple
from datetime import datetime
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from .offer import Offer
from .answer import Answer
from .candidate import Candidate

clients = {}
last_requested_time = {}

class Disconnection:
    def __init__(self, id: str, datetime: int):
        self.id = id
        self.datetime = datetime

TIMEOUT_REQUESTED_TIME = 10000

is_private: bool = False
clients: Dict[str, Set[str]] = {}
last_requested_time: Dict[str, int] = {}
connection_pair: Dict[str, Tuple[Optional[str], Optional[str]]] = {}
offers: Dict[str, Dict[str, Offer]] = {}
answers: Dict[str, Dict[str, Answer]] = {}
candidates: Dict[str, Dict[str, List[Candidate]]] = {}
disconnections: Dict[str, List[Disconnection]] = {}

def get_or_create_connection_ids(session_id: str) -> Set[str]:
    if session_id not in clients:
        clients[session_id] = set()
    return clients[session_id]

def reset(mode: str):
    global is_private, clients, connection_pair, offers, answers, candidates, disconnections
    is_private = mode == "private"
    clients.clear()
    connection_pair.clear()
    offers.clear()
    answers.clear()
    candidates.clear()
    disconnections.clear()

def _delete_connection(session_id: str, connection_id: str, dt: int):
    if session_id in clients:
        clients[session_id].discard(connection_id)
    
    if is_private:
        if connection_id in connection_pair:
            pair = connection_pair[connection_id]
            other_session_id = pair[1] if pair[0] == session_id else pair[0]
            if other_session_id and other_session_id in clients:
                clients[other_session_id].discard(connection_id)
                if other_session_id not in disconnections:
                    disconnections[other_session_id] = []
                disconnections[other_session_id].append(Disconnection(connection_id, dt))
    else:
        for sid, arr in disconnections.items():
            if sid == session_id:
                continue
            arr.append(Disconnection(connection_id, dt))
    
    if connection_id in connection_pair:
        del connection_pair[connection_id]
    
    if session_id in offers and connection_id in offers[session_id]:
        del offers[session_id][connection_id]
    
    if session_id in answers and connection_id in answers[session_id]:
        del answers[session_id][connection_id]
    
    if session_id in candidates and connection_id in candidates[session_id]:
        del candidates[session_id][connection_id]
    
    if session_id not in disconnections:
        disconnections[session_id] = []
    disconnections[session_id].append(Disconnection(connection_id, dt))

def _delete_session(session_id: str):
    if session_id in clients:
        for connection_id in list(clients[session_id]):
            _delete_connection(session_id, connection_id, int(datetime.now().timestamp() * 1000))
    
    offers.pop(session_id, None)
    answers.pop(session_id, None)
    candidates.pop(session_id, None)
    clients.pop(session_id, None)
    disconnections.pop(session_id, None)

def _check_for_timed_out_sessions():
    now = int(datetime.now().timestamp() * 1000)
    for session_id in list(clients.keys()):
        if session_id not in last_requested_time:
            continue
        if last_requested_time[session_id] > now - TIMEOUT_REQUESTED_TIME:
            continue
        _delete_session(session_id)
        print(f"deleted sessionId:{session_id} by timeout.")

def _get_connection(session_id: str) -> List[str]:
    _check_for_timed_out_sessions()
    return list(clients.get(session_id, set()))

def _get_disconnection(session_id: str, from_time: int) -> List[Disconnection]:
    _check_for_timed_out_sessions()
    array_disconnections = disconnections.get(session_id, [])
    if from_time > 0:
        array_disconnections = [d for d in array_disconnections if d.datetime >= from_time]
    return array_disconnections

def _get_offer(session_id: str, from_time: int) -> List[Tuple[str, Offer]]:
    array_offers = []
    if is_private:
        if session_id in offers:
            array_offers = [(cid, offer) for cid, offer in offers[session_id].items()]
    else:
        for sid, offer_map in offers.items():
            if sid != session_id:
                for cid, offer in offer_map.items():
                    array_offers.append((cid, offer))
    
    if from_time > 0:
        array_offers = [(cid, o) for cid, o in array_offers if o.datetime >= from_time]
    return array_offers

def _get_answer(session_id: str, from_time: int) -> List[Tuple[str, Answer]]:
    array_answers = []
    if session_id in answers:
        array_answers = [(cid, ans) for cid, ans in answers[session_id].items()]
    
    if from_time > 0:
        array_answers = [(cid, a) for cid, a in array_answers if a.datetime >= from_time]
    return array_answers

def _get_candidate(session_id: str, from_time: int) -> List[Tuple[str, Candidate]]:
    connection_ids = list(clients.get(session_id, set()))
    result = []
    
    for connection_id in connection_ids:
        pair = connection_pair.get(connection_id)
        if not pair:
            continue
        other_session_id = pair[1] if session_id == pair[0] else pair[0]
        if not other_session_id or other_session_id not in candidates:
            continue
        if connection_id not in candidates[other_session_id]:
            continue
        
        candidate_list = [c for c in candidates[other_session_id][connection_id] if c.datetime >= from_time]
        for candidate in candidate_list:
            result.append((connection_id, candidate))
    
    return result

async def check_session_id(request: Request, call_next):
    if request.url.path == '/':
        return await call_next(request)
    
    session_id = request.headers.get('session-id')
    if session_id not in clients:
        return Response(status_code=404)
    
    last_requested_time[session_id] = int(datetime.now().timestamp() * 1000)
    return await call_next(request)

async def get_connection(request: Request):
    session_id = request.headers.get('session-id')
    connections = _get_connection(session_id)
    return JSONResponse({
        "connections": [{"connectionId": c, "type": "connect", "datetime": int(datetime.now().timestamp() * 1000)} for c in connections]
    })

async def get_offer(request: Request):
    from_time = int(request.query_params.get('fromtime', 0))
    session_id = request.headers.get('session-id')
    offers_list = _get_offer(session_id, from_time)
    return JSONResponse({
        "offers": [{"connectionId": cid, "sdp": o.sdp, "polite": o.polite, "type": "offer", "datetime": o.datetime} for cid, o in offers_list]
    })

async def get_answer(request: Request):
    from_time = int(request.query_params.get('fromtime', 0))
    session_id = request.headers.get('session-id')
    answers_list = _get_answer(session_id, from_time)
    return JSONResponse({
        "answers": [{"connectionId": cid, "sdp": a.sdp, "type": "answer", "datetime": a.datetime} for cid, a in answers_list]
    })

async def get_candidate(request: Request):
    from_time = int(request.query_params.get('fromtime', 0))
    session_id = request.headers.get('session-id')
    candidates_list = _get_candidate(session_id, from_time)
    return JSONResponse({
        "candidates": [{"connectionId": cid, "candidate": cand.candidate, "sdpMLineIndex": cand.sdpMLineIndex, "sdpMid": cand.sdpMid, "type": "candidate", "datetime": cand.datetime} for cid, cand in candidates_list]
    })

async def get_all(request: Request):
    from_time = int(request.query_params.get('fromtime', 0))
    session_id = request.headers.get('session-id')
    
    connections = _get_connection(session_id)
    offers_list = _get_offer(session_id, from_time)
    answers_list = _get_answer(session_id, from_time)
    candidates_list = _get_candidate(session_id, from_time)
    disconnections_list = _get_disconnection(session_id, from_time)
    
    dt = last_requested_time.get(session_id, int(datetime.now().timestamp() * 1000))
    
    messages = []
    messages.extend([{"connectionId": c, "type": "connect", "datetime": dt} for c in connections])
    messages.extend([{"connectionId": cid, "sdp": o.sdp, "polite": o.polite, "type": "offer", "datetime": o.datetime} for cid, o in offers_list])
    messages.extend([{"connectionId": cid, "sdp": a.sdp, "type": "answer", "datetime": a.datetime} for cid, a in answers_list])
    messages.extend([{"connectionId": cid, "candidate": cand.candidate, "sdpMLineIndex": cand.sdpMLineIndex, "sdpMid": cand.sdpMid, "type": "candidate", "datetime": cand.datetime} for cid, cand in candidates_list])
    messages.extend([{"connectionId": d.id, "type": "disconnect", "datetime": d.datetime} for d in disconnections_list])
    
    messages.sort(key=lambda x: x["datetime"])
    
    return JSONResponse({"messages": messages, "datetime": dt})

async def create_session(request: Request = None, session_id: str = None):
    if session_id is None:
        session_id = str(uuid.uuid4())
    
    clients[session_id] = set()
    offers[session_id] = {}
    answers[session_id] = {}
    candidates[session_id] = {}
    disconnections[session_id] = []
    
    return JSONResponse({"sessionId": session_id})

async def delete_session(request: Request):
    session_id = request.headers.get('session-id')
    _delete_session(session_id)
    return Response(status_code=200)

async def create_connection(request: Request):
    session_id = request.headers.get('session-id')
    body = await request.json()
    connection_id = body.get('connectionId')
    
    if not connection_id:
        return Response(status_code=400, content={"error": "connectionId is required"})
    
    dt = last_requested_time.get(session_id, int(datetime.now().timestamp() * 1000))
    polite = True
    
    if is_private:
        if connection_id in connection_pair:
            pair = connection_pair[connection_id]
            if pair[0] is not None and pair[1] is not None:
                return Response(status_code=400, content={"error": f"{connection_id}: This connection id is already used."})
            elif pair[0] is not None:
                connection_pair[connection_id] = (pair[0], session_id)
                get_or_create_connection_ids(pair[0]).add(connection_id)
        else:
            connection_pair[connection_id] = (session_id, None)
            polite = False
    
    get_or_create_connection_ids(session_id).add(connection_id)
    
    return JSONResponse({"connectionId": connection_id, "polite": polite, "type": "connect", "datetime": dt})

async def delete_connection(request: Request):
    session_id = request.headers.get('session-id')
    body = await request.json()
    connection_id = body.get('connectionId')
    dt = last_requested_time.get(session_id, int(datetime.now().timestamp() * 1000))
    
    _delete_connection(session_id, connection_id, dt)
    return JSONResponse({"connectionId": connection_id})

async def post_offer(request: Request):
    session_id = request.headers.get('session-id')
    body = await request.json()
    connection_id = body.get('connectionId')
    dt = last_requested_time.get(session_id, int(datetime.now().timestamp() * 1000))
    
    key_session_id = None
    polite = False
    
    if is_private:
        if connection_id in connection_pair:
            pair = connection_pair[connection_id]
            key_session_id = pair[1] if pair[0] == session_id else pair[0]
            if key_session_id:
                polite = True
                if key_session_id not in offers:
                    offers[key_session_id] = {}
                offers[key_session_id][connection_id] = Offer(body.get('sdp'), dt, polite)
        return Response(status_code=200)
    
    if connection_id not in connection_pair:
        connection_pair[connection_id] = (session_id, None)
    
    key_session_id = session_id
    if key_session_id not in offers:
        offers[key_session_id] = {}
    offers[key_session_id][connection_id] = Offer(body.get('sdp'), dt, polite)
    
    return Response(status_code=200)

async def post_answer(request: Request):
    session_id = request.headers.get('session-id')
    body = await request.json()
    connection_id = body.get('connectionId')
    dt = last_requested_time.get(session_id, int(datetime.now().timestamp() * 1000))
    
    get_or_create_connection_ids(session_id).add(connection_id)
    
    if connection_id not in connection_pair:
        return Response(status_code=200)
    
    pair = connection_pair[connection_id]
    other_session_id = pair[1] if pair[0] == session_id else pair[0]
    
    if other_session_id not in clients:
        return Response(status_code=200)
    
    if not is_private:
        connection_pair[connection_id] = (other_session_id, session_id)
    
    if other_session_id not in answers:
        answers[other_session_id] = {}
    answers[other_session_id][connection_id] = Answer(body.get('sdp'), dt)
    
    if other_session_id in candidates and connection_id in candidates[other_session_id]:
        for cand in candidates[other_session_id][connection_id]:
            cand.datetime = dt
    
    return Response(status_code=200)

async def post_candidate(request: Request):
    session_id = request.headers.get('session-id')
    body = await request.json()
    connection_id = body.get('connectionId')
    dt = last_requested_time.get(session_id, int(datetime.now().timestamp() * 1000))
    
    if session_id not in candidates:
        candidates[session_id] = {}
    if connection_id not in candidates[session_id]:
        candidates[session_id][connection_id] = []
    
    candidate = Candidate(
        body.get('candidate'),
        body.get('sdpMLineIndex'),
        body.get('sdpMid'),
        dt
    )
    candidates[session_id][connection_id].append(candidate)
    
    return Response(status_code=200)