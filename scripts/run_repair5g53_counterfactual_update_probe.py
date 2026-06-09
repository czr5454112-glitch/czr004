"""Attempt Repair5G.5.3 counterfactual UpdateLTM probes from checkpoints."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g3_common import read_jsonl, repo_root, resolve, write_csv_rows, write_json  # noqa: E402
from repair5g51_common import write_text  # noqa: E402


DEFAULT_REPLAY_SUMMARY = "outputs/reports/phase5p5_repair5g53_checkpoint_replayability_summary.json"
DEFAULT_CHECKPOINTS = "outputs/logs/phase5p5_repair5g53_checkpoint_export/phase5p5_repair5g53_update_checkpoints.jsonl"
DEFAULT_LABELS = "outputs/tables/phase5p5_repair5g53_counterfactual_update_labels.csv"
DEFAULT_ORACLE = "outputs/tables/phase5p5_repair5g53_counterfactual_oracle_by_context.csv"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g53_counterfactual_label_report.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g53_counterfactual_label_summary.json"

CANDIDATES = [
    "repair5g2_best_frozen_static_candidate",
    "repair5g2_frozen_static_or_selector",
    "repair5g_dual_c_equiv_additive",
    "repair5g2_c_equiv_best_frozen_baseline",
    "repair5g1_shield_c100_b125_w075_d100_beta0p35_max0p75",
    "repair5g1_shield_c125_b125_w075_d095_beta0p35_max0p75",
    "additive_ltm",
]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--replayability-summary-json", type=Path, default=Path(DEFAULT_REPLAY_SUMMARY))
    parser.add_argument("--checkpoint-jsonl", type=Path, default=Path(DEFAULT_CHECKPOINTS))
    parser.add_argument("--labels-csv", type=Path, default=Path(DEFAULT_LABELS))
    parser.add_argument("--oracle-csv", type=Path, default=Path(DEFAULT_ORACLE))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    parser.add_argument("--max-checkpoints", type=int, default=500)
    return parser.parse_args(argv)


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    replay_summary = load_json(resolve(args.replayability_summary_json, root))
    replay_ok = bool(replay_summary.get("gates", {}).get("checkpoint_replayability_passed"))
    blocked_reason = str(replay_summary.get("blocked_reason") or replay_summary.get("decision") or "")
    if not replay_ok and blocked_reason:
        gap = f"checkpoint replayability blocked by {blocked_reason}"
    elif not replay_ok:
        gap = "checkpoint replayability did not pass"
    else:
        gap = "checkpoint export exists, but no CLI imports checkpoint state and runs per-candidate one-shot probes yet"
    checkpoints = read_jsonl(resolve(args.checkpoint_jsonl, root))[: max(0, int(args.max_checkpoints))] if replay_ok else []
    rows: list[dict[str, Any]] = []
    oracle_rows: list[dict[str, Any]] = []
    for index, checkpoint in enumerate(checkpoints):
        context_id = f"{checkpoint.get('map')}|a{checkpoint.get('agents')}|s{checkpoint.get('seed')}|i{checkpoint.get('iteration')}|{index}"
        for candidate in CANDIDATES:
            rows.append(
                {
                    "context_id": context_id,
                    "candidate_id": candidate,
                    "counterfactual_label_available": False,
                    "label_status": "unavailable_no_checkpoint_replay_probe_cli",
                    "success": "",
                    "ratio": "",
                    "expanded_nodes": "",
                    "low_level_pibt_calls": "",
                    "time_ms": "",
                    "feature_leakage_safe": True,
                }
            )
        oracle_rows.append(
            {
                "context_id": context_id,
                "candidate_coverage_complete": False,
                "oracle_candidate_id": "",
                "oracle_gap_over_static": "",
                "label_status": "unavailable_no_checkpoint_replay_probe_cli",
            }
        )
    write_csv_rows(resolve(args.labels_csv, root), rows)
    write_csv_rows(resolve(args.oracle_csv, root), oracle_rows)
    available = [row for row in rows if row["counterfactual_label_available"]]
    gates = {
        "label_rows_gt_0": len(rows) > 0,
        "available_label_rows_gt_0": len(available) > 0,
        "candidate_coverage_complete": False,
        "oracle_gap_over_static_measured": False,
        "feature_leakage_audit_passes": all(row["feature_leakage_safe"] for row in rows) if rows else False,
        "runtime_feature_availability_audit_passes": False,
        "labels_are_contextual_not_run_level": bool(rows),
    }
    gates["counterfactual_labels_passed"] = all(
        [
            gates["available_label_rows_gt_0"],
            gates["candidate_coverage_complete"],
            gates["oracle_gap_over_static_measured"],
            gates["feature_leakage_audit_passes"],
            gates["runtime_feature_availability_audit_passes"],
            gates["labels_are_contextual_not_run_level"],
        ]
    )
    summary = {
        "schema_version": "phase5p5_repair5g53_counterfactual_label_summary_v1",
        "checkpoint_rows_used": len(checkpoints),
        "label_rows": len(rows),
        "available_label_rows": len(available),
        "candidate_count": len(CANDIDATES),
        "gates": gates,
        "gap": gap,
        "decision": "counterfactual_labels_available_continue_g6_design" if gates["counterfactual_labels_passed"] else "counterfactual_labels_unavailable",
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "aaai_ready": False,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.3 Counterfactual UpdateLTM Labels\n\n"
        f"- checkpoint_rows_used: `{len(checkpoints)}`\n"
        f"- label_rows: `{len(rows)}`\n"
        f"- available_label_rows: `{len(available)}`\n"
        f"- counterfactual_labels_passed: `{gates['counterfactual_labels_passed']}`\n"
        f"- decision: `{summary['decision']}`\n\n"
        f"Gap: {gap}.\n\n"
        "No labels are inferred from final full-run outcomes.\n",
    )
    print(json.dumps({"decision": summary["decision"], "available_label_rows": len(available)}))
    return 0 if gates["counterfactual_labels_passed"] else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
