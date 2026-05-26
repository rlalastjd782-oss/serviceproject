DEFAULT_BODY_WEIGHT_KG = 70.0
DEFAULT_DAILY_CALORIES = 2200
DEFAULT_REST_SECONDS = 90
DEFAULT_SET_COUNT = 3
DEFAULT_WEIGHT_PLACEHOLDER = 60
DEFAULT_REPS_PLACEHOLDER = 10
REST_TIMER_PRESETS = [60, 90, 120]
SUMMARY_DAY_OPTIONS = [7, 14, 30, 60, 90]
SET_TYPE_OPTIONS = ["본세트", "워밍업", "드롭세트", "실패"]

BODY_PARTS = ["하체", "가슴", "팔", "등", "어깨", "유산소", "기타"]

BODY_PART_CLASSES = {
    "하체": "body-part-legs",
    "가슴": "body-part-chest",
    "팔": "body-part-arms",
    "등": "body-part-back",
    "어깨": "body-part-shoulders",
    "유산소": "body-part-cardio",
    "기타": "body-part-other",
}

MEAL_TYPE_CLASSES = {
    "아침": "meal-type-breakfast",
    "점심": "meal-type-lunch",
    "저녁": "meal-type-dinner",
    "간식": "meal-type-snack",
    "기타": "meal-type-other",
}

EQUIPMENT_OPTIONS = ["바벨", "덤벨", "머신", "케이블", "프리웨이트", "맨몸", "유산소기구"]

EQUIPMENT_ALIASES = {
    "스미스 머신": "머신",
    "스미스머신": "머신",
    "런닝머신": "유산소기구",
    "러닝머신": "유산소기구",
    "트레드밀": "유산소기구",
    "사이클": "유산소기구",
    "바이크": "유산소기구",
}


def normalize_equipment_category(value: str | None) -> str:
    clean = (value or "").strip()
    if not clean:
        return ""
    if clean in EQUIPMENT_OPTIONS:
        return clean
    if clean in EQUIPMENT_ALIASES:
        return EQUIPMENT_ALIASES[clean]
    for keyword, category in [
        ("케이블", "케이블"),
        ("덤벨", "덤벨"),
        ("바벨", "바벨"),
        ("프리웨이트", "프리웨이트"),
        ("머신", "머신"),
        ("트레드밀", "유산소기구"),
        ("런닝", "유산소기구"),
        ("러닝", "유산소기구"),
        ("사이클", "유산소기구"),
        ("맨몸", "맨몸"),
    ]:
        if keyword in clean:
            return category
    return ""

DEFAULT_PROGRAMS = {
    "5x5": [
        ("하체", "스쿼트", "본세트", None, 5),
        ("가슴", "벤치프레스", "본세트", None, 5),
        ("등", "바벨로우", "본세트", None, 5),
        ("어깨", "오버헤드프레스", "본세트", None, 5),
        ("등", "데드리프트", "본세트", None, 5),
    ],
    "상체/하체": [
        ("가슴", "벤치프레스", "본세트", None, 8),
        ("등", "랫풀다운", "본세트", None, 10),
        ("하체", "스쿼트", "본세트", None, 8),
        ("하체", "레그프레스", "본세트", None, 12),
    ],
    "푸쉬/풀/레그": [
        ("가슴", "벤치프레스", "본세트", None, 8),
        ("어깨", "숄더프레스", "본세트", None, 10),
        ("등", "시티드로우", "본세트", None, 10),
        ("팔", "바벨컬", "본세트", None, 12),
        ("하체", "스쿼트", "본세트", None, 8),
    ],
}

RECOMMENDED_EXERCISE_MAP = {
    "하체": ["스쿼트", "레그프레스"],
    "등": ["랫풀다운", "시티드로우"],
    "어깨": ["숄더프레스", "사이드레터럴"],
    "가슴": ["벤치프레스", "인클라인프레스"],
    "팔": ["바벨컬", "케이블푸시다운"],
    "유산소": ["트레드밀 30분"],
}
