from __future__ import annotations

import argparse
import csv
import json
import math
import os
import random
import sys
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import repair5g549_common as g549  # noqa: E402
import run_repair5g561_development_replay as dev  # noqa: E402
import run_repair5g561_replay_ladder as ladder  # noqa: E402
from gcst.goal_aware_actor import GoalAwareDualChannelActor, make_graph_batch, pad_od_tokens, scalar_features  # noqa: E402
from gcst.theta_schema import BASELINE_G556, THETA_HI, THETA_LO, THETA_NUMERIC_COLUMNS, clamp_theta_row  # noqa: E402
from run_repair5g561_materialization_contract import claims, sha256_file  # noqa: E402


ROUND = "phase5p5_repair5g561"
PHASE = "hard_negative_finetune_panel"
MODEL_DIR = Path("artifacts/models/gcst")
HARD_NEGATIVE_CSV = Path(f"outputs/tables/{ROUND}_hard_negative_acquisition.csv")
SOURCE_PAIRS = Path(f"outputs/tables/{ROUND}_development_replay_pairs.csv")
TRAINING_MATRIX = Path(f"outputs/tables/{ROUND}_hard_negative_finetune_training_matrix.csv")
TRAINING_EXAMPLES = Path(f"outputs/tables/{ROUND}_hard_negative_finetune_examples.csv")
TRAINING_SUMMARY = Path(f"outputs/reports/{ROUND}_hard_negative_finetune_summary.json")
TRAINING_MD = Path(f"outputs/reports/{ROUND}_hard_negative_finetune.md")
TRAINING_PROGRESS = Path(f"outputs/reports/{ROUND}_hard_negative_finetune_progress.jsonl")
PANEL_PLAN = Path(f"outputs/tables/{ROUND}_hard_negative_finetune_panel_plan.csv")
PANEL_REGISTRY = Path(f"outputs/tables/{ROUND}_hard_negative_finetune_panel_registry.csv")
PANEL_RESULTS = Path(f"outputs/tables/{ROUND}_hard_negative_finetune_panel_results.csv")
PANEL_RAW_RESULTS = Path(f"outputs/tables/{ROUND}_hard_negative_finetune_panel_results.raw.csv")
PANEL_PAIRS = Path(f"outputs/tables/{ROUND}_hard_negative_finetune_panel_pairs.csv")
PANEL_BY_METHOD = Path(f"outputs/tables/{ROUND}_hard_negative_finetune_panel_by_method.csv")
PANEL_SUMMARY = Path(f"outputs/reports/{ROUND}_hard_negative_finetune_panel_summary.json")
PANEL_MD = Path(f"outputs/reports/{ROUND}_hard_negative_finetune_panel.md")
PANEL_SCENARIO_DIR = Path(f"outputs/tmp/{ROUND}_hard_negative_finetune_panel_scenarios")
PANEL_SCENARIO_METADATA = Path(f"outputs/reports/{ROUND}_hard_negative_finetune_panel_scenario_generation.json")
PANEL_MAP_DIR = Path(f"outputs/tmp/{ROUND}_hard_negative_finetune_panel_maps")
PANEL_LOG_DIR = Path(f"outputs/logs/{ROUND}_hard_negative_finetune_panel")


@dataclass
class FineTuneExample:
    example_id: str
    category: str
    source_method: str
    context: dev.DevelopmentContext
    target: np.ndarray
    source_theta: np.ndarray
    blend_to_g556: float
    weight: float


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


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def append_progress(path: str | Path, row: dict[str, Any]) -> None:
    p = resolve(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps({"ts_utc": utc_now(), **row}, sort_keys=True)
    with p.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")
    print(line, flush=True)


def number(value: Any, default: float = 0.0) -> float:
    try:
        out = float(value)
    except Exception:
        return default
    return out if math.isfinite(out) else default


def hard_negative_blend(category: str, success_regression: Any = False) -> float:
    if dev.boolish(success_regression) or category == "success_regression":
        return 1.0
    if category in {"large_positive_quality_delta", "critic_false_safe_proxy"}:
        return 0.75
    if category == "worst_map_family":
        return 0.60
    if category == "actor_outputs_far_from_support":
        return 0.50
    return 0.65


def hard_negative_weight(category: str, success_regression: Any = False) -> float:
    if dev.boolish(success_regression) or category == "success_regression":
        return 3.0
    if category in {"large_positive_quality_delta", "critic_false_safe_proxy"}:
        return 2.0
    if category == "worst_map_family":
        return 1.5
    return 1.0


def target_from_pair(pair: dict[str, Any], category: str) -> tuple[np.ndarray, np.ndarray, float]:
    source = np.asarray([number(pair.get(col), float(BASELINE_G556[idx])) for idx, col in enumerate(THETA_NUMERIC_COLUMNS)], dtype=np.float32)
    blend = hard_negative_blend(category, pair.get("success_regression"))
    target = (1.0 - blend) * source + blend * np.asarray(BASELINE_G556, dtype=np.float32)
    target_row = clamp_theta_row({col: float(target[idx]) for idx, col in enumerate(THETA_NUMERIC_COLUMNS)})
    target = np.asarray([float(target_row[col]) for col in THETA_NUMERIC_COLUMNS], dtype=np.float32)
    return target, source, blend


def context_key(row: dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        str(row.get("map", "")),
        str(int(number(row.get("agents"), 0))),
        str(int(number(row.get("seed"), 0))),
        str(int(number(row.get("budget_ms"), 0))),
    )


def pair_key(row: dict[str, Any]) -> tuple[str, str, str, str, str, str]:
    return (
        str(row.get("map", "")),
        str(int(number(row.get("agents"), 0))),
        str(int(number(row.get("seed"), 0))),
        str(int(number(row.get("budget_ms"), 0))),
        str(row.get("horizon_id", "")),
        str(row.get("theta_id", "")),
    )


def load_contexts(limit: int) -> list[dev.DevelopmentContext]:
    contexts = dev.select_development_contexts(limit)
    if not contexts:
        raise SystemExit("no development contexts available for fine-tune")
    dev.prepare_missing_scenarios(contexts)
    return dev.enrich_contexts(contexts)


def build_examples(contexts: list[dev.DevelopmentContext], *, max_rows: int = 0) -> list[FineTuneExample]:
    hard_rows = read_rows(HARD_NEGATIVE_CSV)
    pairs = read_rows(SOURCE_PAIRS)
    contexts_by_key = {context_key({"map": ctx.map, "agents": ctx.agents, "seed": ctx.seed, "budget_ms": ctx.budget_ms}): ctx for ctx in contexts}
    pairs_by_key = {pair_key(row): row for row in pairs}
    examples: list[FineTuneExample] = []
    for idx, hard in enumerate(hard_rows):
        if max_rows and len(examples) >= max_rows:
            break
        ctx = contexts_by_key.get(context_key(hard))
        if ctx is None:
            continue
        pair = pairs_by_key.get(
            (
                str(hard.get("map", "")),
                str(int(number(hard.get("agents"), 0))),
                str(int(number(hard.get("seed"), 0))),
                str(int(number(hard.get("budget_ms"), 0))),
                str(hard.get("horizon_id", "")),
                str(hard.get("theta_id", "")),
            )
        )
        if pair is None:
            continue
        category = str(hard.get("acquisition_category", "hard_negative"))
        target, source, blend = target_from_pair(pair, category)
        examples.append(
            FineTuneExample(
                example_id=f"g561_hn_ft_{idx:05d}",
                category=category,
                source_method=str(hard.get("method", "")),
                context=ctx,
                target=target,
                source_theta=source,
                blend_to_g556=blend,
                weight=hard_negative_weight(category, hard.get("success_regression")),
            )
        )
    if not examples:
        raise SystemExit("no hard-negative examples matched development contexts and replay pairs")
    return examples


def configure_panel_paths() -> None:
    dev.PHASE = PHASE
    dev.SCENARIO_DIR = PANEL_SCENARIO_DIR
    dev.SCENARIO_METADATA = PANEL_SCENARIO_METADATA
    dev.MAP_DIR = PANEL_MAP_DIR
    dev.LOG_DIR = PANEL_LOG_DIR
    dev.PLAN_CSV = PANEL_PLAN
    dev.REGISTRY_CSV = PANEL_REGISTRY
    dev.RESULTS_CSV = PANEL_RESULTS
    dev.RAW_RESULTS_CSV = PANEL_RAW_RESULTS
    dev.PAIR_CSV = PANEL_PAIRS
    dev.BY_STRATUM_CSV = PANEL_BY_METHOD
    dev.SUMMARY_JSON = PANEL_SUMMARY
    dev.REPORT_MD = PANEL_MD
    dev.configure_ladder_paths()


def tensor_batch(examples: list[FineTuneExample], device: str):
    import torch

    graph_batch = ladder.move_graph_batch(make_graph_batch([ex.context.graph_with_traffic for ex in examples]), device)
    od_tokens, od_mask = pad_od_tokens([ex.context.assignment for ex in examples])
    scalars = torch.tensor(np.stack([scalar_features(ex.context.feature_row or {}) for ex in examples]), dtype=torch.float32, device=device)
    target = torch.tensor(np.stack([ex.target for ex in examples]), dtype=torch.float32, device=device)
    weights = torch.tensor([ex.weight for ex in examples], dtype=torch.float32, device=device)
    return graph_batch, od_tokens.to(device), od_mask.to(device), scalars, target, weights


def model_from_checkpoint(checkpoint: dict[str, Any], device: str):
    residual_scale = 0.35 if bool(checkpoint.get("critic_training_only")) else 0.30
    model = GoalAwareDualChannelActor(
        hidden_dim=int(checkpoint.get("hidden_dim", 32)),
        use_graph=bool(checkpoint.get("uses_graph")),
        use_paired_od=bool(checkpoint.get("uses_paired_od")),
        use_c0f0=bool(checkpoint.get("uses_c0f0")),
        residual_scale=residual_scale,
    ).module().to(device)
    model.load_state_dict(checkpoint["actor_state_dict"])
    return model


def evaluate_loss(model: Any, examples: list[FineTuneExample], device: str, batch_size: int) -> float:
    import torch

    model.eval()
    losses = []
    span = torch.tensor(np.asarray(THETA_HI - THETA_LO, dtype=np.float32), device=device).clamp_min(1.0e-6)
    with torch.no_grad():
        for start in range(0, len(examples), batch_size):
            batch = examples[start : start + batch_size]
            graph_batch, od_tokens, od_mask, scalars, target, weights = tensor_batch(batch, device)
            pred = model(graph_batch, od_tokens, od_mask, scalars)
            per = torch.mean(torch.abs((pred - target) / span), dim=1)
            losses.extend((per * weights).detach().cpu().numpy().tolist())
    return float(sum(losses) / max(1, len(losses)))


def fine_tune_one(variant: dict[str, Any], examples: list[FineTuneExample], args: argparse.Namespace, device: str) -> dict[str, Any]:
    import torch

    model_path = resolve(str(variant["model_path"]))
    checkpoint = torch.load(model_path, map_location=device, weights_only=False)
    model = model_from_checkpoint(checkpoint, device)
    model.train()
    rng = random.Random(args.seed + sum(ord(c) for c in str(variant["variant_id"])))
    torch.manual_seed(args.seed + sum(ord(c) for c in str(variant["variant_id"])))
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1.0e-5)
    span = torch.tensor(np.asarray(THETA_HI - THETA_LO, dtype=np.float32), device=device).clamp_min(1.0e-6)
    anchor = torch.tensor(np.asarray(BASELINE_G556, dtype=np.float32), device=device)
    before = evaluate_loss(model, examples, device, args.batch_size)
    start_time = time.perf_counter()
    for step in range(1, args.steps + 1):
        batch = rng.sample(examples, min(args.batch_size, len(examples)))
        graph_batch, od_tokens, od_mask, scalars, target, weights = tensor_batch(batch, device)
        pred = model(graph_batch, od_tokens, od_mask, scalars)
        per = torch.mean(torch.abs((pred - target) / span), dim=1)
        loss = torch.mean(per * weights)
        loss = loss + args.anchor_penalty * torch.mean(torch.relu(torch.abs(pred - anchor) / span - args.anchor_margin))
        opt.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step()
        if step == 1 or step == args.steps or (args.progress_interval > 0 and step % args.progress_interval == 0):
            append_progress(
                TRAINING_PROGRESS,
                {
                    "event": "fine_tune_step",
                    "variant_id": variant["variant_id"],
                    "step": step,
                    "steps": args.steps,
                    "loss": float(loss.detach().cpu()),
                    "elapsed_sec": time.perf_counter() - start_time,
                },
            )
    after = evaluate_loss(model, examples, device, args.batch_size)
    out_variant = f"{variant['variant_id']}FT"
    out_name = f"{variant['variant_name']}_hard_negative_finetuned"
    out_path = ROOT / MODEL_DIR / f"g561_{out_variant.lower()}_{out_name}_seed{args.seed}.pt"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            **checkpoint,
            "artifact_type": "g561_goal_aware_direct_actor_hard_negative_finetuned",
            "variant_id": out_variant,
            "variant_name": out_name,
            "base_variant_id": variant["variant_id"],
            "base_model_path": str(variant["model_path"]),
            "actor_state_dict": model.state_dict(),
            "fine_tune_seed": args.seed,
            "fine_tune_steps": args.steps,
            "fine_tune_examples": len(examples),
            "fine_tune_loss_before": before,
            "fine_tune_loss_after": after,
        },
        out_path,
    )
    row = {
        "variant_id": out_variant,
        "variant_name": out_name,
        "base_variant_id": variant["variant_id"],
        "base_variant_name": variant["variant_name"],
        "model_path": str(out_path.relative_to(ROOT)).replace("\\", "/"),
        "base_model_path": str(variant["model_path"]),
        "seed": args.seed,
        "fine_tune_steps": args.steps,
        "fine_tune_examples": len(examples),
        "hard_negative_loss_before": before,
        "hard_negative_loss_after": after,
        "hard_negative_loss_delta": after - before,
        "uses_graph": checkpoint.get("uses_graph"),
        "uses_paired_od": checkpoint.get("uses_paired_od"),
        "uses_c0f0": checkpoint.get("uses_c0f0"),
        "critic_training_only": checkpoint.get("critic_training_only"),
        "model_sha256": sha256_file(out_path),
        **claims(),
    }
    append_progress(TRAINING_PROGRESS, {"event": "fine_tune_done", **row})
    return row


def write_training_artifacts(rows: list[dict[str, Any]], examples: list[FineTuneExample], elapsed: float, device: str, args: argparse.Namespace) -> dict[str, Any]:
    example_rows = [
        {
            "example_id": ex.example_id,
            "category": ex.category,
            "source_method": ex.source_method,
            "map": ex.context.map,
            "map_family": ex.context.map_family,
            "agents": ex.context.agents,
            "seed": ex.context.seed,
            "budget_ms": ex.context.budget_ms,
            "blend_to_g556": ex.blend_to_g556,
            "weight": ex.weight,
            **claims(),
        }
        for ex in examples
    ]
    category_counts = dict(sorted(Counter(ex.category for ex in examples).items()))
    summary = {
        "schema_version": f"{ROUND}_hard_negative_finetune_summary_v1",
        "decision": "g561_hard_negative_finetune_completed",
        "device": device,
        "cuda_used": str(device).startswith("cuda"),
        "fine_tune_completed": True,
        "fine_tune_rows": len(rows),
        "fine_tune_variants": [row["variant_id"] for row in rows],
        "base_variants": [row["base_variant_id"] for row in rows],
        "hard_negative_examples": len(examples),
        "hard_negative_category_counts": category_counts,
        "steps": args.steps,
        "batch_size": args.batch_size,
        "lr": args.lr,
        "run_elapsed_sec": elapsed,
        "next_required_gate": "rerun frozen-comparison development panel with original and fine-tuned actors",
        **claims(),
    }
    write_rows(TRAINING_MATRIX, rows)
    write_rows(TRAINING_EXAMPLES, example_rows)
    write_json(TRAINING_SUMMARY, summary)
    write_text(
        TRAINING_MD,
        "# Repair5G.5.61 Hard-Negative Fine-Tune\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- variants: `{','.join(summary['fine_tune_variants'])}`\n"
        f"- examples: `{summary['hard_negative_examples']}`\n"
        f"- category counts: `{summary['hard_negative_category_counts']}`\n"
        f"- next gate: `{summary['next_required_gate']}`\n\n"
        "The fine-tuned actors remain development-only artifacts. They do not open runtime, Phase5.5, Phase6, or AAAI claims.\n",
    )
    return summary


def selected_for_panel(fine_tuned_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    originals = dev.select_best_two_actor_variants(write_selection=False)
    selected = [dict(row) for row in originals]
    for row in fine_tuned_rows:
        selected.append(
            {
                "variant_id": row["variant_id"],
                "variant_name": row["variant_name"],
                "model_path": row["model_path"],
                "base_variant_id": row["base_variant_id"],
                "selected_for_hard_negative_finetune_panel": True,
                **claims(),
            }
        )
    return selected


def summarize_panel_by_method(pairs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for method in sorted({str(pair.get("method", "")) for pair in pairs}):
        group = [pair for pair in pairs if pair.get("method") == method]
        values = []
        for pair in group:
            try:
                value = float(pair.get("quality_delta_vs_g556", "nan"))
            except Exception:
                value = math.nan
            if math.isfinite(value):
                values.append(value)
        rows.append(
            {
                "method": method,
                "is_finetuned": "_hard_negative_finetuned" in method,
                "pairs": len(group),
                "success_regressions": sum(dev.boolish(pair.get("success_regression")) for pair in group),
                "success_gains": sum(dev.boolish(pair.get("success_gain")) for pair in group),
                "mean_quality_delta_vs_g556": sum(values) / len(values) if values else "",
                "better": sum(value < 0 for value in values),
                "worse": sum(value > 0 for value in values),
                "ties": sum(value == 0 for value in values),
                **claims(),
            }
        )
    return rows


def run_panel(contexts: list[dev.DevelopmentContext], selected: list[dict[str, Any]], args: argparse.Namespace, device: str) -> dict[str, Any]:
    configure_panel_paths()
    plan_rows, _registry_rows = dev.build_plan_and_registry(contexts, selected, device)
    if args.plan_only:
        summary = {
            "decision": "g561_hard_negative_finetune_panel_plan_created",
            "contexts": len(contexts),
            "planned_rows": len(plan_rows),
            "selected": [row.get("variant_id") for row in selected],
            **claims(),
        }
        write_json(PANEL_SUMMARY, summary)
        print(json.dumps(summary, sort_keys=True))
        return summary
    binary = dev.solver_binary(args.binary)
    os.environ.setdefault("REPAIR5G_STREAM_RESULT_CSV", "1")
    os.environ.setdefault("REPAIR5G_SKIP_AGGREGATE_JSONL", "1")
    g549.run_probe_plan(
        plan_rows,
        binary=binary,
        overwrite=True,
        row_limit=0,
        max_workers=max(1, int(args.max_workers)),
        registry_path=str(resolve(PANEL_REGISTRY)),
        result_csv=str(resolve(PANEL_RESULTS)),
        raw_csv=str(resolve(PANEL_RAW_RESULTS)),
        log_dir=str(resolve(PANEL_LOG_DIR)),
        run_jsonl=str(resolve(PANEL_LOG_DIR / "runs.jsonl")),
        command_jsonl=str(resolve(PANEL_LOG_DIR / "commands.jsonl")),
        update_jsonl=str(resolve(PANEL_LOG_DIR / "updates.jsonl")),
        probe_jsonl=str(resolve(PANEL_LOG_DIR / "counterfactual_probes.jsonl")),
        checkpoint_jsonl=str(resolve(PANEL_LOG_DIR / "checkpoints.jsonl")),
        status_json=str(resolve(PANEL_LOG_DIR / "status.json")),
        scenario_dir=str(resolve(PANEL_SCENARIO_DIR)),
        scenario_metadata=str(resolve(PANEL_SCENARIO_METADATA)),
        manifest_prefix="g561_hard_negative_finetune_panel",
        row_prefix="g561_hard_negative_finetune_panel",
        execution_mode="g561_hard_negative_finetune_panel_real_solver_row",
    )
    audited = ladder.audit_results(read_rows(PANEL_RESULTS), plan_rows)
    write_rows(PANEL_RESULTS, audited)
    pairs = ladder.build_pairs(audited, phase=PHASE)
    by_method = summarize_panel_by_method(pairs)
    write_rows(PANEL_PAIRS, pairs)
    write_rows(PANEL_BY_METHOD, by_method)
    summary = ladder.summarize_pairs(pairs, audited, PHASE)
    fine_methods = [row for row in by_method if dev.boolish(row.get("is_finetuned"))]
    fine_values = [number(row.get("mean_quality_delta_vs_g556"), math.nan) for row in fine_methods if str(row.get("mean_quality_delta_vs_g556", "")).strip()]
    fine_regressions = sum(int(number(row.get("success_regressions"), 0)) for row in fine_methods)
    fine_better = sum(int(number(row.get("better"), 0)) for row in fine_methods)
    fine_worse = sum(int(number(row.get("worse"), 0)) for row in fine_methods)
    fine_mean = sum(fine_values) / len(fine_values) if fine_values else None
    exact = summary["decision"].endswith("_executed_exact_materialization")
    passed = bool(exact and fine_regressions == 0 and fine_mean is not None and fine_mean < 0.0 and fine_better > fine_worse)
    summary.update(
        {
            "schema_version": f"{ROUND}_hard_negative_finetune_panel_summary_v1",
            "decision": (
                "g561_hard_negative_finetune_panel_passed_stage1_candidate"
                if passed
                else "g561_hard_negative_finetune_panel_executed_not_promotable"
                if exact
                else "g561_hard_negative_finetune_panel_materialization_invalid_continue_repair"
            ),
            "panel_contexts": len(contexts),
            "panel_selected_variants": [row.get("variant_id") for row in selected],
            "fine_tune_completed": True,
            "fine_tuned_panel_passed": passed,
            "fine_tuned_success_regressions": fine_regressions,
            "fine_tuned_mean_quality_delta_vs_g556": fine_mean,
            "fine_tuned_better": fine_better,
            "fine_tuned_worse": fine_worse,
            "fine_tuned_methods": [row["method"] for row in fine_methods],
            "next_required_gate": (
                "write Stage1 plan from hard-negative fine-tuned actor"
                if passed
                else "keep g556 as supported baseline; direct actor remains not promotable after hard-negative fine-tune"
            ),
        }
    )
    write_json(PANEL_SUMMARY, summary)
    write_text(
        PANEL_MD,
        "# Repair5G.5.61 Hard-Negative Fine-Tune Panel\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- contexts: `{summary['panel_contexts']}`\n"
        f"- executed rows: `{summary['executed_rows']}`\n"
        f"- actor rows: `{summary['actor_rows']}`\n"
        f"- materialization-invalid rows: `{summary['materialization_invalid_rows']}`\n"
        f"- fine-tuned success regressions: `{summary['fine_tuned_success_regressions']}`\n"
        f"- fine-tuned mean quality delta vs g556: `{summary['fine_tuned_mean_quality_delta_vs_g556']}`\n"
        f"- fine-tuned better/worse: `{summary['fine_tuned_better']}` / `{summary['fine_tuned_worse']}`\n"
        f"- next gate: `{summary['next_required_gate']}`\n\n"
        "This is a frozen development comparison between original F6/F7 and hard-negative fine-tuned F6FT/F7FT. Claims remain closed.\n",
    )
    print(json.dumps({"decision": summary["decision"], "rows": len(audited), "pairs": len(pairs)}, sort_keys=True))
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fine-tune G5.61 actors on hard negatives and rerun a frozen development panel.")
    parser.add_argument("--contexts", type=int, default=400)
    parser.add_argument("--steps", type=int, default=300)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--lr", type=float, default=5.0e-5)
    parser.add_argument("--seed", type=int, default=561)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--max-workers", type=int, default=4)
    parser.add_argument("--binary", type=Path, default=Path("build/phase1a-batch/phase1a_batch"))
    parser.add_argument("--progress-interval", type=int, default=100)
    parser.add_argument("--anchor-penalty", type=float, default=0.04)
    parser.add_argument("--anchor-margin", type=float, default=0.30)
    parser.add_argument("--max-hard-negative-rows", type=int, default=0)
    parser.add_argument("--train-only", action="store_true")
    parser.add_argument("--panel-only", action="store_true")
    parser.add_argument("--plan-only", action="store_true")
    args = parser.parse_args(argv)

    import torch

    run_start = time.perf_counter()
    device = args.device if args.device != "auto" else ("cuda" if torch.cuda.is_available() else "cpu")
    progress = resolve(TRAINING_PROGRESS)
    progress.parent.mkdir(parents=True, exist_ok=True)
    if not args.panel_only:
        progress.write_text("", encoding="utf-8")
    append_progress(TRAINING_PROGRESS, {"event": "run_start", "device": device, "contexts": args.contexts, "steps": args.steps})
    contexts = load_contexts(args.contexts)
    examples = build_examples(contexts, max_rows=args.max_hard_negative_rows)
    fine_rows: list[dict[str, Any]] = []
    if args.panel_only:
        fine_rows = read_rows(TRAINING_MATRIX)
        if not fine_rows:
            raise SystemExit("panel-only requested but fine-tune training matrix is missing")
    else:
        selected_originals = dev.select_best_two_actor_variants(write_selection=False)
        for variant in selected_originals:
            fine_rows.append(fine_tune_one(variant, examples, args, device))
        write_training_artifacts(fine_rows, examples, time.perf_counter() - run_start, device, args)
    if args.train_only:
        return 0
    panel_summary = run_panel(contexts, selected_for_panel(fine_rows), args, device)
    append_progress(TRAINING_PROGRESS, {"event": "run_done", "decision": panel_summary.get("decision"), "elapsed_sec": time.perf_counter() - run_start})
    return 0 if str(panel_summary.get("decision", "")).startswith("g561_hard_negative_finetune_panel_") else 2


if __name__ == "__main__":
    raise SystemExit(main())
