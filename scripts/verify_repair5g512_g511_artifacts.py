"""Verify the G5.11 artifacts required by Repair5G.5.12."""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter
from pathlib import Path

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g512_common import (  # noqa: E402
    CLOSED_CLAIMS,
    PRIMARY_BUDGETS_MS,
    context_key,
    finite_number,
    observed_id_flags,
    read_csv_rows,
    read_json,
    repo_root,
    resolve,
    score_from_probe,
    write_json,
    write_text,
)


DEFAULT_RESULTS = "outputs/tables/phase5p5_repair5g511_full_lattice_counterfactual_results.csv"
DEFAULT_CANDIDATES = "outputs/tables/phase5p5_repair5g59_candidate_lattice.csv"
DEFAULT_ORACLE = "outputs/tables/phase5p5_repair5g511_lattice_oracle_by_context.csv"
DEFAULT_CONFIDENCE = "outputs/tables/phase5p5_repair5g511_confidence_targets_v5.csv"
DEFAULT_SUMMARIES = [
    "outputs/reports/phase5p5_repair5g511_full_lattice_integrity_summary.json",
    "outputs/reports/phase5p5_repair5g511_lattice_oracle_gap_full_summary.json",
    "outputs/reports/phase5p5_repair5g511_confidence_targets_v5_summary.json",
    "outputs/reports/phase5p5_repair5g511_decision_summary.json",
]
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g512_g511_artifact_verification.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g512_g511_artifact_verification_summary.json"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-csv", type=Path, default=Path(DEFAULT_RESULTS))
    parser.add_argument("--candidate-csv", type=Path, default=Path(DEFAULT_CANDIDATES))
    parser.add_argument("--oracle-csv", type=Path, default=Path(DEFAULT_ORACLE))
    parser.add_argument("--confidence-csv", type=Path, default=Path(DEFAULT_CONFIDENCE))
    parser.add_argument("--summary-json", action="append", type=Path, default=[Path(path) for path in DEFAULT_SUMMARIES])
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--output-summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    return parser.parse_args(argv)


def safe_read_csv(path: Path) -> tuple[list[dict[str, object]], str | None]:
    try:
        return read_csv_rows(path), None
    except Exception as exc:  # pragma: no cover - diagnostic path
        return [], str(exc)


def safe_read_json(path: Path) -> tuple[object | None, str | None]:
    try:
        return read_json(path), None
    except Exception as exc:  # pragma: no cover - diagnostic path
        return None, str(exc)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    csv_paths = [args.results_csv, args.candidate_csv, args.oracle_csv, args.confidence_csv]
    missing = [str(path) for path in csv_paths + args.summary_json if not resolve(path, root).exists()]
    errors: dict[str, str] = {}

    results, error = safe_read_csv(resolve(args.results_csv, root))
    if error:
        errors[str(args.results_csv)] = error
    candidates, error = safe_read_csv(resolve(args.candidate_csv, root))
    if error:
        errors[str(args.candidate_csv)] = error
    oracle, error = safe_read_csv(resolve(args.oracle_csv, root))
    if error:
        errors[str(args.oracle_csv)] = error
    confidence, error = safe_read_csv(resolve(args.confidence_csv, root))
    if error:
        errors[str(args.confidence_csv)] = error

    parsed_summaries = {}
    for path in args.summary_json:
        payload, error = safe_read_json(resolve(path, root))
        if error:
            errors[str(path)] = error
        else:
            parsed_summaries[str(path)] = payload

    candidate_ids = {str(row.get("candidate_id", "")) for row in candidates if str(row.get("candidate_id", ""))}
    result_candidates = {str(row.get("candidate_id", "")) for row in results if str(row.get("candidate_id", ""))}
    contexts = {context_key(row) for row in results}
    primary_rows = [
        row
        for row in results
        if int(finite_number(row.get("short_budget_ms"), -1)) in set(PRIMARY_BUDGETS_MS)
    ]
    primary_contexts = {context_key(row) for row in primary_rows}
    row_keys = [
        (
            context_key(row),
            str(row.get("candidate_id", "")),
            int(finite_number(row.get("short_budget_ms"), -1)),
        )
        for row in results
    ]
    duplicate_rows = sum(count - 1 for count in Counter(row_keys).values() if count > 1)
    flags = observed_id_flags(results)
    primary_finite_rows = sum(1 for row in primary_rows if math.isfinite(score_from_probe(row)))
    documented_equivalent = len(results) >= 3360
    gates = {
        "full_lattice_results_exist": not missing and bool(results),
        "candidate_lattice_exists": not missing and bool(candidates),
        "oracle_by_context_exists": not missing and bool(oracle),
        "confidence_targets_v5_exists": not missing and bool(confidence),
        "summary_json_files_parse": len(parsed_summaries) == len(args.summary_json) and not errors,
        "contexts_eq_60": len(contexts) == 60,
        "candidate_count_eq_14": len(candidate_ids) == 14 and len(result_candidates) == 14,
        "full_rows_3360_or_documented_equivalent": len(results) == 3360 or documented_equivalent,
        "primary_1000_2000_rows_available": len(primary_rows) >= 60 * 14 * 2,
        "primary_1000_2000_contexts_eq_60": len(primary_contexts) == 60,
        "observed_ids_only": flags["observed_ids_only"],
        "ids_166_205_untouched": flags["ids_166_205_untouched"],
        "duplicate_context_candidate_budget_rows_eq_0": duplicate_rows == 0,
    }
    decision = "g511_artifacts_verified_continue_g512" if all(gates.values()) and not missing and not errors else "missing_g511_artifacts_stop"
    summary = {
        "schema_version": "phase5p5_repair5g512_g511_artifact_verification_summary_v1",
        "decision": decision,
        "missing": missing,
        "parse_errors": errors,
        "results_rows": len(results),
        "candidate_count": len(candidate_ids),
        "result_candidate_count": len(result_candidates),
        "contexts": len(contexts),
        "oracle_context_rows": len(oracle),
        "confidence_target_rows": len(confidence),
        "primary_rows": len(primary_rows),
        "primary_finite_rows": primary_finite_rows,
        "primary_contexts": len(primary_contexts),
        "duplicate_context_candidate_budget_rows": duplicate_rows,
        "gates": gates,
        **CLOSED_CLAIMS,
    }
    write_json(resolve(args.output_summary_json, root), summary)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.12 G5.11 Artifact Verification\n\n"
        f"- decision: `{decision}`\n"
        f"- results_rows: `{len(results)}`\n"
        f"- candidate_count: `{len(candidate_ids)}`\n"
        f"- contexts: `{len(contexts)}`\n"
        f"- primary_rows: `{len(primary_rows)}`\n"
        f"- primary_contexts: `{len(primary_contexts)}`\n"
        f"- duplicate_context_candidate_budget_rows: `{duplicate_rows}`\n"
        f"- missing: `{missing}`\n"
        f"- parse_errors: `{errors}`\n"
        f"- gates: `{gates}`\n\n"
        "The verifier only checks tracked G5.11 artifacts and the observed-ID boundary. "
        "It does not run the solver and keeps runtime, Phase5.5, Phase6, and AAAI claims closed.\n",
    )
    print(json.dumps({"decision": decision, "results_rows": len(results), "contexts": len(contexts)}))
    return 0 if decision != "missing_g511_artifacts_stop" else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
