from __future__ import annotations

import sqlite3

from health_tracker.app_database import get_db
from health_tracker.constants import EQUIPMENT_OPTIONS
from health_tracker.services.location import (
    deactivate_location,
    deactivate_location_equipment,
    delete_location_if_unused,
    get_location as get_location_from_db,
    get_recent_or_default_location as get_recent_or_default_location_from_db,
    list_location_equipment as list_location_equipment_from_db,
    list_locations as list_locations_from_db,
    save_location as save_location_to_db,
    set_default_location as set_default_location_in_db,
    set_session_location as set_session_location_in_db,
    upsert_location_equipment,
)


def equipment_options() -> list[str]:
    return EQUIPMENT_OPTIONS


def list_workout_locations(include_inactive: bool = False) -> list[sqlite3.Row]:
    return list_locations_from_db(get_db(), include_inactive)


def get_workout_location(location_id: int | None = None) -> sqlite3.Row:
    return get_location_from_db(get_db(), location_id)


def get_recent_or_default_location() -> sqlite3.Row:
    return get_recent_or_default_location_from_db(get_db())


def save_workout_location(
    name: str,
    address: str = "",
    memo: str = "",
    location_id: int | None = None,
    is_default: bool = False,
) -> int:
    saved_id = save_location_to_db(get_db(), name, address, memo, location_id, is_default)
    get_db().commit()
    return saved_id


def set_default_workout_location(location_id: int) -> None:
    set_default_location_in_db(get_db(), location_id)
    get_db().commit()


def deactivate_workout_location(location_id: int) -> None:
    deactivate_location(get_db(), location_id)
    get_db().commit()


def delete_unused_workout_location(location_id: int) -> bool:
    deleted = delete_location_if_unused(get_db(), location_id)
    get_db().commit()
    return deleted


def set_workout_session_location(session_id: int, location_id: int | None) -> sqlite3.Row:
    location = set_session_location_in_db(get_db(), session_id, location_id)
    get_db().commit()
    return location


def list_location_equipment(location_id: int | None = None, include_inactive: bool = False) -> list[sqlite3.Row]:
    return list_location_equipment_from_db(get_db(), location_id, include_inactive)


def save_location_equipment(
    location_id: int,
    equipment_name: str,
    equipment_type: str = "",
    memo: str = "",
) -> None:
    upsert_location_equipment(get_db(), location_id, equipment_name, equipment_type, memo)
    get_db().commit()


def delete_location_equipment(equipment_id: int) -> None:
    deactivate_location_equipment(get_db(), equipment_id)
    get_db().commit()


def equipment_options_for_location(location_id: int | None = None) -> list[str]:
    return list(EQUIPMENT_OPTIONS)

