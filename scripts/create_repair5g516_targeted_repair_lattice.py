"""Design the Repair5G.5.16 targeted repair candidate lattice."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g512_common import repo_root, resolve, write_csv_rows, write_json, write_text  # noqa: E402
from repair5g516_common import DEFAULT_G516_ERROR_BANK_SUMMARY, DEFAULT_G516_LATTICE, DEFAULT_G516_LATTICE_SUMMARY, G516_CLOSED_CLAIMS  # noqa: E402
from repair5g512_common import read_json  # noqa: E402


DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g516_targeted_repair_lattice.md"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--error-bank-summary", type=Path, default=Path(DEFAULT_G516_ERROR_BANK_SUMMARY))
    parser.add_argument("--output-csv", type=Path, default=Path(DEFAULT_G516_LATTICE))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_G516_LATTICE_SUMMARY))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    return parser.parse_args(argv)


def adapter_methods(root: Path) -> set[str]:
    source = resolve("cpp/tools/phase1a_batch.cpp", root)
    if not source.exists():
        return set()
    text = source.read_text(encoding="utf-8", errors="ignore")
    return set(re.findall(r'"(repair5g[0-9a-zA-Z_]+)"', text))


def candidate_rows() -> list[dict[str, object]]:
    return [
        {
            "candidate_id": "repair5g516_slow_decay_safer_beta025_cap050",
            "family": "safer_slow_decay",
            "base_candidate_id": "repair5g59_slow_decay_high_shield",
            "alpha_cong_committed": 1.25,
            "alpha_cong_blocked": 1.25,
            "alpha_flow_progress": 1.00,
            "alpha_flow_wait_or_nonprogress": 0.75,
            "rho_cong": 0.92,
            "rho_flow": 1.00,
            "flow_shield_beta": 0.25,
            "max_flow_shield": 0.50,
            "c_only": False,
            "intended_context_category": "harmful_false_positive",
            "repair_hypothesis": "lower shield beta and cap to reduce slow-decay harmful false positives",
        },
        {
            "candidate_id": "repair5g516_slow_decay_safer_beta020_cap045",
            "family": "safer_slow_decay",
            "base_candidate_id": "repair5g59_slow_decay_high_shield",
            "alpha_cong_committed": 1.20,
            "alpha_cong_blocked": 1.20,
            "alpha_flow_progress": 1.00,
            "alpha_flow_wait_or_nonprogress": 0.75,
            "rho_cong": 0.90,
            "rho_flow": 1.00,
            "flow_shield_beta": 0.20,
            "max_flow_shield": 0.45,
            "c_only": False,
            "intended_context_category": "harmful_false_positive",
            "repair_hypothesis": "slightly faster congestion decay and lower shield cap",
        },
        {
            "candidate_id": "repair5g516_slow_decay_safer_beta015_cap040",
            "family": "safer_slow_decay",
            "base_candidate_id": "repair5g59_slow_decay_high_shield",
            "alpha_cong_committed": 1.15,
            "alpha_cong_blocked": 1.15,
            "alpha_flow_progress": 1.00,
            "alpha_flow_wait_or_nonprogress": 0.75,
            "rho_cong": 0.88,
            "rho_flow": 1.00,
            "flow_shield_beta": 0.15,
            "max_flow_shield": 0.40,
            "c_only": False,
            "intended_context_category": "harmful_false_positive",
            "repair_hypothesis": "conservative slow-decay boundary variant",
        },
        {
            "candidate_id": "repair5g516_wait_aggressive_low_cap",
            "family": "wait_neighborhood",
            "base_candidate_id": "repair5g59_wait_aggressive",
            "alpha_cong_committed": 1.00,
            "alpha_cong_blocked": 1.00,
            "alpha_flow_progress": 1.05,
            "alpha_flow_wait_or_nonprogress": 1.25,
            "rho_cong": 0.95,
            "rho_flow": 0.95,
            "flow_shield_beta": 0.20,
            "max_flow_shield": 0.50,
            "c_only": False,
            "intended_context_category": "missed_helpful_fallback",
            "repair_hypothesis": "capture wait-heavy maze opportunities with lower cap",
        },
        {
            "candidate_id": "repair5g516_wait_conservative_mid_cap",
            "family": "wait_neighborhood",
            "base_candidate_id": "repair5g59_wait_conservative",
            "alpha_cong_committed": 1.00,
            "alpha_cong_blocked": 1.00,
            "alpha_flow_progress": 1.00,
            "alpha_flow_wait_or_nonprogress": 1.05,
            "rho_cong": 0.95,
            "rho_flow": 0.98,
            "flow_shield_beta": 0.18,
            "max_flow_shield": 0.45,
            "c_only": False,
            "intended_context_category": "static_near_oracle",
            "repair_hypothesis": "near-static wait-safe boundary candidate",
        },
        {
            "candidate_id": "repair5g516_wait_aggressive_fast_flow_decay",
            "family": "wait_neighborhood",
            "base_candidate_id": "repair5g59_wait_aggressive",
            "alpha_cong_committed": 1.00,
            "alpha_cong_blocked": 1.00,
            "alpha_flow_progress": 1.10,
            "alpha_flow_wait_or_nonprogress": 1.30,
            "rho_cong": 0.95,
            "rho_flow": 0.90,
            "flow_shield_beta": 0.18,
            "max_flow_shield": 0.45,
            "c_only": False,
            "intended_context_category": "missed_helpful_fallback",
            "repair_hypothesis": "wait-aggressive with faster flow decay to reduce persistence risk",
        },
        {
            "candidate_id": "repair5g516_commit_heavy_low_beta",
            "family": "commit_neighborhood",
            "base_candidate_id": "repair5g59_commit_heavy_flow_guard",
            "alpha_cong_committed": 1.45,
            "alpha_cong_blocked": 0.90,
            "alpha_flow_progress": 1.10,
            "alpha_flow_wait_or_nonprogress": 0.80,
            "rho_cong": 0.95,
            "rho_flow": 1.00,
            "flow_shield_beta": 0.18,
            "max_flow_shield": 0.45,
            "c_only": False,
            "intended_context_category": "harmful_false_positive",
            "repair_hypothesis": "random a50-style commit-heavy alternative to slow decay",
        },
        {
            "candidate_id": "repair5g516_commit_heavy_static_guard",
            "family": "commit_neighborhood",
            "base_candidate_id": "repair5g59_commit_heavy_flow_guard",
            "alpha_cong_committed": 1.35,
            "alpha_cong_blocked": 0.90,
            "alpha_flow_progress": 1.05,
            "alpha_flow_wait_or_nonprogress": 0.75,
            "rho_cong": 0.92,
            "rho_flow": 0.98,
            "flow_shield_beta": 0.15,
            "max_flow_shield": 0.35,
            "c_only": False,
            "intended_context_category": "static_near_oracle",
            "repair_hypothesis": "commit-heavy variant with conservative static-boundary guard",
        },
        {
            "candidate_id": "repair5g516_static_boundary_light_flow",
            "family": "conservative_static_boundary",
            "base_candidate_id": "repair5g59_static_flow_shield",
            "alpha_cong_committed": 1.00,
            "alpha_cong_blocked": 1.00,
            "alpha_flow_progress": 1.00,
            "alpha_flow_wait_or_nonprogress": 0.90,
            "rho_cong": 0.95,
            "rho_flow": 1.00,
            "flow_shield_beta": 0.10,
            "max_flow_shield": 0.25,
            "c_only": False,
            "intended_context_category": "static_near_oracle",
            "repair_hypothesis": "minimal nonstatic boundary for abstention calibration",
        },
        {
            "candidate_id": "repair5g516_static_boundary_c_only",
            "family": "conservative_static_boundary",
            "base_candidate_id": "repair5g59_c_only_f_disabled",
            "alpha_cong_committed": 1.05,
            "alpha_cong_blocked": 1.05,
            "alpha_flow_progress": 1.00,
            "alpha_flow_wait_or_nonprogress": 0.75,
            "rho_cong": 0.95,
            "rho_flow": 1.00,
            "flow_shield_beta": 0.0,
            "max_flow_shield": 0.0,
            "c_only": True,
            "intended_context_category": "static_near_oracle",
            "repair_hypothesis": "congestion-only static-boundary contrast",
        },
    ]


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    error_summary = read_json(resolve(args.error_bank_summary, root)) if resolve(args.error_bank_summary, root).exists() else {}
    known = adapter_methods(root)
    rows = candidate_rows()
    for row in rows:
        row["update_only"] = True
        row["executable_by_current_cpp_adapter"] = row["candidate_id"] in known
    executable_count = sum(1 for row in rows if row["executable_by_current_cpp_adapter"])
    gates = {
        "error_bank_available": error_summary.get("decision") == "error_bank_created_continue_lattice",
        "new_candidate_count_le_12": len(rows) <= 12,
        "update_only": all(row["update_only"] for row in rows),
        "current_cpp_adapter_recognizes_all": executable_count == len(rows),
    }
    decision = (
        "targeted_repair_lattice_created_executable_continue_probe"
        if all(gates.values())
        else "targeted_repair_lattice_requires_adapter_followup"
    )
    summary = {
        "schema_version": "phase5p5_repair5g516_targeted_repair_lattice_summary_v1",
        "decision": decision,
        "new_candidate_count": len(rows),
        "executable_candidate_count": executable_count,
        "candidate_ids": [str(row["candidate_id"]) for row in rows],
        "families": sorted({str(row["family"]) for row in rows}),
        "gates": gates,
        **G516_CLOSED_CLAIMS,
    }
    write_csv_rows(resolve(args.output_csv, root), rows)
    write_json(resolve(args.summary_json, root), summary)
    lines = "\n".join(
        f"- `{row['candidate_id']}` ({row['family']}): executable=`{row['executable_by_current_cpp_adapter']}`, hypothesis=`{row['repair_hypothesis']}`"
        for row in rows
    )
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.16 Targeted Repair Lattice\n\n"
        f"- decision: `{decision}`\n"
        f"- new_candidate_count: `{len(rows)}`\n"
        f"- executable_candidate_count: `{executable_count}`\n"
        f"- gates: `{gates}`\n"
        "- cplusplus_changed: `false`\n"
        "- solver_probe_allowed: `false` unless the adapter recognition gate is satisfied later\n\n"
        "## Candidate Neighborhood\n\n"
        f"{lines}\n\n"
        "The lattice is an update-parameter design artifact only in this round. Because these `repair5g516_*` names are not recognized by the current C++ adapter, the local probe must stop before solver execution.\n",
    )
    print(json.dumps({"decision": decision, "new_candidate_count": len(rows), "executable_candidate_count": executable_count}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
