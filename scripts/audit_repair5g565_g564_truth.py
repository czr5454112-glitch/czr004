from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ROUND = "phase5p5_repair5g565"
REPORTS = ROOT / "outputs/reports"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    g564_decision = load_json(REPORTS / "phase5p5_repair5g564_decision_summary.json")
    g564_scaling = load_json(REPORTS / "phase5p5_repair5g564_rich_scaling_summary.json")
    g564_neural = load_json(REPORTS / "phase5p5_repair5g564_neural_memorization_summary.json")
    g564_oracle = load_json(REPORTS / "phase5p5_repair5g564_parameter_oracle_summary.json")
    g564_cycle = load_json(REPORTS / "phase5p5_repair5g564_true_cycle_summary.json")
    g564_fixed = load_json(REPORTS / "phase5p5_repair5g564_fixed_solver_panel_summary.json")
    summary = {
        "schema_version": f"{ROUND}_g564_truth_audit_summary_v1",
        "decision": "g565_g564_rich_scaling_underpowered_anchor_confounded",
        "g564_parameter_oracle_loss": "repaired_floor_corrected_objective",
        "g564_rich_actor_loss": "old_g563_set_valued_actor_loss",
        "g564_oracle_actor_loss_parity": False,
        "g564_neural_memorization_context_sizes": [1, 4],
        "g564_neural_memorization_strong_gate": False,
        "g564_neural_memorization_decision": g564_neural.get("decision", ""),
        "g564_parameter_oracle_decision": g564_oracle.get("decision", ""),
        "g564_rich_scaling_train_contexts": g564_scaling.get("train_contexts_available"),
        "g564_rich_scaling_validation_contexts": g564_scaling.get("fixed_validation_contexts"),
        "g564_rich_scaling_seeds": len(g564_scaling.get("seeds", [])),
        "g564_rich_scaling_folds": 1,
        "g564_rich_scaling_steps": 30,
        "g564_rich_scaling_statistically_supported": False,
        "g564_rich_vs_scalar_output_parameterization_matched": False,
        "g564_true_cycle_model": "scalar",
        "g564_true_cycle_decision": g564_cycle.get("decision", ""),
        "g564_true_cycle_rich_actor": False,
        "g564_new_solver_panel_ran": bool(g564_fixed.get("new_g564_solver_panel_ran")),
        "g564_fixed_solver_decision": g564_fixed.get("decision", ""),
        "g564_final_decision": g564_decision.get("decision", ""),
        "historical_interpretation": "promising_underpowered_offline_probe_not_strict_rich_actor_feasibility_pass",
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "runtime_claim_allowed": False,
        "learned_runtime_policy_validated": False,
        "aaai_ready": False,
    }
    write_json(REPORTS / f"{ROUND}_g564_truth_audit_summary.json", summary)
    (REPORTS / f"{ROUND}_g564_truth_audit.md").write_text(
        "# G5.65 Truth Audit of G5.64\n\n"
        f"- decision: `{summary['decision']}`\n"
        "- G5.64 remains useful engineering evidence, but its rich-scaling gate was underpowered and anchor-confounded.\n"
        "- G5.64 oracle and actor did not optimize the same mathematical loss.\n"
        "- G5.64 true-cycle was scalar-only and the fixed panel was copied from older exact rows.\n"
        "- G5.65 therefore reopens loss parity, matched controls, strong memorization, current-bank scaling, rich retraining, and fresh solver transfer.\n",
        encoding="utf-8",
    )
    print(json.dumps({"decision": summary["decision"], "g564_final": summary["g564_final_decision"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
