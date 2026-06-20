from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "outputs/reports"
ROUND = "phase5p5_repair5g564"


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    dataset = load_json(REPORTS / "phase5p5_repair5g563_labelv52_set_dataset_summary.json")
    tiny = load_json(REPORTS / "phase5p5_repair5g563_tiny_overfit_summary.json")
    scaling = load_json(REPORTS / "phase5p5_repair5g563_scaling_study_summary.json")
    leakage_features = ["original_row_count", "positive_rows", "safe_rows", "harmful_rows", "censored_rows"]
    summary = {
        "schema_version": f"{ROUND}_g563_truth_audit_v1",
        "decision": "g564_g563_scaling_invalid_target_leakage",
        "g563_labelv52_dataset_valid": dataset.get("positive_set_is_not_averaged") is True
        and dataset.get("censored_rows_are_negative") is False,
        "g563_tiny_overfit_valid_graph_actor_evidence": False,
        "g563_tiny_overfit_failure_reinterpreted_as": "per_context_free_theta_loss_floor_or_optimizer_diagnostic",
        "g563_scaling_valid_primary_evidence": False,
        "g563_scaling_invalid_reason": "scalar_context_set_mlp_control consumed label/outcome counts",
        "g563_leaking_scalar_features": leakage_features,
        "g563_reported_scaling_decision": scaling.get("decision", ""),
        "g563_reported_tiny_decision": tiny.get("decision", ""),
        "g563_contexts": dataset.get("contexts"),
        "g563_candidate_rows": dataset.get("candidate_rows"),
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "runtime_claim_allowed": False,
        "learned_runtime_policy_validated": False,
        "aaai_ready": False,
    }
    write_json(REPORTS / f"{ROUND}_g563_truth_audit_summary.json", summary)
    (REPORTS / f"{ROUND}_g563_truth_audit.md").write_text(
        "# G5.64 Truth Audit of G5.63\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- valid carried forward: Label-v5.2 set-valued rows, non-averaged positives, censored-not-negative semantics.\n"
        "- invalidated: G5.63 scalar scaling as primary evidence, because the scalar model read label/outcome counts.\n"
        "- reinterpreted: G5.63 tiny overfit as a per-context free-theta diagnostic, not a graph-actor memorization result.\n"
        f"- leaking G5.63 fields: `{', '.join(leakage_features)}`\n\n"
        "G5.64 therefore starts from the Label-v5.2 data repair, but reopens loss geometry, neural memorization, and leakage-free scaling.\n",
        encoding="utf-8",
    )
    print(json.dumps({"decision": summary["decision"], "g563_contexts": summary["g563_contexts"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
