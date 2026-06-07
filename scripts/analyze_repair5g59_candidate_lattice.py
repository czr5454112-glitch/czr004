"""Analyze the Repair5G.5.9 goal-aware dual-channel candidate lattice."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g59_common import G59_CLOSED_STATUS, read_csv_rows, repo_root, resolve, write_json, write_text  # noqa: E402


DEFAULT_CANDIDATES = "outputs/tables/phase5p5_repair5g59_candidate_lattice.csv"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g59_candidate_lattice_summary.json"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g59_candidate_lattice.md"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-csv", type=Path, default=Path(DEFAULT_CANDIDATES))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    rows = read_csv_rows(resolve(args.candidate_csv, root))
    gates = {
        "candidate_count_gt_0": bool(rows),
        "candidate_count_le_16": len(rows) <= 16,
        "update_ltm_only": all(str(row.get("update_ltm_only", "")).lower() == "true" for row in rows),
        "no_forbidden_outputs": all(not row.get("forbidden_outputs") for row in rows),
        "static_fallback_available": any(str(row.get("static_fallback", "")).lower() == "true" for row in rows),
        "additive_fallback_available": any(str(row.get("additive_fallback", "")).lower() == "true" for row in rows),
        "c_only_f_disabled_ablation_available": any(str(row.get("c_only_f_disabled", "")).lower() == "true" for row in rows),
    }
    summary = {
        "schema_version": "phase5p5_repair5g59_candidate_lattice_summary_v1",
        "decision": "candidate_lattice_ready_for_counterfactual_probe_design" if all(gates.values()) else "candidate_lattice_failed_static_safety_gate",
        "candidate_count": len(rows),
        "candidate_ids": [row.get("candidate_id", "") for row in rows],
        "varied_parameters": [
            "alpha_cong_committed",
            "alpha_cong_blocked",
            "alpha_flow_progress",
            "alpha_flow_wait_or_nonprogress",
            "rho_cong",
            "rho_flow",
            "flow_shield_beta",
            "max_flow_shield",
            "static_fallback",
            "additive_fallback",
            "c_only_f_disabled",
        ],
        "gates": gates,
        "candidate_csv": str(resolve(args.candidate_csv, root)),
        **G59_CLOSED_STATUS,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.9 Candidate Lattice\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- candidate_count: `{len(rows)}`\n"
        f"- candidate_count_le_16: `{gates['candidate_count_le_16']}`\n"
        f"- static_fallback_available: `{gates['static_fallback_available']}`\n"
        f"- additive_fallback_available: `{gates['additive_fallback_available']}`\n"
        f"- c_only_f_disabled_ablation_available: `{gates['c_only_f_disabled_ablation_available']}`\n\n"
        "The lattice remains UpdateLTM-only and bounded; runtime integration is not claimed.\n",
    )
    print(json.dumps({"decision": summary["decision"], "candidate_count": len(rows)}))
    return 0 if all(gates.values()) else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
