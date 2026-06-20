from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ROUND = "phase5p5_repair5g562"
ARCH = ROOT / f"outputs/tables/{ROUND}_architecture_matrix.csv"
SUMMARY = ROOT / f"outputs/reports/{ROUND}_actor_export_summary.json"
EXPORT = ROOT / "artifacts/models/gcst/g562_exported_actor.pt"


def claims() -> dict[str, bool]:
    return {
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "runtime_claim_allowed": False,
        "learned_runtime_policy_validated": False,
        "aaai_ready": False,
    }


def number(value: Any, default: float = 999.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def main() -> int:
    if not ARCH.exists():
        raise SystemExit(f"missing actor matrix: {ARCH}")
    with ARCH.open(newline="", encoding="utf-8") as handle:
        rows = [dict(row) for row in csv.DictReader(handle)]
    candidates = [row for row in rows if str(row.get("rich_attention_actor", "")).lower() == "true" and row.get("model_path")]
    if not candidates:
        candidates = [row for row in rows if row.get("model_path")]
    if not candidates:
        raise SystemExit("no actor checkpoint rows available for export")
    candidates.sort(key=lambda row: (number(row.get("validation_real_label_normalized_l1")), str(row.get("variant_id")), str(row.get("seed"))))
    selected = candidates[0]
    src = ROOT / selected["model_path"]
    if not src.exists():
        raise SystemExit(f"missing selected checkpoint: {src}")
    EXPORT.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, EXPORT)
    summary = {
        "schema_version": f"{ROUND}_actor_export_summary_v1",
        "decision": "g562_actor_exported_one_forward_one_theta",
        "selected_variant_id": selected.get("variant_id", ""),
        "selected_seed": selected.get("seed", ""),
        "selected_model_path": selected.get("model_path", ""),
        "export_path": str(EXPORT.relative_to(ROOT)).replace("\\", "/"),
        "critic_included_for_export": False,
        "codebook_included_for_export": False,
        "one_forward_one_theta": True,
        "theta_fixed_for_run": True,
        **claims(),
    }
    SUMMARY.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
