from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from typing import Mapping
from urllib.parse import urlencode


PER_PAGE_OPTIONS = (10, 20, 50)
DEFAULT_PER_PAGE = 20


@dataclass(frozen=True)
class Pagination:
    page: int
    per_page: int
    total: int
    total_pages: int
    offset: int

    @property
    def has_prev(self) -> bool:
        return self.page > 1

    @property
    def has_next(self) -> bool:
        return self.page < self.total_pages


def parse_positive_int(value: object, default: int) -> int:
    try:
        parsed = int(str(value))
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def page_params(args: Mapping[str, object], default_per_page: int = DEFAULT_PER_PAGE) -> tuple[int, int]:
    page = parse_positive_int(args.get("page"), 1)
    per_page = parse_positive_int(args.get("per_page"), default_per_page)
    if per_page not in PER_PAGE_OPTIONS:
        per_page = default_per_page
    return page, per_page


def build_pagination(total: int, page: int, per_page: int) -> Pagination:
    total = max(0, int(total or 0))
    per_page = per_page if per_page in PER_PAGE_OPTIONS else DEFAULT_PER_PAGE
    total_pages = max(1, ceil(total / per_page))
    page = min(max(1, page), total_pages)
    return Pagination(page=page, per_page=per_page, total=total, total_pages=total_pages, offset=(page - 1) * per_page)


def query_url(endpoint: str, args: Mapping[str, object], **updates: object) -> str:
    values: dict[str, object] = {}
    for key, value in args.items():
        if key in updates:
            continue
        if value is not None and str(value) != "":
            values[key] = value
    for key, value in updates.items():
        if value is not None and str(value) != "":
            values[key] = value
    return f"{endpoint}?{urlencode(values, doseq=True)}" if values else endpoint
