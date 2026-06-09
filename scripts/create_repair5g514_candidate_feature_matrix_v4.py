"""Join G5.14 rich context features onto the G5.12 candidate feature matrix v3."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g512_common import (  # noqa: E402
    count_by,
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
from repair5g514_common import (  # noqa: E402
    ALLOWED_RICH_FIELDS,
    DEFAULT_RICH_CONTEXT_CSV,
    DEFAULT_RICH_CONTEXT_SUMMARY,
    DEFAULT_V4_MATRIX,
    G514_CLOSED_CLAIMS,
    all_rich_feature_columns,
)


DEFAULT_V3 = "outputs/tables/phase5p5_repair5g512_candidate_feature_matrix_v3.csv"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g514_candidate_feature_matrix_v4.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g514_candidate_feature_matrix_v4_summary.json"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--v3-csv", type=Path, default=Path(DEFAULT_V3))
    parser.add_argument("--rich-context-csv", type=Path, default=Path(DEFAULT_RICH_CONTEXT_CSV))
    parser.add_argument("--rich-summary-json", type=Path, default=Path(DEFAULT_RICH_CONTEXT_SUMMARY))
    parser.add_argument("--output-csv", type=Path, default=Path(DEFAULT_V4_MATRIX))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    v3_rows = read_csv_rows(resolve(args.v3_csv, root))
    rich_rows = read_csv_rows(resolve(args.rich_context_csv, root))
    rich_summary = json.loads(resolve(args.rich_summary_json, root).read_text(encoding="utf-8")) if resolve(args.rich_summary_json, root).exists() else {}
    rich_by_context = {str(row.get("normalized_context_key", "")): row for row in rich_rows}
    output_rows = []
    for row in v3_rows:
        key = str(row.get("normalized_context_key", ""))
        rich = rich_by_context.get(key, {})
        item = dict(row)
        item["rich_feature_source"] = rich.get("feature_source", "missing_existing_checkpoint")
        item["rich_source_checkpoint_path"] = rich.get("source_checkpoint_path", "")
        item["rich_context_feature_present"] = item["rich_feature_source"] == "existing_checkpoint"
        for field in ALLOWED_RICH_FIELDS:
            item[f"rich_{field}"] = rich.get(f"rich_{field}", "")
            value = rich.get(f"feature_rich_{field}", "")
            item[f"feature_rich_{field}"] = finite_number(value, 0.0) if str(value).strip() else 0.0
        output_rows.append(item)

    feature_names = [name for name in output_rows[0] if name.startswith("feature_")] if output_rows else []
    rich_feature_names = [name for name in feature_names if name in set(all_rich_feature_columns())]
    contexts = {str(row.get("normalized_context_key", "")) for row in output_rows}
    rich_contexts = {str(row.get("normalized_context_key", "")) for row in output_rows if row.get("rich_context_feature_present") in {True, "True", "true", "1"}}
    candidates = {str(row.get("candidate_id", "")) for row in output_rows}
    leak = leakage_scan(feature_names)
    flags = observed_id_flags(output_rows)
    gates = {
        "candidate_rows_ge_840": len(output_rows) >= 840,
        "contexts_eq_60": len(contexts) == 60,
        "candidates_eq_14": len(candidates) == 14,
        "rich_feature_count_gt_0": len(rich_feature_names) > 0,
        "rich_contexts_ge_60_if_source_complete": (
            len(rich_contexts) >= 60 if rich_summary.get("source_complete") else len(rich_contexts) == int(rich_summary.get("rich_contexts", len(rich_contexts)))
        ),
        "forbidden_feature_count_eq_0": leak["forbidden_feature_count"] == 0,
        "observed_ids_only": flags["observed_ids_only"],
        "ids_166_205_untouched": flags["ids_166_205_untouched"],
    }
    decision = "candidate_feature_matrix_v4_created_continue_ranker" if all(gates.values()) else "candidate_feature_matrix_v4_gate_failed"
    summary = {
        "schema_version": "phase5p5_repair5g514_candidate_feature_matrix_v4_summary_v1",
        "decision": decision,
        "candidate_rows": len(output_rows),
        "contexts": len(contexts),
        "candidates": len(candidates),
        "feature_count": len(feature_names),
        "rich_feature_count": len(rich_feature_names),
        "rich_contexts": len(rich_contexts),
        "rich_feature_source_distribution": count_by(output_rows, "rich_feature_source"),
        "forbidden_feature_count": leak["forbidden_feature_count"],
        "forbidden_features": leak["forbidden_features"],
        "gates": gates,
        **flags,
        **G514_CLOSED_CLAIMS,
    }
    write_csv_rows(resolve(args.output_csv, root), output_rows)
    write_json(resolve(args.summary_json, root), summary)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.14 Candidate Feature Matrix V4\n\n"
        f"- decision: `{decision}`\n"
        f"- candidate_rows: `{len(output_rows)}`\n"
        f"- contexts: `{len(contexts)}`\n"
        f"- candidates: `{len(candidates)}`\n"
        f"- feature_count: `{len(feature_names)}`\n"
        f"- rich_feature_count: `{len(rich_feature_names)}`\n"
        f"- rich_contexts: `{len(rich_contexts)}`\n"
        f"- forbidden_feature_count: `{leak['forbidden_feature_count']}`\n"
        f"- gates: `{gates}`\n"
        "- runtime_claim_allowed: `false`\n\n"
        "V4 is a strict join of G5.12 candidate rows with recovered rich context aggregates. "
        "No outcome, oracle, action, priority, restart, h-value, or candidate-deletion feature is added.\n",
    )
    print(json.dumps({"decision": decision, "candidate_rows": len(output_rows), "rich_contexts": len(rich_contexts)}))
    return 0 if decision != "candidate_feature_matrix_v4_gate_failed" else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
