from __future__ import annotations

import sqlite3

from health_tracker.constants import normalize_equipment_category


DEFAULT_LOCATION_NAME = "기본 헬스장"


def ensure_default_location(db: sqlite3.Connection) -> sqlite3.Row:
    row = db.execute(
        "SELECT * FROM workout_locations WHERE is_default = 1 AND is_active = 1 ORDER BY id LIMIT 1"
    ).fetchone()
    if row:
        return row

    row = db.execute(
        "SELECT * FROM workout_locations WHERE name = ?",
        (DEFAULT_LOCATION_NAME,),
    ).fetchone()
    if not row:
        cursor = db.execute(
            """
            INSERT INTO workout_locations (name, memo, is_default, is_active)
            VALUES (?, ?, 1, 1)
            """,
            (DEFAULT_LOCATION_NAME, "기존 기록을 보존하기 위한 기본 장소"),
        )
        location_id = cursor.lastrowid
    else:
        location_id = row["id"]
        db.execute(
            "UPDATE workout_locations SET is_default = 1, is_active = 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (location_id,),
        )
    db.execute("UPDATE workout_locations SET is_default = CASE WHEN id = ? THEN 1 ELSE 0 END", (location_id,))
    return db.execute("SELECT * FROM workout_locations WHERE id = ?", (location_id,)).fetchone()


def bootstrap_locations(db: sqlite3.Connection) -> sqlite3.Row:
    default_location = ensure_default_location(db)
    db.execute(
        "UPDATE workout_sessions SET location_id = ? WHERE location_id IS NULL",
        (default_location["id"],),
    )
    sync_location_equipment_from_sets(db, int(default_location["id"]))
    cleanup_location_equipment_categories(db)
    return default_location


def sync_location_equipment_from_sets(db: sqlite3.Connection, default_location_id: int) -> None:
    rows = db.execute(
        """
        SELECT DISTINCT COALESCE(NULLIF(ws.equipment, ''), NULLIF(es.equipment, '')) AS equipment
        FROM workout_sets ws
        JOIN exercises e ON e.id = ws.exercise_id
        LEFT JOIN exercise_settings es ON es.exercise_name = e.name
        WHERE COALESCE(NULLIF(ws.equipment, ''), NULLIF(es.equipment, '')) IS NOT NULL
        """
    ).fetchall()
    for row in rows:
        equipment = normalize_equipment_category(str(row["equipment"] or ""))
        if equipment:
            upsert_location_equipment(db, default_location_id, equipment)


def list_locations(db: sqlite3.Connection, include_inactive: bool = False) -> list[sqlite3.Row]:
    where = "" if include_inactive else "WHERE wl.is_active = 1"
    return db.execute(
        f"""
        SELECT wl.*,
               COUNT(DISTINCT le.id) AS equipment_count,
               COUNT(DISTINCT ws.id) AS session_count
        FROM workout_locations wl
        LEFT JOIN location_equipment le ON le.location_id = wl.id AND le.is_active = 1
        LEFT JOIN workout_sessions ws ON ws.location_id = wl.id
        {where}
        GROUP BY wl.id
        ORDER BY wl.is_default DESC, wl.is_active DESC, wl.name
        """
    ).fetchall()


def get_location(db: sqlite3.Connection, location_id: int | None) -> sqlite3.Row:
    if location_id:
        row = db.execute("SELECT * FROM workout_locations WHERE id = ?", (location_id,)).fetchone()
        if row:
            return row
    return ensure_default_location(db)


def get_recent_or_default_location(db: sqlite3.Connection) -> sqlite3.Row:
    row = db.execute(
        """
        SELECT wl.*
        FROM workout_sessions ws
        JOIN workout_locations wl ON wl.id = ws.location_id
        WHERE wl.is_active = 1
        ORDER BY ws.workout_date DESC, ws.id DESC
        LIMIT 1
        """
    ).fetchone()
    return row or ensure_default_location(db)


def save_location(
    db: sqlite3.Connection,
    name: str,
    address: str = "",
    memo: str = "",
    location_id: int | None = None,
    is_default: bool = False,
) -> int:
    clean_name = name.strip()[:60]
    if not clean_name:
        return int(ensure_default_location(db)["id"])
    if location_id:
        db.execute(
            """
            UPDATE workout_locations
            SET name = ?, address = ?, memo = ?, is_active = 1, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (clean_name, address.strip()[:120], memo.strip()[:240], location_id),
        )
        saved_id = location_id
    else:
        cursor = db.execute(
            """
            INSERT INTO workout_locations (name, address, memo, is_default, is_active, updated_at)
            VALUES (?, ?, ?, 0, 1, CURRENT_TIMESTAMP)
            ON CONFLICT(name) DO UPDATE SET
                address = excluded.address,
                memo = excluded.memo,
                is_active = 1,
                updated_at = CURRENT_TIMESTAMP
            """,
            (clean_name, address.strip()[:120], memo.strip()[:240]),
        )
        row = db.execute("SELECT id FROM workout_locations WHERE name = ?", (clean_name,)).fetchone()
        saved_id = int(row["id"] if row else cursor.lastrowid)
    if is_default:
        set_default_location(db, saved_id)
    return int(saved_id)


def set_default_location(db: sqlite3.Connection, location_id: int) -> None:
    db.execute("UPDATE workout_locations SET is_default = CASE WHEN id = ? THEN 1 ELSE 0 END", (location_id,))
    db.execute("UPDATE workout_locations SET is_active = 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (location_id,))


def deactivate_location(db: sqlite3.Connection, location_id: int) -> None:
    default_id = int(ensure_default_location(db)["id"])
    if location_id == default_id:
        return
    db.execute(
        "UPDATE workout_locations SET is_active = 0, is_default = 0, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (location_id,),
    )


def delete_location_if_unused(db: sqlite3.Connection, location_id: int) -> bool:
    default_id = int(ensure_default_location(db)["id"])
    if location_id == default_id:
        return False
    session_count = db.execute(
        "SELECT COUNT(*) FROM workout_sessions WHERE location_id = ?",
        (location_id,),
    ).fetchone()[0]
    if int(session_count or 0) > 0:
        return False
    db.execute("DELETE FROM location_equipment WHERE location_id = ?", (location_id,))
    db.execute("DELETE FROM workout_locations WHERE id = ?", (location_id,))
    return True


def set_session_location(db: sqlite3.Connection, session_id: int, location_id: int | None) -> sqlite3.Row:
    location = get_location(db, location_id)
    db.execute("UPDATE workout_sessions SET location_id = ? WHERE id = ?", (location["id"], session_id))
    return location


def list_location_equipment(db: sqlite3.Connection, location_id: int | None = None, include_inactive: bool = False) -> list[sqlite3.Row]:
    params: list[object] = []
    where_parts = []
    if location_id:
        where_parts.append("le.location_id = ?")
        params.append(location_id)
    if not include_inactive:
        where_parts.append("le.is_active = 1")
    where = "WHERE " + " AND ".join(where_parts) if where_parts else ""
    return db.execute(
        f"""
        SELECT le.*, wl.name AS location_name
        FROM location_equipment le
        JOIN workout_locations wl ON wl.id = le.location_id
        {where}
        ORDER BY wl.is_default DESC, wl.name, le.equipment_name
        """,
        params,
    ).fetchall()


def location_equipment_names(db: sqlite3.Connection, location_id: int | None) -> list[str]:
    location = get_location(db, location_id)
    rows = list_location_equipment(db, int(location["id"]))
    names = [normalize_equipment_category(str(row["equipment_name"])) for row in rows]
    names = [name for name in names if name]
    if names:
        return list(dict.fromkeys(names))
    rows = db.execute(
        """
        SELECT DISTINCT COALESCE(NULLIF(equipment, ''), '미지정') AS equipment
        FROM workout_sets
        WHERE COALESCE(NULLIF(equipment, ''), '') != ''
        ORDER BY equipment
        """
    ).fetchall()
    normalized = [normalize_equipment_category(str(row["equipment"])) for row in rows]
    return list(dict.fromkeys([name for name in normalized if name]))


def upsert_location_equipment(
    db: sqlite3.Connection,
    location_id: int,
    equipment_name: str,
    equipment_type: str = "",
    memo: str = "",
) -> None:
    clean_name = normalize_equipment_category(equipment_name)
    if not clean_name:
        return
    clean_type = normalize_equipment_category(equipment_type) or clean_name
    db.execute(
        """
        INSERT INTO location_equipment (
            location_id, equipment_name, equipment_type, memo, is_active, updated_at
        )
        VALUES (?, ?, ?, ?, 1, CURRENT_TIMESTAMP)
        ON CONFLICT(location_id, equipment_name) DO UPDATE SET
            equipment_type = COALESCE(NULLIF(excluded.equipment_type, ''), location_equipment.equipment_type),
            memo = COALESCE(NULLIF(excluded.memo, ''), location_equipment.memo),
            is_active = 1,
            updated_at = CURRENT_TIMESTAMP
        """,
        (location_id, clean_name, clean_type, memo.strip()[:160]),
    )


def cleanup_location_equipment_categories(db: sqlite3.Connection) -> None:
    rows = db.execute("SELECT id, location_id, equipment_name, equipment_type, memo FROM location_equipment").fetchall()
    for row in rows:
        category = normalize_equipment_category(row["equipment_name"]) or normalize_equipment_category(row["equipment_type"])
        if not category:
            db.execute("UPDATE location_equipment SET is_active = 0, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (row["id"],))
            continue
        db.execute(
            """
            INSERT INTO location_equipment (location_id, equipment_name, equipment_type, memo, is_active, updated_at)
            VALUES (?, ?, ?, ?, 1, CURRENT_TIMESTAMP)
            ON CONFLICT(location_id, equipment_name) DO UPDATE SET
                equipment_type = excluded.equipment_type,
                is_active = 1,
                updated_at = CURRENT_TIMESTAMP
            """,
            (row["location_id"], category, category, row["memo"] or ""),
        )
        db.execute(
            """
            UPDATE location_equipment
            SET is_active = CASE WHEN equipment_name = ? THEN is_active ELSE 0 END,
                updated_at = CURRENT_TIMESTAMP
            WHERE location_id = ? AND id = ?
            """,
            (category, row["location_id"], row["id"]),
        )


def deactivate_location_equipment(db: sqlite3.Connection, equipment_id: int) -> None:
    db.execute(
        "UPDATE location_equipment SET is_active = 0, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (equipment_id,),
    )
