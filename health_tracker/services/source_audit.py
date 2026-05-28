from __future__ import annotations

from pathlib import Path


SOURCE_AUDIT_LIMITS = {
    ".py": 500,
    ".js": 300,
    ".css": 700,
    ".html": 200,
}

SOURCE_AUDIT_DIRS = ("health_tracker", "static", "tests")


def list_long_source_files(base_dir: Path, limit: int = 12) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for folder in SOURCE_AUDIT_DIRS:
        root = base_dir / folder
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix not in SOURCE_AUDIT_LIMITS:
                continue
            lines = path.read_text(encoding="utf-8", errors="ignore").count("\n") + 1
            threshold = SOURCE_AUDIT_LIMITS[path.suffix]
            if lines >= threshold:
                rows.append(
                    {
                        "path": str(path.relative_to(base_dir)),
                        "lines": lines,
                        "threshold": threshold,
                    }
                )
    return sorted(rows, key=lambda item: int(item["lines"]), reverse=True)[:limit]
