"""Analyze Repair5G.5.5 short-probe budget rank stability."""

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

from repair5g54_common import score_from_label  # noqa: E402
from repair5g55_common import (  # noqa: E402
    G55_STATIC_CANDIDATE,
    normalized_context_key,
    read_jsonl,
    repo_root,
    resolve,
    write_csv_rows,
    write_json,
    write_text,
)


DEFAULT_PROBES = "outputs/logs/phase5p5_repair5g55_probe_budget_stability/phase5p5_repair5g55_probe_budget_update_probes.jsonl"
DEFAULT_RANKS = "outputs/tables/phase5p5_repair5g55_probe_budget_rank_stability.csv"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g55_probe_budget_stability.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g55_probe_budget_stability_summary.json"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--probe-jsonl", type=Path, default=Path(DEFAULT_PROBES))
    parser.add_argument("--rank-stability-csv", type=Path, default=Path(DEFAULT_RANKS))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    return parser.parse_args(argv)


def budget_value(row: dict[str, Any]) -> float:
    value = row.get("short_budget_ms", "")
    try:
        return float(value)
    except (TypeError, ValueError):
        return math.nan


def context_key_text(key: tuple[str, int, int, int, str]) -> str:
    return f"{key[0]}|a{key[1]}|s{key[2]}|it{key[3]}|{key[4]}"


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    rows = read_jsonl(resolve(args.probe_jsonl, root))
    by_context_budget: dict[tuple[tuple[str, int, int, int, str], float], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        budget = budget_value(row)
        if math.isfinite(budget):
            by_context_budget[(normalized_context_key(row), budget)].append(row)

    context_to_budgets: dict[tuple[str, int, int, int, str], dict[float, list[dict[str, Any]]]] = defaultdict(dict)
    for (context_key, budget), budget_rows in by_context_budget.items():
        context_to_budgets[context_key][budget] = budget_rows

    table_rows: list[dict[str, Any]] = []
    stable_contexts = 0
    sign_stable_contexts = 0
    unstable_contexts = 0
    for context_key, budget_map in sorted(context_to_budgets.items()):
        oracle_by_budget: dict[float, str] = {}
        sign_by_budget: dict[float, str] = {}
        ranked_by_budget: dict[float, list[tuple[float, dict[str, Any]]]] = {}
        for budget, budget_rows in sorted(budget_map.items()):
            ranked = sorted(
                ((score_from_label(row), row) for row in budget_rows),
                key=lambda item: (item[0], str(item[1].get("candidate_id", ""))),
            )
            ranked_by_budget[budget] = ranked
            best_score, best_row = ranked[0] if ranked else (math.inf, {})
            static = next((row for row in budget_rows if row.get("candidate_id") == G55_STATIC_CANDIDATE), {})
            static_score = score_from_label(static) if static else math.inf
            oracle_by_budget[budget] = str(best_row.get("candidate_id", ""))
            if math.isfinite(best_score) and math.isfinite(static_score):
                sign_by_budget[budget] = "oracle_beats_static" if best_score < static_score - 1.0e-12 else "static_ties_or_beats"
            else:
                sign_by_budget[budget] = "unmeasured"

        oracle_stable = len(set(oracle_by_budget.values())) == 1 if oracle_by_budget else False
        sign_stable = len(set(sign_by_budget.values())) == 1 if sign_by_budget else False
        training_eligible = oracle_stable and sign_stable and len(budget_map) >= 2
        stable_contexts += int(training_eligible)
        sign_stable_contexts += int(sign_stable and len(budget_map) >= 2)
        unstable_contexts += int((not training_eligible) and len(budget_map) >= 2)

        for budget, ranked in sorted(ranked_by_budget.items()):
            for rank, (score, row) in enumerate(ranked, start=1):
                table_rows.append(
                    {
                        "normalized_context_key": context_key_text(context_key),
                        "map": context_key[0],
                        "agents": context_key[1],
                        "seed": context_key[2],
                        "iteration": context_key[3],
                        "traffic_before_hash_full": context_key[4],
                        "short_budget_ms": budget,
                        "candidate_id": row.get("candidate_id", ""),
                        "rank": rank,
                        "probe_sum_of_loss_ratio": score if math.isfinite(score) else "",
                        "oracle_candidate_id_for_budget": oracle_by_budget.get(budget, ""),
                        "static_vs_oracle_sign_for_budget": sign_by_budget.get(budget, ""),
                        "oracle_candidate_stable_across_budgets": oracle_stable,
                        "static_vs_oracle_sign_stable_across_budgets": sign_stable,
                        "training_eligible_label": training_eligible,
                    }
                )

    write_csv_rows(resolve(args.rank_stability_csv, root), table_rows)
    measured_contexts = sum(1 for budgets in context_to_budgets.values() if len(budgets) >= 2)
    summary = {
        "schema_version": "phase5p5_repair5g55_probe_budget_stability_summary_v1",
        "probe_rows": len(rows),
        "measured_contexts": measured_contexts,
        "budget_values_ms": sorted({budget for _key, budget in by_context_budget}),
        "candidate_rank_stability_measured": measured_contexts > 0 and bool(table_rows),
        "oracle_candidate_stability_measured": measured_contexts > 0,
        "static_vs_oracle_sign_stability_measured": measured_contexts > 0,
        "training_eligible_stable_contexts": stable_contexts,
        "sign_stable_contexts": sign_stable_contexts,
        "unstable_contexts": unstable_contexts,
        "unstable_labels_separated_from_training_eligible": bool(table_rows),
        "rank_stability_csv": str(resolve(args.rank_stability_csv, root)),
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "aaai_ready": False,
        "g6_training_allowed": False,
    }
    gates = {
        "candidate_rank_stability_measured": summary["candidate_rank_stability_measured"],
        "oracle_candidate_stability_measured": summary["oracle_candidate_stability_measured"],
        "static_vs_oracle_sign_stability_measured": summary["static_vs_oracle_sign_stability_measured"],
        "unstable_labels_separated_from_training_eligible": summary["unstable_labels_separated_from_training_eligible"],
    }
    summary["gates"] = gates
    summary["probe_budget_stability_measured"] = all(gates.values())
    write_json(resolve(args.summary_json, root), summary)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.5 Probe Budget Stability\n\n"
        f"- measured_contexts: `{measured_contexts}`\n"
        f"- budget_values_ms: `{summary['budget_values_ms']}`\n"
        f"- training_eligible_stable_contexts: `{stable_contexts}`\n"
        f"- unstable_contexts: `{unstable_contexts}`\n"
        f"- probe_budget_stability_measured: `{summary['probe_budget_stability_measured']}`\n\n"
        "Unstable labels are marked out of any future training-eligible pool. No G6 training is authorized here.\n",
    )
    print(json.dumps({"probe_budget_stability_measured": summary["probe_budget_stability_measured"], "measured_contexts": measured_contexts}))
    return 0 if summary["probe_budget_stability_measured"] else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
