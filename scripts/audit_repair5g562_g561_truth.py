from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


ROUND = "phase5p5_repair5g562"
G561 = "phase5p5_repair5g561"

REPORT_MD = Path(f"outputs/reports/{ROUND}_g561_training_truth_audit.md")
SUMMARY_JSON = Path(f"outputs/reports/{ROUND}_g561_training_truth_audit_summary.json")
TARGET_PROVENANCE = Path(f"outputs/tables/{ROUND}_g561_target_provenance_audit.csv")
SCENARIO_USAGE = Path(f"outputs/tables/{ROUND}_g561_scenario_bank_usage_audit.csv")
CRITIC_TRUTH = Path(f"outputs/tables/{ROUND}_g561_critic_truth_audit.csv")
REPLAY_EVIDENCE = Path(f"outputs/tables/{ROUND}_g561_replay_evidence_matrix.csv")


def claims() -> dict[str, bool]:
    return {
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "runtime_claim_allowed": False,
        "learned_runtime_policy_validated": False,
        "aaai_ready": False,
    }


def resolve(path: str | Path) -> Path:
    p = Path(path)
    return p if p.is_absolute() else ROOT / p


def read_json(path: str | Path) -> dict[str, Any]:
    p = resolve(path)
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def read_rows(path: str | Path) -> list[dict[str, str]]:
    p = resolve(path)
    if not p.exists():
        return []
    with p.open(newline="", encoding="utf-8") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def write_rows(path: str | Path, rows: list[dict[str, Any]]) -> None:
    p = resolve(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with p.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: str | Path, data: dict[str, Any]) -> None:
    p = resolve(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def source_contains(path: str | Path, text: str) -> bool:
    p = resolve(path)
    return p.exists() and text in p.read_text(encoding="utf-8")


def target_provenance_rows() -> list[dict[str, Any]]:
    analytic = source_contains("scripts/train_repair5g561_goal_aware_actor.py", "context_target_theta")
    build_samples = source_contains("scripts/train_repair5g561_goal_aware_actor.py", "def build_samples")
    hard_blend = source_contains("scripts/run_repair5g561_hard_negative_finetune_panel.py", "blend * np.asarray(BASELINE_G556")
    return [
        {
            "component": "g561_initial_graph_actor_training",
            "target_source": "analytic_context_target_theta",
            "real_solver_label_target": False,
            "evidence": "train_repair5g561_goal_aware_actor.py calls build_samples and context_target_theta",
            "present": analytic and build_samples,
            "g562_allowed_primary_target": False,
            **claims(),
        },
        {
            "component": "g561_hard_negative_finetune",
            "target_source": "harmful_actor_output_blended_toward_g556",
            "real_solver_label_target": "partial_hard_negative_only",
            "evidence": "run_repair5g561_hard_negative_finetune_panel.py target_from_pair blends source theta toward BASELINE_G556",
            "present": hard_blend,
            "g562_allowed_primary_target": False,
            **claims(),
        },
        {
            "component": "g562_required_actor_training",
            "target_source": "real_label_v51_safe_improving_and_harmful_sets",
            "real_solver_label_target": True,
            "evidence": "G5.62 must build a new graph/OD/C0/F0 dataset from real solver-derived Label-v5.1 rows",
            "present": False,
            "g562_allowed_primary_target": True,
            **claims(),
        },
    ]


def scenario_usage_rows(training: dict[str, Any], scenario: dict[str, Any]) -> list[dict[str, Any]]:
    variants = training.get("variants", [])
    first_variant = variants[0] if variants else {}
    train_instances = first_variant.get("train_instances", "")
    valid_instances = first_variant.get("validation_instances", "")
    return [
        {
            "component": "g561_valid_scenario_bank",
            "scenario_rows": scenario.get("valid_scenarios", ""),
            "consumed_by_primary_actor_training": False,
            "consumed_by_self_supervised_pretraining": False,
            "consumed_by_critic_training": False,
            "consumed_by_targeted_design": False,
            "consumed_by_heldout_replay": True,
            "evidence": f"G5.61 training used generated build_samples train={train_instances} validation={valid_instances}; development replay consumed heldout contexts.",
            **claims(),
        },
        {
            "component": "g562_required_real_graph_dataset",
            "scenario_rows": "",
            "consumed_by_primary_actor_training": "required",
            "consumed_by_self_supervised_pretraining": "required",
            "consumed_by_critic_training": "required",
            "consumed_by_targeted_design": "required",
            "consumed_by_heldout_replay": "required",
            "evidence": "Must record exact scenario IDs consumed by each loader.",
            **claims(),
        },
    ]


def critic_truth_rows(training: dict[str, Any], primary: dict[str, Any]) -> list[dict[str, Any]]:
    calibration = read_rows(f"outputs/tables/{G561}_critic_calibration.csv")
    f7_cal = next((row for row in calibration if row.get("variant_id") == "F7"), {})
    variants = training.get("variants", [])
    f7 = next((row for row in variants if row.get("variant_id") == "F7"), {})
    return [
        {
            "component": "g561_F7_flag",
            "critic_training_only": bool(f7.get("critic_training_only")),
            "real_graph_conditioned_outcome_critic": False,
            "has_theta_input": False,
            "has_real_success_regression_target": False,
            "has_quality_target": False,
            "has_heldout_calibration": False,
            "risk_pr_auc": f7_cal.get("risk_pr_auc", ""),
            "evidence": "F7 is a training flag/regularizer path; calibration table is placeholder-level and deployment_includes_critic is false.",
            **claims(),
        },
        {
            "component": "g562_required_critic",
            "critic_training_only": True,
            "real_graph_conditioned_outcome_critic": "required",
            "has_theta_input": "required",
            "has_real_success_regression_target": "required",
            "has_quality_target": "required",
            "has_heldout_calibration": "required",
            "risk_pr_auc": "",
            "evidence": "Must train a graph-conditioned theta-outcome critic for actor training only.",
            **claims(),
        },
    ]


def replay_rows() -> list[dict[str, Any]]:
    arch = read_json(f"outputs/reports/{G561}_architecture_replay_summary.json")
    dev = read_json(f"outputs/reports/{G561}_dev_replay_summary.json")
    panel = read_json(f"outputs/reports/{G561}_hard_negative_finetune_panel_summary.json")
    rows = []
    for name, data, interpretation in [
        ("architecture_replay", arch, "small exact-materialized architecture panel"),
        ("development_replay", dev, "larger heldout replay exposing success regressions and positive quality loss"),
        ("hard_negative_finetune_panel", panel, "fine-tune reduced regressions but remained not promotable"),
    ]:
        rows.append(
            {
                "evidence_source": name,
                "decision": data.get("decision", ""),
                "actor_rows": data.get("actor_rows", ""),
                "replay_pairs": data.get("replay_pairs", ""),
                "materialization_invalid_rows": data.get("materialization_invalid_rows", ""),
                "success_regressions": data.get("success_regressions", data.get("fine_tuned_success_regressions", "")),
                "mean_quality_delta_vs_g556": data.get("mean_quality_delta_vs_g556", data.get("fine_tuned_mean_quality_delta_vs_g556", "")),
                "better": data.get("better", data.get("fine_tuned_better", "")),
                "worse": data.get("worse", data.get("fine_tuned_worse", "")),
                "interpretation": interpretation,
                **claims(),
            }
        )
    return rows


def main() -> int:
    training = read_json(f"outputs/reports/{G561}_training_summary.json")
    primary = read_json(f"outputs/reports/{G561}_primary_seed_training_summary.json")
    scenario = read_json(f"outputs/reports/{G561}_scenario_validity_summary.json")
    decision = read_json(f"outputs/reports/{G561}_decision_summary.json")
    target_rows = target_provenance_rows()
    usage_rows = scenario_usage_rows(training, scenario)
    critic_rows = critic_truth_rows(training, primary)
    replay_evidence = replay_rows()
    write_rows(TARGET_PROVENANCE, target_rows)
    write_rows(SCENARIO_USAGE, usage_rows)
    write_rows(CRITIC_TRUTH, critic_rows)
    write_rows(REPLAY_EVIDENCE, replay_evidence)
    g561_training_was_synthetic = any(row["component"] == "g561_initial_graph_actor_training" and row["present"] for row in target_rows)
    g561_critic_not_real = bool(critic_rows and critic_rows[0]["real_graph_conditioned_outcome_critic"] is False)
    summary = {
        "schema_version": f"{ROUND}_g561_training_truth_audit_summary_v1",
        "decision": "g562_g561_synthetic_target_training_confirmed",
        "g561_start_decision": decision.get("decision", ""),
        "g561_training_was_analytic_target_smoke": g561_training_was_synthetic,
        "g561_scenario_bank_valid_scenarios": scenario.get("valid_scenarios", ""),
        "g561_primary_actor_training_used_valid_scenario_bank_as_main_dataset": False,
        "g561_critic_was_real_calibrated_graph_conditioned_outcome_critic": not g561_critic_not_real,
        "g561_hard_negative_finetune_was_safety_shrinkage_not_positive_frontier_learning": True,
        "g562_requires_real_label_graph_dataset": True,
        **claims(),
    }
    write_json(SUMMARY_JSON, summary)
    lines = [
        "# Repair5G.5.62 G5.61 Training Truth Audit",
        "",
        f"- decision: `{summary['decision']}`",
        f"- G5.61 final decision: `{summary['g561_start_decision']}`",
        f"- analytic target smoke confirmed: `{summary['g561_training_was_analytic_target_smoke']}`",
        f"- valid scenario bank as main actor dataset: `{summary['g561_primary_actor_training_used_valid_scenario_bank_as_main_dataset']}`",
        f"- real calibrated graph-conditioned critic present: `{summary['g561_critic_was_real_calibrated_graph_conditioned_outcome_critic']}`",
        "",
        "G5.61 repaired materialization and representation plumbing, but its first graph actors were trained on analytic targets and later safety shrinkage. G5.62 must train from real Label-v5.1 safe/improving, harmful, and censored solver rows.",
        "",
        "Claims remain closed.",
    ]
    resolve(REPORT_MD).parent.mkdir(parents=True, exist_ok=True)
    resolve(REPORT_MD).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"decision": summary["decision"], "valid_scenarios": summary["g561_scenario_bank_valid_scenarios"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
