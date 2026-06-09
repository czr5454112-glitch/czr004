"""Analyze Repair5G.5.10 lattice adapter parity from probe rows."""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g510_common import (  # noqa: E402
    G510_ADDITIVE_CANDIDATE,
    G510_C_ONLY_CANDIDATE,
    G510_REFERENCE_ADDITIVE,
    G510_REFERENCE_STATIC,
    G510_STATIC_ALIAS_CANDIDATE,
    G510_STATIC_CANDIDATE,
    G59_CLOSED_STATUS,
    boolish,
    budget_key,
    context_key,
    finite_number,
    lattice_candidate_ids,
    read_csv_rows,
    repo_root,
    resolve,
    score_from_probe,
    write_json,
    write_text,
)


DEFAULT_RESULTS = "outputs/tables/phase5p5_repair5g510_lattice_smoke_results.csv"
DEFAULT_CANDIDATES = "outputs/tables/phase5p5_repair5g59_candidate_lattice.csv"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g510_lattice_adapter_parity.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g510_lattice_adapter_parity_summary.json"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-csv", type=Path, default=Path(DEFAULT_RESULTS))
    parser.add_argument("--candidate-csv", type=Path, default=Path(DEFAULT_CANDIDATES))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    return parser.parse_args(argv)


def key_for_parity(row: dict[str, object]) -> tuple[str, float]:
    return (context_key(row), budget_key(row.get("short_budget_ms")))


def row_by_candidate(rows: list[dict[str, object]]) -> dict[tuple[str, float], dict[str, dict[str, object]]]:
    grouped: dict[tuple[str, float], dict[str, dict[str, object]]] = defaultdict(dict)
    for row in rows:
        candidate = str(row.get("candidate_id", ""))
        if candidate:
            grouped[key_for_parity(row)][candidate] = row
    return grouped


def rows_match(left: dict[str, object], right: dict[str, object]) -> bool:
    if str(left.get("updateparams_hash", "")) != str(right.get("updateparams_hash", "")):
        return False
    left_score = score_from_probe(left)
    right_score = score_from_probe(right)
    if math.isfinite(left_score) or math.isfinite(right_score):
        return abs(left_score - right_score) <= 1.0e-12
    return True


def parity_check(
    grouped: dict[tuple[str, float], dict[str, dict[str, object]]],
    left_id: str,
    right_id: str,
) -> dict[str, object]:
    compared = 0
    mismatches = []
    for key, candidates in grouped.items():
        left = candidates.get(left_id)
        right = candidates.get(right_id)
        if left is None or right is None:
            continue
        compared += 1
        if not rows_match(left, right):
            mismatches.append(
                {
                    "context_budget_key": f"{key[0]}|b{int(key[1])}",
                    "left_hash": left.get("updateparams_hash", ""),
                    "right_hash": right.get("updateparams_hash", ""),
                    "left_score": finite_number(left.get("probe_sum_of_loss_ratio"), math.inf),
                    "right_score": finite_number(right.get("probe_sum_of_loss_ratio"), math.inf),
                }
            )
    return {
        "left_id": left_id,
        "right_id": right_id,
        "compared_pairs": compared,
        "mismatch_count": len(mismatches),
        "passed": compared > 0 and not mismatches,
        "mismatches": mismatches[:10],
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    rows = read_csv_rows(resolve(args.results_csv, root))
    lattice_ids = set(lattice_candidate_ids(resolve(args.candidate_csv, root)))
    lattice_rows = [row for row in rows if str(row.get("candidate_id", "")) in lattice_ids]
    recognized = [row for row in lattice_rows if boolish(row.get("candidate_recognized"))]
    grouped = row_by_candidate(rows)
    static_parity = parity_check(grouped, G510_STATIC_CANDIDATE, G510_REFERENCE_STATIC)
    additive_parity = parity_check(grouped, G510_ADDITIVE_CANDIDATE, G510_REFERENCE_ADDITIVE)
    static_alias_parity = parity_check(grouped, G510_STATIC_CANDIDATE, G510_STATIC_ALIAS_CANDIDATE)
    c_only_rows = [row for row in lattice_rows if row.get("candidate_id") == G510_C_ONLY_CANDIDATE]
    c_only_fingerprints = [str(row.get("updateparams_fingerprint", "")) for row in c_only_rows]
    c_only_runs = bool(c_only_rows) and all(boolish(row.get("candidate_recognized")) for row in c_only_rows)
    c_only_f_disabled = bool(c_only_fingerprints) and all(
        "alpha_flow_commit_progress=0" in fp
        and "goal_projection_mode=none" in fp
        and "flow_shield_beta=0" in fp
        for fp in c_only_fingerprints
    )
    gates = {
        "candidate_id_propagated": bool(lattice_rows) and all(row.get("candidate_id") for row in lattice_rows),
        "all_lattice_rows_recognized": bool(lattice_rows) and len(recognized) == len(lattice_rows),
        "static_flow_shield_matches_prior_static": static_parity["passed"],
        "additive_fallback_matches_additive_ltm": additive_parity["passed"],
        "static_abstain_alias_matches_static": static_alias_parity["passed"],
        "c_only_f_disabled_candidate_runs": c_only_runs,
        "c_only_f_disabled_params_verified": c_only_f_disabled,
        "observed_ids_only": all(int(finite_number(row.get("seed"), 0.0)) <= 165 for row in rows),
        "ids_166_205_untouched": all(not (166 <= int(finite_number(row.get("seed"), 0.0)) <= 205) for row in rows),
    }
    summary = {
        "schema_version": "phase5p5_repair5g510_lattice_adapter_parity_summary_v1",
        "decision": "lattice_adapter_parity_passed" if all(gates.values()) else "lattice_adapter_parity_failed",
        "probe_rows": len(rows),
        "lattice_rows": len(lattice_rows),
        "lattice_candidate_count": len(lattice_ids),
        "recognized_lattice_rows": len(recognized),
        "static_parity": static_parity,
        "additive_parity": additive_parity,
        "static_alias_parity": static_alias_parity,
        "c_only_rows": len(c_only_rows),
        "gates": gates,
        **G59_CLOSED_STATUS,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.10 Lattice Adapter Parity\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- probe_rows: `{len(rows)}`\n"
        f"- lattice_rows: `{len(lattice_rows)}`\n"
        f"- static_flow_shield_matches_prior_static: `{gates['static_flow_shield_matches_prior_static']}`\n"
        f"- additive_fallback_matches_additive_ltm: `{gates['additive_fallback_matches_additive_ltm']}`\n"
        f"- c_only_f_disabled_candidate_runs: `{gates['c_only_f_disabled_candidate_runs']}`\n"
        f"- all_lattice_rows_recognized: `{gates['all_lattice_rows_recognized']}`\n"
        f"- ids_166_205_untouched: `{gates['ids_166_205_untouched']}`\n\n"
        "The parity check compares actual same-context probe rows and UpdateParams hashes. "
        "The adapter is project-owned and does not modify external/lacam2 or solver search semantics.\n",
    )
    print(json.dumps({"decision": summary["decision"], "lattice_rows": len(lattice_rows)}))
    return 0 if all(gates.values()) else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
