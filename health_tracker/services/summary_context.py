from __future__ import annotations


def selected_body_part_filter(args, body_parts: list[str]) -> str:
    selected = args.get("part", "").strip()
    return selected if selected in body_parts else ""


def filter_body_part_summary(rows, selected_part: str):
    if not selected_part:
        return rows
    return [row for row in rows if row["body_part"] == selected_part]


def build_daily_summary_context(args, deps: dict[str, object]) -> dict[str, object]:
    page, per_page = deps["configured_page_params"](args)
    days = deps["normalize_summary_days"](args.get("days"))
    daily_sort = args.get("sort", "newest")
    daily_rows = deps["list_daily_summary"](days=days)
    if daily_sort == "oldest":
        daily_rows = list(reversed(daily_rows))
    else:
        daily_sort = "newest"
    daily_pagination = deps["build_pagination"](len(daily_rows), page, per_page)
    body_parts = deps["body_part_options"]()
    selected_part = selected_body_part_filter(args, body_parts)
    return {
        "page_title": "일간 집계",
        "page_kicker": "Daily",
        "table_kind": "daily",
        "daily_summary": daily_rows[daily_pagination.offset : daily_pagination.offset + daily_pagination.per_page],
        "daily_pagination": daily_pagination,
        "daily_sort": daily_sort,
        "selected_days": days,
        "body_part_summary": filter_body_part_summary(deps["list_body_part_summary"]("daily", limit=120), selected_part),
        "body_parts": body_parts,
        "selected_body_part": selected_part,
        "active_page": "daily",
    }


def build_weekly_summary_context(args, deps: dict[str, object]) -> dict[str, object]:
    page, per_page = deps["configured_page_params"](args)
    period_sort = args.get("sort", "newest")
    selected_week = deps["normalize_date"](args.get("week"))
    week_start = deps["week_start_for_date"](selected_week)
    week_end = deps["shift_date"](week_start, 6)
    chart_rows = deps["list_daily_summary"](start_date=week_start, end_date=week_end)
    all_period_rows = deps["list_weekly_summary"](limit=240)
    if period_sort == "oldest":
        all_period_rows = list(reversed(all_period_rows))
    elif period_sort == "volume":
        all_period_rows = sorted(all_period_rows, key=lambda row: float(row["volume"] or 0), reverse=True)
    else:
        period_sort = "newest"
    period_pagination = deps["build_pagination"](len(all_period_rows), page, per_page)
    period_rows = all_period_rows[period_pagination.offset : period_pagination.offset + period_pagination.per_page]
    return {
        "page_title": "주간 집계",
        "page_kicker": "Weekly",
        "table_kind": "period",
        "period_rows": period_rows,
        "period_pagination": period_pagination,
        "period_sort": period_sort,
        "period_label": "기간",
        "chart_items": deps["build_daily_chart"](chart_rows),
        "chart_title": "일별 추이",
        "chart_note": "선택한 주를 일별로 표시합니다.",
        "body_part_summary": deps["list_body_part_summary"]("weekly", date_text=week_start),
        "body_part_details": deps["list_weekly_body_part_details"](week_start),
        "weekly_report": deps["build_weekly_report"](week_start),
        "weekly_rule_report": deps["build_weekly_rule_report"](week_start),
        "weekly_goals": deps["get_goal_progress"](week_start),
        "weekly_goal_insights": deps["build_goal_insights"]("weekly", week_start),
        "rpe_report": deps["build_rpe_report"]("weekly", week_start),
        "report_insights": deps["build_period_insights"]("weekly", week_start),
        "period_highlights": deps["build_period_highlights"]("weekly", week_start),
        "balance_warnings": deps["list_balance_warnings"]("weekly", week_start),
        "nutrition_training_link": deps["build_nutrition_training_link"]("weekly", week_start),
        "selected_week": week_start,
        "prev_week": deps["shift_date"](week_start, -7),
        "next_week": deps["shift_date"](week_start, 7),
        "active_page": "weekly",
    }


def build_monthly_summary_context(args, deps: dict[str, object]) -> dict[str, object]:
    page, per_page = deps["configured_page_params"](args)
    period_sort = args.get("sort", "newest")
    selected_month = args.get("month") or deps["current_local_date"]()[:7]
    month_start = deps["normalize_month"](selected_month)
    all_period_rows = deps["list_weekly_summary"](month_start=month_start, limit=12)
    if period_sort == "oldest":
        all_period_rows = list(reversed(all_period_rows))
    elif period_sort == "volume":
        all_period_rows = sorted(all_period_rows, key=lambda row: float(row["volume"] or 0), reverse=True)
    else:
        period_sort = "newest"
    period_pagination = deps["build_pagination"](len(all_period_rows), page, per_page)
    period_rows = all_period_rows[period_pagination.offset : period_pagination.offset + period_pagination.per_page]
    return {
        "page_title": "월간 집계",
        "page_kicker": "Monthly",
        "table_kind": "period",
        "period_rows": period_rows,
        "period_pagination": period_pagination,
        "period_sort": period_sort,
        "period_label": "기간",
        "chart_items": deps["build_period_chart"](period_rows),
        "chart_title": "주간별 추이",
        "chart_note": "선택한 월을 주간 단위로 표시합니다.",
        "body_part_summary": deps["list_body_part_summary"]("monthly", date_text=month_start),
        "monthly_report": deps["build_monthly_report"](month_start),
        "body_monthly_report": deps["build_body_monthly_report"](month_start),
        "body_metric_trend": deps["list_body_metric_trend"](month_start),
        "monthly_goals": deps["get_goal_progress"](month_start),
        "monthly_goal_insights": deps["build_goal_insights"]("monthly", month_start),
        "report_insights": deps["build_period_insights"]("monthly", month_start),
        "period_highlights": deps["build_period_highlights"]("monthly", month_start),
        "nutrition_training_link": deps["build_nutrition_training_link"]("monthly", month_start),
        "selected_month": month_start[:7],
        "prev_month": deps["shift_month"](month_start, -1)[:7],
        "next_month": deps["shift_month"](month_start, 1)[:7],
        "active_page": "monthly",
    }
