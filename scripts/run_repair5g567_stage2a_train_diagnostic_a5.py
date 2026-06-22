from __future__ import annotations

import argparse
import hashlib
import json
import math
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


PHASE = "stage2a_diagnostic_a5"
LABEL_PHASE = "stage2a_diagnostic_a5_label_train"
SEED_PHASE = "stage2a_diagnostic_seed_actor_response"
DEFAULT_STAGE_ROOT = Path(f"outputs/tmp/{g567.ROUND}_{PHASE}")
SUMMARY_NAME = f"{g567.ROUND}_{PHASE}_summary.json"
REPORT_NAME = f"{g567.ROUND}_{PHASE}.md"
CONTEXT_MANIFEST_NAME = f"{g567.ROUND}_{PHASE}_label_train_contexts.csv"


def configure_isolated_outputs(stage_root: Path) -> None:
    stage_root = Path(stage_root)
    g567.OUTPUT_ROOT = stage_root
    g567.ARTIFACT_ROOT = stage_root / "artifacts"
    g567.TABLES = stage_root / "tables"
    g567.REPORTS = stage_root / "reports"
    g567.LOGS = stage_root / "logs"
    g567.MODEL_DIR = stage_root / "models" / "gcst"
    g567.TMP_ROOT = stage_root / "scenario_bank"
    g567.REPLAY_SCENARIO_DIR = stage_root / "replay_scenarios"
    g567.VALID_CONTEXT_MANIFEST = g567.TABLES / f"{g567.ROUND}_{PHASE}_valid_context_manifest.csv"
    g567.INVALID_QUARANTINE = g567.TABLES / f"{g567.ROUND}_{PHASE}_invalid_quarantine.csv"
    g567.SCENARIO_VALIDITY = g567.TABLES / f"{g567.ROUND}_{PHASE}_scenario_validity.csv"
    g567.SPLIT_MANIFEST = g567.TABLES / f"{g567.ROUND}_{PHASE}_physical_map_split_manifest.csv"
    g567.VALIDITY_SUMMARY = g567.REPORTS / f"{g567.ROUND}_{PHASE}_validity_summary.json"
    g567.VALIDITY_MD = g567.REPORTS / f"{g567.ROUND}_{PHASE}_validity.md"
    g567.BASELINE_REGISTRY = g567.TABLES / f"{g567.ROUND}_{PHASE}_three_tier_baseline_registry.csv"
    g567.BASELINE_REGISTRY_SUMMARY = g567.REPORTS / f"{g567.ROUND}_{PHASE}_baseline_registry_summary.json"
    g567.REPEATABILITY_SUMMARY = g567.REPORTS / f"{g567.ROUND}_{PHASE}_repeatability_summary.json"
    g567.LABELV54_CONTEXTS = g567.TABLES / f"{g567.ROUND}_{PHASE}_labelv54_contexts.csv"
    g567.LABELV54_CANDIDATES = g567.TABLES / f"{g567.ROUND}_{PHASE}_labelv54_candidates.csv"
    g567.LABELV54_REPLICATES = g567.TABLES / f"{g567.ROUND}_{PHASE}_labelv54_replicates.csv"
    g567.LABELV54_SAFE_SETS = g567.REPORTS / f"{g567.ROUND}_{PHASE}_labelv54_safe_sets.jsonl"
    g567.LABELV54_SUMMARY = g567.REPORTS / f"{g567.ROUND}_{PHASE}_labelv54_summary.json"
    g567.SOURCE_STATE = g567.REPORTS / f"{g567.ROUND}_{PHASE}_source_state.json"
    g567.ACTOR_TRAINING_MATRIX = g567.TABLES / f"{g567.ROUND}_{PHASE}_actor_training_matrix.csv"
    g567.ACTOR_GRADIENT_AUDIT = g567.TABLES / f"{g567.ROUND}_{PHASE}_actor_gradient_audit.csv"
    g567.ACTOR_TRAINING_SUMMARY = g567.REPORTS / f"{g567.ROUND}_{PHASE}_actor_training_summary.json"
    g567.OUTCOME_ENSEMBLE_SUMMARY = g567.REPORTS / f"{g567.ROUND}_{PHASE}_outcome_ensemble_summary.json"
    g567.DISTRIBUTIONAL_CRITIC_SUMMARY = g567.REPORTS / f"{g567.ROUND}_{PHASE}_distributional_critic_summary.json"
    g567.DISTRIBUTIONAL_CRITIC_PREDICTIONS = g567.TABLES / f"{g567.ROUND}_{PHASE}_distributional_critic_predictions.csv"
    g567.DISTRIBUTIONAL_CRITIC_MODEL_AUDIT = g567.TABLES / f"{g567.ROUND}_{PHASE}_distributional_critic_model_audit.csv"
    g567.SOLVER_BUDGET_AUDIT = g567.TABLES / f"{g567.ROUND}_{PHASE}_solver_budget_audit.csv"
    g567.SOLVER_BUDGET_AUDIT_SUMMARY = g567.REPORTS / f"{g567.ROUND}_{PHASE}_solver_budget_audit_summary.json"


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


def parse_tiers(text: str) -> list[int]:
    tiers = [int(token.strip()) for token in text.split(",") if token.strip()]
    if not tiers:
        raise ValueError("at least one training tier is required")
    return tiers


def select_training_rows(
    rows: list[dict[str, Any]],
    *,
    context_count: int,
    tiers: list[int],
    max_free_cells: int,
    max_area: int,
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    per_tier = max(1, math.ceil(context_count / len(tiers)))
    family_counts: Counter[str] = Counter()
    for tier in tiers:
        candidates = [
            row for row in rows
            if int(g567.number(row.get("agent_count"), 0)) == tier
            and int(g567.number(row.get("free_cells"), 0)) <= max_free_cells
            and int(g567.number(row.get("width"), 0)) * int(g567.number(row.get("height"), 0)) <= max_area
        ]
        if len(candidates) < per_tier:
            raise RuntimeError(f"not enough Stage-2A contexts for tier {tier}: {len(candidates)} < {per_tier}")
        candidates.sort(
            key=lambda row: (
                family_counts[str(row.get("map_family", ""))],
                int(g567.number(row.get("free_cells"), 0)),
                int(g567.number(row.get("width"), 0)) * int(g567.number(row.get("height"), 0)),
                str(row.get("map_source_type", "")) != "canonical_public_benchmark_map",
                str(row.get("map_family", "")),
                str(row.get("map", "")),
                str(row.get("g567_instance_uid", "")),
            )
        )
        for row in candidates[:per_tier]:
            selected.append(dict(row))
            family_counts[str(row.get("map_family", ""))] += 1
            if len(selected) >= context_count:
                return selected
    return selected[:context_count]


def scenario_source_type(row: dict[str, Any]) -> str:
    if str(row.get("map_source_type", "")) == "canonical_public_benchmark_map":
        return "czr004_derived_on_public_parent_map"
    return "czr004_synthetic_derived_scenario"


def prepare_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    replay_dir = g567.resolve(g567.REPLAY_SCENARIO_DIR)
    prepared: list[dict[str, Any]] = []
    for idx, row in enumerate(rows):
        row = dict(row)
        row["split"] = "LABEL_TRAIN"
        row["blind_locked"] = False
        row["diagnostic_only"] = True
        row["scenario_source_type"] = scenario_source_type(row)
        row["official_scenario_consumed"] = False
        row["g567_dataset_row_id"] = f"g567_stage2a_label_train_{idx:05d}"
        replay = g567.copy_for_replay(row, g567.resolve(row["raw_scenario_path"]), replay_dir)
        row["replay_scenario_path"] = g567.rel(replay)
        row["replay_scenario_sha256"] = g567.sha256_file(replay)
        prepared.append(row)
    return prepared


def materialize_contexts(rows: list[dict[str, Any]]) -> list[g567.G567Context]:
    g567.update_remote_map_registries(g567.resolve(g567.TMP_ROOT) / "maps")
    contexts: list[g567.G567Context] = []
    for row in rows:
        ctx = g567.context_from_manifest_row(row)
        if ctx is None:
            raise RuntimeError(f"Stage-2A context materialization failed: {row.get('g567_dataset_row_id')}")
        contexts.append(ctx)
    return contexts


def dataset_sha256(contexts: list[g567.G567Context], label_candidate_path: Path) -> str:
    payload = {
        "context_uids": [ctx.evaluation_uid for ctx in contexts],
        "context_identity": [
            {
                "uid": ctx.evaluation_uid,
                "map": ctx.map,
                "agents": ctx.agents,
                "scenario_sha256": ctx.scenario_sha256,
                "assignment_sha256": ctx.assignment_sha256,
                "physical_map_sha256": ctx.physical_map_sha256,
            }
            for ctx in contexts
        ],
        "labelv54_candidates_sha256": g567.sha256_file(label_candidate_path),
    }
    text = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def replay_summary_passes_stage2a_label_gate(replay_summary: dict[str, Any]) -> bool:
    return (
        replay_summary.get("decision") == "g567_three_tier_replay_materialized"
        and int(g567.number(replay_summary.get("process_hard_timeout_rows"), 0)) == 0
        and float(g567.number(replay_summary.get("exact_materialization_rate"), 0.0)) == 1.0
        and float(g567.number(replay_summary.get("candidate_recognized_rate"), 0.0)) == 1.0
        and float(g567.number(replay_summary.get("scenario_hash_match_rate"), 0.0)) == 1.0
        and float(g567.number(replay_summary.get("identity_retention_rate"), 0.0)) == 1.0
    )


def write_report(summary: dict[str, Any]) -> None:
    g567.write_text(
        g567.REPORTS / REPORT_NAME,
        "# Repair5G.5.67 Stage-2A Diagnostic A5 Training\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- checkpoint: `{summary.get('checkpoint_path', '')}`\n"
        f"- checkpoint sha256: `{summary.get('checkpoint_sha256', '')}`\n"
        f"- source state: `{summary.get('source_state', {}).get('decision')}`\n"
        f"- label-train contexts: `{summary.get('training_contexts', 0)}`\n"
        f"- candidate rows: `{summary.get('labelv54_summary', {}).get('candidates', 0)}`\n"
        f"- replay decision: `{summary.get('replay_summary', {}).get('decision')}`\n"
        f"- replay hard-timeout rows: `{summary.get('replay_summary', {}).get('process_hard_timeout_rows')}`\n"
        f"- CUDA BF16 training: `{summary.get('actor_training_row', {}).get('cuda_bf16_training')}`\n"
        f"- diagnostic_only: `{summary.get('checkpoint_metadata', {}).get('diagnostic_only')}`\n\n"
        "This artifact is diagnostic-only and makes no performance claim. It is only intended to prove the "
        "A5 checkpoint -> inference -> continuous theta -> registry -> C++ UpdateLTM path used by Gate-3A.\n",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Train a small diagnostic-only true A5 checkpoint for G5.67 Gate-3A.")
    parser.add_argument("--contexts", type=int, default=64)
    parser.add_argument("--context-pool", type=int, default=384)
    parser.add_argument("--train-agent-tiers", default="32,64,128,256")
    parser.add_argument("--max-train-free-cells", type=int, default=12000)
    parser.add_argument("--max-train-area", type=int, default=20000)
    parser.add_argument("--seed", type=int, default=567)
    parser.add_argument("--seed-checkpoint-glob", nargs="*", default=["artifacts/models/gcst/phase5p5_repair5g565_expanded_e1_seed565.pt"])
    parser.add_argument("--candidates-per-context", type=int, default=1)
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--min-epochs", type=int, default=2)
    parser.add_argument("--patience", type=int, default=3)
    parser.add_argument("--hidden-dim", type=int, default=256)
    parser.add_argument("--lr", type=float, default=2.0e-4)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--train-token-budget", type=int, default=int(os.environ.get("G567_STAGE2A_TRAIN_TOKEN_BUDGET", "12000")))
    parser.add_argument("--device", default="auto")
    parser.add_argument("--binary", type=Path, default=Path("build/phase1a-batch/phase1a_batch"))
    parser.add_argument("--max-workers", type=int, default=1)
    parser.add_argument("--margin", type=float, default=0.043)
    parser.add_argument("--stage-root", type=Path, default=DEFAULT_STAGE_ROOT)
    parser.add_argument("--expected-head", default=os.environ.get("G567_EXPECTED_HEAD", ""))
    parser.add_argument("--allow-cpu-for-tests", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(argv)

    configure_isolated_outputs(args.stage_root)
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
            "decision": "stage2a_blocked_source_state_fail_closed",
            "source_state": source_state,
            **g567.claims(),
        }
        g567.write_json(g567.REPORTS / SUMMARY_NAME, summary)
        write_report({**summary, "training_contexts": 0, "checkpoint_metadata": {}})
        print(json.dumps({"decision": summary["decision"]}, sort_keys=True))
        return 2

    import torch

    device = "cuda" if args.device == "auto" and torch.cuda.is_available() else ("cpu" if args.device == "auto" else args.device)
    if not str(device).startswith("cuda") and not args.allow_cpu_for_tests:
        summary = {
            "schema_version": f"{g567.ROUND}_{PHASE}_summary_v1",
            "decision": "stage2a_blocked_cuda_bf16_required",
            "device": device,
            "source_state": source_state,
            **g567.claims(),
        }
        g567.write_json(g567.REPORTS / SUMMARY_NAME, summary)
        write_report({**summary, "training_contexts": 0, "checkpoint_metadata": {}})
        print(json.dumps({"decision": summary["decision"], "device": device}, sort_keys=True))
        return 2

    if args.contexts < 64 or args.contexts > 256:
        raise RuntimeError("Stage-2A diagnostic A5 training requires 64-256 non-blind contexts")
    seed_ckpts = g567.checkpoint_paths(args.seed_checkpoint_glob)
    if not seed_ckpts:
        summary = {
            "schema_version": f"{g567.ROUND}_{PHASE}_summary_v1",
            "decision": "stage2a_blocked_missing_seed_actor_checkpoint",
            "seed_checkpoint_glob": args.seed_checkpoint_glob,
            **g567.claims(),
        }
        g567.write_json(g567.REPORTS / SUMMARY_NAME, summary)
        write_report({**summary, "training_contexts": 0, "checkpoint_metadata": {}})
        print(json.dumps({"decision": summary["decision"]}, sort_keys=True))
        return 2

    tiers = parse_tiers(args.train_agent_tiers)
    audit_rows, manifest_rows, meta = g567.make_generated_contexts(max(args.context_pool, args.contexts * 4), args.seed, g567.resolve(g567.TMP_ROOT))
    selected_rows = prepare_rows(
        select_training_rows(
            manifest_rows,
            context_count=args.contexts,
            tiers=tiers,
            max_free_cells=max(int(args.max_train_free_cells), max(tiers)),
            max_area=max(int(args.max_train_area), max(tiers) * 2),
        )
    )
    if any(str(row.get("split", "")).upper() == "BLIND" or g567.boolish(row.get("blind_locked")) for row in selected_rows):
        raise RuntimeError("Stage-2A training must not use BLIND contexts")
    g567.write_rows(g567.TABLES / CONTEXT_MANIFEST_NAME, selected_rows)
    contexts = materialize_contexts(selected_rows)
    g567.write_baseline_registry()
    raw_theta = g567.infer_checkpoint_thetas(contexts, seed_ckpts[:1], device=device, batch_size=max(1, int(args.batch_size)), phase=SEED_PHASE)
    response_rows = g567.generate_response_thetas(
        contexts,
        raw_theta,
        phase=LABEL_PHASE,
        target_rows=len(contexts) * max(1, int(args.candidates_per_context)),
    )
    replay_summary = g567.run_replay_phase(
        LABEL_PHASE,
        contexts,
        response_rows,
        binary=args.binary,
        max_workers=max(1, int(args.max_workers)),
        overwrite=bool(args.overwrite),
        margin=float(args.margin),
        plan_only=False,
    )
    replay_pass = replay_summary_passes_stage2a_label_gate(replay_summary)
    if not replay_pass:
        summary = {
            "schema_version": f"{g567.ROUND}_{PHASE}_summary_v1",
            "decision": "stage2a_blocked_label_replay_not_materialized",
            "elapsed_sec": time.perf_counter() - started,
            "source_state": source_state,
            "stage_root": g567.rel(args.stage_root),
            "seed_checkpoint": g567.rel(seed_ckpts[0]),
            "training_contexts": len(contexts),
            "training_agent_tiers": dict(sorted(Counter(ctx.agents for ctx in contexts).items())),
            "training_map_source_types": dict(sorted(Counter(row.get("map_source_type", "") for row in selected_rows).items())),
            "training_scenario_source_types": dict(sorted(Counter(row.get("scenario_source_type", "") for row in selected_rows).items())),
            "max_train_free_cells": int(args.max_train_free_cells),
            "max_train_area": int(args.max_train_area),
            "replay_summary": replay_summary,
            "forbidden_actions": {
                "blind_contexts_loaded": False,
                "full_100k_generation_launched": False,
                "million_row_solver_acquisition_launched": False,
                "forty_eight_hour_training_launched": False,
                "final_blind_panel_constructed_or_accessed": False,
            },
            **g567.claims(),
        }
        g567.write_json(g567.REPORTS / SUMMARY_NAME, summary)
        write_report({**summary, "checkpoint_metadata": {}})
        print(json.dumps({"decision": summary["decision"], "process_hard_timeout_rows": replay_summary.get("process_hard_timeout_rows")}, sort_keys=True))
        return 2
    label_summary = g567.create_labelv54_from_pairs([g567.plan_paths(LABEL_PHASE)["pairs"]], float(args.margin))
    if int(g567.number(label_summary.get("label_train_unique_exact_labeled_contexts"), 0)) < len(contexts):
        summary = {
            "schema_version": f"{g567.ROUND}_{PHASE}_summary_v1",
            "decision": "stage2a_blocked_label_train_unique_contexts_incomplete",
            "elapsed_sec": time.perf_counter() - started,
            "source_state": source_state,
            "training_contexts": len(contexts),
            "labelv54_summary": label_summary,
            "replay_summary": replay_summary,
            **g567.claims(),
        }
        g567.write_json(g567.REPORTS / SUMMARY_NAME, summary)
        write_report({**summary, "checkpoint_metadata": {}})
        print(json.dumps({"decision": summary["decision"]}, sort_keys=True))
        return 2
    training_dataset_sha = dataset_sha256(contexts, g567.LABELV54_CANDIDATES)
    training_uids = [ctx.evaluation_uid for ctx in contexts]
    examples = g567.actor_examples_from_labelv54(contexts)
    if not examples:
        summary = {
            "schema_version": f"{g567.ROUND}_{PHASE}_summary_v1",
            "decision": "stage2a_blocked_no_labelv54_training_examples",
            "replay_summary": replay_summary,
            "labelv54_summary": label_summary,
            **g567.claims(),
        }
        g567.write_json(g567.REPORTS / SUMMARY_NAME, summary)
        write_report({**summary, "training_contexts": len(contexts), "checkpoint_metadata": {}})
        print(json.dumps({"decision": summary["decision"]}, sort_keys=True))
        return 2

    source_commit = g567.git_capture("rev-parse", "HEAD")
    actor_row, grad_row = g567.train_one_g567_actor(
        "A5",
        int(args.seed),
        examples,
        device=device,
        epochs=int(args.epochs),
        min_epochs=int(args.min_epochs),
        patience=int(args.patience),
        batch_size=max(1, int(args.batch_size)),
        token_budget=max(1, int(args.train_token_budget)),
        hidden_dim=int(args.hidden_dim),
        lr=float(args.lr),
        checkpoint_interval_sec=3600.0,
        resume=False,
        diagnostic_only=True,
        training_context_uids=training_uids,
        training_dataset_sha256=training_dataset_sha,
        source_commit=source_commit,
        no_performance_claim=True,
    )
    g567.write_rows(g567.ACTOR_TRAINING_MATRIX, [actor_row])
    g567.write_rows(g567.ACTOR_GRADIENT_AUDIT, [grad_row])
    checkpoint_path = g567.resolve(actor_row["model_path"])
    checkpoint_payload = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    checkpoint_metadata = {
        "artifact_type": checkpoint_payload.get("artifact_type", ""),
        "variant_id": checkpoint_payload.get("variant_id", ""),
        "labelv54_training": bool(checkpoint_payload.get("labelv54_training")),
        "diagnostic_only": bool(checkpoint_payload.get("diagnostic_only")),
        "no_performance_claim": bool(checkpoint_payload.get("no_performance_claim")),
        "cuda_bf16_training": bool(checkpoint_payload.get("cuda_bf16_training")),
        "training_context_count": checkpoint_payload.get("training_context_count", 0),
        "training_dataset_sha256": checkpoint_payload.get("training_dataset_sha256", ""),
        "source_commit": checkpoint_payload.get("source_commit", ""),
        "od_perceiver": bool(checkpoint_payload.get("od_perceiver")),
        "graph_global_layers": checkpoint_payload.get("graph_global_layers", ""),
        "attention_heads": checkpoint_payload.get("attention_heads", checkpoint_payload.get("heads", "")),
        "latent_tokens": checkpoint_payload.get("latent_tokens", ""),
    }
    pass_conditions = {
        "non_blind_only": all(ctx.split == "LABEL_TRAIN" for ctx in contexts),
        "context_count_64_to_256": 64 <= len(contexts) <= 256,
        "labelv54_candidates_present": int(g567.number(label_summary.get("candidates"), 0)) >= len(contexts),
        "label_train_unique_contexts_match": int(g567.number(label_summary.get("label_train_unique_exact_labeled_contexts"), 0)) == len(contexts),
        "replay_materialized": replay_summary.get("decision") == "g567_three_tier_replay_materialized",
        "no_process_hard_timeouts": int(g567.number(replay_summary.get("process_hard_timeout_rows"), 0)) == 0,
        "variant_a5": checkpoint_metadata["variant_id"] == "A5",
        "has_actor_state_dict": isinstance(checkpoint_payload.get("actor_state_dict"), dict) and bool(checkpoint_payload.get("actor_state_dict")),
        "labelv54_training_true": checkpoint_metadata["labelv54_training"],
        "diagnostic_only_true": checkpoint_metadata["diagnostic_only"],
        "cuda_bf16_training_true": checkpoint_metadata["cuda_bf16_training"],
        "dataset_hash_present": bool(checkpoint_metadata["training_dataset_sha256"]),
        "source_commit_present": bool(checkpoint_metadata["source_commit"]) and not str(checkpoint_metadata["source_commit"]).startswith("git_error:"),
        "no_performance_claim": checkpoint_metadata["no_performance_claim"],
    }
    summary = {
        "schema_version": f"{g567.ROUND}_{PHASE}_summary_v1",
        "decision": "stage2a_diagnostic_a5_checkpoint_ready" if all(pass_conditions.values()) else "stage2a_diagnostic_a5_checkpoint_failed",
        "elapsed_sec": time.perf_counter() - started,
        "source_state": source_state,
        "stage_root": g567.rel(args.stage_root),
        "seed_checkpoint": g567.rel(seed_ckpts[0]),
        "generated_contexts": len(manifest_rows),
        "generator_attempts": meta.get("attempts"),
        "audit_rows": len(audit_rows),
        "training_contexts": len(contexts),
        "training_agent_tiers": dict(sorted(Counter(ctx.agents for ctx in contexts).items())),
        "training_map_source_types": dict(sorted(Counter(row.get("map_source_type", "") for row in selected_rows).items())),
        "training_scenario_source_types": dict(sorted(Counter(row.get("scenario_source_type", "") for row in selected_rows).items())),
        "max_train_free_cells": int(args.max_train_free_cells),
        "max_train_area": int(args.max_train_area),
        "context_manifest": g567.rel(g567.TABLES / CONTEXT_MANIFEST_NAME),
        "response_theta_rows": len(response_rows),
        "replay_summary": replay_summary,
        "labelv54_summary": label_summary,
        "actor_training_row": actor_row,
        "actor_gradient_row": grad_row,
        "checkpoint_path": g567.rel(checkpoint_path),
        "checkpoint_sha256": g567.sha256_file(checkpoint_path),
        "checkpoint_metadata": checkpoint_metadata,
        "pass_conditions": pass_conditions,
        "forbidden_actions": {
            "blind_contexts_loaded": False,
            "full_100k_generation_launched": False,
            "million_row_solver_acquisition_launched": False,
            "forty_eight_hour_training_launched": False,
            "final_blind_panel_constructed_or_accessed": False,
        },
        **g567.claims(),
    }
    g567.write_json(g567.ACTOR_TRAINING_SUMMARY, summary)
    g567.write_json(g567.REPORTS / SUMMARY_NAME, summary)
    write_report(summary)
    print(json.dumps({"decision": summary["decision"], "checkpoint_path": summary["checkpoint_path"], "elapsed_sec": summary["elapsed_sec"]}, sort_keys=True))
    return 0 if summary["decision"] == "stage2a_diagnostic_a5_checkpoint_ready" else 2


if __name__ == "__main__":
    raise SystemExit(main())
