from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ROUND = "phase5p5_repair5g562"
ORACLE = ROOT / f"outputs/tables/{ROUND}_valid_oracle_opportunity.csv"
SUMMARY = ROOT / f"outputs/reports/{ROUND}_valid_oracle_summary.json"


def boolish(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def number(value: Any, default: float = 0.0) -> float:
    try:
        out = float(value)
    except Exception:
        return default
    return out if math.isfinite(out) else default


def claims() -> dict[str, bool]:
    return {
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "runtime_claim_allowed": False,
        "learned_runtime_policy_validated": False,
        "aaai_ready": False,
    }


def main() -> int:
    if not ORACLE.exists():
        raise SystemExit(f"missing oracle table: {ORACLE}")
    with ORACLE.open(newline="", encoding="utf-8") as handle:
        rows = [dict(row) for row in csv.DictReader(handle)]
    positives = [row for row in rows if boolish(row.get("target_theta_defined_from_real_positive_safe_set")) or int(number(row.get("safe_improving_count"), 0)) > 0]
    deltas = [number(row.get("best_positive_quality_delta_vs_g556"), math.nan) for row in positives]
    deltas = [value for value in deltas if math.isfinite(value)]
    summary = {
        "schema_version": f"{ROUND}_valid_oracle_summary_v1",
        "decision": "g562_valid_oracle_gap_present" if positives else "g562_valid_oracle_gap_absent",
        "contexts": len(rows),
        "positive_contexts": len(positives),
        "positive_context_rate": len(positives) / max(1, len(rows)),
        "mean_best_positive_quality_delta_vs_g556": sum(deltas) / len(deltas) if deltas else None,
        "min_best_positive_quality_delta_vs_g556": min(deltas) if deltas else None,
        "max_best_positive_quality_delta_vs_g556": max(deltas) if deltas else None,
        **claims(),
    }
    SUMMARY.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
