from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gcst.schemas_v51 import parse_bool  # noqa: E402


ROUND = "phase5p5_repair5g561"
SOURCE = "phase5p5_repair5g560"

SCENARIO_REPAIR_MD = Path(f"outputs/reports/{ROUND}_scenario_generator_repair.md")
SCENARIO_SUMMARY = Path(f"outputs/reports/{ROUND}_scenario_validity_summary.json")
SCENARIO_AUDIT = Path(f"outputs/tables/{ROUND}_scenario_validity_audit.csv")
VALID_MANIFEST = Path(f"outputs/tables/{ROUND}_valid_instance_manifest.csv")
SPLIT_MANIFEST = Path(f"outputs/tables/{ROUND}_physical_map_split_manifest.csv")
ORACLE_MD = Path(f"outputs/reports/{ROUND}_valid_oracle_opportunity.md")
ORACLE_SUMMARY = Path(f"outputs/reports/{ROUND}_valid_oracle_opportunity_summary.json")
ORACLE_BY_STRATUM = Path(f"outputs/tables/{ROUND}_valid_oracle_by_stratum.csv")
FAILURE_MD = Path(f"outputs/reports/{ROUND}_failure_attribution.md")
FAILURE_CSV = Path(f"outputs/tables/{ROUND}_failure_attribution.csv")
ARTIFACT_MANIFEST = Path(f"outputs/reports/{ROUND}_artifact_manifest.json")
CHECKSUMS = Path(f"outputs/tables/{ROUND}_checksums.sha256")
DECISION_MD = Path(f"outputs/reports/{ROUND}_decision.md")
DECISION_SUMMARY = Path(f"outputs/reports/{ROUND}_decision_summary.json")
ARCH_REPLAY_PAIRS = Path(f"outputs/tables/{ROUND}_architecture_replay_pairs.csv")
ARCH_REPLAY_SUMMARY = Path(f"outputs/reports/{ROUND}_architecture_replay_summary.json")
CORRECTED_REPLAY_SUMMARY = Path(f"outputs/reports/{ROUND}_corrected_g560_replay_summary.json")
DEV_REPLAY = Path(f"outputs/tables/{ROUND}_dev_replay_by_stratum.csv")
DEV_REPLAY_SUMMARY = Path(f"outputs/reports/{ROUND}_dev_replay_summary.json")
HARD_NEGATIVE = Path(f"outputs/tables/{ROUND}_hard_negative_acquisition.csv")
HARD_NEGATIVE_SUMMARY = Path(f"outputs/reports/{ROUND}_hard_negative_acquisition_summary.json")
PRIMARY_SEED_SUMMARY = Path(f"outputs/reports/{ROUND}_primary_seed_training_summary.json")
FINE_TUNE_SUMMARY = Path(f"outputs/reports/{ROUND}_hard_negative_finetune_summary.json")
FINE_TUNE_PANEL_SUMMARY = Path(f"outputs/reports/{ROUND}_hard_negative_finetune_panel_summary.json")
CONTRACT_SUMMARY = Path(f"outputs/reports/{ROUND}_materialization_contract_summary.json")


def resolve(path: str | Path) -> Path:
    p = Path(path)
    return p if p.is_absolute() else ROOT / p


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


def read_json(path: str | Path) -> dict[str, Any]:
    p = resolve(path)
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def write_json(path: str | Path, data: dict[str, Any]) -> None:
    p = resolve(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def write_text(path: str | Path, text: str) -> None:
    p = resolve(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def stable_uid(*parts: Any) -> str:
    payload = json.dumps(parts, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def claims() -> dict[str, bool]:
    return {
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "runtime_claim_allowed": False,
        "learned_runtime_policy_validated": False,
        "aaai_ready": False,
    }


def write_scenario_artifacts() -> dict[str, Any]:
    existing = read_json(SCENARIO_SUMMARY)
    if (
        existing.get("valid_independent_instances_target_met") is True
        and resolve(SCENARIO_AUDIT).exists()
        and resolve(VALID_MANIFEST).exists()
        and resolve(SPLIT_MANIFEST).exists()
    ):
        return existing
    source_rows = read_rows(f"outputs/tables/{SOURCE}_scenario_validity_audit.csv")
    out_rows = []
    for row in source_rows:
        copied = dict(row)
        copied["source_round"] = SOURCE
        copied["retained_for_g561"] = True
        out_rows.append(copied)
    write_rows(SCENARIO_AUDIT, out_rows)
    valid = [row for row in out_rows if parse_bool(row.get("valid"))]
    manifest = []
    for idx, row in enumerate(valid):
        instance_uid = stable_uid("g561_valid_instance", row.get("map"), row.get("solver_seed"), row.get("scenario_sha256_actual"))
        manifest.append(
            {
                "g561_instance_uid": instance_uid,
                "map": row.get("map", ""),
                "map_family": row.get("map_family", ""),
                "solver_seed": row.get("solver_seed", ""),
                "scenario_sha256": row.get("scenario_sha256_actual", ""),
                "physical_map_sha256": row.get("map_sha256_actual", ""),
                "assignment_sha256": row.get("assignment_sha256_actual", ""),
                "pair_count": row.get("scenario_pair_count_actual", ""),
                "source_round": SOURCE,
                **claims(),
            }
        )
    write_rows(VALID_MANIFEST, manifest)
    hashes = sorted({row.get("physical_map_sha256", "") for row in manifest if row.get("physical_map_sha256")})
    split_names = ["train", "validation", "development-heldout", "blind-reserved"]
    split_by_hash = {h: split_names[idx % len(split_names)] for idx, h in enumerate(hashes)}
    split_rows = []
    by_hash_meta: dict[str, dict[str, str]] = {}
    for row in manifest:
        by_hash_meta.setdefault(row["physical_map_sha256"], row)
    for h in hashes:
        meta = by_hash_meta[h]
        split_rows.append({"physical_map_sha256": h, "split": split_by_hash[h], "map_example": meta.get("map", ""), "map_family": meta.get("map_family", ""), **claims()})
    write_rows(SPLIT_MANIFEST, split_rows)
    reason_counts = Counter()
    for row in out_rows:
        for reason in str(row.get("failure_reasons", "")).split(";"):
            if reason:
                reason_counts[reason] += 1
    summary = {
        "schema_version": "phase5p5_repair5g561_scenario_validity_summary_v1",
        "decision": "g561_valid_scenario_bank_underpowered_continue_generation",
        "source_round": SOURCE,
        "scenario_rows": len(out_rows),
        "valid_scenarios": len(valid),
        "invalid_scenarios": len(out_rows) - len(valid),
        "validity_rate": len(valid) / max(1, len(out_rows)),
        "valid_independent_instances_target": 2500,
        "valid_independent_instances_target_met": len(valid) >= 2500,
        "physical_map_hashes": len(hashes),
        "reason_counts": dict(sorted(reason_counts.items())),
        **claims(),
    }
    write_json(SCENARIO_SUMMARY, summary)
    write_text(
        SCENARIO_REPAIR_MD,
        "# Repair5G.5.61 Scenario Generator Repair\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- retained valid G5.60 scenarios: `{summary['valid_scenarios']}`\n"
        f"- target valid independent instances: `{summary['valid_independent_instances_target']}`\n"
        "- generator code path no longer uses modulo cell cycling; over-capacity assignments are marked invalid instead of duplicating vertices.\n"
        "- next required work: component-aware replacement generation until the valid bank reaches at least 2,500 independent instances.\n",
    )
    return summary


def write_oracle_artifacts() -> dict[str, Any]:
    pairs = read_rows(f"outputs/tables/{ROUND}_corrected_g560_replay_pairs.csv")
    exact = [row for row in pairs if row.get("materialization_class") == "valid_exact_materialization"]
    deltas = []
    for row in exact:
        try:
            deltas.append(float(row.get("quality_delta_vs_g556", "")))
        except ValueError:
            pass
    summary = {
        "schema_version": "phase5p5_repair5g561_valid_oracle_opportunity_summary_v1",
        "decision": "g561_valid_oracle_opportunity_limited_to_exact_g560_replay",
        "exact_materialized_pairs": len(exact),
        "safe_improvement_fraction": sum((not parse_bool(row.get("success_regression"))) and parse_bool(row.get("success_gain")) for row in exact) / max(1, len(exact)),
        "success_gain_fraction": sum(parse_bool(row.get("success_gain")) for row in exact) / max(1, len(exact)),
        "candidate_regression_rate": sum(parse_bool(row.get("success_regression")) for row in exact) / max(1, len(exact)),
        "mean_oracle_quality_gain_vs_g556": sum(deltas) / len(deltas) if deltas else None,
        **claims(),
    }
    by_class = defaultdict(list)
    for row in pairs:
        by_class[row.get("materialization_class", "unknown")].append(row)
    rows = []
    for klass, group in sorted(by_class.items()):
        vals = []
        for row in group:
            try:
                vals.append(float(row.get("quality_delta_vs_g556", "")))
            except ValueError:
                pass
        rows.append(
            {
                "stratum": klass,
                "pairs": len(group),
                "success_regressions": sum(parse_bool(row.get("success_regression")) for row in group),
                "success_gains": sum(parse_bool(row.get("success_gain")) for row in group),
                "mean_quality_delta_vs_g556": sum(vals) / len(vals) if vals else "",
                **claims(),
            }
        )
    write_rows(ORACLE_BY_STRATUM, rows)
    write_json(ORACLE_SUMMARY, summary)
    write_text(
        ORACLE_MD,
        "# Repair5G.5.61 Valid-Only Oracle Opportunity\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- exact materialized G5.60 replay pairs: `{summary['exact_materialized_pairs']}`\n"
        f"- regression rate on exact rows: `{summary['candidate_regression_rate']}`\n"
        f"- mean quality delta vs g556 on exact rows: `{summary['mean_oracle_quality_gain_vs_g556']}`\n\n"
        "This is a cleaned reinterpretation of G5.60 exact-materialization rows, not a new full G5.61 oracle bank.\n",
    )
    return summary


def write_blocked_replay_artifacts(contract: dict[str, Any]) -> None:
    existing_arch = read_json(ARCH_REPLAY_SUMMARY)
    existing_decision = str(existing_arch.get("decision", ""))
    real_arch_replay = existing_decision.startswith("g561_architecture_replay_") and not any(
        token in existing_decision for token in ["pending", "blocked"]
    )
    if real_arch_replay and resolve(ARCH_REPLAY_PAIRS).exists():
        return
    contract_passed = bool(contract.get("materialization_contract_passed"))
    decision = "skipped_until_replay_ladder_runs" if contract_passed else "skipped_until_materialization_contract_passes"
    reason = (
        "G5.61 materialization contract passed; corrected scalar and architecture replay ladder has not been executed yet."
        if contract_passed
        else "G5.60 replay truth audit found mixed actor materialization; no architecture performance replay may be interpreted yet."
    )
    rows = [
        {
            "decision": decision,
            "reason": reason,
            **claims(),
        }
    ]
    write_rows(ARCH_REPLAY_PAIRS, rows)
    write_rows(DEV_REPLAY, rows)
    write_rows(HARD_NEGATIVE, rows)
    write_json(
        ARCH_REPLAY_SUMMARY,
        {
            "decision": "g561_architecture_replay_pending_after_materialization_contract" if contract_passed else "g561_architecture_replay_blocked_by_materialization_truth_gate",
            "materialization_contract_decision": contract.get("decision"),
            **claims(),
        },
    )
    write_json(
        DEV_REPLAY_SUMMARY,
        {
            "decision": "g561_dev_replay_pending_after_materialization_contract" if contract_passed else "g561_dev_replay_blocked_by_materialization_truth_gate",
            "materialization_contract_decision": contract.get("decision"),
            **claims(),
        },
    )


def build_final_failure_attribution(
    *,
    scenario: dict[str, Any],
    contract: dict[str, Any],
    training: dict[str, Any],
    corrected_replay: dict[str, Any],
    arch_replay: dict[str, Any],
    dev_replay: dict[str, Any],
    hard_negative: dict[str, Any],
    primary_seed: dict[str, Any],
    fine_tune: dict[str, Any],
    fine_tune_panel: dict[str, Any],
    replay_exact: bool,
    dev_real_replay: bool,
    hard_negative_done: bool,
    primary_seed_done: bool,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    scenario_target_met = bool(
        scenario.get("all_scenario_bank_targets_met")
        or scenario.get("valid_independent_instances_target_met")
    )
    contract_passed = bool(contract.get("materialization_contract_passed"))
    dev_success_regressions = as_int(dev_replay.get("success_regressions"))
    dev_success_gains = as_int(dev_replay.get("success_gains"))
    dev_worse = as_int(dev_replay.get("worse"))
    dev_mean_delta = as_float(dev_replay.get("mean_quality_delta_vs_g556"))
    materialization_invalid = as_int(dev_replay.get("materialization_invalid_rows"))
    large_positive = as_int(hard_negative.get("large_positive_quality_delta_source_rows"))
    critic_false_safe = as_int(hard_negative.get("critic_false_safe_proxy_rows"))
    fine_tune_completed = bool(fine_tune.get("fine_tune_completed") or fine_tune_panel.get("fine_tune_completed"))
    fine_tune_panel_executed = str(fine_tune_panel.get("decision", "")).startswith("g561_hard_negative_finetune_panel_")
    fine_tune_panel_passed = bool(fine_tune_panel.get("fine_tuned_panel_passed"))
    fine_tune_required = bool(
        dev_real_replay
        and hard_negative_done
        and primary_seed_done
        and (
            dev_success_regressions > 0
            or dev_mean_delta > 0.0
            or large_positive > 0
            or critic_false_safe > 0
        )
    )
    validation_rows = primary_seed.get("validation_by_variant", [])
    best_variant = ""
    best_validation = ""
    if validation_rows:
        best = min(validation_rows, key=lambda row: as_float(row.get("best_validation_normalized_l1"), float("inf")))
        best_variant = str(best.get("variant_id", ""))
        best_validation = str(best.get("best_validation_normalized_l1", ""))
    variants = ",".join(map(str, primary_seed.get("variants", [])))
    seeds = ",".join(map(str, primary_seed.get("seeds", [])))
    final_complete = bool(dev_real_replay and hard_negative_done and primary_seed_done)
    rows = [
        {
            "branch": "final_data",
            "category": "data",
            "status": (
                "scenario_bank_expanded_and_hard_negative_support_collected"
                if hard_negative_done and scenario_target_met
                else "hard_negative_support_collected_target_bank_still_underpowered"
                if hard_negative_done
                else "incomplete"
            ),
            "evidence": (
                f"valid_scenarios={scenario.get('valid_scenarios')} target={scenario.get('valid_independent_instances_target', 2500)}; "
                f"scenario_target_met={scenario_target_met}; acquisition_rows={hard_negative.get('acquisition_rows')}; "
                f"unique_acquisition_keys={hard_negative.get('unique_acquisition_keys')}"
            ),
        },
        {
            "branch": "final_representation",
            "category": "representation",
            "status": "implemented_and_causally_sensitive_but_not_replay_sufficient" if primary_seed_done else "incomplete",
            "evidence": (
                f"primary_variants={variants}; seeds={seeds}; causal_sensitivity_passed={primary_seed.get('causal_sensitivity_passed')}; "
                f"best_validation_variant={best_variant}; best_validation_normalized_l1={best_validation}"
            ),
        },
        {
            "branch": "final_loss",
            "category": "loss",
            "status": (
                "fine_tune_panel_passed"
                if fine_tune_panel_passed
                else "fine_tuned_but_not_promotable"
                if fine_tune_panel_executed
                else "requires_hard_negative_finetune"
                if fine_tune_required and not fine_tune_completed
                else "no_pending_loss_gate"
            ),
            "evidence": (
                f"dev_success_regressions={dev_success_regressions}; dev_success_gains={dev_success_gains}; "
                f"dev_worse={dev_worse}; mean_quality_delta_vs_g556={dev_replay.get('mean_quality_delta_vs_g556')}; "
                f"large_positive_quality_delta_source_rows={large_positive}; critic_false_safe_proxy_rows={critic_false_safe}; "
                f"fine_tune_decision={fine_tune.get('decision')}; panel_decision={fine_tune_panel.get('decision')}; "
                f"fine_tuned_success_regressions={fine_tune_panel.get('fine_tuned_success_regressions')}; "
                f"fine_tuned_mean_quality_delta_vs_g556={fine_tune_panel.get('fine_tuned_mean_quality_delta_vs_g556')}"
            ),
        },
        {
            "branch": "final_materialization",
            "category": "materialization",
            "status": "repaired_for_g561_exact_replays" if contract_passed and replay_exact and materialization_invalid == 0 else "unresolved",
            "evidence": (
                f"contract_passed={contract_passed}; candidate_rate={contract.get('candidate_recognized_rate')}; "
                f"fingerprint_rate={contract.get('fingerprint_exact_match_rate')}; corrected={corrected_replay.get('decision')}; "
                f"architecture={arch_replay.get('decision')}; dev_materialization_invalid_rows={materialization_invalid}"
            ),
        },
        {
            "branch": "final_solver_behavior",
            "category": "solver_behavior",
            "status": (
                "fine_tuned_panel_stage1_candidate"
                if fine_tune_panel_passed
                else "fine_tuned_panel_not_promotable"
                if fine_tune_panel_executed
                else "development_replay_not_promotable"
                if dev_success_regressions > 0 or dev_mean_delta > 0.0
                else "stable_under_development_replay"
            ),
            "evidence": (
                f"both_success={dev_replay.get('both_success')}; both_fail={dev_replay.get('both_fail')}; "
                f"mean_candidate_expanded_nodes={dev_replay.get('mean_candidate_expanded_nodes')}; "
                f"mean_candidate_low_level_pibt_calls={dev_replay.get('mean_candidate_low_level_pibt_calls')}; "
                f"mean_runtime_overhead_ms={dev_replay.get('mean_runtime_overhead_ms')}; worst_family_count={hard_negative.get('worst_family_count')}; "
                f"panel_contexts={fine_tune_panel.get('panel_contexts')}; panel_actor_rows={fine_tune_panel.get('actor_rows')}"
            ),
        },
    ]
    summary = {
        "final_failure_attribution_complete": final_complete,
        "final_failure_attribution_categories": [row["category"] for row in rows],
        "fine_tune_required": fine_tune_required,
        "fine_tune_completed": fine_tune_completed,
        "fine_tune_panel_executed": fine_tune_panel_executed,
        "fine_tune_panel_passed": fine_tune_panel_passed,
        "fine_tune_panel_decision": fine_tune_panel.get("decision", ""),
        "fine_tune_decision": (
            "fine_tune_panel_passed_stage1_planning_available"
            if fine_tune_panel_passed
            else "fine_tune_panel_completed_keep_g556_or_continue_loss_repair"
            if fine_tune_panel_executed
            else "fine_tune_completed_waiting_for_frozen_development_panel"
            if fine_tune_completed
            else
            "fine_tune_on_hard_negatives_and_rerun_frozen_development_panel"
            if fine_tune_required and not fine_tune_completed
            else "no_additional_fine_tune_required_from_current_evidence"
        ),
        "dev_success_regressions": dev_success_regressions,
        "dev_mean_quality_delta_vs_g556": dev_mean_delta,
        "fine_tuned_success_regressions": fine_tune_panel.get("fine_tuned_success_regressions"),
        "fine_tuned_mean_quality_delta_vs_g556": fine_tune_panel.get("fine_tuned_mean_quality_delta_vs_g556"),
    }
    return rows, summary


def write_failure_and_decision(scenario: dict[str, Any], oracle: dict[str, Any], contract: dict[str, Any]) -> dict[str, Any]:
    audit = read_json(f"outputs/reports/{ROUND}_g560_replay_truth_audit_summary.json")
    training = read_json(f"outputs/reports/{ROUND}_training_summary.json")
    corrected_replay = read_json(CORRECTED_REPLAY_SUMMARY)
    arch_replay = read_json(ARCH_REPLAY_SUMMARY)
    dev_replay = read_json(DEV_REPLAY_SUMMARY)
    hard_negative = read_json(HARD_NEGATIVE_SUMMARY)
    primary_seed = read_json(PRIMARY_SEED_SUMMARY)
    fine_tune = read_json(FINE_TUNE_SUMMARY)
    fine_tune_panel = read_json(FINE_TUNE_PANEL_SUMMARY)
    contract_passed = bool(contract.get("materialization_contract_passed"))
    corrected_decision = str(corrected_replay.get("decision", ""))
    arch_decision = str(arch_replay.get("decision", ""))
    dev_decision = str(dev_replay.get("decision", ""))
    hard_negative_decision = str(hard_negative.get("decision", ""))
    primary_seed_decision = str(primary_seed.get("decision", ""))
    corrected_real_replay = corrected_decision.startswith("g561_corrected_g560_scalar_replay_") and not any(
        token in corrected_decision for token in ["pending", "blocked"]
    )
    arch_real_replay = arch_decision.startswith("g561_architecture_replay_") and not any(token in arch_decision for token in ["pending", "blocked"])
    replay_executed = corrected_real_replay and arch_real_replay
    replay_exact = replay_executed and corrected_decision.endswith("_executed_exact_materialization") and arch_decision.endswith(
        "_executed_exact_materialization"
    )
    if replay_exact:
        replay_status = "executed_exact_materialization"
        next_required_gate = "run development replay and hard-negative acquisition from exact-materialized replay ladder rows"
    elif replay_executed:
        replay_status = "executed_needs_materialization_repair"
        next_required_gate = "repair replay ladder materialization identity/fingerprint failures before interpreting performance"
    elif contract_passed:
        replay_status = "pending_after_contract"
        next_required_gate = "run corrected G5.60 scalar replay and G5.61 architecture replay ladder with exact-materialization rows only"
    else:
        replay_status = "blocked"
        next_required_gate = "run G5.61 materialization contract on server and require candidate_recognized/fingerprint/identity/scenario rates all equal 1.0"
    dev_real_replay = dev_decision.startswith("g561_development_replay_") and not any(token in dev_decision for token in ["pending", "blocked"])
    hard_negative_done = hard_negative_decision.startswith("g561_hard_negative_acquisition_completed")
    primary_seed_done = bool(primary_seed.get("three_training_seeds_complete")) and primary_seed_decision == "g561_primary_seed_training_completed"
    if dev_real_replay and hard_negative_done:
        next_required_gate = "complete three training seeds for primary variants, then final failure attribution/fine-tune gate"
    if dev_real_replay and hard_negative_done and primary_seed_done:
        next_required_gate = "write final failure attribution and decide whether to fine-tune/rerun a frozen comparison panel"
    final_rows, final_summary = build_final_failure_attribution(
        scenario=scenario,
        contract=contract,
        training=training,
        corrected_replay=corrected_replay,
        arch_replay=arch_replay,
        dev_replay=dev_replay,
        hard_negative=hard_negative,
        primary_seed=primary_seed,
        fine_tune=fine_tune,
        fine_tune_panel=fine_tune_panel,
        replay_exact=replay_exact,
        dev_real_replay=dev_real_replay,
        hard_negative_done=hard_negative_done,
        primary_seed_done=primary_seed_done,
    )
    if final_summary["final_failure_attribution_complete"]:
        if final_summary["fine_tune_panel_passed"]:
            next_required_gate = "write Stage1 plan from the hard-negative fine-tuned direct actor"
        elif final_summary["fine_tune_panel_executed"]:
            next_required_gate = "keep g556 as supported baseline; direct actor remains not promotable after hard-negative fine-tune"
        elif final_summary["fine_tune_required"] and not final_summary["fine_tune_completed"]:
            next_required_gate = "fine-tune on acquired hard negatives and rerun one frozen-comparison development panel"
        elif final_summary["fine_tune_completed"]:
            next_required_gate = "rerun one frozen-comparison development panel with original and fine-tuned actors"
        else:
            next_required_gate = "no additional G5.61 fine-tune gate from current evidence; keep promotion gates closed pending Stage1 criteria"
    scenario_target_met = bool(
        scenario.get("all_scenario_bank_targets_met")
        or scenario.get("valid_independent_instances_target_met")
    )
    scenario_status = "expanded_component_aware" if scenario_target_met else "underpowered"
    failure_rows = [
        {
            "branch": "g560_replay_truth",
            "status": "failed_materialization_gate",
            "evidence": f"exact_materialization_actor_rows={audit.get('exact_materialization_actor_rows')}/{audit.get('actor_rows')}; fallback_additive_executed={audit.get('materialization_class_counts', {}).get('fallback_additive_executed')}",
        },
        {
            "branch": "canonical_theta_schema",
            "status": "implemented",
            "evidence": "src/gcst/theta_schema.py is the canonical solver-facing schema; label_v4 actor bounds now use solver bounds.",
        },
        {
            "branch": "valid_scenario_bank",
            "status": scenario_status,
            "evidence": (
                f"valid_scenarios={scenario.get('valid_scenarios')} target={scenario.get('valid_independent_instances_target', 2500)}; "
                f"physical_map_hashes={scenario.get('physical_map_hashes')}; "
                f"map_families={scenario.get('map_family_count')}; "
                f"regimes={scenario.get('start_goal_regime_count')}; "
                f"density_bins={scenario.get('density_bin_count')}; "
                f"budget_profiles={scenario.get('budget_profile_count')}"
            ),
        },
        {
            "branch": "materialization_contract",
            "status": "passed" if contract_passed else "blocked",
            "evidence": (
                f"planned={contract.get('planned_contract_vectors')}; executed={contract.get('executed_contract_vectors')}; "
                f"candidate={contract.get('candidate_recognized_rate')}; fingerprint={contract.get('fingerprint_exact_match_rate')}; "
                f"scenario={contract.get('scenario_hash_match_rate')}; identity={contract.get('identity_retention_rate')}"
            ),
        },
        {
            "branch": "goal_aware_representation",
            "status": "smoke_completed",
            "evidence": f"variants={','.join(row.get('variant_id', '') for row in training.get('variants', []))}; causal_sensitivity_passed={training.get('causal_sensitivity_passed')}",
        },
        {
            "branch": "replay_ladder",
            "status": replay_status,
            "evidence": (
                f"corrected={corrected_decision}; architecture={arch_decision}; "
                f"corrected_actor_rows={corrected_replay.get('actor_rows')}; architecture_actor_rows={arch_replay.get('actor_rows')}"
                if replay_executed
                else (
                "materialization contract passed; corrected G5.60 scalar replay and architecture replay ladder are now the next required experiments."
                if contract_passed
                else "architecture/development replay remains closed until materialization contract passes at 1.0."
                )
            ),
        },
        {
            "branch": "development_replay",
            "status": "executed" if dev_real_replay else ("pending_after_replay_ladder" if replay_exact else "blocked"),
            "evidence": (
                f"decision={dev_decision}; contexts={dev_replay.get('development_contexts')}; "
                f"actor_rows={dev_replay.get('actor_rows')}; materialization_invalid_rows={dev_replay.get('materialization_invalid_rows')}; "
                f"success_regressions={dev_replay.get('success_regressions')}"
                if dev_real_replay
                else "development replay has not produced a real executed summary yet"
            ),
        },
        {
            "branch": "hard_negative_acquisition",
            "status": "completed" if hard_negative_done else ("pending_after_development_replay" if dev_real_replay else "blocked"),
            "evidence": (
                f"decision={hard_negative_decision}; acquisition_rows={hard_negative.get('acquisition_rows')}; "
                f"success_regression_rows={hard_negative.get('success_regression_rows')}; "
                f"large_positive_quality_delta_source_rows={hard_negative.get('large_positive_quality_delta_source_rows')}"
                if hard_negative_done
                else "hard-negative acquisition has not produced a completed summary yet"
            ),
        },
        {
            "branch": "primary_seed_training",
            "status": "completed" if primary_seed_done else ("pending_after_development_replay" if dev_real_replay else "blocked"),
            "evidence": (
                f"decision={primary_seed_decision}; variants={','.join(primary_seed.get('variants', []))}; "
                f"seeds={','.join(map(str, primary_seed.get('seeds', [])))}; "
                f"three_training_seeds_complete={primary_seed.get('three_training_seeds_complete')}; "
                f"causal_sensitivity_passed={primary_seed.get('causal_sensitivity_passed')}"
                if primary_seed
                else "primary seed training summary missing"
            ),
        },
        {
            "branch": "hard_negative_finetune_panel",
            "status": (
                "passed_stage1_candidate"
                if final_summary["fine_tune_panel_passed"]
                else "executed_not_promotable"
                if final_summary["fine_tune_panel_executed"]
                else "fine_tune_completed_waiting_for_panel"
                if final_summary["fine_tune_completed"]
                else "pending"
            ),
            "evidence": (
                f"fine_tune_decision={fine_tune.get('decision')}; panel_decision={fine_tune_panel.get('decision')}; "
                f"fine_tuned_success_regressions={fine_tune_panel.get('fine_tuned_success_regressions')}; "
                f"fine_tuned_mean_quality_delta_vs_g556={fine_tune_panel.get('fine_tuned_mean_quality_delta_vs_g556')}"
            ),
        },
    ]
    failure_rows.extend(final_rows)
    write_rows(FAILURE_CSV, failure_rows)
    decision_label = "g561_g560_replay_invalid_materialization_not_actor_failure"
    if final_summary["fine_tune_panel_passed"]:
        decision_label = "g561_goal_aware_actor_dev_replay_passed_plan_stage1"
    elif final_summary["fine_tune_panel_executed"]:
        decision_label = "g561_no_supported_direct_actor_signal_keep_g556"
    elif dev_real_replay and hard_negative_done and (
        final_summary["dev_success_regressions"] > 0 or final_summary["dev_mean_quality_delta_vs_g556"] > 0.0
    ):
        decision_label = "g561_goal_aware_actor_dev_replay_failed_continue_hard_negative_acquisition"
    decision = {
        "schema_version": "phase5p5_repair5g561_decision_summary_v1",
        "decision": decision_label,
        "g560_replay_truth_decision": audit.get("decision"),
        "exact_materialization_actor_rows": audit.get("exact_materialization_actor_rows"),
        "actor_rows": audit.get("actor_rows"),
        "scenario_decision": scenario.get("decision"),
        "valid_scenarios": scenario.get("valid_scenarios"),
        "oracle_decision": oracle.get("decision"),
        "training_decision": training.get("decision"),
        "materialization_contract_decision": contract.get("decision"),
        "materialization_contract_passed": contract_passed,
        "corrected_g560_replay_decision": corrected_decision,
        "architecture_replay_decision": arch_decision,
        "replay_ladder_executed": replay_executed,
        "replay_ladder_exact_materialization": replay_exact,
        "development_replay_decision": dev_decision,
        "development_replay_executed": dev_real_replay,
        "hard_negative_acquisition_decision": hard_negative_decision,
        "hard_negative_acquisition_completed": hard_negative_done,
        "primary_seed_training_decision": primary_seed_decision,
        "primary_seed_training_completed": primary_seed_done,
        "hard_negative_finetune_decision": fine_tune.get("decision", ""),
        "hard_negative_finetune_panel_decision": fine_tune_panel.get("decision", ""),
        "next_required_gate": next_required_gate,
        **final_summary,
        **claims(),
    }
    write_json(DECISION_SUMMARY, decision)
    write_text(
        FAILURE_MD,
        "# Repair5G.5.61 Failure Attribution\n\n"
        + "\n".join(f"- {row['branch']}: `{row['status']}` ({row['evidence']})" for row in failure_rows)
        + "\n",
    )
    write_text(
        DECISION_MD,
        "# Repair5G.5.61 Decision\n\n"
        f"Decision: `{decision['decision']}`\n\n"
        "G5.60 is reclassified as a replay-materialization/identity contamination, not a clean direct-actor failure. "
        "The exact-materialized subset has zero success regressions, while 135 actor rows executed fallback additive settings. "
        f"The valid scenario bank status is `{scenario.get('decision')}` with `{scenario.get('valid_scenarios')}` valid instances. "
        f"The G5.61 materialization contract status is `{contract.get('decision')}` with `{contract.get('executed_contract_vectors')}` executed vectors. "
        f"The replay ladder status is corrected=`{corrected_decision}` and architecture=`{arch_decision}`. "
        f"The development replay status is `{dev_decision}` and hard-negative acquisition is `{hard_negative_decision}`. "
        f"The primary seed training status is `{primary_seed_decision}`. "
        f"The hard-negative fine-tune status is `{fine_tune.get('decision', '')}` and the frozen panel status is `{fine_tune_panel.get('decision', '')}`. "
        f"The final attribution status is `{decision['fine_tune_decision']}` across data, representation, loss, materialization, and solver behavior. "
        f"The next required work is {decision['next_required_gate']}.\n\n"
        "All Phase5.5, Phase6, runtime, learned-policy, and AAAI claims remain closed.\n",
    )
    return decision


def write_manifest() -> None:
    patterns = [
        "src/gcst/theta_schema.py",
        "src/gcst/goal_aware_actor.py",
        "src/gcst/label_v4.py",
        "scripts/audit_repair5g561_replay_truth.py",
        "scripts/generate_repair5g561_valid_scenario_bank.py",
        "scripts/monitor_repair5g561_server.py",
        "scripts/run_repair5g561_materialization_contract.py",
        "scripts/run_repair5g561_development_replay.py",
        "scripts/run_repair5g561_hard_negative_finetune_panel.py",
        "scripts/run_repair5g561_primary_seed_training.py",
        "scripts/run_repair5g561_replay_ladder.py",
        "scripts/train_repair5g561_goal_aware_actor.py",
        "scripts/write_repair5g561_decision.py",
        "tests/test_repair5g561_truth.py",
        "outputs/reports/phase5p5_repair5g561*",
        "outputs/tables/phase5p5_repair5g561*",
        "artifacts/models/gcst/g561_*.pt",
    ]
    files: list[Path] = []
    for pattern in patterns:
        matches = sorted(ROOT.glob(pattern))
        files.extend(path for path in matches if path.is_file())
    unique = []
    seen = set()
    for path in files:
        rel = str(path.relative_to(ROOT)).replace("\\", "/")
        if rel in seen:
            continue
        seen.add(rel)
        unique.append(path)
    checksum_rows = []
    entries = []
    for path in unique:
        sha = file_sha256(path)
        rel = str(path.relative_to(ROOT)).replace("\\", "/")
        checksum_rows.append(f"{sha}  {rel}")
        entries.append({"path": rel, "sha256": sha, "bytes": path.stat().st_size})
    write_text(CHECKSUMS, "\n".join(checksum_rows) + "\n")
    write_json(
        ARTIFACT_MANIFEST,
        {
            "schema_version": "phase5p5_repair5g561_artifact_manifest_v1",
            "artifacts": entries,
            "artifact_count": len(entries),
            **claims(),
        },
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Write G5.61 closeout decision artifacts.")
    parser.parse_args(argv)
    scenario = write_scenario_artifacts()
    oracle = write_oracle_artifacts()
    contract = read_json(CONTRACT_SUMMARY)
    write_blocked_replay_artifacts(contract)
    decision = write_failure_and_decision(scenario, oracle, contract)
    write_manifest()
    print(json.dumps({"decision": decision["decision"], "valid_scenarios": scenario.get("valid_scenarios")}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
