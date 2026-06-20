from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ROUND = "phase5p5_repair5g564"
REPORTS = ROOT / "outputs/reports"
TABLES = ROOT / "outputs/tables"
MODEL_DIR = ROOT / "artifacts/models/gcst"
DECISION_JSON = REPORTS / f"{ROUND}_decision_summary.json"
DECISION_MD = REPORTS / f"{ROUND}_decision.md"
FAILURE_MD = REPORTS / f"{ROUND}_failure_attribution.md"
MANIFEST_JSON = REPORTS / f"{ROUND}_artifact_manifest.json"
CHECKSUMS = TABLES / f"{ROUND}_checksums.sha256"


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def read_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def artifact_rows() -> list[dict[str, Any]]:
    rows = []
    excluded = {MANIFEST_JSON.resolve(), CHECKSUMS.resolve()}
    for root in [REPORTS, TABLES, MODEL_DIR]:
        if not root.exists():
            continue
        for path in sorted(root.glob(f"{ROUND}*")):
            if not path.is_file() or path.resolve() in excluded:
                continue
            rows.append(
                {
                    "path": str(path.relative_to(ROOT)).replace("\\", "/"),
                    "bytes": path.stat().st_size,
                    "sha256": sha256_file(path),
                }
            )
    return rows


def main() -> int:
    truth = load_json(REPORTS / f"{ROUND}_g563_truth_audit_summary.json")
    geometry = load_json(REPORTS / f"{ROUND}_loss_geometry_summary.json")
    oracle = load_json(REPORTS / f"{ROUND}_parameter_oracle_summary.json")
    neural = load_json(REPORTS / f"{ROUND}_neural_memorization_summary.json")
    scaling = load_json(REPORTS / f"{ROUND}_rich_scaling_summary.json")
    true_cycle = load_json(REPORTS / f"{ROUND}_true_cycle_summary.json")
    fixed = load_json(REPORTS / f"{ROUND}_fixed_solver_panel_summary.json")
    scaling_rows = read_rows(TABLES / f"{ROUND}_rich_scaling_results.csv")
    pair_rows = read_rows(TABLES / f"{ROUND}_rich_vs_scalar_by_fold.csv")

    truth_gate = truth.get("decision") == "g564_g563_scaling_invalid_target_leakage"
    geometry_gate = geometry.get("decision") == "g564_loss_geometry_audited"
    oracle_gate = oracle.get("decision") == "g564_parameter_oracle_passed"
    neural_gate = neural.get("decision") == "g564_neural_memorization_passed"
    scaling_positive = scaling.get("decision") == "g564_rich_scaling_positive"
    true_cycle_gate = true_cycle.get("decision") == "g564_true_retraining_cycle_completed"
    fixed_solver_gate = fixed.get("new_g564_solver_panel_ran") is True and fixed.get("decision") == "g564_fixed_solver_panel_improves_with_data"

    if fixed.get("decision") == "g564_offline_scaling_solver_transfer_blocked":
        decision = "g564_offline_scaling_solver_transfer_blocked"
    elif truth_gate and geometry_gate and oracle_gate and neural_gate and scaling_positive and true_cycle_gate and fixed_solver_gate:
        decision = "g564_feasibility_supported_expand_contexts"
    elif truth_gate and geometry_gate and (oracle_gate or neural_gate) and scaling_rows:
        decision = "g564_feasibility_inconclusive_repair_labels"
    else:
        decision = "g564_feasibility_not_supported_keep_g556"

    summary = {
        "schema_version": f"{ROUND}_decision_summary_v1",
        "decision": decision,
        "truth_gate": truth_gate,
        "geometry_gate": geometry_gate,
        "parameter_oracle_gate": oracle_gate,
        "neural_memorization_gate": neural_gate,
        "rich_scaling_positive": scaling_positive,
        "true_cycle_gate": true_cycle_gate,
        "fixed_solver_gate": fixed_solver_gate,
        "g563_truth_decision": truth.get("decision", ""),
        "geometry_decision": geometry.get("decision", ""),
        "parameter_oracle_decision": oracle.get("decision", ""),
        "neural_memorization_decision": neural.get("decision", ""),
        "rich_scaling_decision": scaling.get("decision", ""),
        "rich_vs_scalar_decision": scaling.get("rich_vs_scalar_decision", ""),
        "true_cycle_decision": true_cycle.get("decision", ""),
        "fixed_solver_panel_decision": fixed.get("decision", ""),
        "contexts_geometry": geometry.get("contexts"),
        "conflicting_theta_pairs": geometry.get("conflicting_theta_pairs"),
        "rich_scaling_rows": len(scaling_rows),
        "rich_vs_scalar_pair_rows": len(pair_rows),
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "runtime_claim_allowed": False,
        "learned_runtime_policy_validated": False,
        "aaai_ready": False,
    }
    DECISION_JSON.parent.mkdir(parents=True, exist_ok=True)
    DECISION_JSON.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    DECISION_MD.write_text(
        "# G5.64 Decision\n\n"
        f"- decision: `{decision}`\n"
        f"- G5.63 truth audit: `{summary['g563_truth_decision']}`\n"
        f"- loss geometry: `{summary['geometry_decision']}`; conflicting theta pairs `{summary['conflicting_theta_pairs']}`\n"
        f"- parameter oracle: `{summary['parameter_oracle_decision']}`\n"
        f"- neural memorization: `{summary['neural_memorization_decision']}`\n"
        f"- leakage-free rich scaling: `{summary['rich_scaling_decision']}`; rich-vs-scalar `{summary['rich_vs_scalar_decision']}`\n"
        f"- true replay cycle: `{summary['true_cycle_decision']}`\n"
        f"- fixed solver panel: `{summary['fixed_solver_panel_decision']}`\n\n"
        "Claims remain closed.  G5.64 repairs the evidence chain and produces offline rich-actor results, but does not open runtime/Phase-6 claims without a fresh fixed solver panel.\n",
        encoding="utf-8",
    )
    FAILURE_MD.write_text(
        "# G5.64 Failure Attribution\n\n"
        "- G5.63 scaling was invalid as primary evidence because label/outcome counts were used as scalar features.\n"
        "- G5.63 tiny overfit did not test graph-actor memorization; it tested free per-context theta behavior.\n"
        f"- G5.64 loss geometry found `{summary['conflicting_theta_pairs']}` near-duplicate positive/harmful theta conflicts.\n"
        "- G5.64 fixed solver transfer remains blocked until a fresh fixed panel is run with the selected leakage-free actor.\n"
        "- Censored rows continue to be treated as unknown, not as negative/no-op supervision.\n",
        encoding="utf-8",
    )
    manifest = artifact_rows()
    MANIFEST_JSON.write_text(json.dumps({"schema_version": f"{ROUND}_artifact_manifest_v1", "artifacts": manifest}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    CHECKSUMS.parent.mkdir(parents=True, exist_ok=True)
    CHECKSUMS.write_text("".join(f"{row['sha256']}  {row['path']}\n" for row in manifest), encoding="utf-8")
    print(json.dumps({"decision": decision, "rich_scaling_rows": len(scaling_rows), "fixed_solver_gate": fixed_solver_gate}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
