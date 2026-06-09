"""Create the stratified G5.22 observed-ID context panel."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, OrderedDict, defaultdict
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g522_common import (  # noqa: E402
    G520_SECOND_WAVE_CONTEXTS_CSV,
    G520_TARGETS_CSV,
    G521_CANDIDATE_TARGETS_CSV,
    G521_CONTEXT_TARGETS_CSV,
    G521_GAP_HARMFUL_CSV,
    G521_GAP_MISSED_CSV,
    G521_TARGETED_CONTEXTS_CSV,
    G522_CLOSED_CLAIMS,
    G522_CONTEXT_PANEL_BUCKET_CSV,
    G522_CONTEXT_PANEL_CSV,
    G522_CONTEXT_PANEL_REPORT,
    G522_CONTEXT_PANEL_SUMMARY,
    boolish,
    finite_number,
    map_agent_key,
    map_family,
    observed_id_flags,
    observed_id_guard,
    read_rows,
    write_json_file,
    write_rows,
    write_text_file,
)

BUCKET_LIMITS = [
    ("new_opportunity_contexts", 16),
    ("static_recovery_contexts", 6),
    ("candidate_induced_risk_contexts", 6),
    ("static_near_oracle_or_no_new_safe_contexts", 4),
    ("unavoidable_failure_controls", 4),
]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-csv", type=Path, default=Path(G522_CONTEXT_PANEL_CSV))
    parser.add_argument("--bucket-summary-csv", type=Path, default=Path(G522_CONTEXT_PANEL_BUCKET_CSV))
    parser.add_argument("--report", type=Path, default=Path(G522_CONTEXT_PANEL_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(G522_CONTEXT_PANEL_SUMMARY))
    return parser.parse_args(argv)


def normalize(row: dict[str, Any], bucket: str, reason: str) -> dict[str, Any]:
    return {
        "normalized_context_key": row.get("normalized_context_key", ""),
        "map": row.get("map", ""),
        "agents": int(finite_number(row.get("agents"), 0)),
        "seed": int(finite_number(row.get("seed"), 0)),
        "iteration": int(finite_number(row.get("iteration"), 0)),
        "traffic_before_hash_full": row.get("traffic_before_hash_full", ""),
        "map_agent_group": row.get("map_agent_group", map_agent_key(row)),
        "map_family": row.get("map_family", map_family(str(row.get("map", "")))),
        "context_bucket": bucket,
        "context_reason": reason,
        "observed_ids_only": True,
        "ids_166_205_untouched": True,
        **G522_CLOSED_CLAIMS,
    }


def add_bucket(panel: OrderedDict[str, dict[str, Any]], source: list[dict[str, Any]], bucket: str, limit: int, reason: str) -> int:
    added = 0
    for row in source:
        key = str(row.get("normalized_context_key", ""))
        if not key or key in panel:
            continue
        panel[key] = normalize(row, bucket, reason)
        added += 1
        if added >= limit:
            break
    return added


def unique_context_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: OrderedDict[str, dict[str, Any]] = OrderedDict()
    for row in rows:
        key = str(row.get("normalized_context_key", ""))
        if key and key not in out:
            out[key] = row
    return list(out.values())


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    context_targets = unique_context_rows(read_rows(G521_CONTEXT_TARGETS_CSV))
    candidate_targets = read_rows(G521_CANDIDATE_TARGETS_CSV)
    g520_targets = read_rows(G520_TARGETS_CSV)
    targeted_contexts = unique_context_rows(read_rows(G521_TARGETED_CONTEXTS_CSV))
    missed = unique_context_rows(read_rows(G521_GAP_MISSED_CSV) + read_rows(G520_SECOND_WAVE_CONTEXTS_CSV))
    harmful = unique_context_rows(read_rows(G521_GAP_HARMFUL_CSV))
    by_context_target = {str(row.get("normalized_context_key", "")): row for row in context_targets + targeted_contexts + g520_targets}
    candidate_by_context: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in candidate_targets:
        candidate_by_context[str(row.get("normalized_context_key", ""))].append(row)

    recovery = []
    risk = []
    static_near = []
    unavoidable = []
    for key, rows in sorted(candidate_by_context.items()):
        base = by_context_target.get(key, rows[0])
        if any(boolish(row.get("candidate_recovers_static_no_solution")) for row in rows):
            recovery.append(base)
        if any(boolish(row.get("candidate_induced_no_solution")) for row in rows):
            risk.append(base)
        if not any(boolish(row.get("candidate_safe_policy_positive")) for row in rows):
            static_near.append(base)
        if str(base.get("map", "")).startswith("warehouse") and not any(boolish(row.get("candidate_finite_primary_pair")) for row in rows):
            unavoidable.append(base)
    for row in harmful:
        if str(row.get("normalized_context_key", "")) not in {str(x.get("normalized_context_key", "")) for x in risk}:
            risk.append(by_context_target.get(str(row.get("normalized_context_key", "")), row))

    panel: OrderedDict[str, dict[str, Any]] = OrderedDict()
    added_by_bucket = {
        "new_opportunity_contexts": add_bucket(panel, missed + targeted_contexts, "new_opportunity_contexts", 16, "G5.20/G5.21 missed new opportunity or targeted second-wave context"),
        "static_recovery_contexts": add_bucket(panel, recovery, "static_recovery_contexts", 6, "At least one observed candidate recovers static no-solution"),
        "candidate_induced_risk_contexts": add_bucket(panel, risk, "candidate_induced_risk_contexts", 6, "Static finite or controlled context with candidate-induced no-solution risk"),
        "static_near_oracle_or_no_new_safe_contexts": add_bucket(panel, static_near, "static_near_oracle_or_no_new_safe_contexts", 4, "No safe new candidate positive label or old/static hard to beat"),
        "unavoidable_failure_controls": add_bucket(panel, unavoidable, "unavoidable_failure_controls", 4, "Warehouse/no-solution control with no finite candidate evidence"),
    }
    contexts = list(panel.values())[:36]
    observed_id_guard([row["seed"] for row in contexts], label="G5.22 context panel")
    flags = observed_id_flags(contexts)
    bucket_counts = Counter(str(row.get("context_bucket", "")) for row in contexts)
    bucket_rows = [
        {
            "context_bucket": bucket,
            "target_cap": limit,
            "selected_contexts": bucket_counts.get(bucket, 0),
            "source_available_or_added_before_cap": added_by_bucket.get(bucket, 0),
            **G522_CLOSED_CLAIMS,
        }
        for bucket, limit in BUCKET_LIMITS
    ]
    gates = {
        "context_count_le_36": len(contexts) <= 36,
        "observed_ids_only": flags["observed_ids_only"],
        "ids_166_205_untouched": flags["ids_166_205_untouched"],
        "at_least_3_context_buckets_present": len([count for count in bucket_counts.values() if count > 0]) >= 3,
    }
    decision = "context_panel_passed_continue_response_design" if all(gates.values()) else "context_panel_failed"
    summary = {
        "schema_version": "phase5p5_repair5g522_context_panel_summary_v1",
        "decision": decision,
        "context_count": len(contexts),
        "bucket_counts": dict(sorted(bucket_counts.items())),
        "observed_ids_only": flags["observed_ids_only"],
        "ids_166_205_untouched": flags["ids_166_205_untouched"],
        "at_least_3_context_buckets_present": gates["at_least_3_context_buckets_present"],
        "gates": gates,
        **G522_CLOSED_CLAIMS,
    }
    write_rows(args.output_csv, contexts)
    write_rows(args.bucket_summary_csv, bucket_rows)
    write_json_file(args.summary_json, summary)
    write_text_file(
        args.report,
        "# Repair5G.5.22 Context Panel\n\n"
        f"- decision: `{decision}`\n"
        f"- context_count: `{len(contexts)}`\n"
        f"- bucket_counts: `{dict(sorted(bucket_counts.items()))}`\n"
        f"- observed_ids_only: `{flags['observed_ids_only']}`\n"
        f"- ids_166_205_untouched: `{flags['ids_166_205_untouched']}`\n"
        f"- gates: `{gates}`\n",
    )
    print(json.dumps({"decision": decision, "context_count": len(contexts), "bucket_counts": dict(bucket_counts)}))
    return 0 if decision != "context_panel_failed" else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
