"""Plan the Repair5G.5.16 local targeted probe without running the solver."""

from __future__ import annotations

import argparse
import json
import sys
from collections import OrderedDict
from pathlib import Path

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g512_common import observed_id_flags, read_csv_rows, read_json, repo_root, resolve, write_csv_rows, write_json, write_text  # noqa: E402
from repair5g516_common import (  # noqa: E402
    DEFAULT_G515_V5_MATRIX,
    DEFAULT_G516_ERROR_BANK,
    DEFAULT_G516_LATTICE,
    DEFAULT_G516_LATTICE_SUMMARY,
    DEFAULT_G516_PROBE_PLAN,
    DEFAULT_G516_PROBE_PLAN_SUMMARY,
    G516_CLOSED_CLAIMS,
    current_candidate_ids,
)


DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g516_local_targeted_probe_plan.md"
BUDGETS = [1000, 2000]
MAX_TARGET_CONTEXTS = 20
MAX_WORKERS = 1


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feature-csv", type=Path, default=Path(DEFAULT_G515_V5_MATRIX))
    parser.add_argument("--error-bank-csv", type=Path, default=Path(DEFAULT_G516_ERROR_BANK))
    parser.add_argument("--lattice-csv", type=Path, default=Path(DEFAULT_G516_LATTICE))
    parser.add_argument("--lattice-summary", type=Path, default=Path(DEFAULT_G516_LATTICE_SUMMARY))
    parser.add_argument("--output-csv", type=Path, default=Path(DEFAULT_G516_PROBE_PLAN))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_G516_PROBE_PLAN_SUMMARY))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    return parser.parse_args(argv)


def selected_contexts(error_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    priority = {
        "harmful_false_positive": 0,
        "missed_helpful_fallback": 1,
        "static_near_oracle": 2,
        "high_uncertainty": 3,
        "oracle_gap_high": 4,
        "candidate_disagreement": 5,
    }
    chosen: OrderedDict[str, dict[str, str]] = OrderedDict()
    for row in sorted(error_rows, key=lambda item: (priority.get(str(item.get("error_category", "")), 99), str(item.get("normalized_context_key", "")))):
        key = str(row.get("normalized_context_key", ""))
        if key and key not in chosen:
            chosen[key] = row
        if len(chosen) >= MAX_TARGET_CONTEXTS:
            break
    return list(chosen.values())


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    feature_rows = read_csv_rows(resolve(args.feature_csv, root))
    error_rows = read_csv_rows(resolve(args.error_bank_csv, root))
    lattice_rows = read_csv_rows(resolve(args.lattice_csv, root))
    lattice_summary = read_json(resolve(args.lattice_summary, root)) if resolve(args.lattice_summary, root).exists() else {}
    base_candidates = current_candidate_ids(feature_rows)
    repair_candidates = [str(row.get("candidate_id", "")) for row in lattice_rows if row.get("candidate_id")]
    candidates = base_candidates + [candidate for candidate in repair_candidates if candidate not in base_candidates]
    contexts = selected_contexts(error_rows)
    rows = []
    for context in contexts:
        for candidate in candidates:
            for budget in BUDGETS:
                rows.append(
                    {
                        "row_type": "local_targeted_probe_plan",
                        "normalized_context_key": context.get("normalized_context_key", ""),
                        "map": context.get("map", ""),
                        "agents": context.get("agents", ""),
                        "seed": context.get("seed", ""),
                        "iteration": context.get("iteration", ""),
                        "error_category": context.get("error_category", ""),
                        "candidate_id": candidate,
                        "short_budget_ms": budget,
                        "max_workers": MAX_WORKERS,
                        "observed_ids_only": True,
                        "ids_166_205_untouched": True,
                    }
                )
    flags = observed_id_flags(rows)
    executable = lattice_summary.get("decision") == "targeted_repair_lattice_created_executable_continue_probe"
    estimated_rows = len(rows)
    gates = {
        "target_contexts_le_20": len(contexts) <= MAX_TARGET_CONTEXTS,
        "candidate_count_le_26": len(candidates) <= 26,
        "budgets_eq_1000_2000": BUDGETS == [1000, 2000],
        "max_workers_eq_1": MAX_WORKERS == 1,
        "all_ids_observed": flags["observed_ids_only"],
        "ids_166_205_untouched": flags["ids_166_205_untouched"],
        "estimated_row_count_local_safe": estimated_rows <= MAX_TARGET_CONTEXTS * 26 * len(BUDGETS),
        "candidate_methods_executable": executable,
    }
    no_run_reason = "" if executable else "targeted_repair_lattice_requires_adapter_followup: repair5g516_* names are not recognized by the current C++ adapter"
    decision = "local_targeted_probe_plan_ready_to_run" if all(gates.values()) else "local_targeted_probe_planned_but_not_runnable"
    summary = {
        "schema_version": "phase5p5_repair5g516_local_targeted_probe_plan_summary_v1",
        "decision": decision,
        "target_contexts": len(contexts),
        "candidate_count": len(candidates),
        "base_candidate_count": len(base_candidates),
        "repair_candidate_count": len(repair_candidates),
        "budgets": BUDGETS,
        "max_workers": MAX_WORKERS,
        "estimated_rows": estimated_rows,
        "no_run_reason": no_run_reason,
        "gates": gates,
        **flags,
        **G516_CLOSED_CLAIMS,
    }
    write_csv_rows(resolve(args.output_csv, root), rows)
    write_json(resolve(args.summary_json, root), summary)
    context_lines = "\n".join(f"- `{row.get('normalized_context_key')}`: `{row.get('error_category')}`" for row in contexts)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.16 Local Targeted Probe Plan\n\n"
        f"- decision: `{decision}`\n"
        f"- target_contexts: `{len(contexts)}`\n"
        f"- candidate_count: `{len(candidates)}`\n"
        f"- budgets: `{BUDGETS}`\n"
        f"- max_workers: `{MAX_WORKERS}`\n"
        f"- estimated_rows: `{estimated_rows}`\n"
        f"- no_run_reason: `{no_run_reason}`\n"
        f"- gates: `{gates}`\n\n"
        "## Target Contexts\n\n"
        f"{context_lines}\n",
    )
    print(json.dumps({"decision": decision, "target_contexts": len(contexts), "estimated_rows": estimated_rows, "no_run_reason": no_run_reason}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
