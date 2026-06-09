"""Verify required G5.12/G5.13 artifacts before G5.14."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g512_common import read_csv_rows, read_json, repo_root, resolve, write_json, write_text  # noqa: E402
from repair5g514_common import G514_CLOSED_CLAIMS  # noqa: E402


REQUIRED_JSON = [
    "outputs/reports/phase5p5_repair5g512_decision_summary.json",
    "outputs/reports/phase5p5_repair5g513_decision_summary.json",
    "outputs/reports/phase5p5_repair5g513_g512_selection_audit_summary.json",
    "outputs/reports/phase5p5_repair5g513_hard_control_eval_summary.json",
    "outputs/reports/phase5p5_repair5g513_rich_context_feature_matrix_summary.json",
    "outputs/reports/phase5p5_repair5g513_static_abstention_safety_preflight_summary.json",
]

REQUIRED_CSV = [
    "outputs/tables/phase5p5_repair5g512_candidate_regret_targets.csv",
    "outputs/tables/phase5p5_repair5g512_candidate_feature_matrix_v3.csv",
    "outputs/tables/phase5p5_repair5g512_candidate_ranker_eval.csv",
    "outputs/tables/phase5p5_repair5g512_candidate_ranker_context_decisions.csv",
    "outputs/tables/phase5p5_repair5g513_g512_selection_audit.csv",
    "outputs/tables/phase5p5_repair5g513_hard_control_eval.csv",
    "outputs/tables/phase5p5_repair5g513_static_abstention_safety_preflight.csv",
]

DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g514_g513_artifact_verification.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g514_g513_artifact_verification_summary.json"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    missing: list[str] = []
    malformed: list[str] = []
    json_payloads = {}
    csv_counts = {}

    for path in REQUIRED_JSON:
        target = resolve(path, root)
        if not target.exists():
            missing.append(path)
            continue
        try:
            json_payloads[path] = read_json(target)
        except (OSError, json.JSONDecodeError) as exc:
            malformed.append(f"{path}: {exc}")

    for path in REQUIRED_CSV:
        target = resolve(path, root)
        if not target.exists():
            missing.append(path)
            continue
        try:
            csv_counts[path] = len(read_csv_rows(target))
        except OSError as exc:
            malformed.append(f"{path}: {exc}")

    g512_feature_rows = csv_counts.get("outputs/tables/phase5p5_repair5g512_candidate_feature_matrix_v3.csv", 0)
    g513_decision = json_payloads.get("outputs/reports/phase5p5_repair5g513_decision_summary.json", {}).get("decision", "")
    hard_control = json_payloads.get("outputs/reports/phase5p5_repair5g513_hard_control_eval_summary.json", {})
    rich_scan = json_payloads.get("outputs/reports/phase5p5_repair5g513_rich_context_feature_matrix_summary.json", {})

    gates = {
        "required_json_present": not any(path in missing for path in REQUIRED_JSON),
        "required_csv_present": not any(path in missing for path in REQUIRED_CSV),
        "json_and_csv_parse": not malformed,
        "g512_candidate_rows_ge_840": g512_feature_rows >= 840,
        "g513_decision_is_simple_prior_downgrade": g513_decision == "candidate_ranker_signal_reduced_to_simple_prior_continue_rich_features",
        "g513_hard_control_summary_present": bool(hard_control),
        "g513_rich_scan_present": bool(rich_scan),
    }
    decision = "g513_artifacts_verified_continue_g514" if all(gates.values()) else "missing_g513_artifacts_stop"
    summary = {
        "schema_version": "phase5p5_repair5g514_g513_artifact_verification_summary_v1",
        "decision": decision,
        "missing": missing,
        "malformed": malformed,
        "csv_counts": csv_counts,
        "g513_decision": g513_decision,
        "g513_hard_control_decision": hard_control.get("decision", ""),
        "g513_rich_scan_decision": rich_scan.get("decision", ""),
        "gates": gates,
        **G514_CLOSED_CLAIMS,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.14 G5.13 Artifact Verification\n\n"
        f"- decision: `{decision}`\n"
        f"- missing: `{missing}`\n"
        f"- malformed: `{malformed}`\n"
        f"- g512_candidate_feature_rows: `{g512_feature_rows}`\n"
        f"- g513_decision: `{g513_decision}`\n"
        f"- g513_hard_control_decision: `{hard_control.get('decision', '')}`\n"
        f"- g513_rich_scan_decision: `{rich_scan.get('decision', '')}`\n"
        f"- gates: `{gates}`\n"
        "- runtime_claim_allowed: `false`\n",
    )
    print(json.dumps({"decision": decision, "missing": len(missing), "malformed": len(malformed)}))
    return 0 if decision != "missing_g513_artifacts_stop" else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
