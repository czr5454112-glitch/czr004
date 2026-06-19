from __future__ import annotations

import argparse
import csv
import json
import math
import os
import random
import statistics
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from gcst.actor_critic_training import ActorNormalizer  # noqa: E402
from gcst.direct_actor import ACTOR_FEATURE_SCHEMA, DirectGCSTActor, actor_features  # noqa: E402
from gcst.generated_theta_audit import generated_theta_uid  # noqa: E402
from gcst.goal_aware_actor import GoalAwareDualChannelActor, make_graph_batch, pad_od_tokens, scalar_features  # noqa: E402
from gcst.graph_data import GraphData, build_graph  # noqa: E402
from gcst.label_v5 import solver_ratio, solver_success  # noqa: E402
from gcst.map_hash import physical_hashes  # noqa: E402
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
from gcst.traffic_prior import compute_traffic_prior  # noqa: E402
from repair5g2_common import scenario_path  # noqa: E402
from repair5g5_common import DEFAULT_SOURCE_SCENARIO_DIR, prepare_scenarios  # noqa: E402
from run_repair5f4_static_updateparams_validation import MAPS as MAP_PATHS  # noqa: E402

import repair5g549_common as g549  # noqa: E402
from run_repair5g561_materialization_contract import claims, sha256_file, stable_uid  # noqa: E402


ROUND = "phase5p5_repair5g561"
ADDITIVE = "repair5g59_additive_fallback"
G556 = "g556_c063174"
SCENARIO_DIR = Path(f"outputs/tmp/{ROUND}_replay_ladder_scenarios")
SCENARIO_METADATA = Path(f"outputs/reports/{ROUND}_replay_ladder_scenario_generation.json")
LOG_DIR = Path(f"outputs/logs/{ROUND}_replay_ladder")
PLAN_CSV = Path(f"outputs/tables/{ROUND}_replay_ladder_plan.csv")
REGISTRY_CSV = Path(f"outputs/tables/{ROUND}_replay_ladder_registry.csv")
RESULTS_CSV = Path(f"outputs/tables/{ROUND}_replay_ladder_results.csv")
RAW_RESULTS_CSV = Path(f"outputs/tables/{ROUND}_replay_ladder_results.raw.csv")
CORRECTED_PAIRS = Path(f"outputs/tables/{ROUND}_corrected_g560_replay_pairs.csv")
CORRECTED_SUMMARY = Path(f"outputs/reports/{ROUND}_corrected_g560_replay_summary.json")
CORRECTED_MD = Path(f"outputs/reports/{ROUND}_corrected_g560_replay.md")
ARCH_PAIRS = Path(f"outputs/tables/{ROUND}_architecture_replay_pairs.csv")
ARCH_SUMMARY = Path(f"outputs/reports/{ROUND}_architecture_replay_summary.json")
ARCH_MD = Path(f"outputs/reports/{ROUND}_architecture_replay.md")
HARD_NEGATIVE = Path(f"outputs/tables/{ROUND}_hard_negative_acquisition.csv")


@dataclass
class ReplayContext:
    context_id: str
    map: str
    map_family: str
    agents: int
    seed: int
    budget_ms: int
    base_time_limit_sec: float
    ltm_max_iterations: int
    horizon_id: str
    graph: GraphData | None = None
    graph_with_traffic: GraphData | None = None
    assignment: dict[str, Any] | None = None
    feature_row: dict[str, Any] | None = None
    scenario_sha256: str = ""
    physical_map_sha256: str = ""


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


def fingerprint(theta: dict[str, Any]) -> str:
    return "|".join(f"{key}={value}" for key, value in expected_cpp_params(theta).items())


def base_theta() -> dict[str, Any]:
    row = {col: float(value) for col, value in zip(THETA_NUMERIC_COLUMNS, BASELINE_G556)}
    row.update(mode_columns("flow_shield"))
    return clamp_theta_row(row)


def build_contexts(limit: int = 100) -> list[ReplayContext]:
    maps = [
        ("random-32-32-20", "random"),
        ("maze-32-32-4", "maze"),
        ("warehouse-10-20-10-2-1", "warehouse"),
    ]
    agents = [32, 64, 96]
    budgets = [
        (500, 0.50, 2),
        (1000, 1.00, 3),
        (2000, 2.00, 4),
        (3000, 3.00, 4),
    ]
    contexts: list[ReplayContext] = []
    for idx in range(limit):
        map_name, family = maps[idx % len(maps)]
        agent_count = agents[(idx // len(maps)) % len(agents)]
        budget_ms, base_sec, ltm_iters = budgets[(idx // (len(maps) * len(agents))) % len(budgets)]
        seed = 9100 + idx
        horizon = f"g561_replay_{family}_a{agent_count}_b{budget_ms}_i{ltm_iters}"
        context_id = stable_uid("g561_replay_context", map_name, agent_count, seed, budget_ms, ltm_iters)
        contexts.append(
            ReplayContext(
                context_id=context_id,
                map=map_name,
                map_family=family,
                agents=agent_count,
                seed=seed,
                budget_ms=budget_ms,
                base_time_limit_sec=base_sec,
                ltm_max_iterations=ltm_iters,
                horizon_id=horizon,
            )
        )
    return contexts


def prepare_replay_scenarios(contexts: list[ReplayContext]) -> None:
    prepare_scenarios(
        root=ROOT,
        source_scenario_dir=resolve(DEFAULT_SOURCE_SCENARIO_DIR),
        scenario_dir=resolve(SCENARIO_DIR),
        scenario_metadata=resolve(SCENARIO_METADATA),
        maps=sorted({ctx.map for ctx in contexts}),
        agent_counts=sorted({ctx.agents for ctx in contexts}),
        instance_ids=sorted({ctx.seed for ctx in contexts}),
    )


def parse_scenario_assignment(path: Path, agents: int, graph: GraphData) -> dict[str, Any]:
    starts: list[tuple[int, int]] = []
    goals: list[tuple[int, int]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("version"):
            continue
        cells = line.split()
        if len(cells) < 8:
            continue
        starts.append((int(cells[4]), int(cells[5])))
        goals.append((int(cells[6]), int(cells[7])))
        if len(starts) >= agents:
            break
    distances = [abs(s[0] - g[0]) + abs(s[1] - g[1]) for s, g in zip(starts, goals)]
    od = []
    for s, g, dist in zip(starts, goals, distances):
        od.append(
            [
                s[0] / max(1, graph.width - 1),
                s[1] / max(1, graph.height - 1),
                g[0] / max(1, graph.width - 1),
                g[1] / max(1, graph.height - 1),
                dist / max(1, graph.width + graph.height),
                float(s[0] < g[0]) - float(s[0] > g[0]),
            ]
        )
    return {
        "requested_agent_count": agents,
        "encoded_agent_count": len(starts),
        "represented_agent_mass": len(starts),
        "all_agent_mass_preserved": len(starts) == agents,
        "assignment_capacity_limited": len(starts) < agents,
        "unique_start_count": len(set(starts)),
        "unique_goal_count": len(set(goals)),
        "assignment_valid": len(starts) == agents and len(set(starts)) == len(starts) and len(set(goals)) == len(goals),
        "starts": starts,
        "goals": goals,
        "od_tokens": np.asarray(od, dtype=np.float32),
        "shortest_path_distance_mean": float(np.mean(distances)) if distances else 0.0,
        "shortest_path_distance_max": int(max(distances)) if distances else 0,
    }


def enrich_contexts(contexts: list[ReplayContext]) -> list[ReplayContext]:
    for ctx in contexts:
        scen = scenario_path(resolve(SCENARIO_DIR), ctx.map, ctx.seed)
        graph = build_graph({"map": ctx.map})
        assignment = parse_scenario_assignment(scen, ctx.agents, graph)
        traffic = compute_traffic_prior(graph, assignment)
        graph_t = GraphData(
            topology_id=graph.topology_id,
            map_name=graph.map_name,
            width=graph.width,
            height=graph.height,
            cells=graph.cells,
            node_features=graph.node_features,
            edge_index=graph.edge_index,
            edge_features=traffic["edge_features"],
            hashes=graph.hashes,
            component_count=graph.component_count,
            physical_free_cell_count=graph.physical_free_cell_count,
        )
        density = ctx.agents / max(1, graph.physical_free_cell_count)
        feature_row = {
            "context_id": ctx.context_id,
            "map": ctx.map,
            "map_family": ctx.map_family,
            "agent_count": ctx.agents,
            "agents": ctx.agents,
            "seed": ctx.seed,
            "nominal_budget_ms": ctx.budget_ms,
            "budget_ms": ctx.budget_ms,
            "base_time_limit_sec": ctx.base_time_limit_sec,
            "ltm_max_iterations": ctx.ltm_max_iterations,
            "requested_agent_count": assignment["requested_agent_count"],
            "encoded_OD_token_count": assignment["encoded_agent_count"],
            "represented_agent_mass": assignment["represented_agent_mass"],
            "represented_flow_mass": traffic["summary"]["expected_edge_use_total"],
            "physical_free_cell_count": graph.physical_free_cell_count,
            "agent_density": density,
            **traffic["summary"],
        }
        ctx.graph = graph
        ctx.graph_with_traffic = graph_t
        ctx.assignment = assignment
        ctx.feature_row = feature_row
        ctx.scenario_sha256 = sha256_file(scen)
        ctx.physical_map_sha256 = physical_hashes({"map": ctx.map})["physical_map_sha256"]
    return contexts


def move_graph_batch(batch: Any, device: str) -> Any:
    from gcst.graph_encoder import GraphBatch

    return GraphBatch(
        batch.node_features.to(device),
        batch.edge_index.to(device),
        batch.edge_features.to(device),
        batch.batch_index.to(device),
        batch.num_graphs,
    )


def infer_g560(contexts: list[ReplayContext], device: str) -> list[dict[str, Any]]:
    import torch

    outputs: list[dict[str, Any]] = []
    model_paths = [
        ("G0_direct_actor", Path("artifacts/models/gcst/g560_direct_actor_g0_560.pt")),
        ("G1_direct_actor_aux_critic", Path("artifacts/models/gcst/g560_direct_actor_g1_561.pt")),
    ]
    x = np.stack([actor_features(ctx.feature_row or {}) for ctx in contexts]).astype(np.float32)
    for method, rel_path in model_paths:
        path = resolve(rel_path)
        bundle = torch.load(path, map_location=device, weights_only=False)
        actor = DirectGCSTActor(len(bundle.get("feature_schema", ACTOR_FEATURE_SCHEMA)), int(bundle.get("hidden_dim", 128)), float(bundle.get("residual_scale", 0.35))).module().to(device)
        actor.load_state_dict(bundle["actor_state_dict"])
        actor.eval()
        normalizer = ActorNormalizer(np.asarray(bundle["feature_mean"], dtype=np.float32), np.asarray(bundle["feature_std"], dtype=np.float32))
        xs = normalizer.transform(x)
        with torch.no_grad():
            theta = actor(torch.tensor(xs, dtype=torch.float32, device=device)).detach().cpu().numpy()
        for ctx, values in zip(contexts, theta):
            row = {col: float(values[idx]) for idx, col in enumerate(THETA_NUMERIC_COLUMNS)}
            row.update(mode_columns("flow_shield"))
            outputs.append(
                {
                    "replay_phase": "corrected_g560_scalar_replay",
                    "method": method,
                    "model_path": str(rel_path),
                    "context_id": ctx.context_id,
                    **clamp_theta_row(row),
                }
            )
    return outputs


def infer_g561(contexts: list[ReplayContext], device: str) -> list[dict[str, Any]]:
    import torch

    training = json.loads(resolve(f"outputs/reports/{ROUND}_training_summary.json").read_text(encoding="utf-8"))
    wanted = {"F1", "F4", "F6", "F7"}
    variants = [row for row in training.get("variants", []) if row.get("variant_id") in wanted]
    outputs: list[dict[str, Any]] = []
    graphs = [ctx.graph_with_traffic for ctx in contexts]
    assignments = [ctx.assignment for ctx in contexts]
    scalars = torch.tensor(np.stack([scalar_features(ctx.feature_row or {}) for ctx in contexts]), dtype=torch.float32, device=device)
    graph_batch = move_graph_batch(make_graph_batch(graphs), device)
    od_tokens, od_mask = pad_od_tokens(assignments)
    od_tokens = od_tokens.to(device)
    od_mask = od_mask.to(device)
    for variant in variants:
        path = resolve(str(variant["model_path"]))
        checkpoint = torch.load(path, map_location=device, weights_only=False)
        residual_scale = 0.35 if bool(checkpoint.get("critic_training_only")) else 0.30
        model = GoalAwareDualChannelActor(
            hidden_dim=int(checkpoint.get("hidden_dim", 32)),
            use_graph=bool(checkpoint.get("uses_graph")),
            use_paired_od=bool(checkpoint.get("uses_paired_od")),
            use_c0f0=bool(checkpoint.get("uses_c0f0")),
            residual_scale=residual_scale,
        ).module().to(device)
        model.load_state_dict(checkpoint["actor_state_dict"])
        model.eval()
        with torch.no_grad():
            theta = model(graph_batch, od_tokens, od_mask, scalars).detach().cpu().numpy()
        method = f"{variant['variant_id']}_{variant['variant_name']}"
        for ctx, values in zip(contexts, theta):
            row = {col: float(values[idx]) for idx, col in enumerate(THETA_NUMERIC_COLUMNS)}
            row.update(mode_columns("flow_shield"))
            outputs.append(
                {
                    "replay_phase": "architecture_replay",
                    "method": method,
                    "model_path": str(variant["model_path"]),
                    "context_id": ctx.context_id,
                    **clamp_theta_row(row),
                }
            )
    return outputs


def build_plan_and_registry(contexts: list[ReplayContext], theta_rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    context_by_id = {ctx.context_id: ctx for ctx in contexts}
    plan_rows: list[dict[str, Any]] = []
    registry_rows: list[dict[str, Any]] = [
        {
            "candidate_id": G556,
            "generated_theta_uid": "",
            "registry_role": "g561_replay_g556_baseline",
            **base_theta(),
            **claims(),
        }
    ]

    def add_plan(ctx: ReplayContext, *, role: str, candidate_id: str, method: str, replay_phase: str, theta: dict[str, Any] | None, model_path: str = "") -> None:
        index = len(plan_rows)
        generated_uid = "" if theta is None else generated_theta_uid(model_path or method, ctx.context_id, [theta[col] for col in THETA_NUMERIC_COLUMNS])
        scenario_sha = ctx.scenario_sha256
        identity = stable_uid("g561_replay_identity", ctx.context_id, scenario_sha, candidate_id, generated_uid, replay_phase)
        plan_rows.append(
            {
                "plan_row_id": f"g561_replay_{index:07d}",
                "replay_phase": replay_phase,
                "context_id": ctx.context_id,
                "g561_instance_uid": ctx.context_id,
                "g561_evaluation_uid": stable_uid("g561_replay_eval", ctx.context_id, candidate_id),
                "g561_identity_digest": identity,
                "g561_scenario_sha256": scenario_sha,
                "g561_physical_map_sha256": ctx.physical_map_sha256,
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
                "expected_updateparams_fingerprint": "" if theta is None else fingerprint(theta),
                **({col: theta.get(col, "") for col in THETA_COLUMNS} if theta else {}),
                **claims(),
            }
        )

    for ctx in contexts:
        add_plan(ctx, role="additive_ltm", candidate_id=ADDITIVE, method="paper_faithful_additive_ltm", replay_phase="baseline", theta=None)
        add_plan(ctx, role=G556, candidate_id=G556, method="g556_c063174", replay_phase="baseline", theta=base_theta())

    for theta_row in theta_rows:
        ctx = context_by_id[str(theta_row["context_id"])]
        uid = stable_uid("g561_replay_theta", theta_row["method"], ctx.context_id, {col: theta_row[col] for col in THETA_NUMERIC_COLUMNS})
        candidate_id = f"g561_{str(theta_row['method']).lower().replace('+', '_').replace('-', '_')}_{uid[:12]}"
        role = f"generated_theta::{candidate_id}"
        theta = clamp_theta_row(theta_row)
        registry_rows.append(
            {
                "candidate_id": candidate_id,
                "generated_theta_uid": generated_theta_uid(theta_row.get("model_path", ""), ctx.context_id, [theta[col] for col in THETA_NUMERIC_COLUMNS]),
                "registry_role": "g561_replay_actor_theta",
                "replay_phase": theta_row["replay_phase"],
                "method": theta_row["method"],
                **{col: theta.get(col, "") for col in THETA_COLUMNS},
                **claims(),
            }
        )
        add_plan(
            ctx,
            role=role,
            candidate_id=candidate_id,
            method=str(theta_row["method"]),
            replay_phase=str(theta_row["replay_phase"]),
            theta=theta,
            model_path=str(theta_row.get("model_path", "")),
        )
    write_rows(PLAN_CSV, plan_rows)
    write_rows(REGISTRY_CSV, registry_rows)
    return plan_rows, registry_rows


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


def audit_results(rows: list[dict[str, Any]], plan_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
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
            "g561_instance_uid",
            "g561_evaluation_uid",
            "g561_identity_digest",
            "g561_scenario_sha256",
            "g561_physical_map_sha256",
            "generated_theta_uid",
            "expected_updateparams_fingerprint",
            "model_path",
        ]:
            row[key] = plan.get(key, row.get(key, ""))
        for col in THETA_COLUMNS:
            row[col] = plan.get(col, row.get(col, ""))
        parsed = parse_updateparams_fingerprint(row.get("updateparams_fingerprint", ""))
        is_actor = str(row.get("role", "")).startswith("generated_theta::")
        is_g556 = row.get("materialized_method") == G556
        is_additive = row.get("materialized_method") == ADDITIVE
        fp_match = True
        fp_mismatch = ""
        if is_actor or is_g556:
            fp_match, mismatches = compare_theta_to_fingerprint(row.get("updateparams_fingerprint", ""), plan or row, tolerance=1.0e-9)
            fp_mismatch = ";".join(mismatches)
        elif is_additive:
            fp_match = parsed.get("force_additive") == "1" and parsed.get("enable_dual_channel") == "0"
            fp_mismatch = "" if fp_match else "additive_fingerprint"
        scen = scenario_path(resolve(SCENARIO_DIR), str(row.get("map")), int(float(row.get("seed", 0))))
        scenario_actual = sha256_file(scen)
        identity_actual = stable_uid(
            "g561_replay_identity",
            row.get("g561_instance_uid", ""),
            row.get("g561_scenario_sha256", ""),
            row.get("candidate_id", ""),
            row.get("generated_theta_uid", ""),
            row.get("replay_phase", ""),
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
                "fulltheta_fingerprint_mismatched_fields": fp_mismatch,
                "scenario_sha256_actual": scenario_actual,
                "scenario_sha256_match": bool(scenario_actual) and scenario_actual == row.get("g561_scenario_sha256", ""),
                "identity_digest_actual": identity_actual,
                "identity_retained": bool(row.get("g561_identity_digest", "")) and identity_actual == row.get("g561_identity_digest", ""),
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


def float_value(row: dict[str, Any], key: str) -> float | None:
    try:
        value = float(row.get(key, ""))
    except Exception:
        return None
    return value if math.isfinite(value) else None


def build_pairs(rows: list[dict[str, Any]], *, phase: str, baseline_id: str = G556) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str, str, str], dict[str, dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(group_key(row), {})[str(row.get("materialized_method", ""))] = row
    pairs = []
    for key, by_method in sorted(grouped.items()):
        baseline = by_method.get(baseline_id)
        additive = by_method.get(ADDITIVE)
        if not baseline:
            continue
        for method, candidate in sorted(by_method.items()):
            if method in {baseline_id, ADDITIVE}:
                continue
            if candidate.get("replay_phase") != phase:
                continue
            cand_success = solver_success(candidate)
            base_success = solver_success(baseline)
            cand_ratio = solver_ratio(candidate)
            base_ratio = solver_ratio(baseline)
            additive_ratio = solver_ratio(additive or {}) if additive else None
            both_success = cand_success and base_success
            quality_delta = cand_ratio - base_ratio if both_success and cand_ratio is not None and base_ratio is not None else math.nan
            additive_delta = cand_ratio - additive_ratio if cand_success and additive and solver_success(additive) and cand_ratio is not None and additive_ratio is not None else math.nan
            runtime = float_value(candidate, "probe_runtime_ms")
            base_runtime = float_value(baseline, "probe_runtime_ms")
            pairs.append(
                {
                    "replay_phase": phase,
                    "map": key[0],
                    "agents": key[1],
                    "seed": key[2],
                    "budget_ms": key[3],
                    "horizon_id": key[4],
                    "g561_instance_uid": candidate.get("g561_instance_uid", ""),
                    "g561_evaluation_uid": candidate.get("g561_evaluation_uid", ""),
                    "g561_identity_digest": candidate.get("g561_identity_digest", ""),
                    "g561_scenario_sha256": candidate.get("g561_scenario_sha256", ""),
                    "theta_id": method,
                    "method": candidate.get("sampling_policy", ""),
                    "model_path": candidate.get("model_path", ""),
                    "baseline_id": baseline_id,
                    "candidate_success": cand_success,
                    "baseline_success": base_success,
                    "success_regression": bool(base_success and not cand_success),
                    "success_gain": bool(cand_success and not base_success),
                    "both_success": both_success,
                    "both_fail": bool((not cand_success) and (not base_success)),
                    "quality_delta_vs_g556": quality_delta,
                    "quality_delta_vs_additive": additive_delta,
                    "candidate_recognized": candidate.get("candidate_recognized_bool", False),
                    "fingerprint_match": candidate.get("fulltheta_fingerprint_match_strict", False),
                    "scenario_hash_match": candidate.get("scenario_sha256_match", False),
                    "identity_retained": candidate.get("identity_retained", False),
                    "cost_finite": math.isfinite(quality_delta) if both_success else bool(cand_success != base_success),
                    "candidate_runtime_ms": candidate.get("probe_runtime_ms", ""),
                    "baseline_runtime_ms": baseline.get("probe_runtime_ms", ""),
                    "runtime_overhead_ms": (runtime - base_runtime) if runtime is not None and base_runtime is not None else "",
                    "candidate_expanded_nodes": candidate.get("expanded_nodes", ""),
                    "baseline_expanded_nodes": baseline.get("expanded_nodes", ""),
                    "candidate_low_level_pibt_calls": candidate.get("low_level_pibt_calls", ""),
                    "baseline_low_level_pibt_calls": baseline.get("low_level_pibt_calls", ""),
                    **{col: candidate.get(col, "") for col in THETA_NUMERIC_COLUMNS},
                    **claims(),
                }
            )
    return pairs


def mean_ci(values: list[float]) -> tuple[float | None, float | None, float | None]:
    values = [v for v in values if math.isfinite(v)]
    if not values:
        return None, None, None
    rng = random.Random(561)
    means = []
    for _ in range(1000):
        sample = [values[rng.randrange(len(values))] for _ in values]
        means.append(sum(sample) / len(sample))
    means.sort()
    return sum(values) / len(values), means[int(0.025 * len(means))], means[int(0.975 * len(means)) - 1]


def summarize_pairs(pairs: list[dict[str, Any]], rows: list[dict[str, Any]], phase: str) -> dict[str, Any]:
    actor_rows = [row for row in rows if row.get("replay_phase") == phase and boolish(row.get("is_actor_row"))]
    finite = []
    for pair in pairs:
        try:
            value = float(pair.get("quality_delta_vs_g556", "nan"))
        except Exception:
            value = math.nan
        if math.isfinite(value):
            finite.append(value)
    mean, ci_low, ci_high = mean_ci(finite)
    runtime_overheads = [float(pair["runtime_overhead_ms"]) for pair in pairs if str(pair.get("runtime_overhead_ms", "")).strip()]
    expanded = [float(pair["candidate_expanded_nodes"]) for pair in pairs if str(pair.get("candidate_expanded_nodes", "")).strip()]
    pibt = [float(pair["candidate_low_level_pibt_calls"]) for pair in pairs if str(pair.get("candidate_low_level_pibt_calls", "")).strip()]
    by_method = []
    for method in sorted({str(pair.get("method", "")) for pair in pairs}):
        group = [pair for pair in pairs if pair.get("method") == method]
        values = []
        for pair in group:
            try:
                v = float(pair.get("quality_delta_vs_g556", "nan"))
            except Exception:
                v = math.nan
            if math.isfinite(v):
                values.append(v)
        m, lo, hi = mean_ci(values)
        by_method.append(
            {
                "method": method,
                "pairs": len(group),
                "success_regressions": sum(boolish(pair.get("success_regression")) for pair in group),
                "success_gains": sum(boolish(pair.get("success_gain")) for pair in group),
                "both_success": sum(boolish(pair.get("both_success")) for pair in group),
                "both_fail": sum(boolish(pair.get("both_fail")) for pair in group),
                "mean_quality_delta_vs_g556": m,
                "bootstrap_ci_low": lo,
                "bootstrap_ci_high": hi,
                "better": sum(v < 0 for v in values),
                "worse": sum(v > 0 for v in values),
                "ties": sum(v == 0 for v in values),
            }
        )
    return {
        "schema_version": f"{ROUND}_{phase}_summary_v1",
        "decision": f"g561_{phase}_executed_exact_materialization" if actor_rows and all(boolish(row.get("fulltheta_fingerprint_match_strict")) for row in actor_rows) else f"g561_{phase}_materialization_invalid_continue_repair",
        "total_planned_rows": len([row for row in read_rows(PLAN_CSV) if row.get("replay_phase") in {phase, "baseline"}]),
        "executed_rows": len([row for row in rows if row.get("replay_phase") in {phase, "baseline"}]),
        "valid_scenario_rows": sum(boolish(row.get("scenario_sha256_match")) for row in actor_rows),
        "actor_rows": len(actor_rows),
        "recognized_actor_rows": sum(boolish(row.get("candidate_recognized_bool")) for row in actor_rows),
        "exact_fingerprint_rows": sum(boolish(row.get("fulltheta_fingerprint_match_strict")) for row in actor_rows),
        "materialization_invalid_rows": sum(not boolish(row.get("candidate_recognized_bool")) or not boolish(row.get("fulltheta_fingerprint_match_strict")) for row in actor_rows),
        "identity_complete_rows": sum(boolish(row.get("identity_retained")) for row in actor_rows),
        "replay_pairs": len(pairs),
        "success_regressions": sum(boolish(pair.get("success_regression")) for pair in pairs),
        "success_gains": sum(boolish(pair.get("success_gain")) for pair in pairs),
        "both_success": sum(boolish(pair.get("both_success")) for pair in pairs),
        "both_fail": sum(boolish(pair.get("both_fail")) for pair in pairs),
        "mean_quality_delta_vs_g556": mean,
        "median_quality_delta_vs_g556": statistics.median(finite) if finite else None,
        "bootstrap_ci_low": ci_low,
        "bootstrap_ci_high": ci_high,
        "better": sum(v < 0 for v in finite),
        "worse": sum(v > 0 for v in finite),
        "ties": sum(v == 0 for v in finite),
        "mean_runtime_overhead_ms": (sum(runtime_overheads) / len(runtime_overheads)) if runtime_overheads else None,
        "mean_candidate_expanded_nodes": (sum(expanded) / len(expanded)) if expanded else None,
        "mean_candidate_low_level_pibt_calls": (sum(pibt) / len(pibt)) if pibt else None,
        "by_method": by_method,
        **claims(),
    }


def write_reports(corrected_pairs: list[dict[str, Any]], arch_pairs: list[dict[str, Any]], rows: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any]]:
    corrected = summarize_pairs(corrected_pairs, rows, "corrected_g560_scalar_replay")
    arch = summarize_pairs(arch_pairs, rows, "architecture_replay")
    write_rows(CORRECTED_PAIRS, corrected_pairs)
    write_rows(ARCH_PAIRS, arch_pairs)
    write_json(CORRECTED_SUMMARY, corrected)
    write_json(ARCH_SUMMARY, arch)
    regressions = [pair for pair in [*corrected_pairs, *arch_pairs] if boolish(pair.get("success_regression"))]
    write_rows(HARD_NEGATIVE, regressions[:200] or [{"decision": "g561_replay_ladder_no_success_regressions_observed", **claims()}])
    for path, summary, title in [
        (CORRECTED_MD, corrected, "Repair5G.5.61 Corrected G5.60 Scalar Replay"),
        (ARCH_MD, arch, "Repair5G.5.61 Architecture Replay"),
    ]:
        write_text(
            path,
            f"# {title}\n\n"
            f"- decision: `{summary['decision']}`\n"
            f"- executed rows: `{summary['executed_rows']}`\n"
            f"- actor rows: `{summary['actor_rows']}`\n"
            f"- recognized actor rows: `{summary['recognized_actor_rows']}`\n"
            f"- exact fingerprint rows: `{summary['exact_fingerprint_rows']}`\n"
            f"- identity complete rows: `{summary['identity_complete_rows']}`\n"
            f"- replay pairs: `{summary['replay_pairs']}`\n"
            f"- success regressions: `{summary['success_regressions']}`\n"
            f"- success gains: `{summary['success_gains']}`\n"
            f"- mean quality delta vs g556: `{summary['mean_quality_delta_vs_g556']}`\n\n"
            "All Phase5.5, Phase6, runtime, learned-policy, and AAAI claims remain closed.\n",
        )
    return corrected, arch


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
    parser = argparse.ArgumentParser(description="Run G5.61 corrected scalar and architecture replay ladder.")
    parser.add_argument("--contexts", type=int, default=100)
    parser.add_argument("--binary", type=Path, default=Path("build/phase1a-batch/phase1a_batch"))
    parser.add_argument("--device", default="auto")
    parser.add_argument("--max-workers", type=int, default=4)
    parser.add_argument("--plan-only", action="store_true")
    args = parser.parse_args(argv)

    import torch

    device = args.device if args.device != "auto" else ("cuda" if torch.cuda.is_available() else "cpu")
    contexts = build_contexts(args.contexts)
    prepare_replay_scenarios(contexts)
    contexts = enrich_contexts(contexts)
    theta_rows = [*infer_g560(contexts, device), *infer_g561(contexts, device)]
    plan_rows, _registry_rows = build_plan_and_registry(contexts, theta_rows)
    if args.plan_only:
        print(json.dumps({"decision": "g561_replay_ladder_plan_created", "contexts": len(contexts), "planned_rows": len(plan_rows)}, sort_keys=True))
        return 0

    binary = solver_binary(args.binary)
    if not binary.exists():
        write_json(ARCH_SUMMARY, {"decision": "g561_replay_ladder_blocked_missing_solver_binary", "binary": str(binary), **claims()})
        print(json.dumps({"decision": "g561_replay_ladder_blocked_missing_solver_binary", "binary": str(binary)}, sort_keys=True))
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
        manifest_prefix="g561_replay_ladder",
        row_prefix="g561_replay",
        execution_mode="g561_replay_ladder_real_solver_row",
    )
    rows = audit_results(read_rows(RESULTS_CSV), plan_rows)
    write_rows(RESULTS_CSV, rows)
    corrected_pairs = build_pairs(rows, phase="corrected_g560_scalar_replay")
    arch_pairs = build_pairs(rows, phase="architecture_replay")
    corrected, arch = write_reports(corrected_pairs, arch_pairs, rows)
    print(json.dumps({"decision": "g561_replay_ladder_executed", "corrected": corrected["decision"], "architecture": arch["decision"], "rows": len(rows)}, sort_keys=True))
    return 0 if corrected["materialization_invalid_rows"] == 0 and arch["materialization_invalid_rows"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
