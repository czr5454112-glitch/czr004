"""Merge exact replay outcomes into Label-v5.2 set supervision."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Sequence

from .label_v52_set import LabelV52Context, context_from_rows, label_v52_summary


def merge_rows_by_context(
    base_rows: Sequence[dict[str, Any]],
    replay_rows: Sequence[dict[str, Any]],
    *,
    quality_margin: float = 0.0,
    min_verified_coverage: int = 4,
) -> list[LabelV52Context]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in [*base_rows, *replay_rows]:
        uid = str(row.get("g560_evaluation_uid") or row.get("evaluation_uid") or row.get("context_uid") or "")
        if not uid:
            continue
        grouped[uid].append(dict(row))
    return [
        context_from_rows(uid, grouped[uid], quality_margin=quality_margin, min_verified_coverage=min_verified_coverage)
        for uid in sorted(grouped)
    ]


def replay_merge_summary(base_contexts: Sequence[LabelV52Context], merged_contexts: Sequence[LabelV52Context]) -> dict[str, Any]:
    base_by_uid = {context.evaluation_uid: context for context in base_contexts}
    new_contexts = [context for context in merged_contexts if context.evaluation_uid not in base_by_uid]
    expanded_contexts = [
        context
        for context in merged_contexts
        if context.evaluation_uid in base_by_uid
        and context.original_row_count > base_by_uid[context.evaluation_uid].original_row_count
    ]
    summary = label_v52_summary(merged_contexts)
    summary.update(
        {
            "base_contexts": len(base_contexts),
            "merged_contexts": len(merged_contexts),
            "new_unique_contexts": len(new_contexts),
            "expanded_existing_contexts": len(expanded_contexts),
            "true_cycle_merge_semantics": True,
        }
    )
    return summary
