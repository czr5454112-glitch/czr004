"""Analyze G5.12 candidate-level regret/ranking targets."""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g512_common import (  # noqa: E402
    ADDITIVE_CANDIDATE,
    CLOSED_CLAIMS,
    STATIC_ABSTAIN_CANDIDATE,
    STATIC_FLOW_SHIELD_CANDIDATE,
    boolish,
    count_by,
    finite_number,
    mean,
    observed_id_flags,
    read_csv_rows,
    repo_root,
    resolve,
    write_json,
    write_text,
)


DEFAULT_TARGETS = "outputs/tables/phase5p5_repair5g512_candidate_regret_targets.csv"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g512_candidate_regret_targets.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g512_candidate_regret_targets_summary.json"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--targets-csv", type=Path, default=Path(DEFAULT_TARGETS))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    rows = read_csv_rows(resolve(args.targets_csv, root))
    contexts = {str(row.get("normalized_context_key", "")) for row in rows}
    candidates = {str(row.get("candidate_id", "")) for row in rows}
    labels = count_by(rows, "label_class")
    flags = observed_id_flags(rows)
    static_duplicate_contexts = sum(
        1
        for key in contexts
        if {str(row.get("candidate_id", "")) for row in rows if row.get("normalized_context_key") == key}
        >= {STATIC_FLOW_SHIELD_CANDIDATE, STATIC_ABSTAIN_CANDIDATE}
    )
    by_candidate: dict[str, list[dict[str, object]]] = defaultdict(list)
    by_split = count_by(rows, "split")
    for row in rows:
        by_candidate[str(row.get("candidate_id", ""))].append(row)

    candidate_rows = []
    for candidate, group in sorted(by_candidate.items()):
        deltas = [finite_number(row.get("mean_delta_vs_static_primary"), math.inf) for row in group]
        regrets = [finite_number(row.get("oracle_regret_primary"), math.inf) for row in group]
        ranks = [finite_number(row.get("rank_primary"), math.inf) for row in group]
        candidate_rows.append(
            {
                "candidate_id": candidate,
                "rows": len(group),
                "mean_delta_vs_static_primary": mean(deltas),
                "mean_oracle_regret_primary": mean(regrets),
                "mean_rank_primary": mean(ranks),
                "helpful": sum(1 for row in group if boolish(row.get("helpful_vs_static"))),
                "harmful": sum(1 for row in group if boolish(row.get("harmful_vs_static"))),
                "oracle_wins": sum(1 for row in group if str(row.get("oracle_candidate_for_context", "")) == candidate),
            }
        )
    top_candidates = sorted(candidate_rows, key=lambda row: (row["mean_delta_vs_static_primary"], row["candidate_id"]))[:5]
    gates = {
        "candidate_level_rows_ge_840": len(rows) >= 840,
        "contexts_eq_60": len(contexts) == 60,
        "candidates_eq_14": len(candidates) == 14,
        "helpful_count_gt_0": labels.get("helpful_parameter_candidate", 0) > 0,
        "harmful_count_gt_0": labels.get("harmful_parameter_candidate", 0) > 0,
        "neutral_or_static_count_gt_0": labels.get("neutral_parameter_candidate", 0) + labels.get("static_fallback_candidate", 0) > 0,
        "additive_bad_count_gt_0": labels.get("additive_bad_baseline", 0) > 0,
        "static_alias_duplicate_contexts_reported": static_duplicate_contexts >= 0,
        "observed_ids_only": flags["observed_ids_only"],
        "ids_166_205_untouched": flags["ids_166_205_untouched"],
    }
    decision = "candidate_regret_targets_passed_continue_feature_v3" if all(gates.values()) else "candidate_regret_targets_failed"
    summary = {
        "schema_version": "phase5p5_repair5g512_candidate_regret_targets_summary_v1",
        "decision": decision,
        "candidate_level_rows": len(rows),
        "contexts": len(contexts),
        "candidates": len(candidates),
        "label_counts": labels,
        "split_counts": by_split,
        "helpful_count": labels.get("helpful_parameter_candidate", 0),
        "harmful_count": labels.get("harmful_parameter_candidate", 0),
        "neutral_or_static_count": labels.get("neutral_parameter_candidate", 0) + labels.get("static_fallback_candidate", 0),
        "additive_bad_count": labels.get("additive_bad_baseline", 0),
        "additive_rows": sum(1 for row in rows if row.get("candidate_id") == ADDITIVE_CANDIDATE),
        "static_alias_duplicate_contexts": static_duplicate_contexts,
        "static_alias_target_weight_policy": "split_static_alias_weight_0p5_each",
        "top_mean_delta_candidates": top_candidates,
        "gates": gates,
        **CLOSED_CLAIMS,
    }
    write_json(resolve(args.summary_json, root), summary)
    candidate_lines = "\n".join(
        f"- `{row['candidate_id']}`: mean_delta_vs_static={row['mean_delta_vs_static_primary']:.6f}, "
        f"mean_rank={row['mean_rank_primary']:.3f}, oracle_wins={row['oracle_wins']}"
        for row in top_candidates
    )
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.12 Candidate Regret Target Analysis\n\n"
        f"- decision: `{decision}`\n"
        f"- candidate_level_rows: `{len(rows)}`\n"
        f"- contexts: `{len(contexts)}`\n"
        f"- candidates: `{len(candidates)}`\n"
        f"- label_counts: `{labels}`\n"
        f"- split_counts: `{by_split}`\n"
        f"- static_alias_duplicate_contexts: `{static_duplicate_contexts}`\n"
        f"- gates: `{gates}`\n\n"
        "## Best Mean-Delta Candidates\n\n"
        f"{candidate_lines}\n\n"
        "The candidate-level table exposes helpful and harmful hard negatives inside the same context. "
        "This is the training signal that the G5.11 context-level oracle-class target compressed away.\n",
    )
    print(json.dumps({"decision": decision, "rows": len(rows), "labels": labels}))
    return 0 if decision != "candidate_regret_targets_failed" else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
