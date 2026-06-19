"""Active acquisition scoring for Label-v5 top-up rounds."""

from __future__ import annotations

from typing import Any


def acquisition_score(row: dict[str, Any]) -> float:
    uncertainty = 1.0 - abs(float(row.get("predicted_risk", 0.5)) - 0.5) * 2.0
    disagreement = abs(float(row.get("graph_score", 0.0)) - float(row.get("tabular_score", 0.0)))
    utility = max(0.0, -float(row.get("predicted_quality_delta", 0.0)))
    rarity = float(row.get("morphology_rarity", 0.0))
    return 0.40 * uncertainty + 0.25 * disagreement + 0.25 * utility + 0.10 * rarity


def select_acquisition_rows(rows: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    ranked = sorted(rows, key=acquisition_score, reverse=True)
    return [{**row, "acquisition_score": acquisition_score(row)} for row in ranked[: max(0, limit)]]
