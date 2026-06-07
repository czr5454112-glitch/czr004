"""Verify required G5.14 artifacts before Repair5G.5.15 runs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g512_common import (  # noqa: E402
    observed_id_guard,
    read_csv_rows,
    read_json,
    repo_root,
    resolve,
    write_json,
    write_text,
)
from repair5g514_common import all_rich_feature_columns  # noqa: E402
from repair5g515_common import G515_CLOSED_CLAIMS, REQUIRED_G514_ARTIFACTS  # noqa: E402


DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g515_g514_artifact_verification.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g515_g514_artifact_verification_summary.json"


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
            observed_id_guard(args.ids, label="G5.15 reserved-ID guard probe")
        except ValueError as exc:
            print(json.dumps({"decision": "reserved_id_guard_probe_rejected", "ids": args.ids, "error": str(exc)}))
            return 2
        print(json.dumps({"decision": "reserved_id_guard_probe_passed", "ids": args.ids}))
        return 0

    root = repo_root()
    missing = [path for path in REQUIRED_G514_ARTIFACTS if not resolve(path, root).exists()]
    if missing:
        summary = {
            "schema_version": "phase5p5_repair5g515_g514_artifact_verification_summary_v1",
            "decision": "missing_g514_artifacts_stop",
            "missing_artifacts": missing,
            "gates": {"required_files_present": False},
            **G515_CLOSED_CLAIMS,
        }
        write_json(resolve(args.summary_json, root), summary)
        write_text(
            resolve(args.report, root),
            "# Phase5.5 Repair5G.5.15 G5.14 Artifact Verification\n\n"
            "- decision: `missing_g514_artifacts_stop`\n"
            f"- missing_artifacts: `{missing}`\n"
            "- runtime_claim_allowed: `false`\n",
        )
        print(json.dumps({"decision": summary["decision"], "missing": missing}))
        return 2

    v4_rows = read_csv_rows(resolve("outputs/tables/phase5p5_repair5g514_candidate_feature_matrix_v4.csv", root))
    v4_summary = read_json(resolve("outputs/reports/phase5p5_repair5g514_candidate_feature_matrix_v4_summary.json", root))
    rich_summary = read_json(resolve("outputs/reports/phase5p5_repair5g514_rich_context_features_summary.json", root))
    decision_summary = read_json(resolve("outputs/reports/phase5p5_repair5g514_decision_summary.json", root))
    feature_names = [name for name in v4_rows[0] if name.startswith("feature_")] if v4_rows else []
    rich_features = [name for name in feature_names if name in set(all_rich_feature_columns())]
    contexts = {str(row.get("normalized_context_key", "")) for row in v4_rows}
    candidates = {str(row.get("candidate_id", "")) for row in v4_rows}
    seeds = [row.get("seed", "") for row in v4_rows]
    observed_ids = observed_id_guard(seeds, label="G5.14 v4 matrix seeds")
    gates = {
        "required_files_present": True,
        "v4_candidate_rows_eq_840": len(v4_rows) == 840,
        "contexts_eq_60": len(contexts) == 60,
        "candidates_eq_14": len(candidates) == 14,
        "rich_feature_count_eq_19": len(rich_features) == 19 and int(rich_summary.get("rich_feature_count", 0)) == 19,
        "forbidden_feature_count_eq_0": int(v4_summary.get("forbidden_feature_count", -1)) == 0,
        "observed_ids_only": all(seed <= 165 for seed in observed_ids),
        "ids_166_205_untouched": all(not (166 <= seed <= 205) for seed in observed_ids),
        "v4_decision_exists": bool(decision_summary.get("decision")),
    }
    decision = "g514_artifacts_verified_continue_g515" if all(gates.values()) else "missing_g514_artifacts_stop"
    summary = {
        "schema_version": "phase5p5_repair5g515_g514_artifact_verification_summary_v1",
        "decision": decision,
        "candidate_rows": len(v4_rows),
        "contexts": len(contexts),
        "candidates": len(candidates),
        "rich_feature_count": len(rich_features),
        "forbidden_feature_count": int(v4_summary.get("forbidden_feature_count", -1)),
        "observed_seed_ids": observed_ids,
        "g514_decision": decision_summary.get("decision", ""),
        "gates": gates,
        **G515_CLOSED_CLAIMS,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.15 G5.14 Artifact Verification\n\n"
        f"- decision: `{decision}`\n"
        f"- candidate_rows: `{len(v4_rows)}`\n"
        f"- contexts: `{len(contexts)}`\n"
        f"- candidates: `{len(candidates)}`\n"
        f"- rich_feature_count: `{len(rich_features)}`\n"
        f"- forbidden_feature_count: `{summary['forbidden_feature_count']}`\n"
        f"- observed_seed_ids: `{observed_ids}`\n"
        f"- g514_decision: `{summary['g514_decision']}`\n"
        f"- gates: `{gates}`\n"
        "- runtime_claim_allowed: `false`\n",
    )
    print(json.dumps({"decision": decision, "candidate_rows": len(v4_rows), "contexts": len(contexts)}))
    return 0 if decision != "missing_g514_artifacts_stop" else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
