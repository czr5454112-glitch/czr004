"""Create or block Repair5G.5.13 rich runtime-safe context features."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g512_common import (  # noqa: E402
    csv_number,
    finite_number,
    leakage_scan,
    observed_id_flags,
    read_csv_rows,
    repo_root,
    resolve,
    write_csv_rows,
    write_json,
    write_text,
)
from repair5g513_common import G513_CLOSED_CLAIMS, grouped_contexts  # noqa: E402


DEFAULT_FEATURES = "outputs/tables/phase5p5_repair5g512_candidate_feature_matrix_v3.csv"
DEFAULT_TARGETS = "outputs/tables/phase5p5_repair5g512_candidate_regret_targets.csv"
DEFAULT_RESULTS = "outputs/tables/phase5p5_repair5g511_full_lattice_counterfactual_results.csv"
DEFAULT_OUTPUT = "outputs/tables/phase5p5_repair5g513_rich_context_feature_matrix.csv"
DEFAULT_INVENTORY = "outputs/tables/phase5p5_repair5g513_rich_context_feature_inventory.csv"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g513_rich_context_feature_matrix.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g513_rich_context_feature_matrix_summary.json"
ALLOWED_RICH_FIELDS = [
    "committed_count",
    "blocked_count",
    "wait_event_count",
    "progress_committed_count",
    "nonprogress_committed_count",
    "blocked_per_committed",
    "wait_per_committed",
    "blocked_per_agent",
    "committed_per_agent",
    "progress_ratio",
    "c_update_count",
    "f_update_count",
    "c_nonzero_edges",
    "f_nonzero_edges",
    "c_flow_update_ratio",
    "cost_min",
    "cost_max",
    "cost_span",
    "cost_bounds_respected",
]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feature-csv", type=Path, default=Path(DEFAULT_FEATURES))
    parser.add_argument("--targets-csv", type=Path, default=Path(DEFAULT_TARGETS))
    parser.add_argument("--results-csv", type=Path, default=Path(DEFAULT_RESULTS))
    parser.add_argument("--output-csv", type=Path, default=Path(DEFAULT_OUTPUT))
    parser.add_argument("--inventory-csv", type=Path, default=Path(DEFAULT_INVENTORY))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    return parser.parse_args(argv)


def source_rows(paths: dict[str, Path], root: Path) -> dict[str, list[dict[str, Any]]]:
    out = {}
    for name, path in paths.items():
        target = resolve(path, root)
        out[name] = read_csv_rows(target) if target.exists() else []
    return out


def inventory_for_sources(sources: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    rows = []
    for field in ALLOWED_RICH_FIELDS:
        present_sources = [
            name
            for name, source in sources.items()
            if source and field in source[0]
        ]
        rows.append(
            {
                "rich_field": field,
                "present": bool(present_sources),
                "present_sources": ",".join(present_sources),
            }
        )
    return rows


def context_values(rows: list[dict[str, Any]], field: str) -> dict[str, Any]:
    values = {}
    for key, group in grouped_contexts(rows).items():
        first = next((row.get(field, "") for row in group if str(row.get(field, "")).strip()), "")
        if str(first).strip():
            values[key] = first
    return values


def build_rich_matrix(base_rows: list[dict[str, Any]], sources: dict[str, list[dict[str, Any]]], present_fields: list[str]) -> list[dict[str, Any]]:
    values_by_field: dict[str, dict[str, Any]] = {}
    for field in present_fields:
        merged: dict[str, Any] = {}
        for source in sources.values():
            merged.update(context_values(source, field))
        values_by_field[field] = merged

    out = []
    for row in base_rows:
        item = dict(row)
        key = str(row.get("normalized_context_key", ""))
        for field in present_fields:
            value = values_by_field[field].get(key, "")
            feature_name = f"feature_rich_{field}"
            if field == "cost_bounds_respected":
                item[feature_name] = 1.0 if str(value).strip().lower() in {"1", "true", "yes"} else 0.0
            else:
                item[feature_name] = csv_number(finite_number(value, 0.0))
        out.append(item)
    return out


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    base_rows = read_csv_rows(resolve(args.feature_csv, root))
    sources = source_rows(
        {
            "g512_feature_matrix_v3": args.feature_csv,
            "g512_candidate_targets": args.targets_csv,
            "g511_full_lattice_results": args.results_csv,
        },
        root,
    )
    inventory = inventory_for_sources(sources)
    present_fields = [row["rich_field"] for row in inventory if row["present"]]
    if present_fields:
        output_rows = build_rich_matrix(base_rows, sources, present_fields)
        decision = "rich_context_feature_matrix_created_continue_signal_analysis"
        rich_candidate_rows = len(output_rows)
    else:
        decision = "rich_context_features_missing_requires_local_feature_probe"
        rich_candidate_rows = 0
        output_rows = [
            {
                "row_type": "rich_context_features_missing",
                "decision": decision,
                "base_candidate_rows": len(base_rows),
                "present_allowed_rich_feature_count": 0,
                "local_feature_probe_required": True,
            }
        ]
    feature_names = [name for name in output_rows[0] if name.startswith("feature_")] if output_rows else []
    leak = leakage_scan(feature_names)
    flags = observed_id_flags(base_rows)
    write_csv_rows(resolve(args.inventory_csv, root), inventory)
    write_csv_rows(resolve(args.output_csv, root), output_rows)
    summary = {
        "schema_version": "phase5p5_repair5g513_rich_context_feature_matrix_summary_v1",
        "decision": decision,
        "base_rows": len(base_rows),
        "rich_matrix_rows": rich_candidate_rows,
        "output_table_rows": len(output_rows),
        "allowed_rich_fields": ALLOWED_RICH_FIELDS,
        "present_allowed_rich_fields": present_fields,
        "present_allowed_rich_feature_count": len(present_fields),
        "forbidden_feature_count": leak["forbidden_feature_count"],
        "forbidden_features": leak["forbidden_features"],
        "inventory_csv": str(resolve(args.inventory_csv, root)),
        "rich_feature_matrix_csv": str(resolve(args.output_csv, root)),
        "local_feature_probe_plan": {
            "needed": not present_fields,
            "max_workers": 1,
            "solver_semantics_change_allowed": False,
            "reserved_ids_166_205_allowed": False,
            "note": "Use an observed-ID pre-choice trace export only if it can be implemented without changing LaCAM*/PIBT semantics.",
        },
        **flags,
        **G513_CLOSED_CLAIMS,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.13 Rich Context Feature Matrix\n\n"
        f"- decision: `{decision}`\n"
        f"- base_rows: `{len(base_rows)}`\n"
        f"- rich_matrix_rows: `{len(output_rows)}`\n"
        f"- present_allowed_rich_fields: `{present_fields}`\n"
        f"- forbidden_feature_count: `{leak['forbidden_feature_count']}`\n"
        f"- observed_ids_only: `{flags['observed_ids_only']}`\n"
        f"- ids_166_205_untouched: `{flags['ids_166_205_untouched']}`\n"
        "- runtime_claim_allowed: `false`\n\n"
        "Existing tracked G5.11/G5.12 artifacts are scanned for explicitly allowed pre-choice rich runtime fields. "
        "When those fields are absent, this script records `rich_context_features_missing_requires_local_feature_probe` and does not fabricate rich features. "
        "Any later local probe must use approved observed IDs, `--max-workers 1`, and no solver semantic changes.\n",
    )
    print(json.dumps({"decision": decision, "present_allowed_rich_feature_count": len(present_fields)}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
