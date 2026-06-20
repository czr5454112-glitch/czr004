from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import random
import statistics
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import repair5g549_common as g549  # noqa: E402
from gcst.dual_stream_graph_actor import DualStreamGoalAwareActor  # noqa: E402
from gcst.generated_theta_audit import generated_theta_uid  # noqa: E402
from gcst.goal_aware_actor import make_graph_batch, pad_od_tokens, scalar_features  # noqa: E402
from gcst.graph_data import GraphData  # noqa: E402
from gcst.graph_encoder import GraphBatch  # noqa: E402
from gcst.label_v5 import solver_ratio, solver_success  # noqa: E402
from gcst.real_label_graph_dataset import DEFAULT_CONTEXT_DIR, build_example, load_label_groups  # noqa: E402
from gcst.theta_schema import (  # noqa: E402
    BASELINE_G556,
    THETA_COLUMNS,
    THETA_NUMERIC_COLUMNS,
    clamp_theta_row,
    compare_theta_to_fingerprint,
    expected_cpp_params,
    mode_columns,
    parse_updateparams_fingerprint,
)
from repair5g2_common import scenario_path  # noqa: E402
from run_repair5f4_static_updateparams_validation import MAPS as MAP_PATHS  # noqa: E402


ROUND = "phase5p5_repair5g562"
ADDITIVE = "repair5g59_additive_fallback"
G556 = "g556_c063174"
RESULT_TABLES = Path("outputs/tables")
REPORTS = Path("outputs/reports")
LOG_ROOT = Path("outputs/logs")
MODEL_MATRIX = Path(f"outputs/tables/{ROUND}_architecture_matrix.csv")
EXTERNAL_CONTEXT_DIR = DEFAULT_CONTEXT_DIR


@dataclass
class ReplayContext:
    dataset_row_id: str
    evaluation_uid: str
    instance_uid: str
    split: str
    map: str
    map_family: str
    agents: int
    seed: int
    budget_ms: int
    base_time_limit_sec: float
    ltm_max_iterations: int
    horizon_id: str
    scenario_sha256: str
    physical_map_sha256: str
    graph_with_traffic: GraphData
    assignment: dict[str, Any]
    feature_row: dict[str, Any]


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


def boolish(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def number(value: Any, default: float = 0.0) -> float:
    try:
        out = float(value)
    except Exception:
        return default
    return out if math.isfinite(out) else default


def write_json(path: str | Path, data: dict[str, Any]) -> None:
    p = resolve(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


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


def write_text(path: str | Path, text: str) -> None:
    p = resolve(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def sha256_file(path: str | Path) -> str:
    p = resolve(path)
    if not p.exists():
        return ""
    h = hashlib.sha256()
    with p.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def stable_uid(*parts: Any) -> str:
    payload = json.dumps(parts, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def safe_token(text: Any) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in str(text).lower()).strip("_")[:48] or "item"


def fingerprint(theta: dict[str, Any]) -> str:
    return "|".join(f"{key}={value}" for key, value in expected_cpp_params(theta).items())


def base_theta() -> dict[str, Any]:
    row = {col: float(value) for col, value in zip(THETA_NUMERIC_COLUMNS, BASELINE_G556)}
    row.update(mode_columns("flow_shield"))
    return clamp_theta_row(row)


def graph_with_edge_features(graph: GraphData, edge_features: np.ndarray) -> GraphData:
    return GraphData(
        topology_id=graph.topology_id,
        map_name=graph.map_name,
        width=graph.width,
        height=graph.height,
        cells=graph.cells,
        node_features=graph.node_features,
        edge_index=graph.edge_index,
        edge_features=edge_features,
        hashes=graph.hashes,
        component_count=graph.component_count,
        physical_free_cell_count=graph.physical_free_cell_count,
    )


def register_external_maps(context_dir: str | Path = EXTERNAL_CONTEXT_DIR) -> None:
    maps_dir = resolve(context_dir) / "maps"
    if not maps_dir.exists():
        return
    for path in sorted(maps_dir.glob("*.map")):
        try:
            MAP_PATHS[path.stem] = str(path.relative_to(ROOT)).replace("\\", "/")
        except ValueError:
            MAP_PATHS[path.stem] = str(path)
    try:
        import repair5g5_common as g5

        g5.MAP_PATHS.update(MAP_PATHS)
    except Exception:
        pass


def load_contexts(max_contexts: int, preferred_split: str = "any") -> list[ReplayContext]:
    register_external_maps()
    groups = load_label_groups(max_contexts=0)
    if preferred_split != "any":
        allowed = {token.strip() for token in preferred_split.split(",") if token.strip()}
        selected = [group for group in groups if group.split in allowed]
        if len(selected) >= max_contexts:
            groups = selected
    contexts: list[ReplayContext] = []
    for idx, group in enumerate(groups):
        built = build_example(group)
        graph_t = graph_with_edge_features(built.graph, built.traffic["edge_features"])
        context = {
            "agent_count": group.agent_count,
            "agents": group.agent_count,
            "nominal_budget_ms": group.budget_ms,
            "budget_ms": group.budget_ms,
            "base_time_limit_sec": group.rows[0].get("base_time_limit_sec", 1.0),
            "ltm_max_iterations": group.rows[0].get("ltm_max_iterations", 3),
            "agent_density": group.rows[0].get("agent_density", 0.0),
            **built.traffic["summary"],
        }
        contexts.append(
            ReplayContext(
                dataset_row_id=f"g562_real_graph_{idx:06d}",
                evaluation_uid=group.evaluation_uid,
                instance_uid=group.instance_uid,
                split=group.split,
                map=group.map,
                map_family=group.map_family,
                agents=group.agent_count,
                seed=group.seed,
                budget_ms=group.budget_ms,
                base_time_limit_sec=float(number(group.rows[0].get("base_time_limit_sec"), max(0.5, group.budget_ms / 1000.0))),
                ltm_max_iterations=max(1, int(number(group.rows[0].get("ltm_max_iterations"), 3))),
                horizon_id=group.horizon_id,
                scenario_sha256=group.scenario_sha256_expected,
                physical_map_sha256=group.physical_map_sha256_expected,
                graph_with_traffic=graph_t,
                assignment=built.assignment,
                feature_row=context,
            )
        )
        if max_contexts and len(contexts) >= max_contexts:
            break
    return contexts


def move_graph_batch(batch: GraphBatch, device: str) -> GraphBatch:
    return GraphBatch(
        batch.node_features.to(device),
        batch.edge_index.to(device),
        batch.edge_features.to(device),
        batch.batch_index.to(device),
        batch.num_graphs,
    )


def hidden_dim_from_checkpoint(checkpoint: dict[str, Any]) -> int:
    if checkpoint.get("hidden_dim"):
        return int(checkpoint["hidden_dim"])
    state = checkpoint.get("actor_state_dict", {})
    for key in ["scalar_encoder.0.weight", "fusion.0.weight"]:
        weight = state.get(key)
        if weight is not None:
            return int(weight.shape[0])
    return 96


def actor_rows_from_matrix(variant_filter: str = "all", seed_filter: str = "all") -> list[dict[str, str]]:
    rows = [row for row in read_rows(MODEL_MATRIX) if row.get("model_path")]
    if variant_filter != "all":
        wanted = {token.strip().upper() for token in variant_filter.split(",") if token.strip()}
        rows = [row for row in rows if str(row.get("variant_id", "")).upper() in wanted]
    if seed_filter != "all":
        wanted_seeds = {token.strip() for token in seed_filter.split(",") if token.strip()}
        rows = [row for row in rows if str(row.get("seed", "")) in wanted_seeds]
    return rows


def infer_actor_thetas(
    contexts: list[ReplayContext],
    *,
    device: str,
    phase: str,
    variant_filter: str,
    seed_filter: str,
    batch_size: int,
) -> list[dict[str, Any]]:
    import torch

    actor_rows = actor_rows_from_matrix(variant_filter, seed_filter)
    outputs: list[dict[str, Any]] = []
    for actor in actor_rows:
        model_path = resolve(str(actor["model_path"]))
        checkpoint = torch.load(model_path, map_location=device, weights_only=False)
        model = DualStreamGoalAwareActor(
            hidden_dim=hidden_dim_from_checkpoint(checkpoint),
            scalar_only_control=boolish(checkpoint.get("scalar_only_control")),
            use_cross_attention=boolish(checkpoint.get("use_cross_attention")),
            safe_subspace=boolish(checkpoint.get("safe_subspace")),
            field_group_trust=boolish(checkpoint.get("field_group_trust")),
        ).module().to(device)
        model.load_state_dict(checkpoint["actor_state_dict"])
        model.eval()
        for start in range(0, len(contexts), batch_size):
            batch = contexts[start : start + batch_size]
            graph_batch = move_graph_batch(make_graph_batch([ctx.graph_with_traffic for ctx in batch]), device)
            od_tokens, od_mask = pad_od_tokens([ctx.assignment for ctx in batch])
            scalar_x = torch.tensor(np.stack([scalar_features(ctx.feature_row) for ctx in batch]), dtype=torch.float32, device=device)
            with torch.no_grad():
                theta = model(graph_batch, od_tokens.to(device), od_mask.to(device), scalar_x).detach().cpu().numpy()
            for ctx, values in zip(batch, theta):
                row = {col: float(values[idx]) for idx, col in enumerate(THETA_NUMERIC_COLUMNS)}
                row.update(mode_columns("flow_shield"))
                outputs.append(
                    {
                        "phase": phase,
                        "context_id": ctx.dataset_row_id,
                        "dataset_row_id": ctx.dataset_row_id,
                        "g562_evaluation_uid": ctx.evaluation_uid,
                        "variant_id": actor.get("variant_id", ""),
                        "variant_name": actor.get("variant_name", ""),
                        "seed": actor.get("seed", ""),
                        "method": f"{actor.get('variant_id', '')}_seed{actor.get('seed', '')}_{actor.get('variant_name', '')}",
                        "model_path": actor["model_path"],
                        **clamp_theta_row(row),
                    }
                )
    return outputs


def paths_for_phase(phase: str) -> dict[str, Path]:
    token = safe_token(phase)
    return {
        "plan": RESULT_TABLES / f"{ROUND}_{token}_plan.csv",
        "registry": RESULT_TABLES / f"{ROUND}_{token}_registry.csv",
        "results": RESULT_TABLES / f"{ROUND}_{token}_results.csv",
        "raw_results": RESULT_TABLES / f"{ROUND}_{token}_results.raw.csv",
        "pairs": RESULT_TABLES / f"{ROUND}_{token}_pairs.csv",
        "summary": REPORTS / f"{ROUND}_{token}_summary.json",
        "report": REPORTS / f"{ROUND}_{token}.md",
        "scenario_metadata": REPORTS / f"{ROUND}_{token}_scenario_generation.json",
        "log_dir": LOG_ROOT / f"{ROUND}_{token}",
        "scenario_dir": resolve(EXTERNAL_CONTEXT_DIR) / "scenarios",
    }


def build_plan_and_registry(contexts: list[ReplayContext], theta_rows: list[dict[str, Any]], phase: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    context_by_row = {ctx.dataset_row_id: ctx for ctx in contexts}
    plan: list[dict[str, Any]] = []
    registry: list[dict[str, Any]] = [
        {
            "candidate_id": G556,
            "generated_theta_uid": "",
            "registry_role": "g562_g556_baseline",
            **base_theta(),
            **claims(),
        }
    ]

    def add_plan(ctx: ReplayContext, *, role: str, candidate_id: str, method: str, theta: dict[str, Any] | None, model_path: str = "", actor_row: dict[str, Any] | None = None) -> None:
        idx = len(plan)
        generated_uid = "" if theta is None else generated_theta_uid(model_path or method, ctx.instance_uid, [theta[col] for col in THETA_NUMERIC_COLUMNS])
        identity = stable_uid("g562_replay_identity", phase, ctx.evaluation_uid, ctx.scenario_sha256, candidate_id, generated_uid)
        plan.append(
            {
                "plan_row_id": f"g562_{safe_token(phase)}_{idx:08d}",
                "replay_phase": phase,
                "context_id": ctx.dataset_row_id,
                "g562_dataset_row_id": ctx.dataset_row_id,
                "g562_instance_uid": ctx.instance_uid,
                "g562_evaluation_uid": ctx.evaluation_uid,
                "g562_identity_digest": identity,
                "g562_scenario_sha256": ctx.scenario_sha256,
                "g562_physical_map_sha256": ctx.physical_map_sha256,
                "split": ctx.split,
                "map": ctx.map,
                "map_family": ctx.map_family,
                "agents": ctx.agents,
                "agent_count": ctx.agents,
                "seed": ctx.seed,
                "budget_ms": ctx.budget_ms,
                "nominal_budget_ms": ctx.budget_ms,
                "short_budget_ms": ctx.budget_ms,
                "base_time_limit_sec": ctx.base_time_limit_sec,
                "ltm_max_iterations": ctx.ltm_max_iterations,
                "horizon_id": ctx.horizon_id,
                "role": role,
                "candidate_id": candidate_id,
                "theta_id": candidate_id,
                "materialized_method": candidate_id,
                "generated_theta_uid": generated_uid,
                "sampling_policy": method,
                "model_path": model_path,
                "variant_id": "" if actor_row is None else actor_row.get("variant_id", ""),
                "actor_training_seed": "" if actor_row is None else actor_row.get("seed", ""),
                "expected_updateparams_fingerprint": "" if theta is None else fingerprint(theta),
                **({col: theta.get(col, "") for col in THETA_COLUMNS} if theta else {}),
                **claims(),
            }
        )

    for ctx in contexts:
        add_plan(ctx, role="additive_ltm", candidate_id=ADDITIVE, method="paper_faithful_additive_ltm", theta=None)
        add_plan(ctx, role=G556, candidate_id=G556, method="g556_c063174", theta=base_theta())
    for row in theta_rows:
        ctx = context_by_row[str(row["context_id"])]
        theta = clamp_theta_row(row)
        uid = stable_uid("g562_actor_theta", phase, row.get("method", ""), ctx.evaluation_uid, {col: theta[col] for col in THETA_NUMERIC_COLUMNS})
        candidate_id = f"g562_{safe_token(phase)}_{safe_token(row.get('variant_id', 'actor'))}_s{safe_token(row.get('seed', '0'))}_{uid[:12]}"
        registry.append(
            {
                "candidate_id": candidate_id,
                "generated_theta_uid": generated_theta_uid(row.get("model_path", ""), ctx.instance_uid, [theta[col] for col in THETA_NUMERIC_COLUMNS]),
                "registry_role": "g562_actor_generated_theta",
                "replay_phase": phase,
                "method": row.get("method", ""),
                "variant_id": row.get("variant_id", ""),
                "actor_training_seed": row.get("seed", ""),
                **{col: theta.get(col, "") for col in THETA_COLUMNS},
                **claims(),
            }
        )
        add_plan(
            ctx,
            role=f"generated_theta::{candidate_id}",
            candidate_id=candidate_id,
            method=str(row.get("method", "")),
            theta=theta,
            model_path=str(row.get("model_path", "")),
            actor_row=row,
        )
    return plan, registry


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


def audit_results(rows: list[dict[str, Any]], plan_rows: list[dict[str, Any]], scenario_dir: Path, phase: str) -> list[dict[str, Any]]:
    lookup = plan_lookup(plan_rows)
    out: list[dict[str, Any]] = []
    for raw in rows:
        row = dict(raw)
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
            "replay_phase",
            "g562_dataset_row_id",
            "g562_instance_uid",
            "g562_evaluation_uid",
            "g562_identity_digest",
            "g562_scenario_sha256",
            "g562_physical_map_sha256",
            "split",
            "generated_theta_uid",
            "expected_updateparams_fingerprint",
            "model_path",
            "variant_id",
            "actor_training_seed",
        ]:
            row[key] = plan.get(key, row.get(key, ""))
        for col in THETA_COLUMNS:
            row[col] = plan.get(col, row.get(col, ""))
        parsed = parse_updateparams_fingerprint(row.get("updateparams_fingerprint", ""))
        is_actor = str(row.get("role", "")).startswith("generated_theta::")
        is_g556 = row.get("materialized_method") == G556
        is_additive = row.get("materialized_method") == ADDITIVE
        fp_match = True
        mismatch = ""
        if is_actor or is_g556:
            fp_match, mismatches = compare_theta_to_fingerprint(row.get("updateparams_fingerprint", ""), plan or row, tolerance=1.0e-9)
            mismatch = ";".join(mismatches)
        elif is_additive:
            fp_match = parsed.get("force_additive") == "1" and parsed.get("enable_dual_channel") == "0"
            mismatch = "" if fp_match else "additive_fingerprint"
        scen = scenario_path(resolve(scenario_dir), str(row.get("map", "")), int(number(row.get("seed"), 0)))
        scenario_actual = sha256_file(scen)
        identity_actual = stable_uid(
            "g562_replay_identity",
            phase,
            row.get("g562_evaluation_uid", ""),
            row.get("g562_scenario_sha256", ""),
            row.get("candidate_id", ""),
            row.get("generated_theta_uid", ""),
        )
        row.update(
            {
                "executed": boolish(row.get("real_solver_execution", True)),
                "is_actor_row": is_actor,
                "is_g556_row": is_g556,
                "is_additive_row": is_additive,
                "candidate_recognized_bool": boolish(row.get("candidate_recognized")),
                "fingerprint_parsed": bool(parsed),
                "fulltheta_fingerprint_match_strict": fp_match,
                "fulltheta_fingerprint_mismatched_fields": mismatch,
                "force_additive_false": parsed.get("force_additive") == "0" if (is_actor or is_g556) else "",
                "dual_channel_enabled": parsed.get("enable_dual_channel") == "1" if (is_actor or is_g556) else "",
                "scenario_sha256_actual": scenario_actual,
                "scenario_sha256_match": bool(scenario_actual) and scenario_actual == row.get("g562_scenario_sha256", ""),
                "identity_digest_actual": identity_actual,
                "identity_retained": bool(row.get("g562_identity_digest", "")) and identity_actual == row.get("g562_identity_digest", ""),
            }
        )
        out.append(row)
    return out


def group_key(row: dict[str, Any]) -> tuple[str, str, str, str, str]:
    return (
        str(row.get("map", "")),
        str(row.get("agents", "")),
        str(row.get("seed", "")),
        str(row.get("budget_ms", "")),
        str(row.get("horizon_id", "")),
    )


def build_pairs(rows: list[dict[str, Any]], phase: str) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str, str, str], dict[str, dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(group_key(row), {})[str(row.get("materialized_method", ""))] = row
    pairs: list[dict[str, Any]] = []
    for key, by_method in sorted(grouped.items()):
        baseline = by_method.get(G556)
        additive = by_method.get(ADDITIVE)
        if not baseline:
            continue
        for method, candidate in sorted(by_method.items()):
            if method in {G556, ADDITIVE}:
                continue
            if candidate.get("replay_phase") != phase:
                continue
            cand_success = solver_success(candidate)
            base_success = solver_success(baseline)
            add_success = solver_success(additive or {}) if additive else False
            cand_ratio = solver_ratio(candidate)
            base_ratio = solver_ratio(baseline)
            add_ratio = solver_ratio(additive or {}) if additive else None
            both_success = cand_success and base_success
            q_delta = cand_ratio - base_ratio if both_success and cand_ratio is not None and base_ratio is not None else math.nan
            add_delta = cand_ratio - add_ratio if cand_success and add_success and cand_ratio is not None and add_ratio is not None else math.nan
            pairs.append(
                {
                    "replay_phase": phase,
                    "map": key[0],
                    "agents": key[1],
                    "seed": key[2],
                    "budget_ms": key[3],
                    "horizon_id": key[4],
                    "split": candidate.get("split", ""),
                    "map_family": candidate.get("map_family", ""),
                    "g562_dataset_row_id": candidate.get("g562_dataset_row_id", ""),
                    "g562_evaluation_uid": candidate.get("g562_evaluation_uid", ""),
                    "g562_identity_digest": candidate.get("g562_identity_digest", ""),
                    "theta_id": method,
                    "method": candidate.get("sampling_policy", ""),
                    "variant_id": candidate.get("variant_id", ""),
                    "actor_training_seed": candidate.get("actor_training_seed", ""),
                    "model_path": candidate.get("model_path", ""),
                    "candidate_success": cand_success,
                    "baseline_success": base_success,
                    "additive_success": add_success,
                    "success_regression": bool(base_success and not cand_success),
                    "success_gain": bool(cand_success and not base_success),
                    "both_success": both_success,
                    "both_fail": bool((not cand_success) and (not base_success)),
                    "quality_delta_vs_g556": q_delta,
                    "quality_delta_vs_additive": add_delta,
                    "candidate_recognized": candidate.get("candidate_recognized_bool", False),
                    "fingerprint_match": candidate.get("fulltheta_fingerprint_match_strict", False),
                    "scenario_hash_match": candidate.get("scenario_sha256_match", False),
                    "identity_retained": candidate.get("identity_retained", False),
                    "force_additive_false": candidate.get("force_additive_false", ""),
                    "dual_channel_enabled": candidate.get("dual_channel_enabled", ""),
                    "candidate_runtime_ms": candidate.get("probe_runtime_ms", ""),
                    "baseline_runtime_ms": baseline.get("probe_runtime_ms", ""),
                    "candidate_expanded_nodes": candidate.get("expanded_nodes", ""),
                    "baseline_expanded_nodes": baseline.get("expanded_nodes", ""),
                    "candidate_low_level_pibt_calls": candidate.get("low_level_pibt_calls", ""),
                    "baseline_low_level_pibt_calls": baseline.get("low_level_pibt_calls", ""),
                    **{col: candidate.get(col, "") for col in THETA_NUMERIC_COLUMNS},
                    **claims(),
                }
            )
    return pairs


def finite_float(value: Any) -> float | None:
    try:
        out = float(value)
    except Exception:
        return None
    return out if math.isfinite(out) else None


def mean_ci(values: list[float]) -> tuple[float | None, float | None]:
    values = [v for v in values if math.isfinite(v)]
    if not values:
        return None, None
    rng = random.Random(562)
    means = []
    for _ in range(1000):
        sample = [values[rng.randrange(len(values))] for _ in values]
        means.append(sum(sample) / len(sample))
    means.sort()
    return sum(values) / len(values), means[int(0.975 * len(means)) - 1]


def summarize_method(group: list[dict[str, Any]]) -> dict[str, Any]:
    values = [finite_float(row.get("quality_delta_vs_g556")) for row in group]
    finite = [v for v in values if v is not None]
    mean, ci_high = mean_ci(finite)
    return {
        "pairs": len(group),
        "success_regressions": sum(boolish(row.get("success_regression")) for row in group),
        "success_gains": sum(boolish(row.get("success_gain")) for row in group),
        "both_success": sum(boolish(row.get("both_success")) for row in group),
        "both_fail": sum(boolish(row.get("both_fail")) for row in group),
        "mean_quality_delta_vs_g556": mean,
        "median_quality_delta_vs_g556": statistics.median(finite) if finite else None,
        "quality_delta_ci_upper_vs_g556": ci_high,
        "better_count_vs_g556": sum(v < 0 for v in finite),
        "worse_count_vs_g556": sum(v > 0 for v in finite),
        "tie_count_vs_g556": sum(v == 0 for v in finite),
    }


def summarize_phase(rows: list[dict[str, Any]], pairs: list[dict[str, Any]], plan_rows: list[dict[str, Any]], phase: str) -> dict[str, Any]:
    actor_rows = [row for row in rows if row.get("replay_phase") == phase and boolish(row.get("is_actor_row"))]
    candidate_rows = len(actor_rows)
    methods = []
    for method in sorted({str(row.get("method", "")) for row in pairs}):
        group = [row for row in pairs if row.get("method") == method]
        methods.append({"method": method, **summarize_method(group), **claims()})
    all_stats = summarize_method(pairs)
    exact = sum(boolish(row.get("fulltheta_fingerprint_match_strict")) for row in actor_rows)
    recognized = sum(boolish(row.get("candidate_recognized_bool")) for row in actor_rows)
    identity = sum(boolish(row.get("identity_retained")) for row in actor_rows)
    scenario = sum(boolish(row.get("scenario_sha256_match")) for row in actor_rows)
    decision = "g562_cycle_replay_completed_exact_materialization" if candidate_rows and exact == candidate_rows and recognized == candidate_rows and identity == candidate_rows and scenario == candidate_rows else "g562_materialization_or_identity_blocker_not_model_failure"
    return {
        "schema_version": f"{ROUND}_{safe_token(phase)}_summary_v1",
        "decision": decision,
        "replay_phase": phase,
        "planned_rows": len(plan_rows),
        "executed_rows": len(rows),
        "contexts": len({row.get("g562_dataset_row_id") for row in plan_rows}),
        "unique_valid_contexts": len({row.get("g562_dataset_row_id") for row in actor_rows}),
        "candidate_rows": candidate_rows,
        "new_exact_materialized_candidate_rows": sum(
            boolish(row.get("candidate_recognized_bool"))
            and boolish(row.get("fulltheta_fingerprint_match_strict"))
            and boolish(row.get("identity_retained"))
            and boolish(row.get("scenario_sha256_match"))
            for row in actor_rows
        ),
        "recognized_actor_rows": recognized,
        "exact_fingerprint_rows": exact,
        "identity_complete_rows": identity,
        "scenario_hash_match_rows": scenario,
        "additive_rows_present": sum(1 for row in rows if row.get("materialized_method") == ADDITIVE),
        "g556_rows_present": sum(1 for row in rows if row.get("materialized_method") == G556),
        "replay_pairs": len(pairs),
        "by_method": methods,
        **all_stats,
        **claims(),
    }


def tail_risk_rows(pairs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for method in sorted({str(row.get("method", "")) for row in pairs}):
        group = [row for row in pairs if row.get("method") == method]
        values = sorted(v for v in (finite_float(row.get("quality_delta_vs_g556")) for row in group) if v is not None)
        losses = [max(0.0, v) for v in values]
        if not values:
            rows.append({"method": method, "pairs": len(group), "finite_pairs": 0, **claims()})
            continue
        q90_index = min(len(values) - 1, int(0.90 * (len(values) - 1)))
        tail = losses[q90_index:] or [0.0]
        rows.append(
            {
                "method": method,
                "pairs": len(group),
                "finite_pairs": len(values),
                "q75_quality_delta": values[min(len(values) - 1, int(0.75 * (len(values) - 1)))],
                "q90_quality_delta": values[q90_index],
                "q95_quality_delta": values[min(len(values) - 1, int(0.95 * (len(values) - 1)))],
                "cvar90_positive_loss": sum(tail) / len(tail),
                "worst_quality_delta": values[-1],
                "frac_delta_gt_0p01": sum(v > 0.01 for v in values) / len(values),
                "frac_delta_gt_0p05": sum(v > 0.05 for v in values) / len(values),
                "frac_delta_gt_0p10": sum(v > 0.10 for v in values) / len(values),
                **claims(),
            }
        )
    return rows


def by_family_rows(pairs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in pairs:
        grouped[(str(row.get("map_family", "")), str(row.get("method", "")))].append(row)
    for (family, method), group in sorted(grouped.items()):
        out.append({"map_family": family, "method": method, **summarize_method(group), **claims()})
    return out


def failure_cases(pairs: list[dict[str, Any]], limit: int = 500) -> list[dict[str, Any]]:
    def severity(row: dict[str, Any]) -> tuple[int, float]:
        delta = finite_float(row.get("quality_delta_vs_g556"))
        return (1 if boolish(row.get("success_regression")) else 0, delta if delta is not None else -999.0)

    cases = [row for row in pairs if boolish(row.get("success_regression")) or (finite_float(row.get("quality_delta_vs_g556")) or 0.0) > 0.0]
    return sorted(cases, key=severity, reverse=True)[:limit] or [{"decision": "g562_no_failure_cases_observed", **claims()}]


def write_phase_artifacts(paths: dict[str, Path], rows: list[dict[str, Any]], pairs: list[dict[str, Any]], plan_rows: list[dict[str, Any]], phase: str) -> dict[str, Any]:
    summary = summarize_phase(rows, pairs, plan_rows, phase)
    write_rows(paths["pairs"], pairs)
    write_rows(RESULT_TABLES / f"{ROUND}_replay_by_method.csv", summary["by_method"])
    write_rows(RESULT_TABLES / f"{ROUND}_replay_by_map_family.csv", by_family_rows(pairs))
    write_rows(RESULT_TABLES / f"{ROUND}_tail_risk_metrics.csv", tail_risk_rows(pairs))
    write_rows(RESULT_TABLES / f"{ROUND}_failure_cases.csv", failure_cases(pairs))
    write_json(paths["summary"], summary)
    write_text(
        paths["report"],
        f"# G5.62 {phase} Replay\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- contexts: `{summary['contexts']}`\n"
        f"- candidate rows: `{summary['candidate_rows']}`\n"
        f"- new exact materialized candidate rows: `{summary['new_exact_materialized_candidate_rows']}`\n"
        f"- replay pairs: `{summary['replay_pairs']}`\n"
        f"- success regressions: `{summary['success_regressions']}`\n"
        f"- success gains: `{summary['success_gains']}`\n"
        f"- mean quality delta vs g556: `{summary['mean_quality_delta_vs_g556']}`\n\n"
        "This is exact-materialized solver evidence against additive LTM and g556_c063174. All broader claims remain closed.\n",
    )
    if phase == "cycle1":
        write_json(REPORTS / f"{ROUND}_cycle1_summary.json", summary)
    elif phase == "cycle2":
        write_json(REPORTS / f"{ROUND}_cycle2_summary.json", summary)
    elif phase == "cycle3":
        write_json(REPORTS / f"{ROUND}_cycle3_summary.json", summary)
    return summary


def run_solver(plan_rows: list[dict[str, Any]], paths: dict[str, Path], args: argparse.Namespace) -> int:
    binary = solver_binary(args.binary)
    if not binary.exists():
        write_json(paths["summary"], {"decision": "g562_replay_blocked_missing_solver_binary", "binary": str(binary), **claims()})
        return 2
    os.environ.setdefault("REPAIR5G_STREAM_RESULT_CSV", "1")
    os.environ.setdefault("REPAIR5G_SKIP_AGGREGATE_JSONL", "1")
    g549.run_probe_plan(
        plan_rows,
        binary=binary,
        overwrite=bool(args.overwrite),
        row_limit=0,
        max_workers=max(1, int(args.max_workers)),
        registry_path=str(resolve(paths["registry"])),
        result_csv=str(resolve(paths["results"])),
        raw_csv=str(resolve(paths["raw_results"])),
        log_dir=str(resolve(paths["log_dir"])),
        run_jsonl=str(resolve(paths["log_dir"] / "runs.jsonl")),
        command_jsonl=str(resolve(paths["log_dir"] / "commands.jsonl")),
        update_jsonl=str(resolve(paths["log_dir"] / "updates.jsonl")),
        probe_jsonl=str(resolve(paths["log_dir"] / "counterfactual_probes.jsonl")),
        checkpoint_jsonl=str(resolve(paths["log_dir"] / "checkpoints.jsonl")),
        status_json=str(resolve(paths["log_dir"] / "status.json")),
        scenario_dir=str(resolve(paths["scenario_dir"])),
        scenario_metadata=str(resolve(paths["scenario_metadata"])),
        manifest_prefix=f"g562_{safe_token(args.phase)}",
        row_prefix=f"g562_{safe_token(args.phase)}",
        execution_mode=f"g562_{safe_token(args.phase)}_real_solver_row",
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run or plan G5.62 exact-materialized replay truth.")
    parser.add_argument("--phase", default="cycle1")
    parser.add_argument("--contexts", type=int, default=200)
    parser.add_argument("--preferred-split", default="validation,heldout")
    parser.add_argument("--variants", default="all")
    parser.add_argument("--seeds", default="all")
    parser.add_argument("--device", default="auto")
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--binary", type=Path, default=Path("build/phase1a-batch/phase1a_batch"))
    parser.add_argument("--max-workers", type=int, default=4)
    parser.add_argument("--plan-only", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(argv)

    import torch

    device = args.device if args.device != "auto" else ("cuda" if torch.cuda.is_available() else "cpu")
    contexts = load_contexts(args.contexts, args.preferred_split)
    if not contexts:
        raise SystemExit("no G5.62 replay contexts available")
    theta_rows = infer_actor_thetas(contexts, device=device, phase=args.phase, variant_filter=args.variants, seed_filter=args.seeds, batch_size=args.batch_size)
    if not theta_rows:
        raise SystemExit("no actor checkpoints selected for G5.62 replay")
    plan_rows, registry_rows = build_plan_and_registry(contexts, theta_rows, args.phase)
    paths = paths_for_phase(args.phase)
    write_rows(paths["plan"], plan_rows)
    write_rows(paths["registry"], registry_rows)
    if args.plan_only:
        planned = {
            "schema_version": f"{ROUND}_{safe_token(args.phase)}_plan_summary_v1",
            "decision": "g562_replay_plan_created_server_run_required",
            "replay_phase": args.phase,
            "contexts": len(contexts),
            "actor_methods": len({(row.get("variant_id"), row.get("seed")) for row in theta_rows}),
            "candidate_rows": len(theta_rows),
            "planned_rows": len(plan_rows),
            "scenario_dir": str(resolve(paths["scenario_dir"])),
            **claims(),
        }
        write_json(paths["summary"], planned)
        print(json.dumps(planned, sort_keys=True))
        return 0
    rc = run_solver(plan_rows, paths, args)
    if rc != 0:
        print(json.dumps({"decision": "g562_replay_solver_not_executed", "phase": args.phase, "rc": rc}, sort_keys=True))
        return rc
    rows = audit_results(read_rows(paths["results"]), plan_rows, paths["scenario_dir"], args.phase)
    write_rows(paths["results"], rows)
    pairs = build_pairs(rows, args.phase)
    summary = write_phase_artifacts(paths, rows, pairs, plan_rows, args.phase)
    print(json.dumps({"decision": summary["decision"], "phase": args.phase, "candidate_rows": summary["candidate_rows"]}, sort_keys=True))
    return 0 if summary["decision"] == "g562_cycle_replay_completed_exact_materialization" else 2


if __name__ == "__main__":
    raise SystemExit(main())
