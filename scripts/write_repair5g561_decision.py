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
DEV_REPLAY = Path(f"outputs/tables/{ROUND}_dev_replay_by_stratum.csv")
DEV_REPLAY_SUMMARY = Path(f"outputs/reports/{ROUND}_dev_replay_summary.json")
HARD_NEGATIVE = Path(f"outputs/tables/{ROUND}_hard_negative_acquisition.csv")
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


def write_failure_and_decision(scenario: dict[str, Any], oracle: dict[str, Any], contract: dict[str, Any]) -> dict[str, Any]:
    audit = read_json(f"outputs/reports/{ROUND}_g560_replay_truth_audit_summary.json")
    training = read_json(f"outputs/reports/{ROUND}_training_summary.json")
    contract_passed = bool(contract.get("materialization_contract_passed"))
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
            "status": "pending_after_contract" if contract_passed else "blocked",
            "evidence": (
                "materialization contract passed; corrected G5.60 scalar replay and architecture replay ladder are now the next required experiments."
                if contract_passed
                else "architecture/development replay remains closed until materialization contract passes at 1.0."
            ),
        },
    ]
    write_rows(FAILURE_CSV, failure_rows)
    decision = {
        "schema_version": "phase5p5_repair5g561_decision_summary_v1",
        "decision": "g561_g560_replay_invalid_materialization_not_actor_failure",
        "g560_replay_truth_decision": audit.get("decision"),
        "exact_materialization_actor_rows": audit.get("exact_materialization_actor_rows"),
        "actor_rows": audit.get("actor_rows"),
        "scenario_decision": scenario.get("decision"),
        "valid_scenarios": scenario.get("valid_scenarios"),
        "oracle_decision": oracle.get("decision"),
        "training_decision": training.get("decision"),
        "materialization_contract_decision": contract.get("decision"),
        "materialization_contract_passed": contract_passed,
        "next_required_gate": (
            "run corrected G5.60 scalar replay and G5.61 architecture replay ladder with exact-materialization rows only"
            if contract_passed
            else "run G5.61 materialization contract on server and require candidate_recognized/fingerprint/identity/scenario rates all equal 1.0"
        ),
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
        "The next required work is corrected scalar replay and architecture replay using exact-materialization rows only.\n\n"
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
