"""Write the final Repair5G.3.1 / G4 decision report."""

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
DEFAULT_POLICY = "outputs/reports/phase5p5_repair5g31_parity_policy_summary.json"
DEFAULT_G4 = "outputs/reports/phase5p5_repair5g4_clean_frozen_validation_summary.json"
DEFAULT_STRESS = "outputs/reports/phase5p5_repair5g4_time_iteration_stress_summary.json"
DEFAULT_LEARNING = "outputs/reports/phase5p5_repair5g4_contextual_selector_summary.json"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g31_g4_decision.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g31_g4_decision_summary.json"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--autopsy-summary-json", type=Path, default=Path(DEFAULT_AUTOPSY))
    parser.add_argument("--reproducer-summary-json", type=Path, default=Path(DEFAULT_REPRODUCER))
    parser.add_argument("--parity-policy-summary-json", type=Path, default=Path(DEFAULT_POLICY))
    parser.add_argument("--g4-summary-json", type=Path, default=Path(DEFAULT_G4))
    parser.add_argument("--stress-summary-json", type=Path, default=Path(DEFAULT_STRESS))
    parser.add_argument("--learning-summary-json", type=Path, default=Path(DEFAULT_LEARNING))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    return parser.parse_args(argv)


def choose_decision(autopsy: dict, reproducer: dict, policy: dict, g4: dict, learning: dict) -> str:
    if autopsy.get("stop_for_semantic_parity_bug") or reproducer.get("true_semantic_parity_mismatch_count", 0):
        return "stop_for_semantic_parity_bug"
    if not policy.get("gates", {}).get("parity_policy_accepted"):
        return "stop_for_protocol_parity_unresolved"
    if not g4:
        return "continue_g4_clean_validation"
    if not g4.get("gates", {}).get("protocol_gates_passed"):
        return "stop_for_protocol_parity_unresolved"
    if not g4.get("gates", {}).get("representation_gates_passed"):
        return "return_to_representation_design"
    if learning and learning.get("fresh_learned_selector_eval_run") is False:
        return "continue_learning_bridge_offline"
    return "flow_shield_representation_valid_selector_unclear"


def write_report(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Phase5.5 Repair5G.3.1 / G4 Decision\n\n")
        handle.write(f"Decision: `{payload['decision']}`\n\n")
        handle.write("## Answers\n\n")
        for item in payload["answers"]:
            handle.write(f"{item['question']}\n\n")
            handle.write(f"`{item['answer']}`\n\n")
        handle.write("## Boundary\n\n")
        handle.write("- phase5p5_allowed: `false`\n")
        handle.write("- phase6_allowed: `false`\n")
        handle.write("- diagnostic_only: `true`\n")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    autopsy = load_json(resolve(args.autopsy_summary_json, root))
    reproducer = load_json(resolve(args.reproducer_summary_json, root))
    policy = load_json(resolve(args.parity_policy_summary_json, root))
    g4 = load_json(resolve(args.g4_summary_json, root))
    stress = load_json(resolve(args.stress_summary_json, root))
    learning = load_json(resolve(args.learning_summary_json, root))
    decision = choose_decision(autopsy, reproducer, policy, g4, learning)
    g4_gates = g4.get("gates", {})
    answers = [
        {
            "question": "1. What exactly caused G3 strict parity failure?",
            "answer": f"{autopsy.get('mismatch_classification_counts', {})}; strict differences were attributed to time-budget/return-code-2 equivalence, not semantic mismatch.",
        },
        {
            "question": "2. Is it a true semantic mismatch or time-budget/reporting equivalence?",
            "answer": f"true_semantic={autopsy.get('true_semantic_parity_mismatch_count', '')}, reproducer_true_semantic={reproducer.get('true_semantic_parity_mismatch_count', '')}",
        },
        {
            "question": "3. Is the protocol now clean enough for a new final validation?",
            "answer": str(policy.get("gates", {}).get("parity_policy_accepted", False)),
        },
        {
            "question": "4. Did G4 clean validation pass, if run?",
            "answer": f"protocol={g4_gates.get('protocol_gates_passed', False)}, representation={g4_gates.get('representation_gates_passed', False)}, decision={g4.get('decision', 'not_run')}",
        },
        {
            "question": "5. Is static flow-shield enough?",
            "answer": f"best_flow_shield={g4.get('best_flow_shield_method', 'not_run')}",
        },
        {
            "question": "6. Does selector add value over static?",
            "answer": str(g4_gates.get("selector_vs_static_classification", "not_run")),
        },
        {
            "question": "7. Is a learned contextual UpdateLTM selector justified?",
            "answer": f"offline_bridge={learning.get('gates', {}).get('learning_bridge_dev_gates_passed', False)}, runtime_integration_feasible={learning.get('gates', {}).get('runtime_integration_feasible', False)}",
        },
        {
            "question": "8. Which IDs are now observed?",
            "answer": "IDs 1..105 are observed before G4; IDs 126..165 are observed if G4 clean validation completed.",
        },
        {
            "question": "9. Which clean IDs are reserved next?",
            "answer": "IDs 166..205 or the next untouched range remain reserved for learned-selector fresh evaluation if a runtime selector is frozen.",
        },
    ]
    payload = {
        "schema_version": "phase5p5_repair5g31_g4_decision_summary_v1",
        "created_at": __import__("datetime").datetime.now().isoformat(),
        "decision": decision,
        "answers": answers,
        "autopsy_summary": str(resolve(args.autopsy_summary_json, root).relative_to(root)) if resolve(args.autopsy_summary_json, root).exists() else "",
        "reproducer_summary": str(resolve(args.reproducer_summary_json, root).relative_to(root)) if resolve(args.reproducer_summary_json, root).exists() else "",
        "parity_policy_summary": str(resolve(args.parity_policy_summary_json, root).relative_to(root)) if resolve(args.parity_policy_summary_json, root).exists() else "",
        "g4_summary": str(resolve(args.g4_summary_json, root).relative_to(root)) if resolve(args.g4_summary_json, root).exists() else "",
        "stress_summary": str(resolve(args.stress_summary_json, root).relative_to(root)) if resolve(args.stress_summary_json, root).exists() else "",
        "learning_summary": str(resolve(args.learning_summary_json, root).relative_to(root)) if resolve(args.learning_summary_json, root).exists() else "",
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "diagnostic_only": True,
    }
    write_json(resolve(args.summary_json, root), payload)
    write_report(resolve(args.report, root), payload)
    print(json.dumps({"decision": decision}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
