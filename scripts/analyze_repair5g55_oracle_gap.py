"""Analyze Repair5G.5.5 oracle adaptivity over static flow-shield."""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g3_common import number  # noqa: E402
from repair5g55_common import (  # noqa: E402
    G55_ADDITIVE_CANDIDATE,
    G55_STATIC_CANDIDATE,
    compact_json_bool,
    mean_or_none,
    median_or_none,
    read_csv_rows,
    repo_root,
    resolve,
    write_csv_rows,
    write_json,
    write_text,
)


DEFAULT_LABEL_SUMMARY = "outputs/reports/phase5p5_repair5g55_counterfactual_label_quality_summary.json"
DEFAULT_LABELS = "outputs/tables/phase5p5_repair5g55_counterfactual_update_labels.csv"
DEFAULT_CONTEXTS = "outputs/tables/phase5p5_repair5g55_counterfactual_contexts.csv"
DEFAULT_ORACLE = "outputs/tables/phase5p5_repair5g55_oracle_by_context.csv"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g55_oracle_gap.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g55_oracle_gap_summary.json"
DEFAULT_BY_GROUP = "outputs/tables/phase5p5_repair5g55_oracle_gap_by_map_agent_iteration.csv"
DEFAULT_WIN_RATES = "outputs/tables/phase5p5_repair5g55_candidate_win_rates.csv"
DEFAULT_STATIC_FAILURES = "outputs/tables/phase5p5_repair5g55_static_failure_contexts.csv"
DEFAULT_REGRET = "outputs/tables/phase5p5_repair5g55_candidate_regret_distribution.csv"
DEFAULT_TRACE_GROUPS = "outputs/tables/phase5p5_repair5g55_oracle_gap_by_trace_traffic_bucket.csv"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label-summary-json", type=Path, default=Path(DEFAULT_LABEL_SUMMARY))
    parser.add_argument("--labels-csv", type=Path, default=Path(DEFAULT_LABELS))
    parser.add_argument("--contexts-csv", type=Path, default=Path(DEFAULT_CONTEXTS))
    parser.add_argument("--oracle-csv", type=Path, default=Path(DEFAULT_ORACLE))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    parser.add_argument("--by-map-agent-iteration-csv", type=Path, default=Path(DEFAULT_BY_GROUP))
    parser.add_argument("--candidate-win-rates-csv", type=Path, default=Path(DEFAULT_WIN_RATES))
    parser.add_argument("--static-failure-contexts-csv", type=Path, default=Path(DEFAULT_STATIC_FAILURES))
    parser.add_argument("--candidate-regret-csv", type=Path, default=Path(DEFAULT_REGRET))
    parser.add_argument("--trace-traffic-bucket-csv", type=Path, default=Path(DEFAULT_TRACE_GROUPS))
    return parser.parse_args(argv)


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def enrich_oracle(oracle: list[dict[str, str]], contexts: list[dict[str, str]]) -> list[dict[str, Any]]:
    context_by_id = {str(row.get("context_id", "")): row for row in contexts}
    out: list[dict[str, Any]] = []
    for row in oracle:
        context = context_by_id.get(str(row.get("context_id", "")), {})
        out.append({**row, **{key: value for key, value in context.items() if key not in row or row.get(key, "") == ""}})
    return out


def grouped_gap_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[(str(row.get("map", "")), str(row.get("agents", "")), str(row.get("iteration", "")))].append(row)
    out: list[dict[str, Any]] = []
    for (map_name, agents, iteration), group in sorted(groups.items()):
        gaps = [number(row.get("oracle_gap_over_static"), math.nan) for row in group]
        wins = [gap for gap in gaps if math.isfinite(gap) and gap < -1.0e-12]
        out.append(
            {
                "map": map_name,
                "agents": agents,
                "iteration": iteration,
                "contexts": len(group),
                "oracle_beats_static_contexts": len(wins),
                "oracle_beats_static_fraction": len(wins) / len(group) if group else 0.0,
                "mean_oracle_gap_over_static": mean_or_none(gaps),
                "median_oracle_gap_over_static": median_or_none(gaps),
                "min_oracle_gap_over_static": min([gap for gap in gaps if math.isfinite(gap)], default=""),
                "max_oracle_gap_over_static": max([gap for gap in gaps if math.isfinite(gap)], default=""),
            }
        )
    return out


def candidate_win_rows(oracle: list[dict[str, Any]], labels: list[dict[str, str]]) -> list[dict[str, Any]]:
    wins = Counter(str(row.get("oracle_candidate_id", "")) for row in oracle)
    candidates = sorted({str(row.get("candidate_id", "")) for row in labels if row.get("candidate_id")})
    total = len(oracle)
    out = []
    for candidate in candidates:
        candidate_labels = [row for row in labels if str(row.get("candidate_id", "")) == candidate]
        out.append(
            {
                "candidate_id": candidate,
                "oracle_win_contexts": wins.get(candidate, 0),
                "oracle_win_rate": wins.get(candidate, 0) / total if total else 0.0,
                "mean_probe_sum_of_loss_ratio": mean_or_none(row.get("probe_sum_of_loss_ratio") for row in candidate_labels),
                "median_delta_vs_static_in_same_context": median_or_none(row.get("delta_vs_static_in_same_context") for row in candidate_labels),
            }
        )
    return out


def regret_rows(labels: list[dict[str, str]], oracle: list[dict[str, Any]]) -> list[dict[str, Any]]:
    oracle_score = {
        str(row.get("context_id", "")): number(row.get("oracle_score"), math.nan)
        for row in oracle
    }
    out = []
    for row in labels:
        context_id = str(row.get("context_id", ""))
        score = number(row.get("probe_sum_of_loss_ratio"), math.nan)
        best = oracle_score.get(context_id, math.nan)
        out.append(
            {
                "context_id": context_id,
                "map": row.get("map", ""),
                "agents": row.get("agents", ""),
                "seed": row.get("seed", ""),
                "iteration": row.get("iteration", ""),
                "candidate_id": row.get("candidate_id", ""),
                "probe_sum_of_loss_ratio": score if math.isfinite(score) else "",
                "oracle_score": best if math.isfinite(best) else "",
                "regret_to_oracle": score - best if math.isfinite(score) and math.isfinite(best) else "",
                "delta_vs_static_in_same_context": row.get("delta_vs_static_in_same_context", ""),
                "delta_vs_additive_in_same_context": row.get("delta_vs_additive_in_same_context", ""),
            }
        )
    return out


def bucket(value: Any, low: float, high: float) -> str:
    numeric = number(value, math.nan)
    if not math.isfinite(numeric):
        return "unknown"
    if numeric <= low:
        return "low"
    if numeric >= high:
        return "high"
    return "mid"


def trace_bucket_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    traces = sorted(number(row.get("trace_event_count"), math.nan) for row in rows if math.isfinite(number(row.get("trace_event_count"), math.nan)))
    if traces:
        low = traces[len(traces) // 3]
        high = traces[(2 * len(traces)) // 3]
    else:
        low = high = math.nan
    groups: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        key = (
            bucket(row.get("trace_event_count"), low, high),
            bucket(row.get("blocked_per_committed"), 0.05, 0.20),
            bucket(row.get("wait_event_ratio"), 0.02, 0.10),
        )
        groups[key].append(row)
    out = []
    for key, group in sorted(groups.items()):
        gaps = [number(row.get("oracle_gap_over_static"), math.nan) for row in group]
        wins = [gap for gap in gaps if math.isfinite(gap) and gap < -1.0e-12]
        out.append(
            {
                "trace_density_bucket": key[0],
                "blocked_per_committed_bucket": key[1],
                "wait_event_ratio_bucket": key[2],
                "contexts": len(group),
                "oracle_beats_static_contexts": len(wins),
                "oracle_beats_static_fraction": len(wins) / len(group) if group else 0.0,
                "mean_oracle_gap_over_static": mean_or_none(gaps),
            }
        )
    return out


def decide(label_summary: dict[str, Any], oracle_fraction: float, mean_gap: float | None, static_dominates: bool) -> str:
    if not label_summary.get("gates", {}).get("scaled_counterfactual_label_smoke_passed"):
        return "scaled_labels_failed"
    if static_dominates:
        return "scaled_labels_passed_static_dominates"
    if oracle_fraction >= 0.20 and mean_gap is not None and mean_gap < -1.0e-4:
        return "scaled_labels_passed_adaptive_gap_strong_continue_g6_design"
    return "scaled_labels_passed_adaptive_gap_weak"


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    label_summary = load_json(resolve(args.label_summary_json, root))
    labels = read_csv_rows(resolve(args.labels_csv, root))
    contexts = read_csv_rows(resolve(args.contexts_csv, root))
    oracle = enrich_oracle(read_csv_rows(resolve(args.oracle_csv, root)), contexts)
    by_group = grouped_gap_rows(oracle)
    wins = candidate_win_rows(oracle, labels)
    regrets = regret_rows(labels, oracle)
    static_failures = [row for row in oracle if compact_json_bool(row.get("oracle_beats_static"))]
    trace_groups = trace_bucket_rows(oracle)
    write_csv_rows(resolve(args.oracle_csv, root), oracle)
    write_csv_rows(resolve(args.by_map_agent_iteration_csv, root), by_group)
    write_csv_rows(resolve(args.candidate_win_rates_csv, root), wins)
    write_csv_rows(resolve(args.static_failure_contexts_csv, root), static_failures)
    write_csv_rows(resolve(args.candidate_regret_csv, root), regrets)
    write_csv_rows(resolve(args.trace_traffic_bucket_csv, root), trace_groups)

    gaps = [number(row.get("oracle_gap_over_static"), math.nan) for row in oracle]
    finite_gaps = [gap for gap in gaps if math.isfinite(gap)]
    beats_static = [gap for gap in finite_gaps if gap < -1.0e-12]
    additive_gaps = [number(row.get("oracle_gap_over_additive"), math.nan) for row in oracle]
    beats_additive = [gap for gap in additive_gaps if math.isfinite(gap) and gap < -1.0e-12]
    static_dominates_all = bool(oracle) and not beats_static
    mean_gap = mean_or_none(finite_gaps)
    oracle_fraction = len(beats_static) / len(oracle) if oracle else 0.0
    decision = decide(label_summary, oracle_fraction, mean_gap, static_dominates_all)
    summary = {
        "schema_version": "phase5p5_repair5g55_oracle_gap_summary_v1",
        "counterfactual_labels_passed": bool(label_summary.get("gates", {}).get("scaled_counterfactual_label_smoke_passed")),
        "context_count": len(oracle),
        "label_rows": len(labels),
        "mean_oracle_gap_over_static": mean_gap,
        "median_oracle_gap_over_static": median_or_none(finite_gaps),
        "oracle_beats_static_contexts": len(beats_static),
        "oracle_beats_static_fraction": oracle_fraction,
        "oracle_beats_additive_contexts": len(beats_additive),
        "oracle_beats_additive_fraction": len(beats_additive) / len(oracle) if oracle else 0.0,
        "static_dominates_all_contexts": static_dominates_all,
        "candidate_win_rates_csv": str(resolve(args.candidate_win_rates_csv, root)),
        "static_failure_contexts_csv": str(resolve(args.static_failure_contexts_csv, root)),
        "decision": decision,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "aaai_ready": False,
        "g6_training_allowed": False,
        "learned_runtime_fresh_holdout": "blocked_not_run",
    }
    write_json(resolve(args.summary_json, root), summary)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.5 Oracle Gap\n\n"
        f"- context_count: `{len(oracle)}`\n"
        f"- oracle_beats_static_fraction: `{oracle_fraction}`\n"
        f"- oracle_beats_additive_fraction: `{summary['oracle_beats_additive_fraction']}`\n"
        f"- mean_oracle_gap_over_static: `{mean_gap}`\n"
        f"- static_dominates_all_contexts: `{static_dominates_all}`\n"
        f"- decision: `{decision}`\n\n"
        "This is an observed-ID adaptive-oracle analysis over UpdateLTM candidates, not a learned-runtime performance claim.\n",
    )
    print(json.dumps({"decision": decision, "oracle_beats_static_fraction": oracle_fraction, "contexts": len(oracle)}))
    return 0 if finite_gaps else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
