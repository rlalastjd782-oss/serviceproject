from __future__ import annotations


def estimate_cardio_met(speed: float | None, incline: float | None) -> float:
    speed_value = float(speed or 0)
    incline_value = max(0.0, float(incline or 0))
    if speed_value >= 8.0:
        base_met = 9.0
    elif speed_value >= 6.5:
        base_met = 7.0
    elif speed_value >= 5.0:
        base_met = 4.8
    else:
        base_met = 3.5
    return min(12.0, base_met + (incline_value * 0.12))


def estimate_exercise_calories_from_weight(
    body_part: str,
    cardio_incline: float | None,
    cardio_speed: float | None,
    cardio_minutes: float | None,
    body_weight: float,
) -> float | None:
    if body_part != "유산소" or not cardio_minutes:
        return None
    met = estimate_cardio_met(cardio_speed, cardio_incline)
    return round(met * body_weight * float(cardio_minutes) / 60)
