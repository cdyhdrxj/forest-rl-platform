from __future__ import annotations

from enum import IntEnum
from typing import Any, Dict, Optional

from .enums import EventType


class RosEventType(IntEnum):
    GOAL = 0
    FLIP = 1
    COLLISION_PASSABLE = 2
    COLLISION_IMPASSABLE = 3
    INTRUDER_APPEARED = 4
    INTRUDER_DETECTED = 5
    INTRUDER_CAUGHT = 6


ROS_EVENT_TO_PLATFORM_EVENT: dict[RosEventType, EventType] = {
    RosEventType.GOAL: EventType.goal_reached,
    RosEventType.FLIP: EventType.flip,
    RosEventType.COLLISION_PASSABLE: EventType.collision_passable,
    RosEventType.COLLISION_IMPASSABLE: EventType.collision_impassable,
    RosEventType.INTRUDER_APPEARED: EventType.intruder_appeared,
    RosEventType.INTRUDER_DETECTED: EventType.intruder_detected,
    RosEventType.INTRUDER_CAUGHT: EventType.intruder_caught,
}

LEGACY_EVENT_NORMALIZATION: dict[EventType, EventType] = {
    EventType.violator_started: EventType.intruder_appeared,
    EventType.violator_detected: EventType.intruder_detected,
    EventType.violator_intercepted: EventType.intruder_caught,
}

INTRUDER_EVENT_TYPES = frozenset(
    {
        EventType.intruder_appeared,
        EventType.intruder_detected,
        EventType.intruder_caught,
        EventType.violator_started,
        EventType.violator_detected,
        EventType.violator_intercepted,
    }
)


def map_ros_event_type(event_type: int | RosEventType) -> EventType:
    return ROS_EVENT_TO_PLATFORM_EVENT[RosEventType(event_type)]


def normalize_event_type(event_type: EventType | str) -> EventType:
    resolved = event_type if isinstance(event_type, EventType) else EventType(event_type)
    return LEGACY_EVENT_NORMALIZATION.get(resolved, resolved)


def extract_intruder_id(payload_json: Optional[Dict[str, Any]]) -> Optional[int]:
    if not isinstance(payload_json, dict):
        return None

    value = payload_json.get("intruder_id")
    if value is None:
        return None

    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def merge_intruder_id(
    payload_json: Optional[Dict[str, Any]],
    intruder_id: Optional[int],
) -> Optional[Dict[str, Any]]:
    payload = dict(payload_json or {})

    if intruder_id is None:
        payload.pop("intruder_id", None)
    else:
        payload["intruder_id"] = int(intruder_id)

    return payload or None
