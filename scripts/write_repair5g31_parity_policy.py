"""Write the conservative Repair5G.3.1 parity policy report."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g3_common import load_json, repo_root, resolve, write_json  # noqa: E402


DEFAULT_AUTOPSY = "outputs/reports/phase5p5_repair5g3_protocol_failure_autopsy_summary.json"
DEFAULT_REPRODUCER = "outputs/reports/phase5p5_repair5g31_control_parity_reproducer_summary.json"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g31_parity_policy.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g31_parity_policy_summary.json"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--autopsy-summary-json", type=Path, default=Path(DEFAULT_AUTOPSY))
    parser.add_argument("--reproducer-summary-json", type=Path, default=Path(DEFAULT_REPRODUCER))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    return parser.parse_args(argv)


def write_report(path: Path, summary: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Phase5.5 Repair5G.3.1 Parity Policy\n\n")
        handle.write("This policy is conservative and diagnostic-only. It does not grant Phase5.5 or Phase6 permission.\n\n")
        handle.write("## Layers\n\n")
        handle.write("### Semantic Parity\n\n")
        handle.write(
            "No control method may change LaCAM*/PIBT/LTM semantics. The accepted semantic gate is "
            "`true_semantic_parity_mismatch_count = 0` after raw-row autopsy and sequential reproduction.\n\n"
        )
        handle.write("### Strict Wall-Clock Parity\n\n")
        handle.write(
            "Exact rows are still reported for additive, disabled, force-additive, dual-additive, and "
            "dual-C-equivalent controls. A strict exact failure must keep `protocol_gates_passed=false` unless "
            "a separate, explicit parity policy is active for broad validation.\n\n"
        )
        handle.write("### Time-Budget-Equivalent Parity\n\n")
        handle.write(
            "For broad anytime validation, strict differences may be accepted only when every mismatch is classified "
            "as time-budget sensitivity, timeout equivalence, return-code-2 no-solution equivalence, or reporting-only, "
            "with zero true semantic mismatches and zero solver crashes.\n\n"
        )
        handle.write("## Decision\n\n")
        handle.write(f"- policy_decision: `{summary['policy_decision']}`\n")
        handle.write(f"- strict_parity_restored: `{summary['strict_parity_restored']}`\n")
        handle.write(f"- broad_validation_policy: `{summary['broad_validation_policy']}`\n")
        handle.write(f"- parity_policy_accepted: `{summary['gates']['parity_policy_accepted']}`\n\n")
        handle.write("## Required G4 Protocol\n\n")
        handle.write("- Keep strict exact parity fields in reports and audits.\n")
        handle.write("- Require semantic parity and time-budget-equivalence classification for broad clean validation.\n")
        handle.write("- Require `returncode 2` to be handled as no-solution/timeout equivalent, not solver crash.\n")
        handle.write("- Require boolean and numeric gate types to remain distinct.\n")
        handle.write("- Do not allow selected or representation gates to override a protocol failure.\n\n")
        handle.write("## Boundary\n\n")
        handle.write("- phase5p5_allowed: `false`\n")
        handle.write("- phase6_allowed: `false`\n")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    autopsy = load_json(resolve(args.autopsy_summary_json, root))
    reproducer = load_json(resolve(args.reproducer_summary_json, root))
    strict_restored = int(reproducer.get("strict_mismatch_pair_count", 1)) == 0
    accepted = bool(
        autopsy.get("ready_for_control_parity_reproducer")
        and reproducer.get("protocol_reproducer_passed")
        and autopsy.get("bool_as_int_gate_type_violations", 1) == 0
        and autopsy.get("true_semantic_parity_mismatch_count", 1) == 0
        and reproducer.get("true_semantic_parity_mismatch_count", 1) == 0
    )
    if strict_restored and accepted:
        policy_decision = "strict_parity_restored_require_strict_g4"
        broad_policy = "strict_exact_parity_required"
    elif accepted:
        policy_decision = "time_budget_equivalent_parity_accepted_for_g4_broad_validation"
        broad_policy = "semantic_parity_plus_time_budget_equivalence_required"
    else:
        policy_decision = "stop_for_protocol_parity_unresolved"
        broad_policy = "blocked"
    summary = {
        "schema_version": "phase5p5_repair5g31_parity_policy_summary_v1",
        "created_at": __import__("datetime").datetime.now().isoformat(),
        "policy_decision": policy_decision,
        "strict_parity_restored": strict_restored,
        "broad_validation_policy": broad_policy,
        "autopsy_summary": str(resolve(args.autopsy_summary_json, root).relative_to(root)),
        "reproducer_summary": str(resolve(args.reproducer_summary_json, root).relative_to(root)),
        "gates": {
            "autopsy_ready_for_reproducer": bool(autopsy.get("ready_for_control_parity_reproducer")),
            "reproducer_passed": bool(reproducer.get("protocol_reproducer_passed")),
            "bool_as_int_gate_type_violations_zero": autopsy.get("bool_as_int_gate_type_violations", 1) == 0,
            "semantic_parity_mismatch_zero": autopsy.get("true_semantic_parity_mismatch_count", 1) == 0
            and reproducer.get("true_semantic_parity_mismatch_count", 1) == 0,
            "parity_policy_accepted": accepted,
            "phase5p5_allowed": False,
            "phase6_allowed": False,
        },
        "diagnostic_only": True,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_report(resolve(args.report, root), summary)
    print(json.dumps({"policy_decision": policy_decision, "accepted": accepted}))
    return 0 if accepted else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
