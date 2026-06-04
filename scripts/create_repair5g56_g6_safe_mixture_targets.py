"""Construct Repair5G.5.6 safe-mixture oracle targets."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g56_common import (  # noqa: E402
    G56_ADDITIVE_CANDIDATE,
    G56_EPSILON_MARGIN,
    G56_HARMFUL_MARGIN,
    G56_STATIC_CANDIDATE,
    best_label_row,
    finite_number,
    group_by_context,
    json_dumps_compact,
    normalized_context_key_text,
    read_csv_rows,
    repo_root,
    resolve,
    score_from_label,
    static_additive_rows,
    validate_observed_rows,
    write_csv_rows,
    write_json,
    write_text,
)


DEFAULT_LABELS = "outputs/tables/phase5p5_repair5g56_counterfactual_update_labels.csv"
DEFAULT_STABLE = "outputs/tables/phase5p5_repair5g56_training_eligible_stable_contexts.csv"
DEFAULT_TARGETS = "outputs/tables/phase5p5_repair5g56_g6_safe_mixture_targets.csv"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g56_g6_target_construction.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g56_g6_target_construction_summary.json"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--labels-csv", type=Path, default=Path(DEFAULT_LABELS))
    parser.add_argument("--stable-contexts-csv", type=Path, default=Path(DEFAULT_STABLE))
    parser.add_argument("--targets-csv", type=Path, default=Path(DEFAULT_TARGETS))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    parser.add_argument("--epsilon-margin", type=float, default=G56_EPSILON_MARGIN)
    parser.add_argument("--harmful-margin", type=float, default=G56_HARMFUL_MARGIN)
    return parser.parse_args(argv)


def stable_keys(rows: list[dict[str, str]]) -> set[str]:
    keys = set()
    for row in rows:
        key = str(row.get("normalized_context_key", ""))
        if key:
            keys.add(key)
    return keys


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    labels = read_csv_rows(resolve(args.labels_csv, root))
    stable = stable_keys(read_csv_rows(resolve(args.stable_contexts_csv, root)))
    targets = []
    for context_id, rows in sorted(group_by_context(labels).items()):
        first = rows[0]
        context_key = normalized_context_key_text(first)
        best_score, best = best_label_row(rows)
        static, additive = static_additive_rows(rows)
        static_score = score_from_label(static) if static else math.inf
        additive_score = score_from_label(additive) if additive else math.inf
        no_solution = not math.isfinite(best_score)
        delta_vs_static = best_score - static_score if math.isfinite(best_score) and math.isfinite(static_score) else math.nan
        delta_vs_additive = best_score - additive_score if math.isfinite(best_score) and math.isfinite(additive_score) else math.nan
        candidate_regret = {}
        harmful = []
        for row in rows:
            candidate = str(row.get("candidate_id", ""))
            score = score_from_label(row)
            if math.isfinite(score) and math.isfinite(best_score):
                candidate_regret[candidate] = score - best_score
            else:
                candidate_regret[candidate] = None
            if math.isfinite(score) and math.isfinite(static_score) and score > static_score + float(args.harmful_margin):
                harmful.append(candidate)
        stable_label = context_key in stable
        abstain_to_static = (
            no_solution
            or not math.isfinite(delta_vs_static)
            or delta_vs_static >= -float(args.epsilon_margin)
            or str(best.get("candidate_id", "")) == G56_STATIC_CANDIDATE
        )
        training_eligible = stable_label and not no_solution
        if abstain_to_static:
            oracle_candidate_id = G56_STATIC_CANDIDATE
        else:
            oracle_candidate_id = str(best.get("candidate_id", ""))
        margin = abs(delta_vs_static) if math.isfinite(delta_vs_static) else 0.0
        train_weight = 0.0 if not training_eligible else min(5.0, 1.0 + margin * 100.0)
        targets.append(
            {
                "context_id": context_id,
                "normalized_context_key": context_key,
                "map": first.get("map", ""),
                "agents": first.get("agents", ""),
                "seed": first.get("seed", ""),
                "iteration": first.get("iteration", ""),
                "traffic_before_hash_full": first.get("traffic_before_hash_full", ""),
                "oracle_candidate_id": oracle_candidate_id,
                "raw_best_candidate_id": best.get("candidate_id", ""),
                "delta_vs_static": delta_vs_static if math.isfinite(delta_vs_static) else "",
                "delta_vs_additive": delta_vs_additive if math.isfinite(delta_vs_additive) else "",
                "candidate_regret": json_dumps_compact(candidate_regret),
                "harmful_vs_static": bool(harmful),
                "harmful_candidate_ids": ",".join(sorted(harmful)),
                "stable_label": stable_label,
                "abstain_to_static": abstain_to_static,
                "training_eligible": training_eligible,
                "train_weight": train_weight,
                "no_solution_context": no_solution,
            }
        )
    write_csv_rows(resolve(args.targets_csv, root), targets)
    training = [row for row in targets if str(row.get("training_eligible")).lower() == "true" or row.get("training_eligible") is True]
    nonstatic_training = [row for row in training if row.get("oracle_candidate_id") not in {"", G56_STATIC_CANDIDATE}]
    static_fallback = [row for row in targets if str(row.get("abstain_to_static")).lower() == "true" or row.get("abstain_to_static") is True]
    harmful_rows = [row for row in targets if str(row.get("harmful_vs_static")).lower() == "true" or row.get("harmful_vs_static") is True]
    gates = {
        "training_eligible_contexts_ge_30": len(training) >= 30,
        "nonstatic_training_eligible_contexts_gt_0": len(nonstatic_training) > 0,
        "static_fallback_contexts_gt_0": len(static_fallback) > 0,
        "harmful_candidate_labels_available": len(harmful_rows) > 0,
        "observed_ids_only": validate_observed_rows(labels, label="Repair5G.5.6 safe-mixture targets"),
    }
    gates["ids_166_205_untouched"] = gates["observed_ids_only"]
    gates["g6_targets_ready"] = all(gates.values())
    summary = {
        "schema_version": "phase5p5_repair5g56_g6_target_construction_summary_v1",
        "target_rows": len(targets),
        "training_eligible_contexts": len(training),
        "nonstatic_training_eligible_contexts": len(nonstatic_training),
        "static_fallback_contexts": len(static_fallback),
        "harmful_label_contexts": len(harmful_rows),
        "targets_csv": str(resolve(args.targets_csv, root)),
        "gates": gates,
        "decision": "g6_targets_ready" if gates["g6_targets_ready"] else "g6_targets_not_training_ready",
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "aaai_ready": False,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.6 G6 Target Construction\n\n"
        f"- target_rows: `{len(targets)}`\n"
        f"- training_eligible_contexts: `{len(training)}`\n"
        f"- nonstatic_training_eligible_contexts: `{len(nonstatic_training)}`\n"
        f"- static_fallback_contexts: `{len(static_fallback)}`\n"
        f"- harmful_label_contexts: `{len(harmful_rows)}`\n"
        f"- g6_targets_ready: `{gates['g6_targets_ready']}`\n\n"
        "Budget-unstable and no-solution contexts are kept for diagnostics but excluded from training eligibility.\n",
    )
    print(json.dumps({"decision": summary["decision"], "training_eligible_contexts": len(training)}))
    return 0 if gates["observed_ids_only"] and bool(targets) else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
