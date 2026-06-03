"""Audit Repair5G.1 parity and determinism before G2 fresh validation."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g2_common import (  # noqa: E402
    dirty_state,
    method_pair_exact,
    parity_mismatch_rows,
    read_jsonl,
    rel,
    repo_root,
    resolve,
    support_gate_summary,
    write_csv_rows,
)


DEFAULT_SMOKE_SUMMARY = "outputs/reports/phase5p5_repair5g1_smoke_summary.json"
DEFAULT_DEV_SUMMARY = "outputs/reports/phase5p5_repair5g1_dev_probe_summary.json"
DEFAULT_ORACLE_SUMMARY = "outputs/reports/phase5p5_repair5g1_agent_aware_dual_channel_oracle_summary.json"
DEFAULT_DEV_JSONL = "outputs/logs/phase5p5_repair5g1_dev_probe/phase5p5_repair5g1_dev_probe.jsonl"
DEFAULT_DEV_LONG = "outputs/tables/phase5p5_repair5g1_dev_utility_long.csv"
DEFAULT_DEV_WIDE = "outputs/tables/phase5p5_repair5g1_dev_utility_wide.csv"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g1_parity_determinism_audit.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g1_parity_determinism_audit_summary.json"
DEFAULT_MISMATCHES = "outputs/tables/phase5p5_repair5g1_parity_mismatch_cases.csv"

PAIRS = [
    ("lacam_star_ltm", "always_additive_defer"),
    ("lacam_star_ltm", "repair5f_candidate_additive_ltm"),
    ("lacam_star_ltm", "laur_disable"),
    ("lacam_star_ltm", "laur_force_additive_direct"),
    ("lacam_star_ltm", "repair5g_dual_additive_parity"),
    ("lacam_star_ltm", "repair5g_dual_c_equiv_additive"),
    ("repair5f_static_c100_b100_w075_d090", "repair5g_dual_c_equiv_c100_b100_w075_d090"),
    (
        "repair5f4_best_static_c125_b125_w075_d095_diagnostic_only",
        "repair5g_dual_c_equiv_c125_b125_w075_d095",
    ),
]


def git_value(args: list[str], cwd: Path) -> str:
    try:
        return subprocess.check_output(["git", *args], cwd=cwd, text=True).strip()
    except (FileNotFoundError, subprocess.CalledProcessError):
        return ""


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_report(path: Path, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Phase5.5 Repair5G.1 Parity and Determinism Audit\n\n")
        handle.write("This audit determines whether G2 may proceed to selector development. It does not permit Phase5.5 or Phase6.\n\n")
        handle.write("## Verdict\n\n")
        handle.write(f"- true_semantic_mismatch: `{summary['true_semantic_mismatch']}`\n")
        handle.write(f"- proceed_to_g2_selector_protocol: `{summary['proceed_to_g2_selector_protocol']}`\n")
        handle.write(f"- classification_counts: `{summary['classification_counts']}`\n")
        handle.write(f"- phase5p5_allowed: `false`\n")
        handle.write(f"- phase6_allowed: `false`\n\n")
        handle.write("## Smoke Gates\n\n")
        for key, value in summary["smoke_gates"].items():
            handle.write(f"- `{key}`: `{value}`\n")
        handle.write("\n## Bulk Dev Gates\n\n")
        for key, value in summary["bulk_dev_gates"].items():
            handle.write(f"- `{key}`: `{value}`\n")
        handle.write("\n## Interpretation\n\n")
        handle.write(summary["interpretation"] + "\n\n")
        handle.write("## G1 Headroom Check\n\n")
        oracle = summary["oracle_check"]
        for key, value in oracle.items():
            handle.write(f"- `{key}`: `{value}`\n")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--smoke-summary-json", type=Path, default=Path(DEFAULT_SMOKE_SUMMARY))
    parser.add_argument("--dev-summary-json", type=Path, default=Path(DEFAULT_DEV_SUMMARY))
    parser.add_argument("--oracle-summary-json", type=Path, default=Path(DEFAULT_ORACLE_SUMMARY))
    parser.add_argument("--dev-jsonl", type=Path, default=Path(DEFAULT_DEV_JSONL))
    parser.add_argument("--dev-long-csv", type=Path, default=Path(DEFAULT_DEV_LONG))
    parser.add_argument("--dev-wide-csv", type=Path, default=Path(DEFAULT_DEV_WIDE))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    parser.add_argument("--mismatch-csv", type=Path, default=Path(DEFAULT_MISMATCHES))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    smoke_summary = read_json(resolve(args.smoke_summary_json, root))
    dev_summary = read_json(resolve(args.dev_summary_json, root))
    oracle_summary = read_json(resolve(args.oracle_summary_json, root))
    dev_jsonl = resolve(args.dev_jsonl, root)
    for path in [
        resolve(args.dev_long_csv, root),
        resolve(args.dev_wide_csv, root),
        dev_jsonl,
    ]:
        if not path.exists():
            raise FileNotFoundError(path)
    rows = read_jsonl(dev_jsonl)
    mismatch_rows = parity_mismatch_rows(rows, PAIRS)
    classification_counts = dict(sorted(Counter(row["classification"] for row in mismatch_rows).items()))
    true_semantic_mismatch = any(row["classification"] == "true_semantic_mismatch" for row in mismatch_rows)
    smoke_gates = {
        key: bool(smoke_summary.get(key))
        for key in [
            "additive_parity_exact",
            "laur_disable_parity_exact",
            "laur_force_additive_direct_parity_exact",
            "dual_additive_parity_exact",
            "dual_c_equiv_additive_parity_exact",
            "dual_c_equiv_locked_matches_scalar",
            "dual_c_equiv_best_f4_static_matches_scalar",
            "critical_smoke_gates_passed",
        ]
    }
    bulk_dev_gates = support_gate_summary(rows)
    pair_exact = {
        f"{left}__vs__{right}": method_pair_exact(rows, left, right)
        for left, right in PAIRS
    }
    oracle_stats = oracle_summary.get("oracle_stats", {})
    oracle_check = {
        "oracle_better": oracle_stats.get("better"),
        "oracle_equal": oracle_stats.get("equal"),
        "oracle_worse": oracle_stats.get("worse"),
        "oracle_mean_delta_ratio_vs_ltm": oracle_stats.get("mean_delta_ratio_vs_ltm"),
        "oracle_bootstrap_ci": oracle_summary.get("oracle_bootstrap_ci"),
        "flow_shield_component_present": any(
            row.get("component") == "flow_shield"
            for row in oracle_summary.get("component_summary", [])
        ),
    }
    proceed = bool(smoke_gates.get("critical_smoke_gates_passed")) and not true_semantic_mismatch
    interpretation = (
        "Sequential G1 smoke parity is exact. Bulk dev discrepancies are classified as time-budget sensitivity "
        "or missing/reporting issues rather than semantic mismatches, so G2 may proceed with a fresh frozen protocol."
        if proceed
        else "A true semantic mismatch or failed sequential smoke gate was detected. Stop before G2 final validation."
    )
    summary = {
        "schema_version": "phase5p5_repair5g1_parity_determinism_audit_v1",
        "created_at": datetime.now().isoformat(),
        "branch": git_value(["branch", "--show-current"], root),
        "commit": git_value(["rev-parse", "--short", "HEAD"], root),
        "dirty": dirty_state(root),
        "inputs": {
            "smoke_summary_json": rel(resolve(args.smoke_summary_json, root), root),
            "dev_summary_json": rel(resolve(args.dev_summary_json, root), root),
            "oracle_summary_json": rel(resolve(args.oracle_summary_json, root), root),
            "dev_jsonl": rel(dev_jsonl, root),
        },
        "smoke_gates": smoke_gates,
        "bulk_dev_gates": bulk_dev_gates,
        "pair_exact_from_dev_rows": pair_exact,
        "bulk_dev_summary_flags": {
            key: dev_summary.get(key)
            for key in [
                "missing_rows",
                "schema_errors",
                "additive_parity_exact",
                "laur_disable_parity_exact",
                "laur_force_additive_direct_parity_exact",
                "dual_additive_parity_exact",
                "dual_c_equiv_additive_parity_exact",
                "dual_c_equiv_locked_matches_scalar",
                "dual_c_equiv_best_f4_static_matches_scalar",
            ]
        },
        "mismatch_count": len(mismatch_rows),
        "classification_counts": classification_counts,
        "true_semantic_mismatch": true_semantic_mismatch,
        "proceed_to_g2_selector_protocol": proceed,
        "top_g1_flow_shield_conclusions_robust_to_sequential_smoke_controls": proceed,
        "oracle_check": oracle_check,
        "mismatch_csv": rel(resolve(args.mismatch_csv, root), root),
        "report": rel(resolve(args.report, root), root),
        "diagnostic_only": True,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "interpretation": interpretation,
    }
    mismatch_fields = [
        "map",
        "agents",
        "seed",
        "scen",
        "left_method",
        "right_method",
        "classification",
        "mismatched_fields",
        "left_ratio",
        "right_ratio",
        "left_success",
        "right_success",
        "left_runtime_ms",
        "right_runtime_ms",
        "time_limit_ms",
    ]
    write_csv_rows(resolve(args.mismatch_csv, root), mismatch_rows, mismatch_fields)
    summary_path = resolve(args.summary_json, root)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(resolve(args.report, root), summary)
    print(json.dumps({"mismatch_count": len(mismatch_rows), "proceed": proceed}))
    return 0 if proceed else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
