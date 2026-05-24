from __future__ import annotations


def value_at(values: list[str], index: int) -> str:
    if index >= len(values):
        return ""
    return values[index] or ""


def parse_float(value: str | None) -> float | None:
    if value is None or value.strip() == "":
        return None
    try:
        return float(value)
    except ValueError:
        return None


def parse_int(value: str | None) -> int | None:
    if value is None or value.strip() == "":
        return None
    try:
        return int(value)
    except ValueError:
        return None


def parse_duration_seconds(hours: str | None, minutes: str | None, seconds: str | None = None) -> int:
    hour_value = parse_int(hours) or 0
    minute_value = parse_int(minutes) or 0
    second_value = parse_int(seconds) or 0
    return max(0, hour_value * 3600 + minute_value * 60 + second_value)


def format_duration(seconds: int | float | None) -> str:
    total_seconds = max(0, int(seconds or 0))
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    remaining_seconds = total_seconds % 60
    if hours:
        return f"{hours}시간 {minutes:02d}분 {remaining_seconds:02d}초"
    if minutes:
        return f"{minutes}분 {remaining_seconds:02d}초"
    return f"{remaining_seconds}초"


def duration_hours(seconds: int | float | None) -> int:
    return max(0, int(seconds or 0)) // 3600


def duration_minutes(seconds: int | float | None) -> int:
    return (max(0, int(seconds or 0)) % 3600) // 60
