"""Update G5.57 docs from the final decision summary.

Run this after the compact server bundle has been ingested and audited.  The
script writes a marker-delimited final-result block into the G5.57 plan and the
two project master documents so baseline/SafeGate wording stays consistent.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DECISION_SUMMARY = ROOT / "outputs/reports/phase5p5_repair5g557_decision_summary.json"
LABEL_SUMMARY = ROOT / "outputs/reports/phase5p5_repair5g557_label_matrix_summary.json"
AUDIT_SUMMARY = ROOT / "outputs/reports/phase5p5_repair5g557_final_artifact_audit_summary.json"
PLAN_MD = ROOT / "czr004_g557_graph_conditioned_static_theta_aaai_plan.md"
DEEP_RESEARCH_MD = ROOT / "deep-research-report.md"
EXECUTION_PLAN_MD = ROOT / "phase4_6_laur_ltm_codex_execution_plan.md"

BEGIN = "<!-- G5.57_FINAL_RESULT_BEGIN -->"
END = "<!-- G5.57_FINAL_RESULT_END -->"
PRIMARY_BASELINE = "g556_c063174"
CLAIM_KEYS = [
    "phase5p5_allowed",
    "phase6_allowed",
    "runtime_claim_allowed",
    "learned_runtime_policy_validated",
    "aaai_ready",
]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args(argv)


def load_json(path: Path, required: bool = True) -> dict[str, Any]:
    if not path.exists():
        if required:
            raise FileNotFoundError(path)
        return {}
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"expected JSON object in {path}")
    return data


def fmt(value: Any) -> str:
    if value is None or value == "":
        return "n/a"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return f"{value:,}"
    return str(value)


def require_static_guardrails(decision: dict[str, Any]) -> None:
    if decision.get("primary_baseline") != PRIMARY_BASELINE:
        raise ValueError(f"primary_baseline must be {PRIMARY_BASELINE}, got {decision.get('primary_baseline')!r}")
    for key in ["dynamic_policy", "checkpoint_policy", *CLAIM_KEYS]:
        if decision.get(key) is not False:
            raise ValueError(f"{key} must remain false, got {decision.get(key)!r}")


def block_text(decision: dict[str, Any], label: dict[str, Any], audit: dict[str, Any], result_date: str | None = None) -> str:
    dated_heading = result_date or date.today().isoformat()
    decision_label = fmt(decision.get("decision"))
    strict_passed = bool(decision.get("strict_blind_passed"))
    outcome = (
        "GCST-LTM passed the strict blind gate, but claim flags remain closed pending separate paper/runtime gates."
        if strict_passed
        else "GCST-LTM is not promoted as a new baseline; keep g556_c063174 as the active promotion baseline."
    )
    audit_line = (
        f"Local final-artifact audit status: `{fmt(audit.get('passed'))}` with `{fmt(audit.get('failed_count'))}` failed checks."
        if audit
        else "Local final-artifact audit must be run after ingest before push."
    )
    return (
        f"{BEGIN}\n"
        f"## {dated_heading} - G5.57 final result: graph-conditioned static theta\n\n"
        f"Final decision: `{decision_label}`. {outcome}\n\n"
        f"Baseline/SafeGate: the declared promotion baseline is `{PRIMARY_BASELINE}`. "
        "Offline prediction, candidate ranking, learned-SafeGate scores, and proxy labels do not promote GCST. "
        "Promotion requires real paired solver replay against `g556_c063174` with the strict zero-success-regression gate.\n\n"
        "Scale and replay evidence:\n\n"
        f"- context horizons: `{fmt(decision.get('context_horizons'))}`\n"
        f"- primary row-level examples vs g556: `{fmt(decision.get('primary_row_level_examples_vs_g556'))}`\n"
        f"- total usable row-level examples: `{fmt(decision.get('total_row_level_examples'))}`\n"
        f"- same-context candidate rows: `{fmt(label.get('same_context_candidate_rows'))}`\n"
        f"- Stage1 / Stage2 / blind solver rows: `{fmt(decision.get('stage1_solver_rows'))}` / `{fmt(decision.get('stage2_solver_rows'))}` / `{fmt(decision.get('blind_solver_rows'))}`\n"
        f"- success regressions vs g556: `{fmt(decision.get('success_regressions_vs_g556'))}`\n"
        f"- quality delta vs g556: `{fmt(decision.get('quality_delta_vs_g556'))}`; CI upper `{fmt(decision.get('quality_delta_ci_upper_vs_g556'))}`\n"
        f"- better/worse quality pairs vs g556: `{fmt(decision.get('better_count_vs_g556'))}` / `{fmt(decision.get('worse_count_vs_g556'))}`\n\n"
        "Closed-claim policy remains unchanged: `phase5p5_allowed=false`, `phase6_allowed=false`, "
        "`runtime_claim_allowed=false`, `learned_runtime_policy_validated=false`, and `aaai_ready=false`.\n\n"
        f"{audit_line}\n"
        f"{END}\n"
    )


def replace_marker_block(text: str, block: str) -> str:
    start = text.find(BEGIN)
    end = text.find(END)
    if start != -1 and end != -1 and end > start:
        end += len(END)
        return text[:start].rstrip() + "\n\n" + block.rstrip() + "\n\n" + text[end:].lstrip()
    return text.rstrip() + "\n\n" + block.rstrip() + "\n"


def insert_after_heading(text: str, heading: str, block: str) -> str:
    if BEGIN in text and END in text:
        return replace_marker_block(text, block)
    idx = text.find(heading)
    if idx == -1:
        return replace_marker_block(text, block)
    next_idx = text.find("\n## ", idx + len(heading))
    if next_idx == -1:
        return text.rstrip() + "\n\n" + block.rstrip() + "\n"
    return text[:next_idx].rstrip() + "\n\n" + block.rstrip() + "\n\n" + text[next_idx + 1 :]


def update_file(path: Path, block: str) -> bool:
    original = path.read_text(encoding="utf-8")
    if path == EXECUTION_PLAN_MD:
        updated = insert_after_heading(original, "## 2026-06-18 Repair5G.5.57 graph-conditioned static-theta execution update", block)
    elif path == DEEP_RESEARCH_MD:
        updated = insert_after_heading(original, "## 2026-06-18 - G5.57 governance update: graph-conditioned static theta, not runtime policy", block)
    else:
        updated = replace_marker_block(original, block)
    if updated == original:
        return False
    path.write_text(updated, encoding="utf-8", newline="\n")
    return True


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    decision = load_json(DECISION_SUMMARY)
    label = load_json(LABEL_SUMMARY, required=False)
    audit = load_json(AUDIT_SUMMARY, required=False)
    require_static_guardrails(decision)
    block = block_text(decision, label, audit)
    files = [PLAN_MD, DEEP_RESEARCH_MD, EXECUTION_PLAN_MD]
    changed: list[str] = []
    if not args.dry_run:
        for path in files:
            if update_file(path, block):
                changed.append(str(path.relative_to(ROOT)))
    print(json.dumps({"decision": decision.get("decision"), "dry_run": args.dry_run, "changed": changed}, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
