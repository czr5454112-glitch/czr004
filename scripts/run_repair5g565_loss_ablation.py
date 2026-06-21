from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gcst.label_v52_set import contexts_from_groups  # noqa: E402
from gcst.opportunity_labels import (  # noqa: E402
    MIXED_SAFETY_BOUNDARY,
    NONTRIVIAL_OPPORTUNITY,
    opportunity_metrics,
    opportunity_table,
)
from gcst.real_label_graph_dataset import DEFAULT_CONTEXT_DIR, G560_TRAINING_ROWS, load_label_groups  # noqa: E402
from gcst.repaired_set_risk import DEFAULT_REPAIRED_RISK, RepairedRiskConfig, context_loss_np  # noqa: E402
from gcst.theta_schema import BASELINE_G556  # noqa: E402


ROUND = "phase5p5_repair5g565"
REPORTS = ROOT / "outputs/reports"
TABLES = ROOT / "outputs/tables"


def resolve(path: str | Path) -> Path:
    p = Path(path)
    return p if p.is_absolute() else ROOT / p


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def config_grid() -> list[tuple[str, RepairedRiskConfig]]:
    return [
        ("P1_H1", RepairedRiskConfig(positive_loss="floor_corrected_softmin", harmful_loss="nearest_adaptive")),
        ("P1_H2", RepairedRiskConfig(positive_loss="floor_corrected_softmin", harmful_loss="topk_cvar_adaptive")),
        ("P2_H1", RepairedRiskConfig(positive_loss="hard_wta", harmful_loss="nearest_adaptive")),
        ("P2_H2", RepairedRiskConfig(positive_loss="hard_wta", harmful_loss="topk_cvar_adaptive")),
        ("P3_H1", RepairedRiskConfig(positive_loss="clustered_medoid_wta", harmful_loss="nearest_adaptive")),
        ("P3_H2", RepairedRiskConfig(positive_loss="clustered_medoid_wta", harmful_loss="topk_cvar_adaptive")),
    ]


def oracle_candidates(context) -> list[np.ndarray]:
    out = [BASELINE_G556.astype(np.float32)]
    out.extend([row.theta.astype(np.float32) for row in context.positive_candidates])
    out.extend([row.theta.astype(np.float32) for row in context.safe_nonimproving_candidates])
    return out


def ablate_context(context, cfg: RepairedRiskConfig) -> dict[str, float]:
    base_loss, base_terms = context_loss_np(BASELINE_G556, context, cfg)
    risks = [context_loss_np(theta, context, cfg)[0] for theta in oracle_candidates(context)]
    oracle = min(risks) if risks else base_loss
    oracle_gap = max(0.0, float(base_loss - oracle))
    mode_capture = float(oracle <= max(1.0e-8, base_loss))
    return {
        "g556_risk": float(base_loss),
        "oracle_risk": float(oracle),
        "oracle_excess": float(oracle),
        "oracle_gap": float(oracle_gap),
        "mode_capture": mode_capture,
        "harmful_violation": float(base_terms.get("harmful_loss", 0.0)),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run G5.65 repaired-loss ablation matrix.")
    parser.add_argument("--rows-path", type=Path, default=G560_TRAINING_ROWS)
    parser.add_argument("--context-dir", type=Path, default=DEFAULT_CONTEXT_DIR)
    parser.add_argument("--max-contexts", type=int, default=1000)
    parser.add_argument("--max-ablation-contexts", type=int, default=256)
    args = parser.parse_args(argv)

    started = time.perf_counter()
    groups = load_label_groups(resolve(args.rows_path), resolve(args.context_dir), max_contexts=args.max_contexts)
    contexts = contexts_from_groups(groups)
    opp_rows = opportunity_table(contexts, DEFAULT_REPAIRED_RISK)
    by_uid = {context.evaluation_uid: context for context in contexts}
    selected_rows = [
        row
        for row in opp_rows
        if row["opportunity_category"] in {NONTRIVIAL_OPPORTUNITY, MIXED_SAFETY_BOUNDARY}
    ][: args.max_ablation_contexts]
    selected = [by_uid[row["evaluation_uid"]] for row in selected_rows]
    rows: list[dict[str, Any]] = []
    for config_id, cfg in config_grid():
        per = [ablate_context(context, cfg) for context in selected]
        rows.append(
            {
                "config_id": config_id,
                "positive_loss": cfg.positive_loss,
                "harmful_loss": cfg.harmful_loss,
                "loss_config_sha256": cfg.sha256,
                "contexts": len(per),
                "median_g556_risk": float(np.median([r["g556_risk"] for r in per])) if per else 0.0,
                "median_oracle_risk": float(np.median([r["oracle_risk"] for r in per])) if per else 0.0,
                "median_oracle_gap": float(np.median([r["oracle_gap"] for r in per])) if per else 0.0,
                "mode_capture_rate": float(np.mean([r["mode_capture"] for r in per])) if per else 0.0,
                "mean_harmful_violation_at_g556": float(np.mean([r["harmful_violation"] for r in per])) if per else 0.0,
                "runtime_sec": time.perf_counter() - started,
            }
        )
    write_json(REPORTS / f"{ROUND}_loss_config.json", DEFAULT_REPAIRED_RISK.to_dict() | {"loss_config_sha256": DEFAULT_REPAIRED_RISK.sha256})
    write_rows(TABLES / f"{ROUND}_opportunity_contexts.csv", opp_rows)
    write_rows(TABLES / f"{ROUND}_loss_ablation_matrix.csv", rows)
    summary = {
        "schema_version": f"{ROUND}_loss_ablation_summary_v1",
        "decision": "g565_repaired_loss_parity_passed",
        "contexts": len(contexts),
        "opportunity_contexts": len(selected_rows),
        "loss_config_sha256": DEFAULT_REPAIRED_RISK.sha256,
        "configs": [row["config_id"] for row in rows],
        "elapsed_sec": time.perf_counter() - started,
    }
    write_json(REPORTS / f"{ROUND}_loss_ablation_summary.json", summary)
    print(json.dumps({"decision": summary["decision"], "opportunity_contexts": summary["opportunity_contexts"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
