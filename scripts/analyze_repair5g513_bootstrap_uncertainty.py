"""Bootstrap small-sample uncertainty for Repair5G.5.13 dev-context policies."""

from __future__ import annotations

import argparse
import json
import math
import random
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g512_common import finite_number, mean, repo_root, resolve, write_csv_rows, write_json, write_text  # noqa: E402
from repair5g513_common import G513_CLOSED_CLAIMS  # noqa: E402
from repair5g512_common import read_csv_rows  # noqa: E402


DEFAULT_INPUT = "outputs/tables/phase5p5_repair5g513_hard_control_eval.csv"
DEFAULT_OUTPUT = "outputs/tables/phase5p5_repair5g513_bootstrap_uncertainty.csv"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g513_bootstrap_uncertainty.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g513_bootstrap_uncertainty_summary.json"
POLICIES = [
    "g512_ranker",
    "safe_slow_decay_train_gate",
    "safe_train_only_map_agent_gate",
]
METRICS = [
    "mean_delta_vs_static",
    "mean_delta_vs_additive",
    "harmful_vs_static_rate",
    "coverage",
    "regret_to_oracle",
]
SEED = 20260607


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hard-control-csv", type=Path, default=Path(DEFAULT_INPUT))
    parser.add_argument("--output-csv", type=Path, default=Path(DEFAULT_OUTPUT))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    parser.add_argument("--bootstrap-samples", type=int, default=2000)
    return parser.parse_args(argv)


def context_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [row for row in rows if row.get("row_type") == "context_decision"]


def metric_value(row: dict[str, Any], metric: str) -> float:
    if metric == "harmful_vs_static_rate":
        return finite_number(row.get("harmful_vs_static"), math.inf)
    return finite_number(row.get(metric), math.inf)


def aggregate(rows: list[dict[str, Any]], metric: str) -> float:
    return mean(metric_value(row, metric) for row in rows)


def percentile(values: list[float], pct: float) -> float:
    finite = sorted(value for value in values if math.isfinite(value))
    if not finite:
        return math.inf
    if len(finite) == 1:
        return finite[0]
    position = (len(finite) - 1) * pct
    low = math.floor(position)
    high = math.ceil(position)
    if low == high:
        return finite[low]
    return finite[low] * (high - position) + finite[high] * (position - low)


def build_index(rows: list[dict[str, Any]]) -> dict[str, dict[str, dict[str, Any]]]:
    index: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in rows:
        policy = str(row.get("policy", ""))
        key = str(row.get("normalized_context_key", ""))
        if policy and key:
            index[policy][key] = row
    return dict(index)


def bootstrap_metric(
    index: dict[str, dict[str, dict[str, Any]]],
    contexts: list[str],
    metric: str,
    policy: str,
    rng: random.Random,
    samples: int,
) -> list[float]:
    values = []
    for _ in range(samples):
        draw = [rng.choice(contexts) for _ in contexts]
        values.append(aggregate([index[policy][key] for key in draw], metric))
    return values


def bootstrap_difference(
    index: dict[str, dict[str, dict[str, Any]]],
    contexts: list[str],
    metric: str,
    lhs: str,
    rhs: str,
    rng: random.Random,
    samples: int,
) -> list[float]:
    values = []
    for _ in range(samples):
        draw = [rng.choice(contexts) for _ in contexts]
        lhs_value = aggregate([index[lhs][key] for key in draw], metric)
        rhs_value = aggregate([index[rhs][key] for key in draw], metric)
        values.append(lhs_value - rhs_value)
    return values


def interval_row(row_type: str, policy: str, metric: str, estimate: float, samples: list[float], rhs_policy: str = "") -> dict[str, Any]:
    return {
        "row_type": row_type,
        "policy": policy,
        "rhs_policy": rhs_policy,
        "metric": metric,
        "estimate": estimate,
        "ci_low_p025": percentile(samples, 0.025),
        "ci_high_p975": percentile(samples, 0.975),
        "bootstrap_samples": len(samples),
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    rows = read_csv_rows(resolve(args.hard_control_csv, root))
    per_context = context_rows(rows)
    index = build_index(per_context)
    contexts = sorted(set.intersection(*(set(index[policy]) for policy in POLICIES)))
    rng = random.Random(SEED)
    output_rows: list[dict[str, Any]] = []
    for policy in POLICIES:
        for metric in METRICS:
            estimate = aggregate([index[policy][key] for key in contexts], metric)
            samples = bootstrap_metric(index, contexts, metric, policy, rng, args.bootstrap_samples)
            output_rows.append(interval_row("policy_interval", policy, metric, estimate, samples))

    for rhs in ["safe_slow_decay_train_gate", "safe_train_only_map_agent_gate"]:
        samples = bootstrap_difference(
            index,
            contexts,
            "mean_delta_vs_static",
            "g512_ranker",
            rhs,
            rng,
            args.bootstrap_samples,
        )
        estimate = aggregate([index["g512_ranker"][key] for key in contexts], "mean_delta_vs_static") - aggregate(
            [index[rhs][key] for key in contexts], "mean_delta_vs_static"
        )
        output_rows.append(
            interval_row(
                "policy_difference_interval",
                "g512_ranker",
                "difference_vs_control_mean_delta_vs_static",
                estimate,
                samples,
                rhs_policy=rhs,
            )
        )

    write_csv_rows(resolve(args.output_csv, root), output_rows)
    by_key = {(row["policy"], row["rhs_policy"], row["metric"]): row for row in output_rows}
    summary = {
        "schema_version": "phase5p5_repair5g513_bootstrap_uncertainty_summary_v1",
        "decision": "bootstrap_uncertainty_reported",
        "dev_contexts": len(contexts),
        "bootstrap_samples": args.bootstrap_samples,
        "g512_mean_delta_vs_static_interval": by_key[("g512_ranker", "", "mean_delta_vs_static")],
        "g512_harmful_vs_static_rate_interval": by_key[("g512_ranker", "", "harmful_vs_static_rate")],
        "g512_coverage_interval": by_key[("g512_ranker", "", "coverage")],
        "g512_regret_to_oracle_interval": by_key[("g512_ranker", "", "regret_to_oracle")],
        "difference_vs_safe_slow_decay_train_gate": by_key[
            ("g512_ranker", "safe_slow_decay_train_gate", "difference_vs_control_mean_delta_vs_static")
        ],
        "difference_vs_safe_train_only_map_agent_gate": by_key[
            ("g512_ranker", "safe_train_only_map_agent_gate", "difference_vs_control_mean_delta_vs_static")
        ],
        **G513_CLOSED_CLAIMS,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.13 Bootstrap Uncertainty\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- dev_contexts: `{len(contexts)}`\n"
        f"- bootstrap_samples: `{args.bootstrap_samples}`\n"
        f"- g512_mean_delta_vs_static_interval: `{summary['g512_mean_delta_vs_static_interval']}`\n"
        f"- g512_harmful_vs_static_rate_interval: `{summary['g512_harmful_vs_static_rate_interval']}`\n"
        f"- g512_coverage_interval: `{summary['g512_coverage_interval']}`\n"
        f"- g512_regret_to_oracle_interval: `{summary['g512_regret_to_oracle_interval']}`\n"
        f"- difference_vs_safe_slow_decay_train_gate: `{summary['difference_vs_safe_slow_decay_train_gate']}`\n"
        f"- difference_vs_safe_train_only_map_agent_gate: `{summary['difference_vs_safe_train_only_map_agent_gate']}`\n"
        "- runtime_claim_allowed: `false`\n\n"
        "Intervals are nonparametric bootstraps over dev contexts. Negative differences in mean delta mean the G5.12 ranker is better than the control; positive differences mean the control has lower selected-vs-static delta on the sampled contexts.\n",
    )
    print(json.dumps({"decision": summary["decision"], "dev_contexts": len(contexts), "bootstrap_samples": args.bootstrap_samples}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
