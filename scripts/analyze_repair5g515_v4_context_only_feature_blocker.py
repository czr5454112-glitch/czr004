"""Audit why G5.14 context-only rich features cannot rank candidates."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g512_common import read_csv_rows, repo_root, resolve, write_json, write_text  # noqa: E402
from repair5g513_common import grouped_contexts  # noqa: E402
from repair5g515_common import (  # noqa: E402
    DEFAULT_V4_MATRIX,
    G515_CLOSED_CLAIMS,
    count_candidate_varying,
    feature_columns,
    feature_varies_within_any_context,
    interaction_feature_names,
)


DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g515_v4_context_only_feature_blocker.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g515_v4_context_only_feature_blocker_summary.json"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--v4-csv", type=Path, default=Path(DEFAULT_V4_MATRIX))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    return parser.parse_args(argv)


def constant_context_count(rows: list[dict[str, object]], feature: str) -> int:
    count = 0
    for group in grouped_contexts(rows).values():
        values = {str(row.get(feature, "")) for row in group}
        if len(values) <= 1:
            count += 1
    return count


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    rows = read_csv_rows(resolve(args.v4_csv, root))
    features = feature_columns(rows)
    contexts = grouped_contexts(rows)
    rich_features = [name for name in features if name.startswith("feature_rich_")]
    rich_inventory = [
        {
            "feature": feature,
            "constant_contexts": constant_context_count(rows, feature),
            "contexts": len(contexts),
            "constant_within_all_contexts": not feature_varies_within_any_context(rows, feature),
        }
        for feature in rich_features
    ]
    context_only_rich_feature_count = sum(1 for row in rich_inventory if row["constant_within_all_contexts"])
    candidate_varying_feature_count = count_candidate_varying(rows, features)
    candidate_varying_interaction_feature_count = count_candidate_varying(rows, interaction_feature_names(rows))
    candidate_varying_rich_interaction_count = count_candidate_varying(
        rows, [name for name in features if name.startswith("feature_interaction_rich_")]
    )
    ranking_signal_blocker_confirmed = (
        len(rich_features) > 0
        and context_only_rich_feature_count == len(rich_features)
        and candidate_varying_rich_interaction_count == 0
    )
    decision = (
        "v4_context_only_rich_feature_blocker_confirmed_continue_interactions"
        if ranking_signal_blocker_confirmed
        else "v4_context_only_rich_feature_blocker_not_confirmed_review_features"
    )
    summary = {
        "schema_version": "phase5p5_repair5g515_v4_context_only_feature_blocker_summary_v1",
        "decision": decision,
        "contexts": len(contexts),
        "feature_count": len(features),
        "rich_feature_count": len(rich_features),
        "context_only_rich_feature_count": context_only_rich_feature_count,
        "candidate_varying_feature_count": candidate_varying_feature_count,
        "candidate_varying_interaction_feature_count": candidate_varying_interaction_feature_count,
        "candidate_varying_rich_interaction_feature_count": candidate_varying_rich_interaction_count,
        "ranking_signal_blocker_confirmed": ranking_signal_blocker_confirmed,
        "rich_feature_inventory": rich_inventory,
        **G515_CLOSED_CLAIMS,
    }
    write_json(resolve(args.summary_json, root), summary)
    inventory_lines = "\n".join(
        f"- `{row['feature']}`: constant_contexts `{row['constant_contexts']}/{row['contexts']}`"
        for row in rich_inventory
    )
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.15 V4 Context-Only Rich Feature Blocker\n\n"
        f"- decision: `{decision}`\n"
        f"- rich_feature_count: `{len(rich_features)}`\n"
        f"- context_only_rich_feature_count: `{context_only_rich_feature_count}`\n"
        f"- candidate_varying_feature_count: `{candidate_varying_feature_count}`\n"
        f"- candidate_varying_interaction_feature_count: `{candidate_varying_interaction_feature_count}`\n"
        f"- candidate_varying_rich_interaction_feature_count: `{candidate_varying_rich_interaction_count}`\n"
        f"- ranking_signal_blocker_confirmed: `{ranking_signal_blocker_confirmed}`\n"
        "- runtime_claim_allowed: `false`\n\n"
        "The recovered `feature_rich_*` values are constant across all 14 candidate rows inside the same context. "
        "A linear candidate scorer can use those context-only values to shift a nonstatic/fallback gate, but the same offset applies to every candidate in that context and therefore cannot provide candidate-ordering evidence by itself. "
        "G5.15 must add rich-context by candidate-parameter interaction features before using rich trace dynamics as ranking evidence.\n\n"
        "## Rich Feature Inventory\n\n"
        f"{inventory_lines}\n",
    )
    print(json.dumps({"decision": decision, "context_only_rich_feature_count": context_only_rich_feature_count}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
