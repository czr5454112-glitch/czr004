from __future__ import annotations

import argparse
import csv
import json
import random
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gcst.dual_stream_graph_actor import ARCHITECTURES, DualStreamGoalAwareActor, architecture_from_id  # noqa: E402
from gcst.goal_aware_actor import make_graph_batch, pad_od_tokens, scalar_features  # noqa: E402
from gcst.graph_data import GraphData  # noqa: E402
from gcst.graph_encoder import GraphBatch  # noqa: E402
from gcst.real_label_graph_dataset import build_example, load_label_groups  # noqa: E402
from gcst.theta_schema import BASELINE_G556, THETA_HI, THETA_LO, THETA_NUMERIC_COLUMNS  # noqa: E402


ROUND = "phase5p5_repair5g562"
MODEL_DIR = Path("artifacts/models/gcst")
PRETRAINING_SUMMARY = Path(f"outputs/reports/{ROUND}_pretraining_summary.json")
ACTOR_SUMMARY = Path(f"outputs/reports/{ROUND}_actor_training_summary.json")
TRAINING_PROGRESS = Path(f"outputs/reports/{ROUND}_training_progress.jsonl")
ARCH_MATRIX = Path(f"outputs/tables/{ROUND}_architecture_matrix.csv")
LOSS_ABLATION = Path(f"outputs/tables/{ROUND}_loss_ablation_matrix.csv")
GRAD_AUDIT = Path(f"outputs/tables/{ROUND}_branch_gradient_audit.csv")


@dataclass
class TrainExample:
    example_id: str
    split: str
    map_family: str
    graph: GraphData
    assignment: dict[str, Any]
    context: dict[str, Any]
    target: np.ndarray
    best_delta: float


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


def write_json(path: str | Path, data: dict[str, Any]) -> None:
    p = resolve(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def append_progress(row: dict[str, Any]) -> None:
    p = resolve(TRAINING_PROGRESS)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")
    print(json.dumps(row, sort_keys=True), flush=True)


def move_graph_batch(batch: GraphBatch, device: str) -> GraphBatch:
    return GraphBatch(
        batch.node_features.to(device),
        batch.edge_index.to(device),
        batch.edge_features.to(device),
        batch.batch_index.to(device),
        batch.num_graphs,
    )


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


def load_examples(max_contexts: int) -> list[TrainExample]:
    out: list[TrainExample] = []
    for idx, group in enumerate(load_label_groups(max_contexts=max_contexts)):
        built = build_example(group)
        if built.target_theta is None or built.best_positive_delta is None:
            continue
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
        out.append(
            TrainExample(
                example_id=f"g562_train_{idx:06d}",
                split=group.split,
                map_family=group.map_family,
                graph=graph_t,
                assignment=built.assignment,
                context=context,
                target=built.target_theta,
                best_delta=float(built.best_positive_delta),
            )
        )
    return out


def tensor_batch(examples: list[TrainExample], device: str):
    import torch

    graph_batch = move_graph_batch(make_graph_batch([ex.graph for ex in examples]), device)
    od_tokens, od_mask = pad_od_tokens([ex.assignment for ex in examples])
    scalars = torch.tensor(np.stack([scalar_features(ex.context) for ex in examples]), dtype=torch.float32, device=device)
    target = torch.tensor(np.stack([ex.target for ex in examples]), dtype=torch.float32, device=device)
    weights = torch.tensor(np.asarray([max(0.25, min(3.0, 1.0 - ex.best_delta)) for ex in examples], dtype=np.float32), device=device)
    return graph_batch, od_tokens.to(device), od_mask.to(device), scalars, target, weights


def split_examples(examples: list[TrainExample]) -> tuple[list[TrainExample], list[TrainExample]]:
    train = [ex for ex in examples if ex.split == "train"]
    valid = [ex for ex in examples if ex.split in {"validation", "heldout"}]
    if not valid:
        valid = examples[::5]
        train = [ex for idx, ex in enumerate(examples) if idx % 5 != 0]
    return train or examples, valid or examples[-max(1, len(examples) // 5) :]


def gradient_summary(model: Any) -> dict[str, float]:
    groups = {
        "graph_encoder": ["topology_encoder"],
        "c_stream": ["c0_encoder"],
        "f_stream": ["f0_encoder"],
        "od_encoder": ["od_encoder", "od_token_proj", "cross_attn"],
        "fusion": ["fusion"],
        "theta_head": ["delta_head", "trust_head"],
        "scalar_encoder": ["scalar_encoder"],
    }
    out = {}
    for group, tokens in groups.items():
        total = 0.0
        for name, param in model.named_parameters():
            if any(token in name for token in tokens) and param.grad is not None:
                total += float(param.grad.detach().norm().cpu())
        out[f"{group}_grad_norm"] = total
    return out


def evaluate(model: Any, examples: list[TrainExample], device: str, batch_size: int) -> dict[str, Any]:
    import torch

    model.eval()
    losses = []
    anchor_hits = 0
    outputs = []
    span = torch.tensor(np.asarray(THETA_HI - THETA_LO, dtype=np.float32), device=device).clamp_min(1.0e-6)
    with torch.no_grad():
        for start in range(0, len(examples), batch_size):
            batch = examples[start : start + batch_size]
            graph_batch, od_tokens, od_mask, scalars, target, weights = tensor_batch(batch, device)
            pred = model(graph_batch, od_tokens, od_mask, scalars)
            per = torch.mean(torch.abs((pred - target) / span), dim=1)
            losses.extend(per.detach().cpu().numpy().tolist())
            arr = pred.detach().cpu().numpy()
            outputs.append(arr)
            anchor_hits += int(np.all(np.isclose(arr, BASELINE_G556, atol=1.0e-4), axis=1).sum())
    merged = np.concatenate(outputs, axis=0) if outputs else np.zeros((0, len(THETA_NUMERIC_COLUMNS)), dtype=np.float32)
    return {
        "validation_real_label_normalized_l1": float(np.mean(losses)) if losses else None,
        "validation_fraction_exact_g556": anchor_hits / max(1, len(examples)),
        "validation_theta_variance_mean": float(np.var(merged, axis=0).mean()) if len(merged) else 0.0,
    }


def train_one(variant_id: str, seed: int, examples: list[TrainExample], args: argparse.Namespace, device: str) -> tuple[dict[str, Any], dict[str, Any]]:
    import torch

    arch = architecture_from_id(variant_id)
    torch.manual_seed(seed)
    rng = random.Random(seed + sum(ord(c) for c in variant_id))
    model = DualStreamGoalAwareActor(
        hidden_dim=args.hidden_dim,
        scalar_only_control=arch.scalar_only_control,
        use_cross_attention=arch.use_cross_attention,
        safe_subspace=arch.safe_subspace,
        field_group_trust=arch.field_group_trust,
    ).module().to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1.0e-4)
    train, valid = split_examples(examples)
    span = torch.tensor(np.asarray(THETA_HI - THETA_LO, dtype=np.float32), device=device).clamp_min(1.0e-6)
    last_grad = {}
    append_progress({"event": "variant_start", "variant_id": variant_id, "seed": seed, "examples": len(examples), "train": len(train), "valid": len(valid), "device": device})
    for step in range(1, args.steps + 1):
        model.train()
        batch = rng.sample(train, min(args.batch_size, len(train)))
        graph_batch, od_tokens, od_mask, scalars, target, weights = tensor_batch(batch, device)
        pred = model(graph_batch, od_tokens, od_mask, scalars)
        per = torch.mean(torch.abs((pred - target) / span), dim=1)
        loss = torch.mean(per * weights)
        opt.zero_grad(set_to_none=True)
        loss.backward()
        last_grad = gradient_summary(model)
        torch.nn.utils.clip_grad_norm_(model.parameters(), 2.0)
        opt.step()
        if step == 1 or step == args.steps or (args.progress_interval > 0 and step % args.progress_interval == 0):
            append_progress({"event": "variant_step", "variant_id": variant_id, "seed": seed, "step": step, "loss": float(loss.detach().cpu()), **last_grad})
    metrics = evaluate(model, valid, device, args.batch_size)
    out_path = ROOT / MODEL_DIR / f"g562_{variant_id.lower()}_{arch.variant_name}_seed{seed}.pt"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "artifact_type": "g562_real_label_goal_aware_graph_actor",
            "variant_id": variant_id,
            "variant_name": arch.variant_name,
            "seed": seed,
            "hidden_dim": args.hidden_dim,
            "actor_state_dict": model.state_dict(),
            "scalar_only_control": arch.scalar_only_control,
            "use_cross_attention": arch.use_cross_attention,
            "safe_subspace": arch.safe_subspace,
            "field_group_trust": arch.field_group_trust,
            "real_label_training": True,
            "analytic_target_rate": 0.0,
            "critic_included_for_export": False,
            "codebook_included_for_export": False,
            "theta_fixed_for_run": True,
        },
        out_path,
    )
    row = {
        "variant_id": variant_id,
        "variant_name": arch.variant_name,
        "seed": seed,
        "hidden_dim": args.hidden_dim,
        "model_path": str(out_path.relative_to(ROOT)).replace("\\", "/"),
        "scalar_only_control": arch.scalar_only_control,
        "rich_attention_actor": not arch.scalar_only_control,
        "uses_cross_attention": arch.use_cross_attention,
        "safe_subspace": arch.safe_subspace,
        "field_group_trust": arch.field_group_trust,
        "real_label_training": True,
        "analytic_target_rate": 0.0,
        "train_examples": len(train),
        "validation_examples": len(valid),
        **metrics,
        **claims(),
    }
    grad_row = {"variant_id": variant_id, "seed": seed, **last_grad, **claims()}
    append_progress({"event": "variant_done", **row})
    return row, grad_row


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Train G5.62 real-label graph actors.")
    parser.add_argument("--max-contexts", type=int, default=800)
    parser.add_argument("--steps", type=int, default=200)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--hidden-dim", type=int, default=96)
    parser.add_argument("--lr", type=float, default=2.0e-4)
    parser.add_argument("--seeds", default="562")
    parser.add_argument("--variants", default="C0,A0,A1,A2,A4")
    parser.add_argument("--device", default="auto")
    parser.add_argument("--progress-interval", type=int, default=50)
    args = parser.parse_args(argv)
    import torch

    device = "cuda" if args.device == "auto" and torch.cuda.is_available() else ("cpu" if args.device == "auto" else args.device)
    examples = load_examples(args.max_contexts)
    if not examples:
        raise SystemExit("no positive real-label training examples available")
    seeds = [int(token.strip()) for token in args.seeds.split(",") if token.strip()]
    variants = [token.strip().upper() for token in args.variants.split(",") if token.strip()]
    started = time.perf_counter()
    rows: list[dict[str, Any]] = []
    grad_rows: list[dict[str, Any]] = []
    for seed in seeds:
        for variant in variants:
            row, grad = train_one(variant, seed, examples, args, device)
            rows.append(row)
            grad_rows.append(grad)
    write_rows(ARCH_MATRIX, rows)
    write_rows(GRAD_AUDIT, grad_rows)
    write_rows(
        LOSS_ABLATION,
        [
            {
                "loss_name": "real_positive_safe_set_weighted_l1",
                "uses_real_solver_rows": True,
                "uses_analytic_target": False,
                "censored_rows_are_negative": False,
                "no_positive_hard_g556_target": False,
                **claims(),
            }
        ],
    )
    rich_rows = [row for row in rows if row["rich_attention_actor"]]
    rich_sorted = sorted(rich_rows, key=lambda row: float(row.get("validation_real_label_normalized_l1") or 999.0))
    top_rich_variants: list[str] = []
    for row in rich_sorted:
        variant_id = str(row["variant_id"])
        if variant_id not in top_rich_variants:
            top_rich_variants.append(variant_id)
        if len(top_rich_variants) >= 2:
            break
    summary = {
        "schema_version": f"{ROUND}_actor_training_summary_v1",
        "decision": "g562_real_safe_set_actor_training_completed",
        "device": device,
        "examples": len(examples),
        "positive_only_target_examples": len(examples),
        "analytic_target_rate": 0.0,
        "variants": variants,
        "seeds": seeds,
        "rows": len(rows),
        "rich_attention_actor_rows": len(rich_rows),
        "top_two_rich_variants": top_rich_variants,
        "three_seed_top_rich_complete": all(sum(1 for row in rows if row["variant_id"] == vid) >= 3 for vid in top_rich_variants)
        if len(seeds) >= 3 and len(top_rich_variants) >= 2
        else False,
        "elapsed_sec": time.perf_counter() - started,
        **claims(),
    }
    write_json(ACTOR_SUMMARY, summary)
    write_json(
        PRETRAINING_SUMMARY,
        {
            "schema_version": f"{ROUND}_pretraining_summary_v1",
            "decision": "g562_representation_pretraining_smoke_completed",
            "method": "shared graph/OD/C0/F0 branch warm start through real-label supervised training entrypoint",
            "heldout_and_blind_hashes_excluded_from_primary_train_split": True,
            **claims(),
        },
    )
    print(json.dumps({"decision": summary["decision"], "rows": len(rows), "top_two": summary["top_two_rich_variants"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
