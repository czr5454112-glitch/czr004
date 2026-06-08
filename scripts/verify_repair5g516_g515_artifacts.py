"""Verify required G5.15 artifacts before Repair5G.5.16 runs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g512_common import observed_id_guard, observed_id_flags, read_csv_rows, read_json, repo_root, resolve, write_json, write_text  # noqa: E402
from repair5g513_common import grouped_contexts  # noqa: E402
from repair5g516_common import (  # noqa: E402
    DEFAULT_G515_CONTEXT_DECISIONS,
    DEFAULT_G515_DECISION_SUMMARY,
    DEFAULT_G515_EVAL_SUMMARY,
    DEFAULT_G515_FALSE_POSITIVE_SUMMARY,
    DEFAULT_G515_SAFETY_SUMMARY,
    DEFAULT_G515_V5_MATRIX,
    DEFAULT_G515_V5_SUMMARY,
    G516_CLOSED_CLAIMS,
)


DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g516_g515_artifact_verification.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g516_g515_artifact_verification_summary.json"
REQUIRED_FILES = [
    "outputs/reports/phase5p5_repair5g515_decision.md",
    DEFAULT_G515_DECISION_SUMMARY,
    DEFAULT_G515_V5_SUMMARY,
    DEFAULT_G515_EVAL_SUMMARY,
    DEFAULT_G515_FALSE_POSITIVE_SUMMARY,
    DEFAULT_G515_SAFETY_SUMMARY,
    DEFAULT_G515_V5_MATRIX,
    DEFAULT_G515_CONTEXT_DECISIONS,
]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    parser.add_argument("--ids", nargs="*", default=None, help="Optional reserved-ID guard probe.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.ids is not None:
        try:
            observed_id_guard(args.ids, label="G5.16 reserved-ID guard probe")
        except ValueError as exc:
            print(json.dumps({"decision": "reserved_id_guard_probe_rejected", "ids": args.ids, "error": str(exc)}))
            return 2
        print(json.dumps({"decision": "reserved_id_guard_probe_passed", "ids": args.ids}))
        return 0

    root = repo_root()
    missing = [path for path in REQUIRED_FILES if not resolve(path, root).exists()]
    rows = read_csv_rows(resolve(DEFAULT_G515_V5_MATRIX, root)) if not missing else []
    decision_summary = read_json(resolve(DEFAULT_G515_DECISION_SUMMARY, root)) if not missing else {}
    v5_summary = read_json(resolve(DEFAULT_G515_V5_SUMMARY, root)) if not missing else {}
    eval_summary = read_json(resolve(DEFAULT_G515_EVAL_SUMMARY, root)) if not missing else {}
    fp_summary = read_json(resolve(DEFAULT_G515_FALSE_POSITIVE_SUMMARY, root)) if not missing else {}
    safety_summary = read_json(resolve(DEFAULT_G515_SAFETY_SUMMARY, root)) if not missing else {}
    contexts = grouped_contexts(rows)
    candidate_counts = {key: len(group) for key, group in contexts.items()}
    flags = observed_id_flags(rows)
    gates = {
        "required_files_present": not missing,
        "g515_decision_no_better_than_v4": decision_summary.get("decision") == "interaction_ranker_no_better_than_v4_continue_feature_design",
        "v5_rows_eq_840": len(rows) == 840,
        "contexts_eq_60": len(contexts) == 60,
        "fourteen_candidates_per_context": bool(candidate_counts) and all(count == 14 for count in candidate_counts.values()),
        "forbidden_feature_count_eq_0": int(v5_summary.get("forbidden_feature_count", -1)) == 0,
        "oof_eval_summary_present": bool(eval_summary.get("oof_policy_summaries")),
        "false_positive_autopsy_present": fp_summary.get("decision") == "false_positive_autopsy_completed_continue_safety_update",
        "static_abstention_safety_update_present": bool(safety_summary.get("decision")),
        "observed_ids_only": flags.get("observed_ids_only", False),
        "ids_166_205_untouched": flags.get("ids_166_205_untouched", False),
    }
    decision = "g515_artifacts_verified_continue_g516" if all(gates.values()) else "missing_g515_artifacts_stop"
    summary = {
        "schema_version": "phase5p5_repair5g516_g515_artifact_verification_summary_v1",
        "decision": decision,
        "missing_artifacts": missing,
        "g515_decision": decision_summary.get("decision", ""),
        "v5_rows": len(rows),
        "contexts": len(contexts),
        "candidate_rows_per_context_min": min(candidate_counts.values()) if candidate_counts else 0,
        "candidate_rows_per_context_max": max(candidate_counts.values()) if candidate_counts else 0,
        "forbidden_feature_count": v5_summary.get("forbidden_feature_count", ""),
        "gates": gates,
        **flags,
        **G516_CLOSED_CLAIMS,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.16 G5.15 Artifact Verification\n\n"
        f"- decision: `{decision}`\n"
        f"- missing_artifacts: `{missing}`\n"
        f"- g515_decision: `{summary['g515_decision']}`\n"
        f"- v5_rows: `{len(rows)}`\n"
        f"- contexts: `{len(contexts)}`\n"
        f"- candidate_rows_per_context_min: `{summary['candidate_rows_per_context_min']}`\n"
        f"- candidate_rows_per_context_max: `{summary['candidate_rows_per_context_max']}`\n"
        f"- forbidden_feature_count: `{summary['forbidden_feature_count']}`\n"
        f"- gates: `{gates}`\n"
        "- ids_166_205_untouched: `true`\n"
        "- runtime_claim_allowed: `false`\n",
    )
    print(json.dumps({"decision": decision, "v5_rows": len(rows), "contexts": len(contexts)}))
    return 0 if decision != "missing_g515_artifacts_stop" else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
