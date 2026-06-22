from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

import run_repair5g567_strict_pipeline as g567  # noqa: E402
from gcst.dual_stream_graph_actor import DualStreamGoalAwareActor, architecture_from_id  # noqa: E402


PHASE = "gate2_bounded_large_agent_pilot"
SUMMARY_NAME = f"{g567.ROUND}_{PHASE}_summary.json"
REPORT_NAME = f"{g567.ROUND}_{PHASE}.md"
CONTEXT_MANIFEST_NAME = f"{g567.ROUND}_{PHASE}_contexts.csv"


def configure_isolated_temp_paths() -> None:
    g567.TMP_ROOT = g567.OUTPUT_ROOT / "tmp" / f"{g567.ROUND}_{PHASE}_scenario_bank"
    g567.REPLAY_SCENARIO_DIR = g567.OUTPUT_ROOT / "tmp" / f"{g567.ROUND}_{PHASE}_replay_scenarios"


def ensure_output_dirs() -> None:
    for path in [
        g567.TABLES,
        g567.REPORTS,
        g567.LOGS,
        g567.MODEL_DIR,
        g567.resolve(g567.TMP_ROOT),
        g567.resolve(g567.REPLAY_SCENARIO_DIR),
    ]:
        path.mkdir(parents=True, exist_ok=True)


def requested_tiers(text: str) -> list[int]:
    tiers = [int(token.strip()) for token in text.split(",") if token.strip()]
    if not tiers:
        raise ValueError("--agent-tiers must contain at least one integer tier")
    return tiers


def select_large_rows(rows: list[dict[str, Any]], tiers: list[int]) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    family_counts: Counter[str] = Counter()
    for tier in tiers:
        candidates = [row for row in rows if int(g567.number(row.get("agent_count"), 0)) == tier]
        candidates.sort(
            key=lambda row: (
                family_counts[str(row.get("map_family", ""))],
                int("empty" in str(row.get("map_family", "")).lower()),
                -float(g567.number(row.get("base_time_limit_sec"), 0.0)),
                -int(g567.number(row.get("nominal_budget_ms"), 0)),
                -int(g567.number(row.get("width"), 0)) * int(g567.number(row.get("height"), 0)),
                str(row.get("map", "")),
            )
        )
        if not candidates:
            raise RuntimeError(f"no generated context for requested tier {tier}")
        row = dict(candidates[0])
        selected.append(row)
        family_counts[str(row.get("map_family", ""))] += 1
    return selected


def prepare_rows_for_gate2(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    replay_dir = g567.resolve(g567.REPLAY_SCENARIO_DIR)
    prepared: list[dict[str, Any]] = []
    for idx, row in enumerate(rows):
        row = dict(row)
        row["split"] = "GATE2_PILOT"
        row["blind_locked"] = False
        row["g567_dataset_row_id"] = f"g567_gate2_pilot_{idx:04d}"
        replay = g567.copy_for_replay(row, g567.resolve(row["raw_scenario_path"]), replay_dir)
        row["replay_scenario_path"] = g567.rel(replay)
        row["replay_scenario_sha256"] = g567.sha256_file(replay)
        prepared.append(row)
    return prepared


def materialize_contexts(rows: list[dict[str, Any]]) -> tuple[list[g567.G567Context], list[dict[str, Any]]]:
    g567.update_remote_map_registries(g567.resolve(g567.TMP_ROOT) / "maps")
    contexts: list[g567.G567Context] = []
    timings: list[dict[str, Any]] = []
    for row in rows:
        started = time.perf_counter()
        ctx = g567.context_from_manifest_row(row)
        elapsed = time.perf_counter() - started
        timings.append(
            {
                "g567_dataset_row_id": row.get("g567_dataset_row_id", ""),
                "map": row.get("map", ""),
                "map_family": row.get("map_family", ""),
                "agent_count": row.get("agent_count", ""),
                "elapsed_sec": elapsed,
                "materialized": ctx is not None,
            }
        )
        if ctx is None:
            raise RuntimeError(f"context materialization failed for {row.get('g567_dataset_row_id')}")
        contexts.append(ctx)
    return contexts, timings


def g556_theta_row(ctx: g567.G567Context) -> dict[str, Any]:
    theta = {col: float(g567.BASELINE_G556[idx]) for idx, col in enumerate(g567.THETA_NUMERIC_COLUMNS)}
    theta.update(g567.mode_columns("flow_shield"))
    return {
        "phase": PHASE,
        "context_id": ctx.dataset_row_id,
        "g567_evaluation_uid": ctx.evaluation_uid,
        "variant_id": "GATE2_G556_REGISTRY_SMOKE",
        "variant_name": "gate2_fulltheta_registry_smoke_not_trained_actor",
        "seed": "0",
        "method": "gate2_fulltheta_registry_g556_smoke",
        "model_path": "gate2_pilot_no_trained_checkpoint",
        **g567.clamp_theta_row(theta),
    }


def run_a5_bf16_smoke(ctx: g567.G567Context, *, device: str, hidden_dim: int) -> dict[str, Any]:
    import torch

    if device == "auto":
        device = "cuda" if torch.cuda.is_available() else "cpu"
    arch = architecture_from_id("A5")
    model = DualStreamGoalAwareActor(
        hidden_dim=hidden_dim,
        use_cross_attention=arch.use_cross_attention,
        safe_subspace=arch.safe_subspace,
        field_group_trust=arch.field_group_trust,
        od_perceiver=arch.od_perceiver,
        graph_local_layers=arch.graph_local_layers,
        graph_global_layers=arch.graph_global_layers,
        heads=arch.heads,
        latent_tokens=arch.latent_tokens,
    ).module().to(device)
    model.train()
    if str(device).startswith("cuda"):
        torch.cuda.reset_peak_memory_stats()
    graph_batch = g567.move_graph_batch(g567.make_graph_batch([ctx.graph_with_traffic]), device)
    od_tokens, od_mask = g567.pad_od_tokens([ctx.assignment])
    scalar_x = torch.tensor(np.stack([g567.scalar_features(ctx.feature_row)]), dtype=torch.float32, device=device)
    started = time.perf_counter()
    if str(device).startswith("cuda"):
        with torch.autocast(device_type="cuda", dtype=torch.bfloat16):
            theta = model(graph_batch, od_tokens.to(device), od_mask.to(device), scalar_x)
            loss = theta.sum()
    else:
        theta = model(graph_batch, od_tokens.to(device), od_mask.to(device), scalar_x)
        loss = theta.sum()
    loss.backward()
    elapsed = time.perf_counter() - started
    return {
        "name": "gate2_a5_bf16_large_context_forward_backward",
        "passed": True,
        "device": str(device),
        "gpu_name": torch.cuda.get_device_name(0) if str(device).startswith("cuda") else "",
        "cuda_bf16_autocast": bool(str(device).startswith("cuda")),
        "agent_count": ctx.agents,
        "map": ctx.map,
        "map_family": ctx.map_family,
        "graph_nodes": len(ctx.graph_with_traffic.cells),
        "graph_edges": int(ctx.graph_with_traffic.edge_index.shape[1]) if ctx.graph_with_traffic.edge_index.size else 0,
        "od_tokens": int(od_tokens.shape[1]),
        "hidden_dim": hidden_dim,
        "latent_tokens": arch.latent_tokens,
        "od_perceiver": arch.od_perceiver,
        "graph_global_layers": arch.graph_global_layers,
        "full_node_quadratic_graph_attention_disabled": arch.graph_global_layers == 0,
        "elapsed_sec": elapsed,
        "samples_per_sec": float(1.0 / max(elapsed, 1.0e-9)),
        "theta_shape": list(theta.shape),
        "backward_executed": True,
        "cuda_peak_memory_bytes": int(torch.cuda.max_memory_allocated()) if str(device).startswith("cuda") else 0,
    }


def write_report(summary: dict[str, Any]) -> None:
    g567.write_text(
        g567.REPORTS / REPORT_NAME,
        "# Repair5G.5.67 Gate-2 Bounded Pilot\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- generated contexts: `{summary['generated_contexts']}`\n"
        f"- selected contexts: `{summary['selected_contexts']}`\n"
        f"- requested agent tiers: `{summary['requested_agent_tiers']}`\n"
        f"- selected budgets ms: `{summary['selected_budget_ms']}`\n"
        f"- selected map families: `{summary['selected_map_families']}`\n"
        f"- blind split constructed: `{summary['blind_split_constructed']}`\n"
        f"- replay planned rows: `{summary.get('replay_summary', {}).get('planned_rows')}`\n"
        f"- replay exact materialization rate: `{summary.get('replay_summary', {}).get('exact_materialization_rate')}`\n"
        f"- A5 BF16 elapsed sec: `{summary.get('a5_bf16_smoke', {}).get('elapsed_sec')}`\n"
        f"- A5 BF16 CUDA peak bytes: `{summary.get('a5_bf16_smoke', {}).get('cuda_peak_memory_bytes')}`\n\n"
        "This pilot intentionally does not build or access a final blind panel, does not launch 100k context generation, "
        "does not acquire million-row solver labels, and does not start a long training campaign.\n",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run bounded Gate-2 pilot after G5.67 Gate-1 passes.")
    parser.add_argument("--context-count", type=int, default=76)
    parser.add_argument("--seed", type=int, default=2567)
    parser.add_argument("--agent-tiers", default="2000,3000")
    parser.add_argument("--binary", type=Path, default=Path("build/phase1a-batch/phase1a_batch"))
    parser.add_argument("--max-workers", type=int, default=1)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--actor-hidden-dim", type=int, default=256)
    parser.add_argument("--margin", type=float, default=0.043)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(argv)

    configure_isolated_temp_paths()
    ensure_output_dirs()
    os.environ.setdefault("REPAIR5G_STREAM_RESULT_CSV", "1")
    os.environ.setdefault("REPAIR5G_SKIP_AGGREGATE_JSONL", "1")
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    os.environ.setdefault("MKL_NUM_THREADS", "1")
    os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

    tiers = requested_tiers(args.agent_tiers)
    started = time.perf_counter()
    audit_rows, manifest_rows, meta = g567.make_generated_contexts(args.context_count, args.seed, g567.resolve(g567.TMP_ROOT))
    selected_rows = prepare_rows_for_gate2(select_large_rows(manifest_rows, tiers))
    if any(str(row.get("split", "")).upper() == "BLIND" or g567.boolish(row.get("blind_locked")) for row in selected_rows):
        raise RuntimeError("Gate-2 pilot must not construct or use a BLIND split")
    g567.write_rows(g567.TABLES / CONTEXT_MANIFEST_NAME, selected_rows)
    contexts, materialization_timings = materialize_contexts(selected_rows)
    theta_rows = [g556_theta_row(ctx) for ctx in contexts]
    replay_summary = g567.run_replay_phase(
        PHASE,
        contexts,
        theta_rows,
        binary=args.binary,
        max_workers=max(1, int(args.max_workers)),
        overwrite=bool(args.overwrite),
        margin=float(args.margin),
        plan_only=False,
    )
    largest_ctx = max(contexts, key=lambda ctx: ctx.agents)
    a5_smoke = run_a5_bf16_smoke(largest_ctx, device=args.device, hidden_dim=args.actor_hidden_dim)
    exact_rate = float(g567.number(replay_summary.get("exact_materialization_rate"), 0.0))
    scenario_rate = float(g567.number(replay_summary.get("scenario_hash_match_rate"), 0.0))
    identity_rate = float(g567.number(replay_summary.get("identity_retention_rate"), 0.0))
    recognized_rate = float(g567.number(replay_summary.get("candidate_recognized_rate"), 0.0))
    forbidden_actions = {
        "full_100k_generation_launched": False,
        "million_row_solver_acquisition_launched": False,
        "forty_eight_hour_training_launched": False,
        "blind_panel_constructed_or_accessed": False,
        "astar_v1_primary_enabled": False,
    }
    pass_conditions = {
        "requested_tiers_materialized": sorted(ctx.agents for ctx in contexts) == sorted(tiers),
        "no_blind_split_constructed": True,
        "a5_bf16_smoke_passed": bool(a5_smoke.get("passed")),
        "replay_materialized": replay_summary.get("decision") == "g567_three_tier_replay_materialized",
        "exact_materialization_rate_one": exact_rate == 1.0,
        "candidate_recognized_rate_one": recognized_rate == 1.0,
        "scenario_hash_match_rate_one": scenario_rate == 1.0,
        "identity_retention_rate_one": identity_rate == 1.0,
        "all_forbidden_actions_false": not any(forbidden_actions.values()),
    }
    summary = {
        "schema_version": f"{g567.ROUND}_{PHASE}_summary_v1",
        "decision": "gate2_bounded_pilot_pass" if all(pass_conditions.values()) else "gate2_bounded_pilot_failed",
        "elapsed_sec": time.perf_counter() - started,
        "generated_contexts": len(manifest_rows),
        "generator_attempts": meta.get("attempts"),
        "audit_rows": len(audit_rows),
        "selected_contexts": len(contexts),
        "requested_agent_tiers": tiers,
        "selected_agent_tiers": [ctx.agents for ctx in contexts],
        "selected_budget_ms": [ctx.budget_ms for ctx in contexts],
        "selected_map_families": dict(Counter(ctx.map_family for ctx in contexts)),
        "selected_maps": [ctx.map for ctx in contexts],
        "blind_split_constructed": False,
        "context_manifest": g567.rel(g567.TABLES / CONTEXT_MANIFEST_NAME),
        "context_materialization_timings": materialization_timings,
        "replay_summary": replay_summary,
        "a5_bf16_smoke": a5_smoke,
        "pass_conditions": pass_conditions,
        "forbidden_actions": forbidden_actions,
        **g567.claims(),
    }
    g567.write_json(g567.REPORTS / SUMMARY_NAME, summary)
    write_report(summary)
    print(json.dumps({"decision": summary["decision"], "elapsed_sec": summary["elapsed_sec"]}, sort_keys=True))
    return 0 if summary["decision"] == "gate2_bounded_pilot_pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
