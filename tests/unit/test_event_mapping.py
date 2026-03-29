from packages.db.models.episode_event import EpisodeEvent
from packages.db.models.enums import EventType as DBEventType
from packages.schemas.episode_event import EpisodeEventBase
from packages.schemas.enums import EventType
from packages.schemas.event_mapping import RosEventType, map_ros_event_type, normalize_event_type


def test_ros_event_mapping_uses_canonical_platform_events():
    assert map_ros_event_type(RosEventType.GOAL) is EventType.goal_reached
    assert map_ros_event_type(RosEventType.COLLISION_IMPASSABLE) is EventType.collision_impassable
    assert map_ros_event_type(RosEventType.INTRUDER_CAUGHT) is EventType.intruder_caught


def test_legacy_violator_events_normalize_to_intruder_events():
    assert normalize_event_type(EventType.violator_started) is EventType.intruder_appeared
    assert normalize_event_type(EventType.violator_detected) is EventType.intruder_detected
    assert normalize_event_type(EventType.violator_intercepted) is EventType.intruder_caught


def test_episode_event_schema_syncs_intruder_id_into_payload():
    event = EpisodeEventBase(
        episode_id=1,
        event_type=EventType.intruder_detected,
        intruder_id=42,
    )

    assert event.payload_json == {"intruder_id": 42}


def test_episode_event_model_exposes_intruder_id_property():
    event = EpisodeEvent(event_type=DBEventType.intruder_appeared, payload_json={"intruder_id": "7"})

    assert event.intruder_id == 7

    event.intruder_id = 11
    assert event.payload_json == {"intruder_id": 11}
