"""Audit local Repair5G.5.57 final artifacts before committing and pushing.

This verifier is intentionally conservative: it treats missing final decision
artifacts, underpowered/top-up decisions, opened runtime/Phase6/AAAI claims, or
a baseline other than g556_c063174 as blockers for the user's requested final
push.  It does not generate results; it only checks evidence already pulled
back from the remote run.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))
else:  # pragma: no cover
    ROOT = Path(__file__).resolve().parents[1]

from repair5g557_common import (  # noqa: E402
    BLIND_SUMMARY,
    BLIND_PLAN_SUMMARY,
    CONTROLS_SUMMARY,
    CONTEXT_SUMMARY,
    DATASET_SUMMARY,
    DECISION_SUMMARY,
    GCST_SUMMARY,
    GRAPH_SUMMARY,
    LABEL_PLAN_SUMMARY,
    LABEL_SUMMARY,
    LITERATURE_SUMMARY,
    MIN_BLIND_ROWS,
    MIN_CONTEXTS,
    MIN_PRIMARY_ROWS,
    MIN_SAME_CONTEXT_ROWS,
    MIN_STAGE1_ROWS,
    MIN_STAGE2_ROWS,
    MIN_TOTAL_ROWS,
    MODEL_ABLATION_SUMMARY,
    POLICY_SUMMARY,
    PROBE_PLAN_SUMMARY,
    PROBE_SUMMARY,
    PRIMARY_BASELINE_ID,
    STAGE1_PLAN_SUMMARY,
    STAGE1_SUMMARY,
    STAGE2_PLAN_SUMMARY,
    STAGE2_SUMMARY,
    THETA_SUMMARY,
    TTGT_SUMMARY,
    TRAFFIC_SUMMARY,
    VERIFY_SUMMARY,
    resolve,
)


REQUIRED_SUMMARIES = [
    VERIFY_SUMMARY,
    LITERATURE_SUMMARY,
    CONTEXT_SUMMARY,
    GRAPH_SUMMARY,
    TRAFFIC_SUMMARY,
    PROBE_PLAN_SUMMARY,
    PROBE_SUMMARY,
    THETA_SUMMARY,
    LABEL_PLAN_SUMMARY,
    LABEL_SUMMARY,
    DATASET_SUMMARY,
    TTGT_SUMMARY,
    GCST_SUMMARY,
    CONTROLS_SUMMARY,
    MODEL_ABLATION_SUMMARY,
    POLICY_SUMMARY,
    STAGE1_PLAN_SUMMARY,
    STAGE1_SUMMARY,
    STAGE2_PLAN_SUMMARY,
    STAGE2_SUMMARY,
    BLIND_PLAN_SUMMARY,
    BLIND_SUMMARY,
    DECISION_SUMMARY,
    "outputs/reports/phase5p5_repair5g557_remote_run_provenance_summary.json",
    "outputs/reports/phase5p5_repair5g557_compact_bundle_manifest.json",
]

CONTINUE_DECISIONS = {
    "g557_context_bank_underpowered_continue",
    "g557_label_matrix_underpowered_continue_topup",
    "g557_dataset_underpowered_continue_topup",
}

STATIC_CLAIM_KEYS = {
    "dynamic_policy": False,
    "checkpoint_policy": False,
    "runtime_claim_allowed": False,
    "learned_runtime_policy_validated": False,
    "phase5p5_allowed": False,
    "phase6_allowed": False,
    "aaai_ready": False,
}

TERMINAL_DECISIONS = {
    "g557_g556_baseline_not_verified_stop",
    "g557_gcst_offline_not_better_than_controls_exploratory_only",
    "g557_stage1_regressed_stop",
    "g557_stage2_heldout_failed_keep_g556",
    "g557_blind_failed_keep_g556",
    "g557_gcst_strict_blind_passed_keep_claims_closed",
    "g557_controlled_regression_candidate_only_not_promoted",
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary-json", type=Path, default=Path("outputs/reports/phase5p5_repair5g557_final_artifact_audit_summary.json"))
    parser.add_argument("--allow-terminal-failure", action="store_true", default=True)
    parser.add_argument("--require-strict-pass", action="store_true")
    return parser.parse_args(argv)


def load_json(rel_path: str) -> dict[str, Any]:
    path = resolve(rel_path)
    if not path.exists():
        raise FileNotFoundError(rel_path)
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{rel_path} is not a JSON object")
    return data


def as_int(value: Any) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def add_check(checks: list[dict[str, Any]], name: str, passed: bool, detail: str) -> None:
    checks.append({"name": name, "passed": bool(passed), "detail": detail})


def check_stage_floor(
    checks: list[dict[str, Any]],
    summary: dict[str, Any],
    field: str,
    minimum: int,
    prefix: str,
) -> bool:
    rows = as_int(summary.get(field))
    passed = rows >= minimum
    add_check(checks, f"{prefix}_rows_min", passed, f"{rows} >= {minimum}")
    return passed


def check_gate_passed(
    checks: list[dict[str, Any]],
    summary: dict[str, Any],
    prefix: str,
    expected: bool,
) -> bool:
    passed = summary.get("gate_passed") is expected
    add_check(checks, f"{prefix}_gate_{'passed' if expected else 'failed'}", passed, f"value={summary.get('gate_passed')!r}")
    return passed


def add_decision_specific_checks(
    checks: list[dict[str, Any]],
    decision_label: str,
    loaded: dict[str, dict[str, Any]],
    require_strict_pass: bool,
) -> None:
    gcst = loaded.get(GCST_SUMMARY, {})
    stage1 = loaded.get(STAGE1_SUMMARY, {})
    stage2 = loaded.get(STAGE2_SUMMARY, {})
    blind = loaded.get(BLIND_SUMMARY, {})

    add_check(
        checks,
        "decision_known_terminal_or_continue",
        decision_label in TERMINAL_DECISIONS or decision_label in CONTINUE_DECISIONS,
        decision_label or "missing decision",
    )
    add_check(
        checks,
        "decision_terminal_for_push",
        decision_label in TERMINAL_DECISIONS,
        decision_label or "missing decision",
    )

    if decision_label == "g557_gcst_offline_not_better_than_controls_exploratory_only":
        add_check(
            checks,
            "offline_gcst_gate_failed_for_exploratory_decision",
            gcst.get("offline_generator_gate_passed") is False,
            f"value={gcst.get('offline_generator_gate_passed')!r}",
        )
        return

    if decision_label in {
        "g557_stage1_regressed_stop",
        "g557_stage2_heldout_failed_keep_g556",
        "g557_blind_failed_keep_g556",
        "g557_gcst_strict_blind_passed_keep_claims_closed",
        "g557_controlled_regression_candidate_only_not_promoted",
    }:
        check_stage_floor(checks, stage1, "stage1_solver_rows", MIN_STAGE1_ROWS, "stage1")

    if decision_label == "g557_stage1_regressed_stop":
        regressions = as_int(stage1.get("success_regression_count_vs_g556_c063174"))
        add_check(checks, "stage1_regression_stop_has_regressions", regressions > 5, f"{regressions} > 5")
        return

    if decision_label in {
        "g557_stage2_heldout_failed_keep_g556",
        "g557_blind_failed_keep_g556",
        "g557_gcst_strict_blind_passed_keep_claims_closed",
        "g557_controlled_regression_candidate_only_not_promoted",
    }:
        check_gate_passed(checks, stage1, "stage1", True)
        check_stage_floor(checks, stage2, "stage2_solver_rows", MIN_STAGE2_ROWS, "stage2")

    if decision_label == "g557_stage2_heldout_failed_keep_g556":
        check_gate_passed(checks, stage2, "stage2", False)
        return

    if decision_label in {
        "g557_blind_failed_keep_g556",
        "g557_gcst_strict_blind_passed_keep_claims_closed",
        "g557_controlled_regression_candidate_only_not_promoted",
    }:
        check_gate_passed(checks, stage2, "stage2", True)
        check_stage_floor(checks, blind, "blind_solver_rows", MIN_BLIND_ROWS, "blind")

    strict_label = decision_label == "g557_gcst_strict_blind_passed_keep_claims_closed"
    if decision_label == "g557_blind_failed_keep_g556":
        check_gate_passed(checks, blind, "blind", False)
    elif strict_label or require_strict_pass:
        check_gate_passed(checks, blind, "blind", True)


def audit(require_strict_pass: bool = False) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    loaded: dict[str, dict[str, Any]] = {}
    for rel in REQUIRED_SUMMARIES:
        try:
            loaded[rel] = load_json(rel)
            add_check(checks, f"summary_present:{rel}", True, "parsed JSON object")
        except Exception as exc:
            add_check(checks, f"summary_present:{rel}", False, str(exc))

    decision = loaded.get(DECISION_SUMMARY, {})
    decision_label = str(decision.get("decision", ""))
    add_check(checks, "decision_present", bool(decision_label), decision_label or "missing decision")
    add_check(
        checks,
        "decision_not_continue_topup",
        decision_label not in CONTINUE_DECISIONS,
        decision_label or "missing decision",
    )
    add_decision_specific_checks(checks, decision_label, loaded, require_strict_pass)
    add_check(
        checks,
        "primary_baseline_g556_c063174",
        decision.get("primary_baseline") == PRIMARY_BASELINE_ID,
        str(decision.get("primary_baseline")),
    )
    for key, expected in STATIC_CLAIM_KEYS.items():
        add_check(checks, f"claim_closed:{key}", decision.get(key) is expected, f"value={decision.get(key)!r}")

    context_horizons = as_int(decision.get("context_horizons"))
    primary_rows = as_int(decision.get("primary_row_level_examples_vs_g556"))
    total_rows = as_int(decision.get("total_row_level_examples"))
    label = loaded.get(LABEL_SUMMARY, {})
    same_context_rows = as_int(label.get("same_context_candidate_rows"))
    add_check(checks, "context_bank_min_contexts", context_horizons >= MIN_CONTEXTS, f"{context_horizons} >= {MIN_CONTEXTS}")
    add_check(checks, "label_primary_rows_min", primary_rows >= MIN_PRIMARY_ROWS, f"{primary_rows} >= {MIN_PRIMARY_ROWS}")
    add_check(checks, "label_total_rows_min", total_rows >= MIN_TOTAL_ROWS, f"{total_rows} >= {MIN_TOTAL_ROWS}")
    add_check(checks, "label_same_context_rows_min", same_context_rows >= MIN_SAME_CONTEXT_ROWS, f"{same_context_rows} >= {MIN_SAME_CONTEXT_ROWS}")

    strict_passed = decision.get("strict_blind_passed") is True
    if require_strict_pass or strict_passed:
        add_check(checks, "strict_blind_passed", strict_passed, f"value={decision.get('strict_blind_passed')!r}")
        add_check(checks, "stage1_rows_min", as_int(decision.get("stage1_solver_rows")) >= MIN_STAGE1_ROWS, str(decision.get("stage1_solver_rows")))
        add_check(checks, "stage2_rows_min", as_int(decision.get("stage2_solver_rows")) >= MIN_STAGE2_ROWS, str(decision.get("stage2_solver_rows")))
        add_check(checks, "blind_rows_min", as_int(decision.get("blind_solver_rows")) >= MIN_BLIND_ROWS, str(decision.get("blind_solver_rows")))
        add_check(checks, "beats_map_family_lookup", decision.get("beats_map_family_lookup") is True, str(decision.get("beats_map_family_lookup")))
        add_check(checks, "beats_tabular_only_control", decision.get("beats_tabular_only_control") is True, str(decision.get("beats_tabular_only_control")))
        add_check(checks, "success_regressions_zero", as_int(decision.get("success_regressions_vs_g556")) == 0, str(decision.get("success_regressions_vs_g556")))

    compact_manifest = loaded.get("outputs/reports/phase5p5_repair5g557_compact_bundle_manifest.json", {})
    selected_count = as_int(compact_manifest.get("selected_file_count"))
    add_check(checks, "compact_bundle_manifest_selected_files", selected_count > 0, f"selected_file_count={selected_count}")
    if isinstance(compact_manifest.get("files"), list):
        bad_files = [
            str(row.get("path", ""))
            for row in compact_manifest["files"]
            if row.get("selected")
            and (
                "/logs/" in str(row.get("path", "")).lower()
                or str(row.get("path", "")).lower().startswith("outputs/logs/")
                or "/tmp/" in str(row.get("path", "")).lower()
                or str(row.get("path", "")).lower().startswith("outputs/tmp/")
                or "/raw/" in str(row.get("path", "")).lower()
                or str(row.get("path", "")).lower().endswith(".raw.csv")
                or str(row.get("path", "")).lower().endswith(".pt")
                or str(row.get("path", "")).lower().endswith(".pth")
                or str(row.get("path", "")).lower().endswith(".ckpt")
                or str(row.get("path", "")).lower().endswith(".tar.gz")
                or str(row.get("path", "")).lower().endswith(".zip")
            )
        ]
        add_check(checks, "compact_bundle_excludes_raw_large_artifacts", not bad_files, ", ".join(bad_files[:5]) or "no selected raw/log/tmp/archive/checkpoint artifacts")

    failed = [check for check in checks if not check["passed"]]
    return {
        "schema_version": "phase5p5_repair5g557_final_artifact_audit_summary_v1",
        "passed": not failed,
        "decision": decision_label,
        "strict_blind_passed": strict_passed,
        "failed_count": len(failed),
        "checks": checks,
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    summary = audit(require_strict_pass=args.require_strict_pass)
    path = resolve(args.summary_json)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"passed": summary["passed"], "decision": summary["decision"], "failed_count": summary["failed_count"]}, sort_keys=True))
    return 0 if summary["passed"] else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
