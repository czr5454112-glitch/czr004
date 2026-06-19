"""Small helpers for G5.59 multi-fidelity replay planning."""

from __future__ import annotations

from collections import defaultdict
from typing import Any


def level0_rows(instances: list[dict[str, Any]], candidates: list[dict[str, Any]], per_instance: int = 64) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for idx, inst in enumerate(instances):
        offset = (idx * per_instance) % max(1, len(candidates))
        slate = [candidates[(offset + j) % len(candidates)] for j in range(min(per_instance, len(candidates)))] if candidates else []
        for cand in slate:
            rows.append({**inst, **cand, "fidelity_level": 0, "candidate_source": cand.get("candidate_source", "codebook")})
    return rows


def promote_uncertain(rows: list[dict[str, Any]], top_n: int = 12) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row.get("instance_uid", ""))].append(row)
    promoted: list[dict[str, Any]] = []
    for _uid, group in grouped.items():
        ranked = sorted(group, key=lambda r: (float(r.get("predicted_risk", 0.5)), float(r.get("predicted_quality_delta", 0.0))))
        for row in ranked[:top_n]:
            promoted.append({**row, "fidelity_level": int(row.get("fidelity_level", 0)) + 1})
    return promoted
