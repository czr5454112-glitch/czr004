from __future__ import annotations

import argparse
import csv
import json
import math
import os
import random
import re
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
import run_repair5g561_replay_ladder as ladder  # noqa: E402
from gcst.generated_theta_audit import generated_theta_uid  # noqa: E402
from gcst.goal_aware_actor import GoalAwareDualChannelActor, make_graph_batch, pad_od_tokens, scalar_features  # noqa: E402
from gcst.graph_data import GraphData, build_graph  # noqa: E402
from gcst.map_hash import free_cells, physical_hashes, synthetic_grid  # noqa: E402
from gcst.theta_schema import THETA_NUMERIC_COLUMNS, clamp_theta_row  # noqa: E402
from gcst.traffic_prior import compute_traffic_prior  # noqa: E402
from generate_repair5g561_valid_scenario_bank import (  # noqa: E402
    BUDGET_PROFILES,
    build_assignment,
    sha256_file,
    write_map,
    write_scenario,
)
from repair5g2_common import scenario_path  # noqa: E402
from repair5g5_common import DEFAULT_SOURCE_SCENARIO_DIR, MAP_PATHS, prepare_scenarios  # noqa: E402
from run_repair5g561_materialization_contract import claims, stable_uid  # noqa: E402


ROUND = "phase5p5_repair5g561"
PHASE = "development_replay"
SCENARIO_DIR = Path(f"outputs/tmp/{ROUND}_development_replay_scenarios")
SCENARIO_METADATA = Path(f"outputs/reports/{ROUND}_development_replay_scenario_generation.json")
MAP_DIR = Path(f"outputs/tmp/{ROUND}_development_replay_maps")
LOG_DIR = Path(f"outputs/logs/{ROUND}_development_replay")
PLAN_CSV = Path(f"outputs/tables/{ROUND}_development_replay_plan.csv")
REGISTRY_CSV = Path(f"outputs/tables/{ROUND}_development_replay_registry.csv")
RESULTS_CSV = Path(f"outputs/tables/{ROUND}_development_replay_results.csv")
RAW_RESULTS_CSV = Path(f"outputs/tables/{ROUND}_development_replay_results.raw.csv")
PAIR_CSV = Path(f"outputs/tables/{ROUND}_development_replay_pairs.csv")
SELECTION_CSV = Path(f"outputs/tables/{ROUND}_development_replay_selection.csv")
BY_STRATUM_CSV = Path(f"outputs/tables/{ROUND}_dev_replay_by_stratum.csv")
SUMMARY_JSON = Path(f"outputs/reports/{ROUND}_dev_replay_summary.json")
REPORT_MD = Path(f"outputs/reports/{ROUND}_development_replay.md")
HARD_NEGATIVE_CSV = Path(f"outputs/tables/{ROUND}_hard_negative_acquisition.csv")
HARD_NEGATIVE_SUMMARY = Path(f"outputs/reports/{ROUND}_hard_negative_acquisition_summary.json")
HARD_NEGATIVE_MD = Path(f"outputs/reports/{ROUND}_hard_negative_acquisition.md")
VALID_MANIFEST = Path(f"outputs/tables/{ROUND}_valid_instance_manifest.csv")
SPLIT_MANIFEST = Path(f"outputs/tables/{ROUND}_physical_map_split_manifest.csv")
ARCH_SUMMARY = Path(f"outputs/reports/{ROUND}_architecture_replay_summary.json")
TRAINING_SUMMARY = Path(f"outputs/reports/{ROUND}_training_summary.json")


@dataclass
class DevelopmentContext:
    context_id: str
    map: str
    map_family: str
    agents: int
    seed: int
    budget_ms: int
    base_time_limit_sec: float
    ltm_max_iterations: int
    horizon_id: str
    source_manifest_uid: str
    scenario_bank_source: str
    development_split_physical_map_sha256: str
    start_goal_regime: str = ""
    width: int = 0
    height: int = 0
    graph: GraphData | None = None
    graph_with_traffic: GraphData | None = None
    assignment: dict[str, Any] | None = None
    feature_row: dict[str, Any] | None = None
    scenario_sha256: str = ""
    physical_map_sha256: str = ""


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
    ladder.write_rows(path, rows)


def write_json(path: str | Path, data: dict[str, Any]) -> None:
    ladder.write_json(path, data)


def write_text(path: str | Path, text: str) -> None:
    ladder.write_text(path, text)


def boolish(value: Any) -> bool:
    return ladder.boolish(value)


def number(value: Any, default: float = 0.0) -> float:
    try:
        out = float(value)
    except Exception:
        return default
    return out if math.isfinite(out) else default


def parse_dimensions(map_name: str) -> tuple[int, int]:
    match = re.search(r"(\d+)x(\d+)", map_name)
    if match:
        return int(match.group(1)), int(match.group(2))
    square = re.search(r"-(\d+)(?:$|-)", map_name)
    if square:
        side = int(square.group(1))
        return side, side
    return 32, 32


def budget_profile(index: int) -> tuple[int, float, int]:
    budget_ms, base_sec, iters = BUDGET_PROFILES[index % len(BUDGET_PROFILES)]
    return int(budget_ms), float(base_sec), int(iters)


def split_lookup() -> dict[str, str]:
    return {row.get("physical_map_sha256", ""): row.get("split", "") for row in read_rows(SPLIT_MANIFEST)}


def eligible_manifest_rows() -> list[dict[str, str]]:
    splits = split_lookup()
    rows = []
    for row in read_rows(VALID_MANIFEST):
        if splits.get(row.get("physical_map_sha256", "")) != "development-heldout":
            continue
        source = row.get("scenario_bank_source", "")
        if source == "generated_g561_component_aware" or row.get("map", "") in MAP_PATHS:
            rows.append(row)
    return rows


def round_robin(rows: list[dict[str, str]], limit: int) -> list[dict[str, str]]:
    buckets: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        buckets[row.get("map_family", "")].append(row)
    for bucket in buckets.values():
        bucket.sort(key=lambda row: (row.get("map", ""), int(number(row.get("solver_seed"), 0))))
    out: list[dict[str, str]] = []
    families = sorted(buckets)
    while len(out) < limit and any(buckets.values()):
        for family in families:
            if buckets[family]:
                out.append(buckets[family].pop(0))
                if len(out) >= limit:
                    break
    return out


def select_development_contexts(limit: int = 400) -> list[DevelopmentContext]:
    rows = eligible_manifest_rows()
    generated = [row for row in rows if row.get("scenario_bank_source") == "generated_g561_component_aware"]
    retained = [row for row in rows if row.get("scenario_bank_source") != "generated_g561_component_aware"]
    selected_rows = generated[:limit]
    if len(selected_rows) < limit:
        selected_rows.extend(round_robin(retained, limit - len(selected_rows)))
    selected_rows = selected_rows[:limit]
    contexts: list[DevelopmentContext] = []
    for idx, row in enumerate(selected_rows):
        profile_budget, profile_base, profile_iters = budget_profile(idx)
        budget_ms = int(number(row.get("nominal_budget_ms"), profile_budget) or profile_budget)
        base_sec = float(number(row.get("base_time_limit_sec"), profile_base) or profile_base)
        iters = int(number(row.get("ltm_max_iterations"), profile_iters) or profile_iters)
        seed = int(number(row.get("solver_seed"), 0))
        agents = int(number(row.get("pair_count"), 0))
        map_name = row.get("map", "")
        width, height = parse_dimensions(map_name)
        context_id = stable_uid(
            "g561_development_context",
            row.get("g561_instance_uid", ""),
            map_name,
            seed,
            agents,
            budget_ms,
            iters,
            idx,
        )
        contexts.append(
            DevelopmentContext(
                context_id=context_id,
                map=map_name,
                map_family=row.get("map_family", ""),
                agents=agents,
                seed=seed,
                budget_ms=budget_ms,
                base_time_limit_sec=base_sec,
                ltm_max_iterations=iters,
                horizon_id=f"g561_dev_{row.get('map_family', 'unknown')}_a{agents}_b{budget_ms}_i{iters}",
                source_manifest_uid=row.get("g561_instance_uid", ""),
                scenario_bank_source=row.get("scenario_bank_source", ""),
                development_split_physical_map_sha256=row.get("physical_map_sha256", ""),
                start_goal_regime=row.get("start_goal_regime", ""),
                width=width,
                height=height,
                physical_map_sha256=row.get("physical_map_sha256", ""),
            )
        )
    return contexts


def register_development_maps(contexts: list[DevelopmentContext]) -> None:
    map_dir = resolve(MAP_DIR)
    map_dir.mkdir(parents=True, exist_ok=True)
    for ctx in contexts:
        if ctx.map in MAP_PATHS and resolve(MAP_PATHS[ctx.map]).exists():
            continue
        grid = synthetic_grid(ctx.map, ctx.width, ctx.height)
        path = map_dir / f"{ctx.map}.map"
        write_map(path, grid)
        MAP_PATHS[ctx.map] = str(path.relative_to(ROOT)).replace("\\", "/")


def materialize_manifest_scenarios(contexts: list[DevelopmentContext]) -> None:
    scenario_dir = resolve(SCENARIO_DIR)
    scenario_dir.mkdir(parents=True, exist_ok=True)
    for ctx in contexts:
        if ctx.scenario_bank_source != "generated_g561_component_aware" or not ctx.start_goal_regime:
            continue
        path = scenario_path(scenario_dir, ctx.map, ctx.seed)
        if path.exists():
            continue
        grid = synthetic_grid(ctx.map, ctx.width, ctx.height)
        assignment = build_assignment(grid, ctx.width, ctx.height, ctx.agents, ctx.start_goal_regime, ctx.seed)
        write_scenario(path, ctx.map, ctx.width, ctx.height, assignment)


def prepare_missing_scenarios(contexts: list[DevelopmentContext]) -> None:
    register_development_maps(contexts)
    materialize_manifest_scenarios(contexts)
    for map_name in sorted({ctx.map for ctx in contexts}):
        group = [ctx for ctx in contexts if ctx.map == map_name]
        prepare_scenarios(
            root=ROOT,
            source_scenario_dir=resolve(DEFAULT_SOURCE_SCENARIO_DIR),
            scenario_dir=resolve(SCENARIO_DIR),
            scenario_metadata=resolve(SCENARIO_METADATA),
            maps=[map_name],
            agent_counts=sorted({ctx.agents for ctx in group}),
            instance_ids=sorted({ctx.seed for ctx in group}),
        )


def enrich_contexts(contexts: list[DevelopmentContext]) -> list[DevelopmentContext]:
    for ctx in contexts:
        scen = scenario_path(resolve(SCENARIO_DIR), ctx.map, ctx.seed)
        graph = build_graph({"map": ctx.map, "width": ctx.width, "height": ctx.height})
        assignment = ladder.parse_scenario_assignment(scen, ctx.agents, graph)
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
        ctx.graph = graph
        ctx.graph_with_traffic = graph_t
        ctx.assignment = assignment
        ctx.feature_row = {
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
            "start_goal_regime": ctx.start_goal_regime,
            **traffic["summary"],
        }
        ctx.scenario_sha256 = sha256_file(scen)
        ctx.physical_map_sha256 = ctx.development_split_physical_map_sha256 or physical_hashes(
            {"map": ctx.map, "width": ctx.width, "height": ctx.height}
        )["physical_map_sha256"]
    return contexts


def select_best_two_actor_variants(*, write_selection: bool = True) -> list[dict[str, Any]]:
    arch = json.loads(resolve(ARCH_SUMMARY).read_text(encoding="utf-8"))
    training = json.loads(resolve(TRAINING_SUMMARY).read_text(encoding="utf-8"))
    variants_by_id = {row.get("variant_id"): row for row in training.get("variants", [])}
    ranked = []
    for row in arch.get("by_method", []):
        method = str(row.get("method", ""))
        variant_id = method.split("_", 1)[0]
        if variant_id not in {"F1", "F4", "F6", "F7"}:
            continue
        ranked.append(
            {
                "variant_id": variant_id,
                "method": method,
                "validation_mean_quality_delta_vs_g556": row.get("mean_quality_delta_vs_g556"),
                "validation_better": row.get("better"),
                "validation_worse": row.get("worse"),
                "validation_success_regressions": row.get("success_regressions"),
                "selected_for_development_replay": False,
                **variants_by_id.get(variant_id, {}),
                **claims(),
            }
        )
    ranked.sort(
        key=lambda row: (
            int(number(row.get("validation_success_regressions"), 9999)),
            float(number(row.get("validation_mean_quality_delta_vs_g556"), 9999.0)),
            -int(number(row.get("validation_better"), 0)),
            str(row.get("variant_id")),
        )
    )
    selected = ranked[:2]
    for row in selected:
        row["selected_for_development_replay"] = True
    if write_selection:
        write_rows(SELECTION_CSV, ranked)
    return selected


def infer_selected_g561(contexts: list[DevelopmentContext], selected: list[dict[str, Any]], device: str) -> list[dict[str, Any]]:
    import torch

    outputs: list[dict[str, Any]] = []
    graphs = [ctx.graph_with_traffic for ctx in contexts]
    assignments = [ctx.assignment for ctx in contexts]
    scalars = torch.tensor(np.stack([scalar_features(ctx.feature_row or {}) for ctx in contexts]), dtype=torch.float32, device=device)
    graph_batch = ladder.move_graph_batch(make_graph_batch(graphs), device)
    od_tokens, od_mask = pad_od_tokens(assignments)
    od_tokens = od_tokens.to(device)
    od_mask = od_mask.to(device)
    for variant in selected:
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
            row.update(ladder.mode_columns("flow_shield"))
            outputs.append(
                {
                    "replay_phase": PHASE,
                    "method": method,
                    "model_path": str(variant["model_path"]),
                    "context_id": ctx.context_id,
                    **clamp_theta_row(row),
                }
            )
    return outputs


def configure_ladder_paths() -> None:
    ladder.SCENARIO_DIR = SCENARIO_DIR
    ladder.SCENARIO_METADATA = SCENARIO_METADATA
    ladder.LOG_DIR = LOG_DIR
    ladder.PLAN_CSV = PLAN_CSV
    ladder.REGISTRY_CSV = REGISTRY_CSV
    ladder.RESULTS_CSV = RESULTS_CSV
    ladder.RAW_RESULTS_CSV = RAW_RESULTS_CSV


def annotate_plan(plan_rows: list[dict[str, Any]], contexts: list[DevelopmentContext], selected: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id = {ctx.context_id: ctx for ctx in contexts}
    selected_ids = ",".join(row.get("variant_id", "") for row in selected)
    for row in plan_rows:
        ctx = by_id.get(str(row.get("context_id", "")))
        if not ctx:
            continue
        row.update(
            {
                "development_split": "development-heldout",
                "development_split_physical_map_sha256": ctx.development_split_physical_map_sha256,
                "source_manifest_uid": ctx.source_manifest_uid,
                "scenario_bank_source": ctx.scenario_bank_source,
                "start_goal_regime": ctx.start_goal_regime,
                "frozen_actor_selection": selected_ids,
            }
        )
    write_rows(PLAN_CSV, plan_rows)
    return plan_rows


def build_plan_and_registry(contexts: list[DevelopmentContext], selected: list[dict[str, Any]], device: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    configure_ladder_paths()
    theta_rows = infer_selected_g561(contexts, selected, device)
    plan_rows, registry_rows = ladder.build_plan_and_registry(contexts, theta_rows)
    return annotate_plan(plan_rows, contexts, selected), registry_rows


def context_meta(contexts: list[DevelopmentContext]) -> dict[str, DevelopmentContext]:
    return {ctx.context_id: ctx for ctx in contexts}


def family_for_pair(pair: dict[str, Any], rows_by_uid: dict[str, DevelopmentContext]) -> str:
    ctx = rows_by_uid.get(str(pair.get("g561_instance_uid", "")))
    return ctx.map_family if ctx else ""


def theta_distance(pair: dict[str, Any]) -> float:
    base = ladder.base_theta()
    total = 0.0
    for col in THETA_NUMERIC_COLUMNS:
        total += (number(pair.get(col), base[col]) - float(base[col])) ** 2
    return math.sqrt(total)


def hard_negative_acquisition(pairs: list[dict[str, Any]], contexts: list[DevelopmentContext]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    by_uid = context_meta(contexts)
    enriched = []
    for pair in pairs:
        row = dict(pair)
        row["map_family"] = family_for_pair(pair, by_uid)
        row["theta_l2_distance_to_g556"] = theta_distance(pair)
        try:
            row["quality_delta_float"] = float(pair.get("quality_delta_vs_g556", "nan"))
        except Exception:
            row["quality_delta_float"] = math.nan
        enriched.append(row)

    finite = [row for row in enriched if math.isfinite(float(row.get("quality_delta_float", math.nan)))]
    positive = [row for row in finite if float(row["quality_delta_float"]) > 0]
    regressions = [row for row in enriched if boolish(row.get("success_regression"))]
    by_family: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in finite:
        by_family[str(row.get("map_family", ""))].append(row)
    worst_families = sorted(
        (
            (sum(float(row["quality_delta_float"]) for row in rows) / max(1, len(rows)), family, rows)
            for family, rows in by_family.items()
        ),
        reverse=True,
    )

    rows: list[dict[str, Any]] = []

    def add(category: str, source: dict[str, Any], rank: int, reason: str) -> None:
        rows.append(
            {
                "acquisition_category": category,
                "rank": rank,
                "reason": reason,
                "replay_phase": PHASE,
                "map": source.get("map", ""),
                "map_family": source.get("map_family", ""),
                "agents": source.get("agents", ""),
                "seed": source.get("seed", ""),
                "budget_ms": source.get("budget_ms", ""),
                "horizon_id": source.get("horizon_id", ""),
                "theta_id": source.get("theta_id", ""),
                "method": source.get("method", ""),
                "success_regression": source.get("success_regression", ""),
                "quality_delta_vs_g556": source.get("quality_delta_vs_g556", ""),
                "quality_delta_vs_additive": source.get("quality_delta_vs_additive", ""),
                "theta_l2_distance_to_g556": source.get("theta_l2_distance_to_g556", ""),
                "candidate_runtime_ms": source.get("candidate_runtime_ms", ""),
                "candidate_expanded_nodes": source.get("candidate_expanded_nodes", ""),
                "candidate_low_level_pibt_calls": source.get("candidate_low_level_pibt_calls", ""),
                **claims(),
            }
        )

    for idx, row in enumerate(regressions[:200]):
        add("success_regression", row, idx + 1, "candidate failed where g556 succeeded")
    for idx, row in enumerate(sorted(positive, key=lambda item: float(item["quality_delta_float"]), reverse=True)[:200]):
        add("large_positive_quality_delta", row, idx + 1, "candidate solved but worse than g556 on sum-of-loss ratio")
    for family_rank, (_mean, family, family_rows) in enumerate(worst_families[:5], start=1):
        for idx, row in enumerate(sorted(family_rows, key=lambda item: float(item["quality_delta_float"]), reverse=True)[:20]):
            add("worst_map_family", row, idx + 1, f"family={family}; family_rank={family_rank}")
    for idx, row in enumerate(sorted(enriched, key=lambda item: float(item.get("theta_l2_distance_to_g556", 0.0)), reverse=True)[:200]):
        add("actor_outputs_far_from_support", row, idx + 1, "largest generated-theta distance from g556 anchor")
    f7_false_safe = [
        row
        for row in positive
        if str(row.get("method", "")).startswith("F7_") and not boolish(row.get("success_regression"))
    ]
    for idx, row in enumerate(sorted(f7_false_safe, key=lambda item: float(item["quality_delta_float"]), reverse=True)[:100]):
        add("critic_false_safe_proxy", row, idx + 1, "critic-trained actor selected a materially worse but non-regressing theta")

    if not rows:
        rows.append({"acquisition_category": "no_adverse_development_cases_observed", "reason": "no positive deltas or regressions", **claims()})

    unique_keys = {(row.get("map"), row.get("agents"), row.get("seed"), row.get("budget_ms"), row.get("theta_id")) for row in rows}
    summary = {
        "schema_version": f"{ROUND}_hard_negative_acquisition_summary_v1",
        "decision": "g561_hard_negative_acquisition_completed_no_success_regressions" if not regressions else "g561_hard_negative_acquisition_completed_with_success_regressions",
        "source_replay_phase": PHASE,
        "source_pairs": len(pairs),
        "acquisition_rows": len(rows),
        "unique_acquisition_keys": len(unique_keys),
        "success_regression_rows": len(regressions),
        "large_positive_quality_delta_source_rows": len(positive),
        "critic_false_safe_proxy_rows": len(f7_false_safe),
        "worst_family_count": len(worst_families),
        "fine_tune_completed": False,
        "next_required_gate": "fine-tune on acquired hard negatives and rerun one frozen-comparison development panel",
        **claims(),
    }
    return rows, summary


def by_stratum_rows(pairs: list[dict[str, Any]], contexts: list[DevelopmentContext]) -> list[dict[str, Any]]:
    by_uid = context_meta(contexts)
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for pair in pairs:
        grouped[(family_for_pair(pair, by_uid), str(pair.get("method", "")))].append(pair)
    rows = []
    for (family, method), group in sorted(grouped.items()):
        values = []
        for row in group:
            try:
                value = float(row.get("quality_delta_vs_g556", "nan"))
            except Exception:
                value = math.nan
            if math.isfinite(value):
                values.append(value)
        rows.append(
            {
                "stratum": family,
                "method": method,
                "pairs": len(group),
                "success_regressions": sum(boolish(row.get("success_regression")) for row in group),
                "success_gains": sum(boolish(row.get("success_gain")) for row in group),
                "mean_quality_delta_vs_g556": sum(values) / len(values) if values else "",
                "median_quality_delta_vs_g556": statistics.median(values) if values else "",
                "better": sum(value < 0 for value in values),
                "worse": sum(value > 0 for value in values),
                "ties": sum(value == 0 for value in values),
                **claims(),
            }
        )
    return rows


def write_reports(rows: list[dict[str, Any]], pairs: list[dict[str, Any]], contexts: list[DevelopmentContext]) -> dict[str, Any]:
    summary = ladder.summarize_pairs(pairs, rows, PHASE)
    summary.update(
        {
            "schema_version": f"{ROUND}_development_replay_summary_v1",
            "decision": "g561_development_replay_executed_exact_materialization"
            if summary.get("decision") == "g561_development_replay_executed_exact_materialization"
            else summary.get("decision"),
            "development_contexts": len(contexts),
            "development_physical_map_hashes": len({ctx.development_split_physical_map_sha256 for ctx in contexts}),
            "development_map_families": dict(sorted(Counter(ctx.map_family for ctx in contexts).items())),
            "development_budget_profiles": dict(sorted(Counter(str(ctx.budget_ms) for ctx in contexts).items())),
            "development_sources": dict(sorted(Counter(ctx.scenario_bank_source for ctx in contexts).items())),
        }
    )
    write_rows(PAIR_CSV, pairs)
    write_rows(BY_STRATUM_CSV, by_stratum_rows(pairs, contexts))
    write_json(SUMMARY_JSON, summary)
    hard_rows, hard_summary = hard_negative_acquisition(pairs, contexts)
    write_rows(HARD_NEGATIVE_CSV, hard_rows)
    write_json(HARD_NEGATIVE_SUMMARY, hard_summary)
    write_text(
        REPORT_MD,
        "# Repair5G.5.61 Development Replay\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- development contexts: `{summary['development_contexts']}`\n"
        f"- executed rows: `{summary['executed_rows']}`\n"
        f"- actor rows: `{summary['actor_rows']}`\n"
        f"- exact fingerprint rows: `{summary['exact_fingerprint_rows']}`\n"
        f"- materialization-invalid rows: `{summary['materialization_invalid_rows']}`\n"
        f"- physical map hashes: `{summary['development_physical_map_hashes']}`\n"
        f"- map families: `{summary['development_map_families']}`\n"
        f"- success regressions: `{summary['success_regressions']}`\n"
        f"- success gains: `{summary['success_gains']}`\n"
        f"- mean quality delta vs g556: `{summary['mean_quality_delta_vs_g556']}`\n\n"
        "The selected actors are frozen from the R2 validation ranking. This is development evidence only; Phase5.5, Phase6, runtime, learned-policy, and AAAI claims remain closed.\n",
    )
    write_text(
        HARD_NEGATIVE_MD,
        "# Repair5G.5.61 Hard-Negative Acquisition\n\n"
        f"- decision: `{hard_summary['decision']}`\n"
        f"- source pairs: `{hard_summary['source_pairs']}`\n"
        f"- acquisition rows: `{hard_summary['acquisition_rows']}`\n"
        f"- success-regression rows: `{hard_summary['success_regression_rows']}`\n"
        f"- large positive quality-delta source rows: `{hard_summary['large_positive_quality_delta_source_rows']}`\n"
        f"- critic false-safe proxy rows: `{hard_summary['critic_false_safe_proxy_rows']}`\n\n"
        "This completes acquisition from R2/R3 adverse development evidence. Fine-tuning and a rerun panel remain closed until a later gate.\n",
    )
    return summary


def solver_binary(arg: Path) -> Path:
    return ladder.solver_binary(arg)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run G5.61 development replay for frozen best-two actors.")
    parser.add_argument("--contexts", type=int, default=400)
    parser.add_argument("--binary", type=Path, default=Path("build/phase1a-batch/phase1a_batch"))
    parser.add_argument("--device", default="auto")
    parser.add_argument("--max-workers", type=int, default=4)
    parser.add_argument("--plan-only", action="store_true")
    args = parser.parse_args(argv)

    import torch

    configure_ladder_paths()
    device = args.device if args.device != "auto" else ("cuda" if torch.cuda.is_available() else "cpu")
    contexts = select_development_contexts(args.contexts)
    if not contexts:
        write_json(SUMMARY_JSON, {"decision": "g561_development_replay_blocked_no_development_contexts", **claims()})
        print(json.dumps({"decision": "g561_development_replay_blocked_no_development_contexts"}))
        return 2
    prepare_missing_scenarios(contexts)
    contexts = enrich_contexts(contexts)
    selected = select_best_two_actor_variants()
    plan_rows, _registry_rows = build_plan_and_registry(contexts, selected, device)
    if args.plan_only:
        print(
            json.dumps(
                {
                    "decision": "g561_development_replay_plan_created",
                    "contexts": len(contexts),
                    "planned_rows": len(plan_rows),
                    "selected": [row.get("variant_id") for row in selected],
                    "families": dict(sorted(Counter(ctx.map_family for ctx in contexts).items())),
                },
                sort_keys=True,
            )
        )
        return 0

    binary = solver_binary(args.binary)
    if not binary.exists():
        write_json(SUMMARY_JSON, {"decision": "g561_development_replay_blocked_missing_solver_binary", "binary": str(binary), **claims()})
        print(json.dumps({"decision": "g561_development_replay_blocked_missing_solver_binary", "binary": str(binary)}, sort_keys=True))
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
        manifest_prefix="g561_development_replay",
        row_prefix="g561_development_replay",
        execution_mode="g561_development_replay_real_solver_row",
    )
    audited = ladder.audit_results(read_rows(RESULTS_CSV), plan_rows)
    write_rows(RESULTS_CSV, audited)
    pairs = ladder.build_pairs(audited, phase=PHASE)
    summary = write_reports(audited, pairs, contexts)
    print(
        json.dumps(
            {
                "decision": summary["decision"],
                "rows": len(audited),
                "contexts": len(contexts),
                "materialization_invalid_rows": summary["materialization_invalid_rows"],
                "success_regressions": summary["success_regressions"],
            },
            sort_keys=True,
        )
    )
    return 0 if summary["materialization_invalid_rows"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
