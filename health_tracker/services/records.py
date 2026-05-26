from __future__ import annotations

import sqlite3
from collections.abc import Callable

from health_tracker.services.pagination import build_pagination


def paged_rows_from_db(
    db: sqlite3.Connection,
    select_sql: str,
    count_sql: str,
    params: list[object],
    page: int,
    per_page: int,
) -> tuple[list[sqlite3.Row], object]:
    total = int(db.execute(count_sql, params).fetchone()[0] or 0)
    pagination = build_pagination(total, page, per_page)
    rows = db.execute(f"{select_sql} LIMIT ? OFFSET ?", (*params, pagination.per_page, pagination.offset)).fetchall()
    return rows, pagination


def allowed_sort(value: str, options: dict[str, str], default: str) -> str:
    return value if value in options else default


def paged_search_workout_records_filtered_from_db(
    db: sqlite3.Connection,
    query: str = "",
    body_part: str = "",
    equipment: str = "",
    location_id: int | None = None,
    start_date: str = "",
    end_date: str = "",
    sort: str = "newest",
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[sqlite3.Row], object, str]:
    sort_options = {
        "newest": "s.workout_date DESC, ws.sort_order ASC, ws.id ASC",
        "oldest": "s.workout_date ASC, ws.sort_order ASC, ws.id ASC",
        "weight": "COALESCE(ws.weight, 0) DESC, s.workout_date DESC, ws.id DESC",
        "volume": "(COALESCE(ws.weight, 0) * COALESCE(ws.reps, 0)) DESC, s.workout_date DESC, ws.id DESC",
    }
    selected_sort = allowed_sort(sort, sort_options, "newest")
    where = []
    params: list[object] = []
    if query:
        where.append("(e.name LIKE ? OR ws.memo LIKE ?)")
        params.extend([f"%{query}%", f"%{query}%"])
    if body_part:
        where.append("COALESCE(NULLIF(ws.body_part, ''), '기타') = ?")
        params.append(body_part)
    if equipment:
        where.append("COALESCE(NULLIF(ws.equipment, ''), NULLIF(es.equipment, ''), '미지정') = ?")
        params.append(equipment)
    if location_id:
        where.append("s.location_id = ?")
        params.append(location_id)
    if start_date:
        where.append("s.workout_date >= ?")
        params.append(start_date)
    if end_date:
        where.append("s.workout_date <= ?")
        params.append(end_date)
    where_sql = "WHERE " + " AND ".join(where) if where else ""
    from_sql = f"""
        FROM workout_sets ws
        JOIN workout_sessions s ON s.id = ws.session_id
        JOIN exercises e ON e.id = ws.exercise_id
        LEFT JOIN exercise_settings es ON es.exercise_name = e.name
        LEFT JOIN workout_locations wl ON wl.id = s.location_id
        {where_sql}
    """
    rows, pagination = paged_rows_from_db(
        db,
        f"""
        SELECT
            s.workout_date,
            wl.name AS location_name,
            e.name AS exercise_name,
            COALESCE(NULLIF(ws.body_part, ''), '기타') AS body_part,
            COALESCE(NULLIF(ws.equipment, ''), NULLIF(es.equipment, ''), '미지정') AS equipment,
            ws.weight,
            ws.reps,
            ws.cardio_incline,
            ws.cardio_speed,
            ws.cardio_minutes,
            ws.estimated_calories,
            ws.rpe,
            ws.memo
        {from_sql}
        ORDER BY {sort_options[selected_sort]}
        """,
        f"SELECT COUNT(*) {from_sql}",
        params,
        page,
        per_page,
    )
    return rows, pagination, selected_sort


def paged_exercise_summary_from_db(
    db: sqlite3.Connection,
    sort: str = "sets",
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[sqlite3.Row], object, str]:
    sort_options = {
        "sets": "set_count DESC, rep_count DESC, e.name",
        "volume": "volume DESC, set_count DESC, e.name",
        "recent": "last_date DESC, set_count DESC, e.name",
        "name": "e.name ASC",
    }
    selected_sort = allowed_sort(sort, sort_options, "sets")
    grouped_sql = """
        FROM workout_sets ws
        JOIN exercises e ON e.id = ws.exercise_id
        JOIN workout_sessions s ON s.id = ws.session_id
        GROUP BY e.id, e.name, COALESCE(NULLIF(ws.body_part, ''), '기타')
    """
    rows, pagination = paged_rows_from_db(
        db,
        f"""
        SELECT
            e.id,
            e.name,
            COALESCE(NULLIF(ws.body_part, ''), '기타') AS body_part,
            COUNT(ws.id) AS set_count,
            COALESCE(SUM(COALESCE(ws.reps, 0)), 0) AS rep_count,
            COALESCE(SUM(COALESCE(ws.weight, 0) * COALESCE(ws.reps, 0)), 0) AS volume,
            COALESCE(SUM(COALESCE(ws.cardio_minutes, 0)), 0) AS cardio_minutes,
            COALESCE(SUM(COALESCE(ws.estimated_calories, 0)), 0) AS exercise_calories,
            MAX(s.workout_date) AS last_date
        {grouped_sql}
        ORDER BY {sort_options[selected_sort]}
        """,
        f"SELECT COUNT(*) FROM (SELECT e.id, COALESCE(NULLIF(ws.body_part, ''), '기타') AS body_part {grouped_sql})",
        [],
        page,
        per_page,
    )
    return rows, pagination, selected_sort


def list_exercise_summary_by_body_part_from_db(
    db: sqlite3.Connection,
    body_part_options: Callable[[], list[str]],
) -> dict[str, list[sqlite3.Row]]:
    rows = db.execute(
        """
        SELECT
            COALESCE(NULLIF(ws.body_part, ''), '기타') AS body_part,
            e.name,
            COUNT(ws.id) AS set_count,
            COALESCE(SUM(COALESCE(ws.reps, 0)), 0) AS rep_count,
            COALESCE(SUM(COALESCE(ws.weight, 0) * COALESCE(ws.reps, 0)), 0) AS volume,
            COALESCE(SUM(COALESCE(ws.cardio_minutes, 0)), 0) AS cardio_minutes,
            COALESCE(SUM(COALESCE(ws.estimated_calories, 0)), 0) AS exercise_calories,
            MAX(s.workout_date) AS last_date
        FROM workout_sets ws
        JOIN exercises e ON e.id = ws.exercise_id
        JOIN workout_sessions s ON s.id = ws.session_id
        GROUP BY body_part, e.name
        ORDER BY body_part, last_date DESC, set_count DESC, e.name
        """
    ).fetchall()
    grouped = {part: [] for part in body_part_options()}
    for row in rows:
        grouped.setdefault(row["body_part"] or "기타", []).append(row)
    return grouped


def equipment_scope_clause(
    scope: str,
    today: str,
    week_start_for_date: Callable[[str], str],
    shift_month: Callable[[str, int], str],
) -> tuple[str, tuple[str, ...]]:
    if scope == "week":
        return "AND s.workout_date >= ? AND s.workout_date <= ?", (week_start_for_date(today), today)
    if scope == "month":
        month_start = f"{today[:7]}-01"
        return "AND s.workout_date >= ? AND s.workout_date < ?", (month_start, shift_month(month_start, 1))
    return "", ()


def paged_equipment_summary_from_db(
    db: sqlite3.Connection,
    scope: str,
    sort: str,
    page: int,
    per_page: int,
    today: str,
    week_start_for_date: Callable[[str], str],
    shift_month: Callable[[str, int], str],
) -> tuple[list[sqlite3.Row], object, str]:
    sort_options = {
        "sets": "set_count DESC, volume DESC, last_date DESC, equipment",
        "recent": "last_date DESC, set_count DESC, equipment",
        "days": "workout_days DESC, set_count DESC, equipment",
        "volume": "volume DESC, set_count DESC, equipment",
    }
    selected_sort = allowed_sort(sort, sort_options, "sets")
    where_sql, params_tuple = equipment_scope_clause(scope, today, week_start_for_date, shift_month)
    params = list(params_tuple)
    from_sql = f"""
        FROM workout_sets ws
        JOIN workout_sessions s ON s.id = ws.session_id
        JOIN exercises e ON e.id = ws.exercise_id
        LEFT JOIN exercise_settings es ON es.exercise_name = e.name
        WHERE 1 = 1 {where_sql}
        GROUP BY COALESCE(NULLIF(ws.equipment, ''), NULLIF(es.equipment, ''), '미지정')
    """
    rows, pagination = paged_rows_from_db(
        db,
        f"""
        SELECT
            COALESCE(NULLIF(ws.equipment, ''), NULLIF(es.equipment, ''), '미지정') AS equipment,
            COUNT(ws.id) AS set_count,
            COUNT(DISTINCT s.workout_date) AS workout_days,
            COALESCE(SUM(COALESCE(ws.reps, 0)), 0) AS rep_count,
            COALESCE(SUM(COALESCE(ws.weight, 0) * COALESCE(ws.reps, 0)), 0) AS volume,
            COALESCE(SUM(COALESCE(ws.cardio_minutes, 0)), 0) AS cardio_minutes,
            COALESCE(SUM(COALESCE(ws.estimated_calories, 0)), 0) AS exercise_calories,
            MAX(s.workout_date) AS last_date
        {from_sql}
        ORDER BY {sort_options[selected_sort]}
        """,
        f"SELECT COUNT(*) FROM (SELECT COALESCE(NULLIF(ws.equipment, ''), NULLIF(es.equipment, ''), '미지정') AS equipment {from_sql})",
        params,
        page,
        per_page,
    )
    return rows, pagination, selected_sort


def paged_equipment_detail_from_db(
    db: sqlite3.Connection,
    equipment: str,
    scope: str,
    page: int,
    per_page: int,
    today: str,
    week_start_for_date: Callable[[str], str],
    shift_month: Callable[[str, int], str],
) -> tuple[list[sqlite3.Row], object]:
    where_sql, params_tuple = equipment_scope_clause(scope, today, week_start_for_date, shift_month)
    params: list[object] = [equipment, *params_tuple]
    from_sql = f"""
        FROM workout_sets ws
        JOIN workout_sessions s ON s.id = ws.session_id
        JOIN exercises e ON e.id = ws.exercise_id
        LEFT JOIN exercise_settings es ON es.exercise_name = e.name
        WHERE COALESCE(NULLIF(ws.equipment, ''), NULLIF(es.equipment, ''), '미지정') = ?
          {where_sql}
        GROUP BY COALESCE(NULLIF(ws.body_part, ''), '기타'), e.name
    """
    return paged_rows_from_db(
        db,
        f"""
        SELECT
            COALESCE(NULLIF(ws.body_part, ''), '기타') AS body_part,
            e.name AS exercise_name,
            COUNT(ws.id) AS set_count,
            COALESCE(SUM(COALESCE(ws.reps, 0)), 0) AS rep_count,
            COALESCE(SUM(COALESCE(ws.weight, 0) * COALESCE(ws.reps, 0)), 0) AS volume,
            MAX(ws.weight) AS best_weight,
            COALESCE(SUM(COALESCE(ws.cardio_minutes, 0)), 0) AS cardio_minutes,
            COALESCE(SUM(COALESCE(ws.estimated_calories, 0)), 0) AS exercise_calories,
            MAX(s.workout_date) AS last_date
        {from_sql}
        ORDER BY set_count DESC, volume DESC, last_date DESC, exercise_name
        """,
        f"SELECT COUNT(*) FROM (SELECT e.name {from_sql})",
        params,
        page,
        per_page,
    )


def paged_equipment_daily_from_db(
    db: sqlite3.Connection,
    equipment: str,
    scope: str,
    page: int,
    per_page: int,
    today: str,
    week_start_for_date: Callable[[str], str],
    shift_month: Callable[[str, int], str],
) -> tuple[list[sqlite3.Row], object]:
    where_sql, params_tuple = equipment_scope_clause(scope, today, week_start_for_date, shift_month)
    params: list[object] = [equipment, *params_tuple]
    from_sql = f"""
        FROM workout_sets ws
        JOIN workout_sessions s ON s.id = ws.session_id
        JOIN exercises e ON e.id = ws.exercise_id
        LEFT JOIN exercise_settings es ON es.exercise_name = e.name
        WHERE COALESCE(NULLIF(ws.equipment, ''), NULLIF(es.equipment, ''), '미지정') = ?
          {where_sql}
        GROUP BY s.workout_date
    """
    return paged_rows_from_db(
        db,
        f"""
        SELECT
            s.workout_date,
            COUNT(ws.id) AS set_count,
            COALESCE(SUM(COALESCE(ws.reps, 0)), 0) AS rep_count,
            COALESCE(SUM(COALESCE(ws.weight, 0) * COALESCE(ws.reps, 0)), 0) AS volume,
            COALESCE(SUM(COALESCE(ws.cardio_minutes, 0)), 0) AS cardio_minutes
        {from_sql}
        ORDER BY s.workout_date DESC
        """,
        f"SELECT COUNT(*) FROM (SELECT s.workout_date {from_sql})",
        params,
        page,
        per_page,
    )
