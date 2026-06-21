"""Staged scaling helpers for G5.65."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

import numpy as np


def read_rows(path: str | Path) -> list[dict[str, str]]:
    p = Path(path)
    if not p.exists():
        return []
    with p.open(newline="", encoding="utf-8") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def number(value: Any, default: float = 0.0) -> float:
    try:
        out = float(value)
    except Exception:
        return default
    return out if np.isfinite(out) else default


def select_top_rich_methods(rows: list[dict[str, Any]], *, top_k: int = 2) -> list[str]:
    scores: list[tuple[float, float, str]] = []
    for method in sorted({str(row.get("model_kind", "")).upper() for row in rows if str(row.get("model_kind", "")).upper().startswith("E")}):
        method_rows = [row for row in rows if str(row.get("model_kind", "")).upper() == method]
        all_rows = [row for row in method_rows if str(row.get("size_label")) == "all"]
        target = all_rows or method_rows
        if not target:
            continue
        median_risk = float(np.median([number(row.get("validation_risk"), 1.0e9) for row in target]))
        first_rows = [row for row in method_rows if str(row.get("size_label")) not in {"all", ""}]
        first_risk = float(np.median([number(row.get("validation_risk"), 1.0e9) for row in first_rows])) if first_rows else median_risk
        scores.append((median_risk, median_risk - first_risk, method))
    return [method for _risk, _slope, method in sorted(scores)[:top_k]]
