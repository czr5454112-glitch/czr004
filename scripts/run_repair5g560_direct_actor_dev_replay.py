from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from gcst.actor_critic_training import ACTOR_THETA_CSV, load_actor_dataset
from gcst.label_v4 import BASELINE_G556, THETA_NUMERIC_COLUMNS
from gcst.label_v5 import pair_record
from gcst.schemas_v51 import PRIMARY_BASELINE, ROUND
from gcst.stage_state import record_stage

import repair5g549_common as g549
import run_repair5f4_static_updateparams_validation as legacy_scenarios


RESULT_CSV = Path(f"outputs/tables/{ROUND}_direct_actor_dev_replay_results.csv")
RAW_CSV = Path(f"outputs/tables/{ROUND}_direct_actor_dev_replay_results.raw.csv")
PAIR_CSV = Path(f"outputs/tables/{ROUND}_direct_actor_dev_replay_pairs.csv")
PLAN_CSV = Path(f"outputs/tables/{ROUND}_direct_actor_dev_replay_plan.csv")
REGISTRY_CSV = Path(f"outputs/tables/{ROUND}_direct_actor_generated_theta_registry.csv")
SUMMARY_JSON = Path(f"outputs/reports/{ROUND}_direct_actor_dev_replay_summary.json")
SUMMARY_MD = Path(f"outputs/reports/{ROUND}_direct_actor_dev_replay.md")
FAILURE_CSV = Path(f"outputs/tables/{ROUND}_direct_actor_failure_attribution.csv")
FAILURE_MD = Path(f"outputs/reports/{ROUND}_direct_actor_failure_attribution.md")
DECISION_JSON = Path(f"outputs/reports/{ROUND}_decision_summary.json")
DECISION_MD = Path(f"outputs/reports/{ROUND}_decision.md")
LOG_DIR = Path(f"outputs/logs/{ROUND}_direct_actor_dev_replay")


def read_rows(path: Path) -> list[dict[str, str]]:
    p = ROOT / path
    if not p.exists():
        return []
    with p.open(newline="", encoding="utf-8") as f:
        return [dict(row) for row in csv.DictReader(f)]


def write_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    p = ROOT / path
    p.parent.mkdir(parents=True, exist_ok=True)
    fieldnames: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row.keys():
            if key not in seen:
                seen.add(key)
                fieldnames.append(key)
    with p.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, data: dict[str, Any]) -> None:
    p = ROOT / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def solver_binary(arg: Path) -> Path:
    for candidate in [arg, Path("build/phase1a-batch/phase1a_batch"), Path("build/phase1-ltm/phase1a_batch"), Path("build/phase1a-batch/phase1a_batch.exe")]:
        p = ROOT / candidate
        if p.exists():
            return p
    return ROOT / arg


def mode_columns() -> dict[str, int]:
    return {
        "theta_goal_projection_mode_flow_shield": 1,
        "theta_goal_projection_mode_agent_progress": 0,
        "theta_goal_projection_mode_none": 0,
    }


def context_seed(row: dict[str, str]) -> str:
    for key in ["legacy_solver_seed", "seed", "solver_seed", "legacy_evaluation_uid"]:
        value = str(row.get(key, "")).strip()
        if value:
            return value
    legacy = str(row.get("legacy_context_key", ""))
    parts = legacy.split("|")
    if len(parts) >= 3 and parts[2].strip():
        return parts[2].strip()
    return ""


def select_theta_rows(limit: int, method: str | None) -> list[dict[str, str]]:
    rows = read_rows(ACTOR_THETA_CSV)
    if method:
        rows = [row for row in rows if row.get("method") == method]
    else:
        preferred = [row for row in rows if row.get("method") == "G1_direct_actor_aux_critic"]
        rows = preferred or rows
    rows = [row for row in rows if row.get("split") in {"heldout", "validation"}]
    seen: set[str] = set()
    out = []
    for row in rows:
        key = row.get("g560_evaluation_uid", "")
        if key in seen:
            continue
        seen.add(key)
        out.append(row)
        if limit and len(out) >= limit:
            break
    return out


def build_plan_and_registry(limit: int, method: str | None) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    dataset = load_actor_dataset(ROOT)
    group_by_eval = {group.key: group for group in dataset.groups}
    theta_rows = select_theta_rows(limit, method)
    plan_rows: list[dict[str, Any]] = []
    registry_rows: list[dict[str, Any]] = []
    baseline = {
        "candidate_id": PRIMARY_BASELINE,
        "generated_theta_uid": "",
        "registry_role": "g556_baseline",
        **{col: float(value) for col, value in zip(THETA_NUMERIC_COLUMNS, BASELINE_G556)},
        **mode_columns(),
    }
    registry_rows.append(baseline)
    for idx, theta_row in enumerate(theta_rows):
        group = group_by_eval.get(theta_row.get("g560_evaluation_uid", ""))
        if not group:
            continue
        uid = theta_row.get("generated_theta_uid", "")
        registry_rows.append(
            {
                "candidate_id": uid,
                "generated_theta_uid": uid,
                "registry_role": "direct_actor_generated_theta_solver_key",
                **{col: theta_row.get(col, "") for col in THETA_NUMERIC_COLUMNS},
                **mode_columns(),
            }
        )
        first = group.feature_row
        context = {
            "context_id": first.get("context_id", group.key),
            "map": first.get("map", ""),
            "map_family": first.get("map_family", ""),
            "agents": first.get("agent_count", first.get("agents", "")),
            "agent_count": first.get("agent_count", first.get("agents", "")),
            "seed": context_seed(first),
            "budget_ms": first.get("nominal_budget_ms", first.get("budget_ms", "")),
            "nominal_budget_ms": first.get("nominal_budget_ms", first.get("budget_ms", "")),
            "horizon_id": first.get("horizon_id", ""),
            "short_budget_ms": first.get("nominal_budget_ms", first.get("budget_ms", "")),
            "base_time_limit_sec": first.get("base_time_limit_sec", "0.5"),
            "ltm_max_iterations": first.get("ltm_max_iterations", "2"),
            "split": group.split,
            "g560_evaluation_uid": group.key,
            "g560_instance_uid": group.instance_uid,
            "g560_physical_map_sha256": group.physical_hash,
        }
        plan_rows.append(
            {
                "plan_row_id": f"g560_direct_replay_{idx:06d}_baseline",
                **context,
                "role": PRIMARY_BASELINE,
                "candidate_id": PRIMARY_BASELINE,
                "theta_id": PRIMARY_BASELINE,
                "materialized_method": PRIMARY_BASELINE,
                "generated_theta_uid": "",
                "sampling_policy": "baseline_control",
                **mode_columns(),
            }
        )
        plan_rows.append(
            {
                "plan_row_id": f"g560_direct_replay_{idx:06d}_actor",
                **context,
                "role": "direct_actor_generated_theta",
                "candidate_id": uid,
                "theta_id": uid,
                "materialized_method": uid,
                "generated_theta_uid": uid,
                "sampling_policy": "direct_actor_single_forward",
                **{col: theta_row.get(col, "") for col in THETA_NUMERIC_COLUMNS},
                **mode_columns(),
            }
        )
    write_rows(PLAN_CSV, plan_rows)
    write_rows(REGISTRY_CSV, registry_rows)
    return plan_rows, registry_rows


def register_g559_maps_for_legacy_prepare(plan_rows: list[dict[str, Any]]) -> None:
    remote_root = Path(os.environ.get("REMOTE_ARTIFACT_ROOT", "/root/shared-nvme/czr004_g559_remote_artifacts"))
    for map_name in sorted({str(row.get("map", "")) for row in plan_rows if row.get("map")}):
        map_path = remote_root / "contexts" / "maps" / f"{map_name}.map"
        if map_path.exists():
            legacy_scenarios.MAPS[map_name] = map_path


def analyze_pairs(result_rows: list[dict[str, str]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    by_group: dict[tuple[str, str, str, str, str], dict[str, dict[str, str]]] = defaultdict(dict)
    for row in result_rows:
        key = (
            str(row.get("map", "")),
            str(row.get("agents", "")),
            str(row.get("seed", "")),
            str(row.get("budget_ms", "")),
            str(row.get("horizon_id", "")),
        )
        by_group[key][str(row.get("materialized_method", row.get("candidate_id", "")))] = row
    pairs = []
    for key, methods in by_group.items():
        baseline = methods.get(PRIMARY_BASELINE)
        if not baseline:
            continue
        for method, row in methods.items():
            if method == PRIMARY_BASELINE:
                continue
            pair = pair_record(row, baseline)
            pair.update(
                {
                    "map": key[0],
                    "agents": key[1],
                    "seed": key[2],
                    "budget_ms": key[3],
                    "horizon_id": key[4],
                    "generated_theta_uid": row.get("generated_theta_uid", method),
                    "materialized_method": method,
                    "phase5p5_allowed": "False",
                    "phase6_allowed": "False",
                    "runtime_claim_allowed": "False",
                    "learned_runtime_policy_validated": "False",
                    "aaai_ready": "False",
                }
            )
            pairs.append(pair)
    finite_delta = []
    for pair in pairs:
        try:
            value = float(pair.get("quality_delta_vs_g556", "nan"))
        except Exception:
            value = math.nan
        if math.isfinite(value):
            finite_delta.append(value)
    summary = {
        "round": ROUND,
        "replay_pairs": len(pairs),
        "success_regressions": sum(str(p.get("success_regression")).lower() == "true" for p in pairs),
        "success_gains": sum(str(p.get("success_gain")).lower() == "true" for p in pairs),
        "both_success": sum(str(p.get("both_success")).lower() == "true" for p in pairs),
        "both_fail": sum(str(p.get("both_fail")).lower() == "true" for p in pairs),
        "mean_quality_delta_vs_g556": float(sum(finite_delta) / len(finite_delta)) if finite_delta else None,
        "better_count": sum(value < 0.0 for value in finite_delta),
        "worse_count": sum(value > 0.0 for value in finite_delta),
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "runtime_claim_allowed": False,
        "learned_runtime_policy_validated": False,
        "aaai_ready": False,
    }
    return pairs, summary


def write_failure_and_decision(summary: dict[str, Any]) -> None:
    passed = (
        int(summary.get("success_regressions", 0)) == 0
        and (summary.get("mean_quality_delta_vs_g556") is not None)
        and float(summary.get("mean_quality_delta_vs_g556")) < 0.0
        and int(summary.get("better_count", 0)) > int(summary.get("worse_count", 0))
    )
    failure_rows = [
        {
            "branch": "scenario_validity",
            "status": "open",
            "evidence": "G5.59 scenario validation retained only 1203/2000 valid contexts; invalid rows were filtered before actor training.",
        },
        {
            "branch": "direct_actor_dev_replay",
            "status": "failed" if not passed else "passed",
            "evidence": f"success_regressions={summary.get('success_regressions')}; success_gains={summary.get('success_gains')}; mean_delta={summary.get('mean_quality_delta_vs_g556')}; better={summary.get('better_count')}; worse={summary.get('worse_count')}",
        },
        {
            "branch": "auxiliary_critic_refinement",
            "status": "open",
            "evidence": "G1 actor did not improve offline nearest-safe distance over G0; critic remains training-only and is not exported.",
        },
        {
            "branch": "selector_control_boundary",
            "status": "closed",
            "evidence": "Actor export excludes critic, theta registry, selector table, and retrieval memory; selector cannot satisfy the main-method gate.",
        },
    ]
    write_rows(FAILURE_CSV, failure_rows)
    decision = {
        "round": ROUND,
        "decision": "g560_direct_actor_dev_replay_failed_keep_g556_and_repair_instances",
        "direct_actor_dev_replay_passed": passed,
        "success_regressions": summary.get("success_regressions"),
        "success_gains": summary.get("success_gains"),
        "mean_quality_delta_vs_g556": summary.get("mean_quality_delta_vs_g556"),
        "better_count": summary.get("better_count"),
        "worse_count": summary.get("worse_count"),
        "primary_method": "Direct Continuous GCST Actor",
        "baseline_kept": PRIMARY_BASELINE,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "runtime_claim_allowed": False,
        "learned_runtime_policy_validated": False,
        "aaai_ready": False,
    }
    write_json(DECISION_JSON, decision)
    md = [
        "# Repair5G.5.60 Decision",
        "",
        f"Decision: `{decision['decision']}`",
        "",
        "The addendum primary method is the Direct Continuous GCST Actor, not a selector. It failed the generated-theta development replay and must not be promoted.",
        "",
        f"- Replay pairs: {summary.get('replay_pairs')}",
        f"- Success regressions: {summary.get('success_regressions')}",
        f"- Success gains: {summary.get('success_gains')}",
        f"- Mean quality delta vs g556: {summary.get('mean_quality_delta_vs_g556')}",
        f"- Better / worse: {summary.get('better_count')} / {summary.get('worse_count')}",
        "",
        "All promotion and runtime claims remain closed.",
    ]
    (ROOT / DECISION_MD).parent.mkdir(parents=True, exist_ok=True)
    (ROOT / DECISION_MD).write_text("\n".join(md) + "\n", encoding="utf-8")
    fmd = ["# Repair5G.5.60 Direct Actor Failure Attribution", ""]
    fmd.extend(f"- {row['branch']}: {row['status']} ({row['evidence']})" for row in failure_rows)
    (ROOT / FAILURE_MD).parent.mkdir(parents=True, exist_ok=True)
    (ROOT / FAILURE_MD).write_text("\n".join(fmd) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run G5.60 direct actor generated-theta development replay.")
    parser.add_argument("--limit", type=int, default=300)
    parser.add_argument("--method", default=None)
    parser.add_argument("--row-limit", type=int, default=0)
    parser.add_argument("--max-workers", type=int, default=6)
    parser.add_argument("--binary", type=Path, default=Path("build/phase1a-batch/phase1a_batch"))
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    plan_rows, registry_rows = build_plan_and_registry(args.limit, args.method)
    register_g559_maps_for_legacy_prepare(plan_rows)
    binary = solver_binary(args.binary)
    result_csv = str(ROOT / RESULT_CSV)
    raw_csv = str(ROOT / RAW_CSV)
    if not binary.exists():
        summary = {"round": ROUND, "decision": "direct_actor_dev_replay_failed_missing_solver_binary", "binary": str(binary), "planned_rows": len(plan_rows)}
        write_json(SUMMARY_JSON, summary)
        print(summary)
        return
    os.environ.setdefault("REPAIR5G_STREAM_RESULT_CSV", "1")
    os.environ.setdefault("REPAIR5G_SKIP_AGGREGATE_JSONL", "1")
    g549.run_probe_plan(
        plan_rows,
        binary=binary,
        overwrite=args.overwrite,
        row_limit=args.row_limit,
        max_workers=args.max_workers,
        registry_path=str(ROOT / REGISTRY_CSV),
        result_csv=result_csv,
        raw_csv=raw_csv,
        log_dir=str(ROOT / LOG_DIR),
        run_jsonl=str(ROOT / LOG_DIR / "runs.jsonl"),
        command_jsonl=str(ROOT / LOG_DIR / "commands.jsonl"),
        update_jsonl=str(ROOT / LOG_DIR / "updates.jsonl"),
        probe_jsonl=str(ROOT / LOG_DIR / "counterfactual_probes.jsonl"),
        checkpoint_jsonl=str(ROOT / LOG_DIR / "checkpoints.jsonl"),
        status_json=str(ROOT / LOG_DIR / "status.json"),
        scenario_dir=str(Path(os.environ.get("REMOTE_ARTIFACT_ROOT", "/root/shared-nvme/czr004_g559_remote_artifacts")) / "contexts" / "scenarios"),
        scenario_metadata=str(Path(os.environ.get("REMOTE_ARTIFACT_ROOT", "/root/shared-nvme/czr004_g559_remote_artifacts")) / "contexts" / "scenario_metadata.json"),
        manifest_prefix="g560_direct_actor_dev_replay",
        row_prefix="g560_direct_actor",
        execution_mode="g560_direct_actor_generated_theta_real_solver_row",
    )
    result_rows = read_rows(RESULT_CSV)
    pairs, summary = analyze_pairs(result_rows)
    summary.update(
        {
            "decision": "g560_direct_actor_dev_replay_completed",
            "planned_contexts": len(plan_rows) // 2,
            "planned_solver_rows": len(plan_rows),
            "registry_rows": len(registry_rows),
            "real_solver_rows": len(result_rows),
            "result_csv": str(ROOT / RESULT_CSV),
            "pair_csv": str(ROOT / PAIR_CSV),
        }
    )
    write_rows(PAIR_CSV, pairs)
    write_json(SUMMARY_JSON, summary)
    write_failure_and_decision(summary)
    md = [
        "# Repair5G.5.60 Direct Actor Development Replay",
        "",
        f"- Planned contexts: {summary['planned_contexts']}",
        f"- Real solver rows: {summary['real_solver_rows']}",
        f"- Replay pairs: {summary['replay_pairs']}",
        f"- Success regressions: {summary['success_regressions']}",
        f"- Success gains: {summary['success_gains']}",
        f"- Mean quality delta vs g556: {summary['mean_quality_delta_vs_g556']}",
        "",
        "Actor-generated rows use `generated_theta_uid` as the solver materialization key; the exported actor bundle does not contain the registry.",
    ]
    (ROOT / SUMMARY_MD).parent.mkdir(parents=True, exist_ok=True)
    (ROOT / SUMMARY_MD).write_text("\n".join(md) + "\n", encoding="utf-8")
    record_stage(
        "direct_actor_generated_theta_dev_replay",
        "completed",
        bool(pairs),
        "python scripts/run_repair5g560_direct_actor_dev_replay.py",
        [str(RESULT_CSV), str(PAIR_CSV), str(SUMMARY_JSON), str(SUMMARY_MD)],
        summary,
        ROOT,
    )
    print(summary)


if __name__ == "__main__":
    main()
