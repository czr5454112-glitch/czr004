"""Analyze Repair5G.5.4 counterfactual oracle gap over static flow-shield."""

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

from repair5g2_common import read_csv_rows  # noqa: E402
from repair5g3_common import number, repo_root, resolve, write_csv_rows  # noqa: E402
from repair5g54_common import load_json, write_json, write_text  # noqa: E402


DEFAULT_LABEL_SUMMARY = "outputs/reports/phase5p5_repair5g54_counterfactual_label_summary.json"
DEFAULT_LABELS = "outputs/tables/phase5p5_repair5g54_counterfactual_update_labels.csv"
DEFAULT_ORACLE = "outputs/tables/phase5p5_repair5g54_counterfactual_oracle_by_context.csv"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g54_counterfactual_oracle_gap.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g54_counterfactual_oracle_gap_summary.json"
DEFAULT_BY_MAP_AGENT = "outputs/tables/phase5p5_repair5g54_counterfactual_oracle_gap_by_map_agent.csv"
DEFAULT_WIN_RATES = "outputs/tables/phase5p5_repair5g54_candidate_win_rates.csv"
DEFAULT_PATTERNS = "outputs/tables/phase5p5_repair5g54_context_feature_oracle_patterns.csv"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label-summary-json", type=Path, default=Path(DEFAULT_LABEL_SUMMARY))
    parser.add_argument("--labels-csv", type=Path, default=Path(DEFAULT_LABELS))
    parser.add_argument("--oracle-csv", type=Path, default=Path(DEFAULT_ORACLE))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    parser.add_argument("--by-map-agent-csv", type=Path, default=Path(DEFAULT_BY_MAP_AGENT))
    parser.add_argument("--candidate-win-rates-csv", type=Path, default=Path(DEFAULT_WIN_RATES))
    parser.add_argument("--context-patterns-csv", type=Path, default=Path(DEFAULT_PATTERNS))
    return parser.parse_args(argv)


def by_map_agent_rows(oracle: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in oracle:
        groups[(str(row.get("map", "")), str(row.get("agents", "")))].append(row)
    out: list[dict[str, Any]] = []
    for (map_name, agents), rows in sorted(groups.items()):
        gaps = [number(row.get("oracle_gap_over_static"), math.nan) for row in rows]
        finite = [value for value in gaps if math.isfinite(value)]
        wins = [row for row in rows if number(row.get("oracle_gap_over_static"), math.inf) < -1.0e-12]
        out.append(
            {
                "map": map_name,
                "agents": agents,
                "contexts": len(rows),
                "oracle_beats_static_contexts": len(wins),
                "oracle_beats_static_fraction": len(wins) / len(rows) if rows else 0.0,
                "mean_oracle_gap_over_static": sum(finite) / len(finite) if finite else "",
                "min_oracle_gap_over_static": min(finite) if finite else "",
                "max_oracle_gap_over_static": max(finite) if finite else "",
            }
        )
    return out


def win_rate_rows(oracle: list[dict[str, Any]], labels: list[dict[str, Any]]) -> list[dict[str, Any]]:
    wins = Counter(str(row.get("oracle_candidate_id", "")) for row in oracle)
    candidates = sorted({str(row.get("candidate_id", "")) for row in labels if row.get("candidate_id")})
    total_contexts = len(oracle)
    out: list[dict[str, Any]] = []
    for candidate in candidates:
        out.append(
            {
                "candidate_id": candidate,
                "oracle_win_contexts": wins.get(candidate, 0),
                "oracle_win_rate": wins.get(candidate, 0) / total_contexts if total_contexts else 0.0,
            }
        )
    return out


def pattern_rows(oracle: list[dict[str, Any]], labels: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_context = {str(row.get("context_id", "")): row for row in oracle}
    traces: dict[str, list[float]] = defaultdict(list)
    runtimes: dict[str, list[float]] = defaultdict(list)
    for row in labels:
        context_id = str(row.get("context_id", ""))
        oracle_row = by_context.get(context_id)
        if not oracle_row:
            continue
        key = str(oracle_row.get("oracle_candidate_id", ""))
        trace_count = number(row.get("trace_event_count"), math.nan)
        runtime = number(row.get("probe_runtime_ms"), math.nan)
        if math.isfinite(trace_count):
            traces[key].append(trace_count)
        if math.isfinite(runtime):
            runtimes[key].append(runtime)
    out: list[dict[str, Any]] = []
    for candidate in sorted(set(traces) | set(runtimes)):
        trace_values = traces.get(candidate, [])
        runtime_values = runtimes.get(candidate, [])
        out.append(
            {
                "oracle_candidate_id": candidate,
                "contexts": sum(1 for row in oracle if row.get("oracle_candidate_id") == candidate),
                "mean_trace_event_count": sum(trace_values) / len(trace_values) if trace_values else "",
                "mean_probe_runtime_ms": sum(runtime_values) / len(runtime_values) if runtime_values else "",
            }
        )
    return out


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    label_summary = load_json(resolve(args.label_summary_json, root))
    labels = read_csv_rows(resolve(args.labels_csv, root))
    oracle = read_csv_rows(resolve(args.oracle_csv, root))
    by_group = by_map_agent_rows(oracle)
    wins = win_rate_rows(oracle, labels)
    patterns = pattern_rows(oracle, labels)
    write_csv_rows(resolve(args.by_map_agent_csv, root), by_group)
    write_csv_rows(resolve(args.candidate_win_rates_csv, root), wins)
    write_csv_rows(resolve(args.context_patterns_csv, root), patterns)
    gaps = [number(row.get("oracle_gap_over_static"), math.nan) for row in oracle]
    finite = [value for value in gaps if math.isfinite(value)]
    oracle_beats_static = [value for value in finite if value < -1.0e-12]
    static_dominates_all = bool(oracle) and not oracle_beats_static
    adaptive_gap_found = bool(oracle_beats_static)
    summary = {
        "schema_version": "phase5p5_repair5g54_counterfactual_oracle_gap_summary_v1",
        "counterfactual_labels_passed": bool(label_summary.get("gates", {}).get("counterfactual_labels_passed")),
        "context_count": len(oracle),
        "label_rows": len(labels),
        "oracle_gap_over_static_measured": bool(finite),
        "oracle_beats_static_contexts": len(oracle_beats_static),
        "oracle_beats_static_fraction": len(oracle_beats_static) / len(oracle) if oracle else 0.0,
        "mean_oracle_gap_over_static": sum(finite) / len(finite) if finite else None,
        "static_dominates_all_contexts": static_dominates_all,
        "adaptive_gap_found": adaptive_gap_found,
        "decision": "counterfactual_labels_available_adaptive_gap_found" if adaptive_gap_found else "counterfactual_labels_available_static_dominates",
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "aaai_ready": False,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.4 Counterfactual Oracle Gap\n\n"
        f"- context_count: `{len(oracle)}`\n"
        f"- oracle_gap_over_static_measured: `{bool(finite)}`\n"
        f"- oracle_beats_static_contexts: `{len(oracle_beats_static)}`\n"
        f"- oracle_beats_static_fraction: `{summary['oracle_beats_static_fraction']}`\n"
        f"- static_dominates_all_contexts: `{static_dominates_all}`\n"
        f"- adaptive_gap_found: `{adaptive_gap_found}`\n"
        f"- decision: `{summary['decision']}`\n\n"
        "This is an observed-ID diagnostic oracle analysis only, not a learned-runtime claim.\n",
    )
    print(json.dumps({"adaptive_gap_found": adaptive_gap_found, "contexts": len(oracle)}))
    return 0 if finite else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
