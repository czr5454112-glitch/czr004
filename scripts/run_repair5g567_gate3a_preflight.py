from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

import run_repair5g567_strict_pipeline as g567  # noqa: E402


PHASE = "gate3a_true_a5_checkpoint_smoke"
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


def parse_agent_tiers(text: str) -> list[int]:
    tiers = [int(token.strip()) for token in text.split(",") if token.strip()]
    if len(set(tiers)) < 3:
        raise ValueError("Gate-3A requires at least three distinct agent tiers")
    return tiers


def true_a5_checkpoint_audit(payload: dict[str, Any], path: Path) -> dict[str, Any]:
    variant_id = g567.model_kind_from_payload(payload, path)
    artifact_type = str(payload.get("artifact_type", ""))
    has_state = isinstance(payload.get("actor_state_dict"), dict) and bool(payload.get("actor_state_dict"))
    trained_marker = bool(payload.get("labelv54_training")) or artifact_type == "phase5p5_repair5g567_labelv54_direct_actor"
    forbidden_smoke = any(
        token in str(value).upper()
        for token in ["G556_REGISTRY_SMOKE", "NO_TRAINED_CHECKPOINT", "GATE2_G556"]
        for value in [path, payload.get("variant_id", ""), payload.get("variant_name", ""), payload.get("artifact_type", "")]
    )
    return {
        "checkpoint_path": g567.rel(path),
        "checkpoint_sha256": g567.sha256_file(path),
        "variant_id": variant_id,
        "artifact_type": artifact_type,
        "has_actor_state_dict": has_state,
        "trained_actor_marker": trained_marker,
        "forbidden_g556_or_untrained_smoke_marker": forbidden_smoke,
        "decision": "true_a5_checkpoint" if variant_id == "A5" and has_state and trained_marker and not forbidden_smoke else "not_true_a5_checkpoint",
    }


def load_true_a5_checkpoint(path: Path) -> tuple[Path, dict[str, Any], dict[str, Any]]:
    import torch

    resolved = g567.resolve(path)
    if not resolved.exists():
        raise FileNotFoundError(resolved)
    payload = torch.load(resolved, map_location="cpu", weights_only=False)
    if not isinstance(payload, dict):
        raise RuntimeError(f"A5 checkpoint payload is not a dict: {resolved}")
    audit = true_a5_checkpoint_audit(payload, resolved)
    if audit["decision"] != "true_a5_checkpoint":
        raise RuntimeError(f"Gate-3A requires a real trained A5 checkpoint, got {audit}")
    return resolved, payload, audit


def select_gate3a_rows(rows: list[dict[str, Any]], tiers: list[int], contexts_per_tier: int) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    family_counts: Counter[str] = Counter()
    for tier in tiers:
        candidates = [row for row in rows if int(g567.number(row.get("agent_count"), 0)) == tier]
        if len(candidates) < contexts_per_tier:
            raise RuntimeError(f"not enough generated contexts for tier {tier}: {len(candidates)} < {contexts_per_tier}")
        candidates.sort(
            key=lambda row: (
                family_counts[str(row.get("map_family", ""))],
                -int(g567.number(row.get("nominal_budget_ms"), 0)),
                -float(g567.number(row.get("base_time_limit_sec"), 0.0)),
                str(row.get("map_family", "")),
                str(row.get("map", "")),
                str(row.get("g567_instance_uid", "")),
            )
        )
        for row in candidates[:contexts_per_tier]:
            selected.append(dict(row))
            family_counts[str(row.get("map_family", ""))] += 1
    return selected


def prepare_rows_for_gate3a(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    replay_dir = g567.resolve(g567.REPLAY_SCENARIO_DIR)
    prepared: list[dict[str, Any]] = []
    for idx, row in enumerate(rows):
        row = dict(row)
        row["split"] = "GATE3A_PREFLIGHT"
        row["blind_locked"] = False
        row["g567_dataset_row_id"] = f"g567_gate3a_a5_{idx:05d}"
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


def gate3a_pass_conditions(
    *,
    checkpoint_audit: dict[str, Any],
    contexts: list[g567.G567Context],
    theta_rows: list[dict[str, Any]],
    replay_summary: dict[str, Any],
    source_state: dict[str, Any],
    forbidden_actions: dict[str, bool],
) -> dict[str, bool]:
    families = {ctx.map_family for ctx in contexts}
    tiers = {ctx.agents for ctx in contexts}
    return {
        "source_state_clean": source_state.get("decision") == "g567_source_state_clean",
        "true_a5_checkpoint": checkpoint_audit.get("decision") == "true_a5_checkpoint",
        "at_least_32_contexts": len(contexts) >= 32,
        "several_agent_tiers": len(tiers) >= 3,
        "several_map_families": len(families) >= 2,
        "all_contexts_non_blind": all(ctx.split == "GATE3A_PREFLIGHT" for ctx in contexts),
        "a5_inference_rows_equal_contexts": len(theta_rows) == len(contexts),
        "a5_inference_variant_only": {str(row.get("variant_id", "")).upper() for row in theta_rows} == {"A5"},
        "no_g556_registry_smoke_theta": not any("G556" in json.dumps(row, sort_keys=True).upper() or "REGISTRY_SMOKE" in json.dumps(row, sort_keys=True).upper() for row in theta_rows),
        "replay_materialized": replay_summary.get("decision") == "g567_three_tier_replay_materialized",
        "exact_materialization_rate_one": float(g567.number(replay_summary.get("exact_materialization_rate"), 0.0)) == 1.0,
        "candidate_recognized_rate_one": float(g567.number(replay_summary.get("candidate_recognized_rate"), 0.0)) == 1.0,
        "scenario_hash_match_rate_one": float(g567.number(replay_summary.get("scenario_hash_match_rate"), 0.0)) == 1.0,
        "identity_retention_rate_one": float(g567.number(replay_summary.get("identity_retention_rate"), 0.0)) == 1.0,
        "no_process_hard_timeouts": int(g567.number(replay_summary.get("process_hard_timeout_rows"), 0)) == 0,
        "all_forbidden_actions_false": not any(forbidden_actions.values()),
    }


def write_report(summary: dict[str, Any]) -> None:
    g567.write_text(
        g567.REPORTS / REPORT_NAME,
        "# Repair5G.5.67 Gate-3A True A5 Checkpoint Smoke\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- source state: `{summary.get('source_state', {}).get('decision')}`\n"
        f"- checkpoint: `{summary.get('checkpoint_audit', {}).get('checkpoint_path')}`\n"
        f"- checkpoint variant: `{summary.get('checkpoint_audit', {}).get('variant_id')}`\n"
        f"- selected contexts: `{summary['selected_contexts']}`\n"
        f"- selected agent tiers: `{summary['selected_agent_tiers']}`\n"
        f"- selected map families: `{summary['selected_map_families']}`\n"
        f"- A5 theta rows: `{summary['a5_theta_rows']}`\n"
        f"- replay decision: `{summary.get('replay_summary', {}).get('decision')}`\n"
        f"- process hard timeout rows: `{summary.get('replay_summary', {}).get('process_hard_timeout_rows')}`\n\n"
        "This Gate-3A preflight does not construct or access the final blind panel and does not unlock full-scale generation, "
        "million-row acquisition, or 48h training.\n",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Gate-3A true A5 checkpoint end-to-end smoke.")
    parser.add_argument("--a5-checkpoint", type=Path, required=True)
    parser.add_argument("--context-count", type=int, default=128)
    parser.add_argument("--contexts-per-tier", type=int, default=8)
    parser.add_argument("--agent-tiers", default="32,256,1000,3000")
    parser.add_argument("--seed", type=int, default=3567)
    parser.add_argument("--binary", type=Path, default=Path("build/phase1a-batch/phase1a_batch"))
    parser.add_argument("--max-workers", type=int, default=1)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--margin", type=float, default=0.043)
    parser.add_argument("--expected-head", default=os.environ.get("G567_EXPECTED_HEAD", ""))
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(argv)

    configure_isolated_temp_paths()
    ensure_output_dirs()
    os.environ.setdefault("REPAIR5G_STREAM_RESULT_CSV", "1")
    os.environ.setdefault("REPAIR5G_SKIP_AGGREGATE_JSONL", "1")
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    os.environ.setdefault("MKL_NUM_THREADS", "1")
    os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

    started = time.perf_counter()
    source_state = g567.write_source_state(args.expected_head)
    if source_state.get("decision") != "g567_source_state_clean":
        summary = {
            "schema_version": f"{g567.ROUND}_{PHASE}_summary_v1",
            "decision": "gate3a_blocked_source_state_fail_closed",
            "source_state": source_state,
            **g567.claims(),
        }
        g567.write_json(g567.REPORTS / SUMMARY_NAME, summary)
        write_report({**summary, "selected_contexts": 0, "selected_agent_tiers": [], "selected_map_families": {}, "a5_theta_rows": 0})
        print(json.dumps({"decision": summary["decision"]}, sort_keys=True))
        return 2

    checkpoint_path, _payload, checkpoint_audit = load_true_a5_checkpoint(args.a5_checkpoint)
    tiers = parse_agent_tiers(args.agent_tiers)
    required_contexts = len(tiers) * max(1, int(args.contexts_per_tier))
    if required_contexts < 32:
        raise RuntimeError(f"Gate-3A requires at least 32 contexts, got {required_contexts}")
    audit_rows, manifest_rows, meta = g567.make_generated_contexts(max(args.context_count, required_contexts), args.seed, g567.resolve(g567.TMP_ROOT))
    selected_rows = prepare_rows_for_gate3a(select_gate3a_rows(manifest_rows, tiers, max(1, int(args.contexts_per_tier))))
    if any(str(row.get("split", "")).upper() == "BLIND" or g567.boolish(row.get("blind_locked")) for row in selected_rows):
        raise RuntimeError("Gate-3A preflight must not construct or use a BLIND split")
    g567.write_rows(g567.TABLES / CONTEXT_MANIFEST_NAME, selected_rows)
    contexts, materialization_timings = materialize_contexts(selected_rows)
    theta_rows = g567.infer_checkpoint_thetas(contexts, [checkpoint_path], device=args.device, batch_size=max(1, int(args.batch_size)), phase=PHASE)
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
    forbidden_actions = {
        "full_100k_generation_launched": False,
        "million_row_solver_acquisition_launched": False,
        "forty_eight_hour_training_launched": False,
        "final_blind_panel_constructed_or_accessed": False,
        "astar_v1_primary_enabled": False,
    }
    pass_conditions = gate3a_pass_conditions(
        checkpoint_audit=checkpoint_audit,
        contexts=contexts,
        theta_rows=theta_rows,
        replay_summary=replay_summary,
        source_state=source_state,
        forbidden_actions=forbidden_actions,
    )
    summary = {
        "schema_version": f"{g567.ROUND}_{PHASE}_summary_v1",
        "decision": "gate3a_true_a5_checkpoint_smoke_pass" if all(pass_conditions.values()) else "gate3a_true_a5_checkpoint_smoke_failed",
        "elapsed_sec": time.perf_counter() - started,
        "source_state": source_state,
        "checkpoint_audit": checkpoint_audit,
        "generated_contexts": len(manifest_rows),
        "generator_attempts": meta.get("attempts"),
        "audit_rows": len(audit_rows),
        "selected_contexts": len(contexts),
        "selected_agent_tiers": sorted({ctx.agents for ctx in contexts}),
        "selected_map_families": dict(Counter(ctx.map_family for ctx in contexts)),
        "selected_maps": sorted({ctx.map for ctx in contexts}),
        "context_manifest": g567.rel(g567.TABLES / CONTEXT_MANIFEST_NAME),
        "context_materialization_timings": materialization_timings,
        "a5_theta_rows": len(theta_rows),
        "a5_theta_methods": sorted({str(row.get("method", "")) for row in theta_rows}),
        "replay_summary": replay_summary,
        "pass_conditions": pass_conditions,
        "forbidden_actions": forbidden_actions,
        **g567.claims(),
    }
    g567.write_json(g567.REPORTS / SUMMARY_NAME, summary)
    write_report(summary)
    print(json.dumps({"decision": summary["decision"], "elapsed_sec": summary["elapsed_sec"]}, sort_keys=True))
    return 0 if summary["decision"] == "gate3a_true_a5_checkpoint_smoke_pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
