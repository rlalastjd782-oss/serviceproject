from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from health_tracker.config import APP_TIMEZONE


def current_local_date() -> str:
    try:
        app_timezone = ZoneInfo(APP_TIMEZONE)
    except ZoneInfoNotFoundError:
        app_timezone = timezone(timedelta(hours=9), name="KST")
    return datetime.now(app_timezone).strftime("%Y-%m-%d")


def normalize_date(date_text: str | None, max_future_days: int = 31) -> str:
    today_text = current_local_date()
    try:
        date_value = datetime.strptime((date_text or "").strip(), "%Y-%m-%d")
    except ValueError:
        return today_text

    today_value = datetime.strptime(today_text, "%Y-%m-%d")
    if date_value > today_value + timedelta(days=max_future_days):
        return today_text
    return date_value.strftime("%Y-%m-%d")


def normalize_optional_date(date_text: str | None, max_future_days: int = 31) -> str:
    if not (date_text or "").strip():
        return ""
    return normalize_date(date_text, max_future_days=max_future_days)


def shift_date(date_text: str, days: int) -> str:
    return (datetime.strptime(date_text, "%Y-%m-%d") + timedelta(days=days)).strftime("%Y-%m-%d")


def week_start_for_date(date_text: str) -> str:
    try:
        date_value = datetime.strptime(date_text, "%Y-%m-%d")
    except ValueError:
        date_value = datetime.strptime(current_local_date(), "%Y-%m-%d")
    return (date_value - timedelta(days=date_value.weekday())).strftime("%Y-%m-%d")


def meal_week_label(week_start: str) -> str:
    date_value = datetime.strptime(shift_date(week_start, 6), "%Y-%m-%d")
    week_of_month = ((date_value.day - 1) // 7) + 1
    return f"{date_value.month}월 {week_of_month}주차"


def meal_day_label(date_text: str) -> str:
    date_value = datetime.strptime(date_text, "%Y-%m-%d")
    weekdays = ["월", "화", "수", "목", "금", "토", "일"]
    return f"{date_value.month}/{date_value.day}({weekdays[date_value.weekday()]})"


def normalize_month(month_text: str) -> str:
    today_month = datetime.strptime(current_local_date(), "%Y-%m-%d").replace(day=1)
    try:
        if len(month_text) == 7:
            month_value = datetime.strptime(f"{month_text}-01", "%Y-%m-%d")
        else:
            month_value = datetime.strptime(month_text, "%Y-%m-%d").replace(day=1)
    except ValueError:
        return today_month.strftime("%Y-%m-01")
    if month_value > today_month + timedelta(days=62):
        return today_month.strftime("%Y-%m-01")
    return month_value.strftime("%Y-%m-%d")


def shift_month(month_start: str, months: int) -> str:
    date_value = datetime.strptime(normalize_month(month_start), "%Y-%m-%d")
    month_index = date_value.month - 1 + months
    year = date_value.year + month_index // 12
    month = month_index % 12 + 1
    return f"{year:04d}-{month:02d}-01"
