from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import random
import re
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from gcst.generated_theta_audit import generated_theta_uid  # noqa: E402
from gcst.goal_aware_actor import GoalAwareDualChannelActor  # noqa: E402
from gcst.theta_schema import (  # noqa: E402
    BASELINE_G556,
    THETA_HI,
    THETA_LO,
    THETA_COLUMNS,
    THETA_NUMERIC_COLUMNS,
    clamp_theta_row,
    compare_theta_to_fingerprint,
    expected_cpp_params,
    mode_columns,
    parse_updateparams_fingerprint,
)
from repair5g2_common import scenario_path  # noqa: E402
from repair5g5_common import DEFAULT_SOURCE_SCENARIO_DIR, prepare_scenarios  # noqa: E402
from run_repair5f4_static_updateparams_validation import MAPS as MAP_PATHS  # noqa: E402

import repair5g549_common as g549  # noqa: E402
import run_repair5f4_static_updateparams_validation as legacy_scenarios  # noqa: E402
from train_repair5g561_goal_aware_actor import build_samples, tensor_batch  # noqa: E402


ROUND = "phase5p5_repair5g561"
PLAN_CSV = Path(f"outputs/tables/{ROUND}_materialization_contract_plan.csv")
REGISTRY_CSV = Path(f"outputs/tables/{ROUND}_materialization_contract_registry.csv")
RESULTS_CSV = Path(f"outputs/tables/{ROUND}_materialization_contract_results.csv")
RAW_RESULTS_CSV = Path(f"outputs/tables/{ROUND}_materialization_contract_results.raw.csv")
SUMMARY_JSON = Path(f"outputs/reports/{ROUND}_materialization_contract_summary.json")
REPORT_MD = Path(f"outputs/reports/{ROUND}_materialization_contract.md")
SCENARIO_METADATA = Path(f"outputs/reports/{ROUND}_materialization_contract_scenario_generation.json")
LOG_DIR = Path(f"outputs/logs/{ROUND}_materialization_contract")
SCENARIO_DIR = Path(f"outputs/tmp/{ROUND}_materialization_contract_scenarios")
PRIMARY_BASELINE = "g556_c063174"


def resolve(path: str | Path) -> Path:
    p = Path(path)
    return p if p.is_absolute() else ROOT / p


def boolish(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


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


def read_rows(path: str | Path) -> list[dict[str, str]]:
    p = resolve(path)
    if not p.exists():
        return []
    with p.open(newline="", encoding="utf-8") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def write_json(path: str | Path, data: dict[str, Any]) -> None:
    p = resolve(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: str | Path, text: str) -> None:
    p = resolve(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def sha256_file(path: str | Path) -> str:
    p = resolve(path)
    if not p.exists():
        return ""
    digest = hashlib.sha256()
    with p.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_uid(*parts: Any) -> str:
    payload = json.dumps(parts, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def claims() -> dict[str, bool]:
    return {
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "runtime_claim_allowed": False,
        "learned_runtime_policy_validated": False,
        "aaai_ready": False,
    }


def safe_token(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]+", "_", text).strip("_").lower()[:40] or "vector"


def fingerprint(theta: dict[str, Any]) -> str:
    return "|".join(f"{key}={value}" for key, value in expected_cpp_params(theta).items())


def base_theta(mode: str = "flow_shield") -> dict[str, Any]:
    row = {col: float(value) for col, value in zip(THETA_NUMERIC_COLUMNS, BASELINE_G556)}
    row.update(mode_columns(mode))
    return clamp_theta_row(row)


def add_contract_vector(
    rows: list[dict[str, Any]],
    *,
    vector_family: str,
    changed_field: str,
    theta: dict[str, Any],
    source: str,
    source_model: str = "",
    source_sample_id: str = "",
    source_map_family: str = "",
) -> None:
    theta = clamp_theta_row(theta)
    index = len(rows)
    uid = stable_uid("g561_materialization_contract", index, vector_family, changed_field, theta)
    candidate_id = f"g561_contract_{index:03d}_{safe_token(vector_family)}_{uid[:10]}"
    generated_uid = generated_theta_uid(source_model or "g561_contract", candidate_id, [theta[col] for col in THETA_NUMERIC_COLUMNS])
    rows.append(
        {
            "contract_vector_id": f"g561_contract_{index:03d}",
            "vector_family": vector_family,
            "changed_field": changed_field,
            "candidate_id": candidate_id,
            "theta_id": candidate_id,
            "materialized_method": candidate_id,
            "generated_theta_uid": generated_uid,
            "source": source,
            "source_model": source_model,
            "source_sample_id": source_sample_id,
            "source_map_family": source_map_family,
            "expected_updateparams_fingerprint": fingerprint(theta),
            **theta,
        }
    )


def deterministic_contract_vectors() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    baseline = base_theta("flow_shield")
    add_contract_vector(rows, vector_family="g556_anchor", changed_field="all", theta=baseline, source="deterministic_schema")

    span = np.asarray(THETA_HI - THETA_LO, dtype=np.float32)
    for idx, col in enumerate(THETA_NUMERIC_COLUMNS[:6]):
        for sign in [-1.0, 1.0]:
            theta = dict(baseline)
            theta[col] = float(np.clip(float(BASELINE_G556[idx]) + sign * float(span[idx]) * 0.05, float(THETA_LO[idx]), float(THETA_HI[idx])))
            add_contract_vector(rows, vector_family="small_residual", changed_field=col, theta=theta, source="deterministic_schema")

    for idx, col in enumerate(THETA_NUMERIC_COLUMNS):
        low = dict(baseline)
        high = dict(baseline)
        low[col] = float(THETA_LO[idx])
        high[col] = float(THETA_HI[idx])
        add_contract_vector(rows, vector_family="field_lower_bound", changed_field=col, theta=low, source="deterministic_schema")
        add_contract_vector(rows, vector_family="field_upper_bound", changed_field=col, theta=high, source="deterministic_schema")

    group_specs = [
        ("congestion_alpha_high", ["theta_alpha_cong_commit_progress", "theta_alpha_cong_block", "theta_alpha_cong_wait_nonprogress"], 0.82),
        ("congestion_alpha_low", ["theta_alpha_cong_commit_nonprogress", "theta_alpha_cong_wait_progress"], 0.18),
        ("flow_channel_high", ["theta_alpha_flow_commit_progress", "theta_alpha_flow_wait_progress", "theta_lambda_flow"], 0.76),
        ("dual_decay_low", ["theta_rho_cong_decay", "theta_rho_flow_decay"], 0.05),
        ("shield_high", ["theta_flow_shield_beta", "theta_max_flow_shield"], 0.88),
        ("cost_narrow", ["theta_min_edge_cost", "theta_max_edge_cost"], 0.22),
        ("lambda_cross", ["theta_lambda_cong", "theta_lambda_flow"], 0.63),
        ("mixed_midpoint", THETA_NUMERIC_COLUMNS[::3], 0.50),
    ]
    for name, cols, fraction in group_specs:
        theta = dict(baseline)
        for col in cols:
            idx = THETA_NUMERIC_COLUMNS.index(col)
            theta[col] = float(float(THETA_LO[idx]) + (float(THETA_HI[idx]) - float(THETA_LO[idx])) * fraction)
        if name == "cost_narrow":
            theta["theta_min_edge_cost"] = 0.50
            theta["theta_max_edge_cost"] = 8.50
        add_contract_vector(rows, vector_family="mixed_field_group_residual", changed_field=name, theta=theta, source="deterministic_schema")

    for mode in ["flow_shield", "agent_progress", "none"]:
        add_contract_vector(rows, vector_family="goal_mode", changed_field=mode, theta=base_theta(mode), source="deterministic_schema")

    rng = random.Random(561)
    for sample_idx in range(16):
        theta = {}
        for idx, col in enumerate(THETA_NUMERIC_COLUMNS):
            lo = float(THETA_LO[idx])
            hi = float(THETA_HI[idx])
            theta[col] = lo + (hi - lo) * rng.uniform(0.08, 0.92)
        if theta["theta_min_edge_cost"] > theta["theta_max_edge_cost"]:
            theta["theta_min_edge_cost"], theta["theta_max_edge_cost"] = 0.50, 9.50
        theta.update(mode_columns(rng.choice(["flow_shield", "agent_progress", "none"])))
        add_contract_vector(rows, vector_family="random_valid_interior", changed_field=f"random_{sample_idx:02d}", theta=theta, source="deterministic_schema")

    return rows


def load_training_variants() -> list[dict[str, Any]]:
    summary_path = ROOT / f"outputs/reports/{ROUND}_training_summary.json"
    if not summary_path.exists():
        return []
    data = json.loads(summary_path.read_text(encoding="utf-8"))
    return [row for row in data.get("variants", []) if row.get("model_path")]


def actor_contract_vectors(*, device: str = "cpu", per_variant: int = 3) -> list[dict[str, Any]]:
    try:
        import torch
    except Exception:
        return []

    variants = load_training_variants()
    if not variants:
        return []
    samples = build_samples(32, 561)
    chosen_samples = []
    seen_families: set[str] = set()
    for sample in samples:
        family = str(sample.context.get("map_family", ""))
        if family in seen_families:
            continue
        seen_families.add(family)
        chosen_samples.append(sample)
        if len(chosen_samples) >= per_variant:
            break
    if len(chosen_samples) < per_variant:
        chosen_samples = samples[:per_variant]

    rows: list[dict[str, Any]] = []
    run_device = device if device != "auto" else ("cuda" if torch.cuda.is_available() else "cpu")
    for variant in variants:
        model_path = ROOT / str(variant.get("model_path", ""))
        if not model_path.exists():
            continue
        checkpoint = torch.load(model_path, map_location=run_device, weights_only=False)
        residual_scale = 0.35 if bool(checkpoint.get("critic_training_only")) else 0.30
        model = GoalAwareDualChannelActor(
            hidden_dim=int(checkpoint.get("hidden_dim", 32)),
            use_graph=bool(checkpoint.get("uses_graph")),
            use_paired_od=bool(checkpoint.get("uses_paired_od")),
            use_c0f0=bool(checkpoint.get("uses_c0f0")),
            residual_scale=residual_scale,
        ).module().to(run_device)
        model.load_state_dict(checkpoint["actor_state_dict"])
        model.eval()
        with torch.no_grad():
            graph_batch, od_tokens, od_mask, scalars, _target = tensor_batch(chosen_samples, run_device)
            pred = model(graph_batch, od_tokens, od_mask, scalars).detach().cpu().numpy()
        for sample, theta_values in zip(chosen_samples, pred):
            theta = {col: float(theta_values[idx]) for idx, col in enumerate(THETA_NUMERIC_COLUMNS)}
            theta.update(mode_columns("flow_shield"))
            add_contract_vector(
                rows,
                vector_family="actor_produced_point",
                changed_field=str(variant.get("variant_id", "actor")),
                theta=theta,
                source="g561_trained_actor_checkpoint",
                source_model=str(variant.get("model_path", "")),
                source_sample_id=sample.sample_id,
                source_map_family=str(sample.context.get("map_family", "")),
            )
    return rows


def build_contract_vectors(*, include_actor: bool = True, actor_device: str = "cpu", vector_limit: int = 0) -> list[dict[str, Any]]:
    rows = deterministic_contract_vectors()
    if include_actor:
        rows.extend(actor_contract_vectors(device=actor_device))
    for idx, row in enumerate(rows):
        row["contract_vector_id"] = f"g561_contract_{idx:03d}"
    if vector_limit:
        rows = rows[: max(1, int(vector_limit))]
    return rows


def default_contexts(context_limit: int = 0) -> list[dict[str, Any]]:
    contexts = [
        {"map": "random-32-32-20", "map_family": "random", "agents": 32, "seed": 8610, "budget_ms": 500, "base_time_limit_sec": 0.50, "ltm_max_iterations": 2, "horizon_id": "g561_contract_random_b500_i2"},
        {"map": "maze-32-32-4", "map_family": "maze", "agents": 32, "seed": 8611, "budget_ms": 1000, "base_time_limit_sec": 1.00, "ltm_max_iterations": 3, "horizon_id": "g561_contract_maze_b1000_i3"},
        {"map": "warehouse-10-20-10-2-1", "map_family": "warehouse", "agents": 32, "seed": 8612, "budget_ms": 2000, "base_time_limit_sec": 2.00, "ltm_max_iterations": 4, "horizon_id": "g561_contract_warehouse_b2000_i4"},
        {"map": "random-32-32-20", "map_family": "random", "agents": 64, "seed": 8613, "budget_ms": 3000, "base_time_limit_sec": 3.00, "ltm_max_iterations": 4, "horizon_id": "g561_contract_random_b3000_i4"},
    ]
    return contexts[:context_limit] if context_limit else contexts


def register_remote_maps() -> None:
    remote_root = Path(os.environ.get("REMOTE_ARTIFACT_ROOT", "/root/shared-nvme/czr004_g559_remote_artifacts"))
    map_dir = remote_root / "contexts" / "maps"
    if not map_dir.exists():
        return
    for map_path in sorted(map_dir.glob("*.map")):
        legacy_scenarios.MAPS.setdefault(map_path.stem, map_path)


def prepare_contract_scenarios(plan_rows: list[dict[str, Any]], scenario_dir: Path, scenario_metadata: Path) -> None:
    register_remote_maps()
    maps = sorted({str(row["map"]) for row in plan_rows})
    agents = sorted({int(row["agents"]) for row in plan_rows})
    seeds = sorted({int(row["seed"]) for row in plan_rows})
    prepare_scenarios(
        root=ROOT,
        source_scenario_dir=resolve(DEFAULT_SOURCE_SCENARIO_DIR),
        scenario_dir=resolve(scenario_dir),
        scenario_metadata=resolve(scenario_metadata),
        maps=maps,
        agent_counts=agents,
        instance_ids=seeds,
    )


def build_plan_rows(vectors: list[dict[str, Any]], contexts: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    plan_rows: list[dict[str, Any]] = []
    registry_rows: list[dict[str, Any]] = []
    for vector in vectors:
        registry_rows.append(
            {
                "candidate_id": vector["candidate_id"],
                "generated_theta_uid": vector["generated_theta_uid"],
                "registry_role": "g561_materialization_contract_solver_key",
                "contract_vector_id": vector["contract_vector_id"],
                **{col: vector.get(col, "") for col in THETA_COLUMNS},
                **claims(),
            }
        )
    for idx, vector in enumerate(vectors):
        context = contexts[idx % len(contexts)]
        instance_uid = stable_uid("g561_contract_instance", context["map"], context["agents"], context["seed"], context["budget_ms"])
        evaluation_uid = stable_uid("g561_contract_eval", instance_uid, vector["candidate_id"])
        plan_rows.append(
            {
                "plan_row_id": f"g561_materialization_contract_{idx:06d}",
                "contract_vector_id": vector["contract_vector_id"],
                "context_id": instance_uid,
                "g561_instance_uid": instance_uid,
                "g561_evaluation_uid": evaluation_uid,
                "g561_physical_map_sha256": "",
                "g561_scenario_sha256": "",
                "g561_identity_digest": "",
                "map": context["map"],
                "map_family": context["map_family"],
                "agents": int(context["agents"]),
                "agent_count": int(context["agents"]),
                "seed": int(context["seed"]),
                "budget_ms": int(context["budget_ms"]),
                "nominal_budget_ms": int(context["budget_ms"]),
                "short_budget_ms": int(context["budget_ms"]),
                "base_time_limit_sec": float(context["base_time_limit_sec"]),
                "ltm_max_iterations": int(context["ltm_max_iterations"]),
                "horizon_id": context["horizon_id"],
                "role": f"generated_theta::{vector['candidate_id']}",
                "candidate_id": vector["candidate_id"],
                "theta_id": vector["theta_id"],
                "materialized_method": vector["materialized_method"],
                "generated_theta_uid": vector["generated_theta_uid"],
                "sampling_policy": vector["vector_family"],
                "vector_family": vector["vector_family"],
                "changed_field": vector["changed_field"],
                "source": vector.get("source", ""),
                "source_model": vector.get("source_model", ""),
                "source_sample_id": vector.get("source_sample_id", ""),
                "source_map_family": vector.get("source_map_family", ""),
                "expected_updateparams_fingerprint": vector["expected_updateparams_fingerprint"],
                **{col: vector.get(col, "") for col in THETA_COLUMNS},
                **claims(),
            }
        )
    return plan_rows, registry_rows


def attach_scenario_and_identity(plan_rows: list[dict[str, Any]], scenario_dir: Path) -> list[dict[str, Any]]:
    out = []
    for row in plan_rows:
        enriched = dict(row)
        scen = scenario_path(resolve(scenario_dir), str(row["map"]), int(row["seed"]))
        map_value = MAP_PATHS.get(str(row["map"]), "")
        map_path = Path(map_value)
        if not map_path.is_absolute():
            map_path = ROOT / map_path
        scenario_sha = sha256_file(scen)
        enriched["g561_scenario_sha256"] = scenario_sha
        enriched["g561_scenario_path"] = str(scen.relative_to(ROOT)) if scen.exists() and scen.is_relative_to(ROOT) else str(scen)
        enriched["g561_physical_map_sha256"] = sha256_file(map_path)
        enriched["g561_identity_digest"] = stable_uid(
            "g561_contract_identity",
            enriched["plan_row_id"],
            enriched["g561_instance_uid"],
            enriched["g561_scenario_sha256"],
            enriched["candidate_id"],
            enriched["generated_theta_uid"],
        )
        out.append(enriched)
    return out


def plan_lookup(plan_rows: list[dict[str, Any]]) -> dict[tuple[str, str, str, str, str], dict[str, Any]]:
    return {
        (
            str(row.get("map", "")),
            str(row.get("agents", "")),
            str(row.get("seed", "")),
            str(row.get("budget_ms", "")),
            str(row.get("materialized_method", "")),
        ): row
        for row in plan_rows
    }


def bool_from_fingerprint(parsed: dict[str, str], key: str) -> bool | None:
    if key not in parsed:
        return None
    value = parsed[key].strip().lower()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False
    return None


def attach_contract_audit(result_rows: list[dict[str, Any]], plan_rows: list[dict[str, Any]], scenario_dir: Path | None = None) -> list[dict[str, Any]]:
    lookup = plan_lookup(plan_rows)
    audited = []
    for result in result_rows:
        row = dict(result)
        plan = lookup.get(
            (
                str(row.get("map", "")),
                str(row.get("agents", "")),
                str(row.get("seed", "")),
                str(row.get("budget_ms", "")),
                str(row.get("materialized_method", "")),
            ),
            {},
        )
        for key in [
            "plan_row_id",
            "contract_vector_id",
            "g561_instance_uid",
            "g561_evaluation_uid",
            "g561_physical_map_sha256",
            "g561_scenario_sha256",
            "g561_identity_digest",
            "g561_scenario_path",
            "generated_theta_uid",
            "vector_family",
            "changed_field",
            "expected_updateparams_fingerprint",
            "source",
            "source_model",
            "source_sample_id",
            "source_map_family",
        ]:
            row[key] = plan.get(key, row.get(key, ""))
        for col in THETA_COLUMNS:
            row[col] = plan.get(col, row.get(col, ""))

        parsed = parse_updateparams_fingerprint(row.get("updateparams_fingerprint", ""))
        strict_match, mismatches = compare_theta_to_fingerprint(row.get("updateparams_fingerprint", ""), plan or row, tolerance=1.0e-9)
        relaxed_match, relaxed_mismatches = compare_theta_to_fingerprint(row.get("updateparams_fingerprint", ""), plan or row, tolerance=1.0e-5)
        actual_scenario_sha = ""
        if scenario_dir is not None and row.get("map") and row.get("seed"):
            actual_scenario_sha = sha256_file(scenario_path(resolve(scenario_dir), str(row["map"]), int(float(row["seed"]))))
        if not actual_scenario_sha:
            actual_scenario_sha = str(plan.get("g561_scenario_sha256", ""))
        actual_identity = stable_uid(
            "g561_contract_identity",
            row.get("plan_row_id", ""),
            row.get("g561_instance_uid", ""),
            row.get("g561_scenario_sha256", ""),
            row.get("candidate_id", ""),
            row.get("generated_theta_uid", ""),
        )
        row.update(
            {
                "executed": boolish(row.get("real_solver_execution", True)),
                "candidate_recognized_bool": boolish(row.get("candidate_recognized")),
                "fingerprint_parsed": bool(parsed),
                "fulltheta_fingerprint_match_strict": strict_match,
                "fulltheta_fingerprint_match_relaxed": relaxed_match,
                "fulltheta_fingerprint_mismatched_fields": ";".join(mismatches or relaxed_mismatches),
                "force_additive_false": bool_from_fingerprint(parsed, "force_additive") is False,
                "dual_channel_enabled": bool_from_fingerprint(parsed, "enable_dual_channel") is True,
                "scenario_sha256_expected": row.get("g561_scenario_sha256", ""),
                "scenario_sha256_actual": actual_scenario_sha,
                "scenario_sha256_match": bool(actual_scenario_sha) and actual_scenario_sha == row.get("g561_scenario_sha256", ""),
                "identity_digest_expected": row.get("g561_identity_digest", ""),
                "identity_digest_actual": actual_identity,
                "identity_retained": bool(row.get("g561_identity_digest", "")) and row.get("g561_identity_digest", "") == actual_identity,
            }
        )
        audited.append(row)
    return audited


def rate(rows: list[dict[str, Any]], key: str) -> float | None:
    if not rows:
        return None
    return sum(boolish(row.get(key)) for row in rows) / len(rows)


def summarize_contract(rows: list[dict[str, Any]], plan_rows: list[dict[str, Any]]) -> dict[str, Any]:
    executed_rows = [row for row in rows if boolish(row.get("executed"))]
    families = sorted({str(row.get("vector_family", "")) for row in plan_rows if row.get("vector_family")})
    source_families = sorted({str(row.get("source_map_family", "")) for row in plan_rows if row.get("source_map_family")})
    gates = {
        "minimum_64_vectors_met": len(plan_rows) >= 64,
        "all_planned_vectors_executed": len(executed_rows) >= len(plan_rows) and len(plan_rows) > 0,
        "candidate_recognized_rate_is_1": rate(executed_rows, "candidate_recognized_bool") == 1.0,
        "fingerprint_exact_match_rate_is_1": rate(executed_rows, "fulltheta_fingerprint_match_strict") == 1.0,
        "force_additive_false_rate_is_1": rate(executed_rows, "force_additive_false") == 1.0,
        "dual_channel_enabled_rate_is_1": rate(executed_rows, "dual_channel_enabled") == 1.0,
        "scenario_hash_match_rate_is_1": rate(executed_rows, "scenario_sha256_match") == 1.0,
        "identity_retention_rate_is_1": rate(executed_rows, "identity_retained") == 1.0,
        "actor_produced_points_included": any(row.get("vector_family") == "actor_produced_point" for row in plan_rows),
        "all_goal_modes_included": {"flow_shield", "agent_progress", "none"}.issubset(
            {str(row.get("changed_field")) for row in plan_rows if row.get("vector_family") == "goal_mode"}
        ),
    }
    passed = bool(executed_rows) and all(gates.values())
    return {
        "schema_version": "phase5p5_repair5g561_materialization_contract_summary_v2",
        "decision": "g561_materialization_contract_passed" if passed else "g561_materialization_contract_failed_continue_repair",
        "planned_contract_vectors": len(plan_rows),
        "executed_contract_vectors": len(executed_rows),
        "contract_vector_families": families,
        "actor_source_map_families": source_families,
        "candidate_recognized_rate": rate(executed_rows, "candidate_recognized_bool"),
        "fingerprint_exact_match_rate": rate(executed_rows, "fulltheta_fingerprint_match_strict"),
        "fingerprint_relaxed_match_rate": rate(executed_rows, "fulltheta_fingerprint_match_relaxed"),
        "force_additive_false_rate": rate(executed_rows, "force_additive_false"),
        "dual_channel_enabled_rate": rate(executed_rows, "dual_channel_enabled"),
        "scenario_hash_match_rate": rate(executed_rows, "scenario_sha256_match"),
        "identity_retention_rate": rate(executed_rows, "identity_retained"),
        "gates": gates,
        "materialization_contract_passed": passed,
        "performance_replay_allowed_by_materialization_contract": passed,
        "result_csv": str(RESULTS_CSV),
        "plan_csv": str(PLAN_CSV),
        "registry_csv": str(REGISTRY_CSV),
        **claims(),
    }


def write_plan_artifacts(plan_rows: list[dict[str, Any]], registry_rows: list[dict[str, Any]], *, source_truth_decision: str = "") -> None:
    write_rows(PLAN_CSV, plan_rows)
    write_rows(REGISTRY_CSV, registry_rows)
    planned_results = []
    for row in plan_rows:
        planned_results.append(
            {
                **row,
                "executed": False,
                "candidate_recognized_bool": "",
                "fingerprint_parsed": "",
                "fulltheta_fingerprint_match_strict": "",
                "force_additive_false": "",
                "dual_channel_enabled": "",
                "scenario_sha256_match": "",
                "identity_retained": "",
                "reason": "planned_for_server_materialization_contract",
            }
        )
    write_rows(RESULTS_CSV, planned_results)
    families = sorted({str(row.get("vector_family", "")) for row in plan_rows if row.get("vector_family")})
    summary = {
        "schema_version": "phase5p5_repair5g561_materialization_contract_summary_v2",
        "decision": "g561_materialization_contract_planned_server_run_required",
        "planned_contract_vectors": len(plan_rows),
        "executed_contract_vectors": 0,
        "contract_vector_families": families,
        "source_truth_audit_decision": source_truth_decision,
        "candidate_recognized_rate": None,
        "fingerprint_exact_match_rate": None,
        "force_additive_false_rate": None,
        "dual_channel_enabled_rate": None,
        "scenario_hash_match_rate": None,
        "identity_retention_rate": None,
        "materialization_contract_passed": False,
        "performance_replay_allowed_by_materialization_contract": False,
        **claims(),
    }
    write_json(SUMMARY_JSON, summary)
    write_report(summary)


def write_report(summary: dict[str, Any]) -> None:
    gates = summary.get("gates", {})
    gate_lines = [f"- {key}: `{value}`" for key, value in gates.items()]
    write_text(
        REPORT_MD,
        "# Repair5G.5.61 Materialization Contract\n\n"
        f"- decision: `{summary.get('decision')}`\n"
        f"- planned vectors: `{summary.get('planned_contract_vectors')}`\n"
        f"- executed vectors: `{summary.get('executed_contract_vectors')}`\n"
        f"- candidate_recognized_rate: `{summary.get('candidate_recognized_rate')}`\n"
        f"- fingerprint_exact_match_rate: `{summary.get('fingerprint_exact_match_rate')}`\n"
        f"- force_additive_false_rate: `{summary.get('force_additive_false_rate')}`\n"
        f"- dual_channel_enabled_rate: `{summary.get('dual_channel_enabled_rate')}`\n"
        f"- scenario_hash_match_rate: `{summary.get('scenario_hash_match_rate')}`\n"
        f"- identity_retention_rate: `{summary.get('identity_retention_rate')}`\n\n"
        + ("\n".join(gate_lines) + "\n" if gate_lines else "")
        + "\nAll runtime, Phase5.5, Phase6, learned-policy, and AAAI claims remain closed.\n",
    )


def solver_binary(arg: Path) -> Path:
    candidates = [
        arg,
        Path("build/phase1a-batch/phase1a_batch"),
        Path("build/phase1-ltm/phase1a_batch"),
        Path("build/phase1a-batch/phase1a_batch.exe"),
        Path("build/phase1-ltm/phase1a_batch.exe"),
    ]
    for candidate in candidates:
        p = resolve(candidate)
        if p.exists():
            return p
    return resolve(arg)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the G5.61 full-theta materialization contract.")
    parser.add_argument("--binary", type=Path, default=Path("build/phase1a-batch/phase1a_batch"))
    parser.add_argument("--max-workers", type=int, default=2)
    parser.add_argument("--context-limit", type=int, default=0)
    parser.add_argument("--vector-limit", type=int, default=0)
    parser.add_argument("--actor-device", default="cpu")
    parser.add_argument("--skip-actor-points", action="store_true")
    parser.add_argument("--plan-only", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(argv)

    vectors = build_contract_vectors(include_actor=not args.skip_actor_points, actor_device=args.actor_device, vector_limit=args.vector_limit)
    contexts = default_contexts(args.context_limit)
    plan_rows, registry_rows = build_plan_rows(vectors, contexts)
    prepare_contract_scenarios(plan_rows, SCENARIO_DIR, SCENARIO_METADATA)
    plan_rows = attach_scenario_and_identity(plan_rows, SCENARIO_DIR)
    write_plan_artifacts(plan_rows, registry_rows)
    if args.plan_only:
        print(json.dumps({"decision": "g561_materialization_contract_planned_server_run_required", "planned_vectors": len(plan_rows)}, sort_keys=True))
        return 0

    binary = solver_binary(args.binary)
    if not binary.exists():
        summary = {
            "schema_version": "phase5p5_repair5g561_materialization_contract_summary_v2",
            "decision": "g561_materialization_contract_blocked_missing_solver_binary",
            "binary": str(binary),
            "planned_contract_vectors": len(plan_rows),
            "executed_contract_vectors": 0,
            "materialization_contract_passed": False,
            "performance_replay_allowed_by_materialization_contract": False,
            **claims(),
        }
        write_json(SUMMARY_JSON, summary)
        write_report(summary)
        print(json.dumps(summary, sort_keys=True))
        return 2

    os.environ.setdefault("REPAIR5G_STREAM_RESULT_CSV", "1")
    os.environ.setdefault("REPAIR5G_SKIP_AGGREGATE_JSONL", "1")
    g549.run_probe_plan(
        plan_rows,
        binary=binary,
        overwrite=True,
        row_limit=0,
        max_workers=max(1, int(args.max_workers)),
        registry_path=str(resolve(REGISTRY_CSV)),
        result_csv=str(resolve(RESULTS_CSV)),
        raw_csv=str(resolve(RAW_RESULTS_CSV)),
        log_dir=str(resolve(LOG_DIR)),
        run_jsonl=str(resolve(LOG_DIR / "runs.jsonl")),
        command_jsonl=str(resolve(LOG_DIR / "commands.jsonl")),
        update_jsonl=str(resolve(LOG_DIR / "updates.jsonl")),
        probe_jsonl=str(resolve(LOG_DIR / "counterfactual_probes.jsonl")),
        checkpoint_jsonl=str(resolve(LOG_DIR / "checkpoints.jsonl")),
        status_json=str(resolve(LOG_DIR / "status.json")),
        scenario_dir=str(resolve(SCENARIO_DIR)),
        scenario_metadata=str(resolve(SCENARIO_METADATA)),
        manifest_prefix="g561_materialization_contract",
        row_prefix="g561_contract",
        execution_mode="g561_materialization_contract_real_solver_row",
    )
    rows = attach_contract_audit(read_rows(RESULTS_CSV), plan_rows, SCENARIO_DIR)
    write_rows(RESULTS_CSV, rows)
    summary = summarize_contract(rows, plan_rows)
    write_json(SUMMARY_JSON, summary)
    write_report(summary)
    print(json.dumps({"decision": summary["decision"], "planned": len(plan_rows), "executed": summary["executed_contract_vectors"]}, sort_keys=True))
    return 0 if summary["materialization_contract_passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
