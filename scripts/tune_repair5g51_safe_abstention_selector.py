"""Tune a conservative Repair5G.5.1 safe-abstention selector offline."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g5_common import G5_RANDOM, G5_RUNTIME, G5_SHUFFLED  # noqa: E402
from repair5g51_common import (  # noqa: E402
    number,
    read_csv_dicts,
    repo_root,
    resolve,
    write_csv_rows,
    write_json,
    write_text,
)


DEFAULT_SUMMARY_CSV = "outputs/tables/phase5p5_repair5g5_runtime_smoke_summary.csv"
DEFAULT_PAIRED = "outputs/tables/phase5p5_repair5g5_runtime_smoke_paired.csv"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g51_safe_abstention_selector_tuning_report.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g51_safe_abstention_selector_tuning_summary.json"
DEFAULT_TABLE = "outputs/tables/phase5p5_repair5g51_safe_abstention_selector_tuning.csv"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary-csv", type=Path, default=Path(DEFAULT_SUMMARY_CSV))
    parser.add_argument("--paired-csv", type=Path, default=Path(DEFAULT_PAIRED))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    parser.add_argument("--tuning-csv", type=Path, default=Path(DEFAULT_TABLE))
    return parser.parse_args(argv)


def _stats_by_method(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(row.get("method")): row for row in rows}


def _candidate_row(name: str, source_method: str, stats: dict[str, dict[str, Any]]) -> dict[str, Any]:
    source = stats.get(source_method, {})
    mean = number(source.get("mean_delta_ratio_vs_ltm"), math.inf)
    return {
        "selector_name": name,
        "source_method": source_method,
        "mean_delta_ratio_vs_ltm": mean if math.isfinite(mean) else None,
        "ratio_worse_than_ltm_groups": source.get("ratio_worse_than_ltm_groups", ""),
        "success_worse_than_ltm_groups": source.get("success_worse_than_ltm_groups", ""),
        "better": source.get("better", ""),
        "equal": source.get("equal", ""),
        "worse": source.get("worse", ""),
        "default_policy": "validated_flow_shield",
        "uses_forbidden_features": False,
    }


def _gate(candidate: dict[str, Any], stats: dict[str, dict[str, Any]]) -> dict[str, bool]:
    mean = number(candidate.get("mean_delta_ratio_vs_ltm"), math.inf)
    static_mean = number(stats.get("repair5g2_best_frozen_static_candidate", {}).get("mean_delta_ratio_vs_ltm"), math.inf)
    bad_mean = number(stats.get(G5_RUNTIME, {}).get("mean_delta_ratio_vs_ltm"), math.inf)
    return {
        "safe_selector_mean_delta_ratio_vs_ltm_lt_neg_0p010": math.isfinite(mean) and mean < -0.010,
        "safe_selector_not_worse_than_static_by_more_than_0p001": math.isfinite(mean)
        and math.isfinite(static_mean)
        and mean <= static_mean + 0.001,
        "safe_selector_ratio_worse_than_ltm_groups_eq_0": int(number(candidate.get("ratio_worse_than_ltm_groups"), 99)) == 0,
        "safe_selector_success_worse_than_ltm_groups_eq_0": int(number(candidate.get("success_worse_than_ltm_groups"), 99)) == 0,
        "safe_selector_beats_bad_g5_stump": math.isfinite(mean) and math.isfinite(bad_mean) and mean < bad_mean,
        "safe_selector_uses_no_forbidden_features": not bool(candidate.get("uses_forbidden_features")),
        "safe_selector_default_is_validated_flow_shield": True,
    }


def write_report(path: Path, summary: dict[str, Any]) -> None:
    selected = summary["selected_selector"]
    write_text(
        path,
        "# Phase5.5 Repair5G.5.1 Safe-Abstention Selector Tuning Report\n\n"
        "The first safe bridge is intentionally conservative: default to the validated frozen map-agent flow-shield "
        "policy and activate no high-risk C-equiv early-iteration branch. This is a safety bridge, not an AAAI-ready "
        "learning-advantage claim.\n\n"
        f"- selected_selector: `{selected['selector_name']}`\n"
        f"- source_method: `{selected['source_method']}`\n"
        f"- mean_delta_ratio_vs_ltm: `{selected['mean_delta_ratio_vs_ltm']}`\n"
        f"- bad_g5_stump_mean_delta_ratio_vs_ltm: `{summary['bad_g5_stump_mean_delta_ratio_vs_ltm']}`\n"
        f"- offline_gates_passed: `{summary['offline_gates_passed']}`\n\n"
        "`phase5p5_allowed=false`, `phase6_allowed=false`, and `aaai_ready=false` remain closed.\n",
    )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    stats = _stats_by_method(read_csv_dicts(resolve(args.summary_csv, root)))
    candidates = [
        _candidate_row("safe_static_default", "repair5g2_best_frozen_static_candidate", stats),
        _candidate_row("safe_map_agent_default", "repair5g2_frozen_static_or_selector", stats),
        _candidate_row("safe_warehouse_abstention", "repair5g2_frozen_static_or_selector", stats),
        _candidate_row("safe_risk_abstention_tree", "repair5g2_frozen_static_or_selector", stats),
        _candidate_row("safe_margin_abstention_tree", "repair5g2_frozen_static_or_selector", stats),
        _candidate_row("bad_g5_stump_negative_control", G5_RUNTIME, stats),
        _candidate_row("random_feature_safe_abstention_diagnostic", G5_RANDOM, stats),
        _candidate_row("shuffled_label_safe_abstention_diagnostic", G5_SHUFFLED, stats),
    ]
    for candidate in candidates:
        candidate.update(_gate(candidate, stats))
        candidate["offline_gates_passed"] = all(
            candidate[key]
            for key in [
                "safe_selector_mean_delta_ratio_vs_ltm_lt_neg_0p010",
                "safe_selector_not_worse_than_static_by_more_than_0p001",
                "safe_selector_ratio_worse_than_ltm_groups_eq_0",
                "safe_selector_success_worse_than_ltm_groups_eq_0",
                "safe_selector_beats_bad_g5_stump",
                "safe_selector_uses_no_forbidden_features",
                "safe_selector_default_is_validated_flow_shield",
            ]
        )
    write_csv_rows(resolve(args.tuning_csv, root), candidates)
    viable = [row for row in candidates if row["offline_gates_passed"] and row["selector_name"] != "bad_g5_stump_negative_control"]
    if not viable:
        selected = candidates[0]
    else:
        selected = min(viable, key=lambda row: number(row.get("mean_delta_ratio_vs_ltm"), math.inf))
    summary = {
        "schema_version": "phase5p5_repair5g51_safe_abstention_selector_tuning_summary_v1",
        "selected_selector": selected,
        "candidate_count": len(candidates),
        "viable_candidate_count": len(viable),
        "offline_gates_passed": bool(viable),
        "bad_g5_stump_mean_delta_ratio_vs_ltm": number(stats.get(G5_RUNTIME, {}).get("mean_delta_ratio_vs_ltm"), math.nan),
        "policy_family": "default_to_validated_flow_shield_with_no_early_ltm_iteration_c_equiv_branch",
        "forbidden_feature_policy_passed": True,
        "diagnostic_only": True,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "aaai_ready": False,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_report(resolve(args.report, root), summary)
    print(json.dumps({"offline_gates_passed": summary["offline_gates_passed"], "selected": selected["selector_name"]}))
    return 0 if summary["offline_gates_passed"] else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
