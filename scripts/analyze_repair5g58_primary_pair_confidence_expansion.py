"""Analyze Repair5G.5.8 primary-pair confidence expansion."""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g58_common import (  # noqa: E402
    G58_DEFAULT_MARGIN_THRESHOLD,
    G58_PRIMARY_BUDGET_MS,
    G58_SENTINEL_BUDGET_MS,
    G58_STRESS_BUDGET_MS,
    budget_summary_value,
    classify_context,
    contexts_from_probe_jsonl,
    finite_number,
    format_optional_float,
    gate_counts,
    read_jsonl_many,
    repo_root,
    resolve,
    validate_observed_rows,
    write_csv_rows,
    write_json,
    write_text,
)


DEFAULT_G56_PROBES = "outputs/logs/phase5p5_repair5g56_probe_budget_stability/phase5p5_repair5g56_probe_budget_update_probes.jsonl"
DEFAULT_G58_PROBES = "outputs/logs/phase5p5_repair5g58_primary_pair_confidence_expansion/phase5p5_repair5g58_primary_pair_update_probes.jsonl"
DEFAULT_BY_CONTEXT = "outputs/tables/phase5p5_repair5g58_primary_pair_confidence_by_context.csv"
DEFAULT_BY_MAP_AGENT = "outputs/tables/phase5p5_repair5g58_primary_pair_confidence_by_map_agent.csv"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g58_primary_pair_confidence_expansion.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g58_primary_pair_confidence_expansion_summary.json"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--probe-jsonl", nargs="+", type=Path, default=[Path(DEFAULT_G56_PROBES), Path(DEFAULT_G58_PROBES)])
    parser.add_argument("--by-context-csv", type=Path, default=Path(DEFAULT_BY_CONTEXT))
    parser.add_argument("--by-map-agent-csv", type=Path, default=Path(DEFAULT_BY_MAP_AGENT))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    parser.add_argument("--default-margin-threshold", type=float, default=G58_DEFAULT_MARGIN_THRESHOLD)
    return parser.parse_args(argv)


def same_nonempty(left: Any, right: Any) -> bool:
    return bool(left) and bool(right) and left == right


def context_row(context: dict[str, Any], *, margin_threshold: float) -> dict[str, Any]:
    budgets = context.get("budgets", {})
    primary = budgets.get(G58_PRIMARY_BUDGET_MS)
    sentinel = budgets.get(G58_SENTINEL_BUDGET_MS)
    stress = budgets.get(G58_STRESS_BUDGET_MS)
    primary_oracle = budget_summary_value(primary, "oracle_candidate_id")
    sentinel_oracle = budget_summary_value(sentinel, "oracle_candidate_id")
    primary_finite = int(budget_summary_value(primary, "finite_candidate_count", 0) or 0)
    sentinel_finite = int(budget_summary_value(sentinel, "finite_candidate_count", 0) or 0)
    primary_sign = budget_summary_value(primary, "static_vs_oracle_sign")
    sentinel_sign = budget_summary_value(sentinel, "static_vs_oracle_sign")
    measured = bool(primary and sentinel)
    oracle_agree = measured and same_nonempty(primary_oracle, sentinel_oracle)
    sign_agree = measured and same_nonempty(primary_sign, sentinel_sign)
    feasibility_agree = measured and primary_finite == sentinel_finite
    primary_stable = oracle_agree and sign_agree and feasibility_agree
    margin_1000 = budget_summary_value(primary, "margin_vs_static", math.nan)
    margin_2000 = budget_summary_value(sentinel, "margin_vs_static", math.nan)
    label_class, target, training, margin, reason = classify_context(context, margin_threshold=margin_threshold)
    stress_disagrees = bool(stress and primary) and (
        budget_summary_value(stress, "oracle_candidate_id") != primary_oracle
        or budget_summary_value(stress, "static_vs_oracle_sign") != primary_sign
        or int(budget_summary_value(stress, "finite_candidate_count", 0) or 0) != primary_finite
    )
    return {
        "context_id": context.get("context_id", ""),
        "normalized_context_key": context.get("normalized_context_key", ""),
        "map": context.get("map", ""),
        "agents": context.get("agents", ""),
        "seed": context.get("seed", ""),
        "iteration": context.get("iteration", ""),
        "traffic_before_hash_full": context.get("traffic_before_hash_full", ""),
        "budgets_present": ",".join(str(int(value)) for value in sorted(budgets)),
        "primary_1000_2000_measured": measured,
        "primary_1000_2000_stable": primary_stable,
        "oracle_1000": primary_oracle,
        "oracle_2000": sentinel_oracle,
        "finite_candidates_1000": primary_finite,
        "finite_candidates_2000": sentinel_finite,
        "static_score_1000": format_optional_float(budget_summary_value(primary, "static_score", math.nan)),
        "static_score_2000": format_optional_float(budget_summary_value(sentinel, "static_score", math.nan)),
        "oracle_score_1000": format_optional_float(budget_summary_value(primary, "oracle_score", math.nan)),
        "oracle_score_2000": format_optional_float(budget_summary_value(sentinel, "oracle_score", math.nan)),
        "margin_vs_static_1000": format_optional_float(margin_1000),
        "margin_vs_static_2000": format_optional_float(margin_2000),
        "static_vs_oracle_sign_1000": primary_sign,
        "static_vs_oracle_sign_2000": sentinel_sign,
        "oracle_agreement_1000_2000": oracle_agree,
        "static_vs_oracle_sign_agreement_1000_2000": sign_agree,
        "feasibility_agreement_1000_2000": feasibility_agree,
        "stress_250_disagrees_with_1000": stress_disagrees,
        "default_margin_threshold": margin_threshold,
        "label_class_at_default_threshold": label_class,
        "target_candidate_id_at_default_threshold": target,
        "training_eligible_at_default_threshold": training,
        "confidence_margin_at_default_threshold": format_optional_float(margin),
        "confidence_reason_at_default_threshold": reason,
    }


def ratio(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    probe_paths = [resolve(path, root) for path in args.probe_jsonl]
    probe_rows = read_jsonl_many(probe_paths)
    contexts = contexts_from_probe_jsonl(probe_paths)
    rows = [context_row(context, margin_threshold=float(args.default_margin_threshold)) for _key, context in sorted(contexts.items())]
    write_csv_rows(resolve(args.by_context_csv, root), rows)

    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[(str(row.get("map", "")), str(row.get("agents", "")))].append(row)
    group_rows = []
    for (map_name, agents), group in sorted(groups.items()):
        measured = [row for row in group if row["primary_1000_2000_measured"]]
        stable = [row for row in group if row["primary_1000_2000_stable"]]
        label_metrics = gate_counts([row | {"label_class": row["label_class_at_default_threshold"], "training_eligible": row["training_eligible_at_default_threshold"]} for row in group])
        group_rows.append(
            {
                "map": map_name,
                "agents": agents,
                "context_count": len(group),
                "measured_confidence_contexts": len(measured),
                "primary_1000_2000_stable_contexts": len(stable),
                "training_eligible_contexts": label_metrics["training_eligible_contexts"],
                "stable_high_confidence_nonstatic_count": label_metrics["stable_high_confidence_nonstatic_count"],
                "stable_static_or_abstain_count": label_metrics["stable_static_or_abstain_count"],
                "no_solution_or_budget_abstain_count": label_metrics["no_solution_or_budget_abstain_count"],
                "stress_250_disagreements": sum(1 for row in group if row["stress_250_disagrees_with_1000"]),
            }
        )
    write_csv_rows(resolve(args.by_map_agent_csv, root), group_rows)

    measured = [row for row in rows if row["primary_1000_2000_measured"]]
    stable = [row for row in rows if row["primary_1000_2000_stable"]]
    default_label_rows = [
        row | {"label_class": row["label_class_at_default_threshold"], "training_eligible": row["training_eligible_at_default_threshold"]}
        for row in rows
    ]
    label_metrics = gate_counts(default_label_rows)
    observed_ok = validate_observed_rows(probe_rows + rows, label="Repair5G.5.8 primary-pair confidence expansion")
    stress_compared = sum(
        1
        for row in rows
        if "250" in {part.strip() for part in str(row.get("budgets_present", "")).split(",") if part.strip()}
    )
    stress_disagreements = sum(1 for row in rows if row["stress_250_disagrees_with_1000"])
    gates = {
        "measured_confidence_contexts_ge_60": len(measured) >= 60,
        "primary_1000_2000_stable_contexts_ge_30": len(stable) >= 30,
        "training_eligible_contexts_ge_30": label_metrics["training_eligible_contexts"] >= 30,
        "stable_high_confidence_nonstatic_count_ge_10": label_metrics["stable_high_confidence_nonstatic_count"] >= 10,
        "stable_static_or_abstain_count_ge_10": label_metrics["stable_static_or_abstain_count"] >= 10,
        "no_solution_or_budget_abstain_count_gt_0": label_metrics["no_solution_or_budget_abstain_count"] > 0,
        "observed_ids_only": observed_ok,
    }
    gates["ids_166_205_untouched"] = observed_ok
    gates["primary_pair_confidence_expansion_passed"] = all(gates.values())
    summary = {
        "schema_version": "phase5p5_repair5g58_primary_pair_confidence_expansion_summary_v1",
        "probe_jsonl": [str(path) for path in probe_paths],
        "probe_rows": len(probe_rows),
        "context_count": len(rows),
        "measured_confidence_contexts": len(measured),
        "primary_1000_2000_stable_contexts": len(stable),
        **label_metrics,
        "default_margin_threshold": float(args.default_margin_threshold),
        "stress_250_compared_contexts": stress_compared,
        "stress_250_disagreement_contexts": stress_disagreements,
        "stress_250_disagreement_rate": ratio(stress_disagreements, stress_compared),
        "by_context_csv": str(resolve(args.by_context_csv, root)),
        "by_map_agent_csv": str(resolve(args.by_map_agent_csv, root)),
        "gates": gates,
        "decision": "primary_pair_confidence_expansion_passed" if gates["primary_pair_confidence_expansion_passed"] else "confidence_expansion_failed_continue_probe_design",
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "aaai_ready": False,
        "runtime_claim_allowed": False,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.8 Primary-Pair Confidence Expansion\n\n"
        f"- measured_confidence_contexts: `{summary['measured_confidence_contexts']}`\n"
        f"- primary_1000_2000_stable_contexts: `{summary['primary_1000_2000_stable_contexts']}`\n"
        f"- training_eligible_contexts: `{summary['training_eligible_contexts']}`\n"
        f"- stable_high_confidence_nonstatic_count: `{summary['stable_high_confidence_nonstatic_count']}`\n"
        f"- stable_static_or_abstain_count: `{summary['stable_static_or_abstain_count']}`\n"
        f"- no_solution_or_budget_abstain_count: `{summary['no_solution_or_budget_abstain_count']}`\n"
        f"- stress_250_disagreement_rate: `{summary['stress_250_disagreement_rate']}`\n"
        f"- primary_pair_confidence_expansion_passed: `{gates['primary_pair_confidence_expansion_passed']}`\n\n"
        "The primary training-confidence pair is 1000/2000 ms. The 250 ms tier remains stress-only.\n",
    )
    print(json.dumps({"decision": summary["decision"], "measured_confidence_contexts": len(measured)}))
    return 0 if observed_ok and rows else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
