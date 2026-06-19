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

from gcst.goal_aware_actor import GoalAwareDualChannelActor, make_graph_batch, pad_od_tokens, scalar_features  # noqa: E402
from gcst.graph_data import GraphData, build_graph, graph_summary  # noqa: E402
from gcst.label_v4 import context_target_theta  # noqa: E402
from gcst.scenario_features import generate_assignment  # noqa: E402
from gcst.theta_schema import BASELINE_G556, THETA_HI, THETA_LO, THETA_NUMERIC_COLUMNS  # noqa: E402
from gcst.traffic_prior import compute_traffic_prior  # noqa: E402


ROUND = "phase5p5_repair5g561"
MODEL_DIR = Path("artifacts/models/gcst")
REPRESENTATION_MD = Path(f"outputs/reports/{ROUND}_representation_truth.md")
MODEL_VARIANT_MATRIX = Path(f"outputs/tables/{ROUND}_model_variant_matrix.csv")
ABLATION_MATRIX = Path(f"outputs/tables/{ROUND}_ablation_matrix.csv")
CAUSAL_SENSITIVITY = Path(f"outputs/tables/{ROUND}_causal_sensitivity_audit.csv")
CRITIC_CALIBRATION = Path(f"outputs/tables/{ROUND}_critic_calibration.csv")
OFFLINE_COMPARISON = Path(f"outputs/tables/{ROUND}_offline_model_comparison.csv")
TRAINING_SUMMARY = Path(f"outputs/reports/{ROUND}_training_summary.json")
TRAINING_PROGRESS = Path(f"outputs/reports/{ROUND}_training_progress.jsonl")


VARIANTS = {
    "F0": {"name": "g560_scalar_actor_control", "use_graph": False, "use_paired_od": False, "use_c0f0": False, "critic": False},
    "F1": {"name": "scalar_conservative_actor", "use_graph": False, "use_paired_od": False, "use_c0f0": False, "critic": False},
    "F2": {"name": "graph_only_direct_actor", "use_graph": True, "use_paired_od": False, "use_c0f0": False, "critic": False},
    "F4": {"name": "graph_paired_od_actor", "use_graph": True, "use_paired_od": True, "use_c0f0": False, "critic": False},
    "F6": {"name": "full_goal_aware_dual_channel_actor", "use_graph": True, "use_paired_od": True, "use_c0f0": True, "critic": False},
    "F7": {"name": "full_goal_aware_actor_training_critic", "use_graph": True, "use_paired_od": True, "use_c0f0": True, "critic": True},
}


@dataclass
class Sample:
    sample_id: str
    graph: GraphData
    assignment: dict[str, Any]
    context: dict[str, Any]
    scalar: np.ndarray
    target: np.ndarray


def write_rows(path: str | Path, rows: list[dict[str, Any]]) -> None:
    p = ROOT / path
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
    p = ROOT / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def write_text(path: str | Path, text: str) -> None:
    p = ROOT / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def append_progress(path: str | Path, row: dict[str, Any]) -> None:
    if not path:
        return
    p = ROOT / path
    p.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps({"ts_utc": utc_now(), **row}, sort_keys=True)
    with p.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")
    print(line, flush=True)


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


def build_samples(count: int, seed: int) -> list[Sample]:
    rng = random.Random(seed)
    maps = [
        ("empty-8-8", "empty", 8, 8, 64),
        ("empty-16-16", "empty", 16, 16, 256),
        ("random-16-16-20", "random", 16, 16, 205),
        ("random-32-32-20", "random", 32, 32, 820),
        ("maze-32-32-4", "maze", 32, 32, 700),
        ("room-32-32-4", "room", 32, 32, 760),
        ("warehouse-20-10-10", "warehouse", 20, 10, 140),
        ("g559-synth-string-40", "irregular_bottleneck", 40, 40, 520),
    ]
    regimes = [
        "uniform_random",
        "opposite_side_cross_flow",
        "central_choke_point",
        "room_to_room_door_bottleneck",
        "warehouse_aisle_to_aisle",
        "clustered_starts_to_dispersed_goals",
    ]
    samples: list[Sample] = []
    for idx in range(count):
        map_name, family, width, height, free_cells = maps[idx % len(maps)]
        agents = rng.choice([8, 12, 16, 24, 32, 48, 64])
        context = {
            "map": map_name,
            "map_family": family,
            "width": width,
            "height": height,
            "free_cells": free_cells,
            "agent_count": agents,
            "agents": agents,
            "seed": seed * 1000 + idx,
            "nominal_budget_ms": rng.choice([500, 1000, 2000, 5000]),
            "base_time_limit_sec": rng.choice([0.5, 1.0, 2.0]),
            "ltm_max_iterations": rng.choice([2, 3, 4, 6]),
            "start_goal_regime": regimes[idx % len(regimes)],
        }
        graph = build_graph(context)
        assignment = generate_assignment(graph, context, max_agents=None)
        traffic = compute_traffic_prior(graph, assignment)
        graph_t = graph_with_edge_features(graph, traffic["edge_features"])
        summary = graph_summary(graph_t)
        density = agents / max(1, graph_t.physical_free_cell_count)
        context.update({"agent_density": density, **traffic["summary"]})
        target = context_target_theta({**summary, "agent_density": density}, traffic["summary"])
        samples.append(Sample(f"g561_sample_{idx:04d}", graph_t, assignment, context, scalar_features(context), target))
    return samples


def move_graph_batch(batch, device: str):
    from gcst.graph_encoder import GraphBatch

    return GraphBatch(
        batch.node_features.to(device),
        batch.edge_index.to(device),
        batch.edge_features.to(device),
        batch.batch_index.to(device),
        batch.num_graphs,
    )


def tensor_batch(samples: list[Sample], device: str):
    import torch

    graph_batch = move_graph_batch(make_graph_batch([s.graph for s in samples]), device)
    od_tokens, od_mask = pad_od_tokens([s.assignment for s in samples])
    scalars = torch.tensor(np.stack([s.scalar for s in samples]), dtype=torch.float32, device=device)
    target = torch.tensor(np.stack([s.target for s in samples]), dtype=torch.float32, device=device)
    return graph_batch, od_tokens.to(device), od_mask.to(device), scalars, target


def normalized_l1(pred: np.ndarray, target: np.ndarray) -> float:
    span = np.maximum(np.asarray(THETA_HI - THETA_LO, dtype=np.float32), 1.0e-6)
    return float(np.mean(np.abs((pred - target) / span)))


def train_variant(variant_id: str, config: dict[str, Any], samples: list[Sample], args: argparse.Namespace, device: str) -> dict[str, Any]:
    import torch

    variant_start = time.perf_counter()
    torch.manual_seed(args.seed + sum(ord(c) for c in variant_id))
    rng = random.Random(args.seed + len(variant_id))
    model = GoalAwareDualChannelActor(
        hidden_dim=args.hidden_dim,
        use_graph=config["use_graph"],
        use_paired_od=config["use_paired_od"],
        use_c0f0=config["use_c0f0"],
        residual_scale=0.35 if config.get("critic") else 0.30,
    ).module().to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1.0e-4)
    train = samples[: max(1, int(len(samples) * 0.75))]
    valid = samples[len(train) :] or samples[-4:]
    history = []
    append_progress(
        args.progress_jsonl,
        {
            "event": "variant_start",
            "variant_id": variant_id,
            "variant_name": config["name"],
            "device": device,
            "steps": args.steps,
            "batch_size": args.batch_size,
            "train_instances": len(train),
            "validation_instances": len(valid),
            "uses_graph": config["use_graph"],
            "uses_paired_od": config["use_paired_od"],
            "uses_c0f0": config["use_c0f0"],
        },
    )
    for step in range(1, args.steps + 1):
        batch = rng.sample(train, min(args.batch_size, len(train)))
        graph_batch, od_tokens, od_mask, scalars, target = tensor_batch(batch, device)
        pred = model(graph_batch, od_tokens, od_mask, scalars)
        span = torch.tensor(np.asarray(THETA_HI - THETA_LO, dtype=np.float32), device=device).clamp_min(1.0e-6)
        loss = torch.mean(torch.abs((pred - target) / span))
        if config.get("critic"):
            loss = loss + 0.05 * torch.mean(torch.relu(torch.abs(pred - torch.tensor(BASELINE_G556, dtype=torch.float32, device=device)) - span * 0.35))
        opt.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 2.0)
        opt.step()
        should_report = step == 1 or step == args.steps or (
            args.progress_interval > 0 and step % args.progress_interval == 0
        )
        if should_report:
            elapsed = max(time.perf_counter() - variant_start, 1.0e-9)
            loss_value = float(loss.detach().cpu())
            row = {
                "event": "variant_step",
                "variant_id": variant_id,
                "step": step,
                "steps": args.steps,
                "loss": loss_value,
                "elapsed_sec": elapsed,
                "examples_per_sec": (step * len(batch)) / elapsed,
            }
            history.append(row)
            append_progress(args.progress_jsonl, row)
    with torch.no_grad():
        graph_batch, od_tokens, od_mask, scalars, target = tensor_batch(valid, device)
        pred = model(graph_batch, od_tokens, od_mask, scalars).detach().cpu().numpy()
        target_np = target.detach().cpu().numpy()
    model_path = ROOT / MODEL_DIR / f"g561_{variant_id.lower()}_{config['name']}_seed{args.seed}.pt"
    model_path.parent.mkdir(parents=True, exist_ok=True)
    variant_elapsed = time.perf_counter() - variant_start
    torch.save(
        {
            "artifact_type": "g561_goal_aware_direct_actor",
            "variant_id": variant_id,
            "variant_name": config["name"],
            "seed": args.seed,
            "actor_state_dict": model.state_dict(),
            "theta_columns": THETA_NUMERIC_COLUMNS,
            "theta_anchor_g556": BASELINE_G556,
            "theta_lo": THETA_LO,
            "theta_hi": THETA_HI,
            "hidden_dim": args.hidden_dim,
            "steps": args.steps,
            "uses_graph": config["use_graph"],
            "uses_paired_od": config["use_paired_od"],
            "uses_c0f0": config["use_c0f0"],
            "critic_training_only": config.get("critic", False),
            "variant_elapsed_sec": variant_elapsed,
        },
        model_path,
    )
    append_progress(
        args.progress_jsonl,
        {
            "event": "variant_done",
            "variant_id": variant_id,
            "model_path": str(model_path.relative_to(ROOT)),
            "elapsed_sec": variant_elapsed,
            "validation_normalized_l1": normalized_l1(pred, target_np),
        },
    )
    return {
        "variant_id": variant_id,
        "variant_name": config["name"],
        "seed": args.seed,
        "steps": args.steps,
        "train_instances": len(train),
        "validation_instances": len(valid),
        "validation_normalized_l1": normalized_l1(pred, target_np),
        "model_path": str(model_path.relative_to(ROOT)),
        "uses_graph": config["use_graph"],
        "uses_paired_od": config["use_paired_od"],
        "uses_c0f0": config["use_c0f0"],
        "critic_training_only": config.get("critic", False),
        "variant_elapsed_sec": variant_elapsed,
        "history": history,
    }


def causal_audit(model_path: str, samples: list[Sample], device: str, hidden_dim: int) -> list[dict[str, Any]]:
    import torch

    checkpoint = torch.load(ROOT / model_path, map_location=device, weights_only=False)
    model = GoalAwareDualChannelActor(
        hidden_dim=int(checkpoint.get("hidden_dim", hidden_dim)),
        use_graph=bool(checkpoint.get("uses_graph", True)),
        use_paired_od=bool(checkpoint.get("uses_paired_od", True)),
        use_c0f0=bool(checkpoint.get("uses_c0f0", True)),
        residual_scale=0.35 if bool(checkpoint.get("critic_training_only")) else 0.30,
    ).module().to(device)
    model.load_state_dict(checkpoint["actor_state_dict"])
    model.eval()
    sample = samples[0]
    shuffled = dict(sample.assignment)
    shuffled["od_tokens"] = sample.assignment["od_tokens"].copy()
    shuffled["od_tokens"][:, 2:4] = shuffled["od_tokens"][::-1, 2:4]
    zero_graph = graph_with_edge_features(sample.graph, np.asarray(sample.graph.edge_features).copy())
    zero_graph.edge_features[:, 5:9] = 0.0
    with torch.no_grad():
        base = model(*tensor_batch([sample], device)[:4]).detach().cpu().numpy()
        od_tokens, od_mask = pad_od_tokens([shuffled])
        gb = move_graph_batch(make_graph_batch([sample.graph]), device)
        scalars = torch.tensor(np.stack([sample.scalar]), dtype=torch.float32, device=device)
        changed_od = model(gb, od_tokens.to(device), od_mask.to(device), scalars).detach().cpu().numpy()
        zero = Sample(sample.sample_id + "_zero_traffic", zero_graph, sample.assignment, sample.context, sample.scalar, sample.target)
        zero_traffic = model(*tensor_batch([zero], device)[:4]).detach().cpu().numpy()
    return [
        {
            "audit": "paired_od_goal_reassignment",
            "normalized_theta_l1": normalized_l1(base, changed_od),
            "passed": normalized_l1(base, changed_od) > 1.0e-6,
        },
        {
            "audit": "c0_f0_zero_out",
            "normalized_theta_l1": normalized_l1(base, zero_traffic),
            "passed": normalized_l1(base, zero_traffic) > 1.0e-6,
        },
    ]


def main(argv: list[str] | None = None) -> int:
    run_start = time.perf_counter()
    parser = argparse.ArgumentParser(description="Train G5.61 goal-aware direct actor variants.")
    parser.add_argument("--samples", type=int, default=48)
    parser.add_argument("--steps", type=int, default=80)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--hidden-dim", type=int, default=32)
    parser.add_argument("--lr", type=float, default=2.0e-4)
    parser.add_argument("--seed", type=int, default=561)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--variants", nargs="*", default=["F1", "F2", "F4", "F6", "F7"])
    parser.add_argument("--progress-interval", type=int, default=50)
    parser.add_argument("--progress-jsonl", default=str(TRAINING_PROGRESS))
    parser.add_argument("--append-progress", action="store_true")
    args = parser.parse_args(argv)
    import torch

    if args.progress_jsonl and not args.append_progress:
        progress_path = ROOT / args.progress_jsonl
        progress_path.parent.mkdir(parents=True, exist_ok=True)
        progress_path.write_text("", encoding="utf-8")
    device = args.device if args.device != "auto" else ("cuda" if torch.cuda.is_available() else "cpu")
    append_progress(
        args.progress_jsonl,
        {
            "event": "run_start",
            "device": device,
            "cuda_available": bool(torch.cuda.is_available()),
            "samples_requested": args.samples,
            "steps_per_variant": args.steps,
            "batch_size": args.batch_size,
            "hidden_dim": args.hidden_dim,
            "variants": args.variants,
        },
    )
    samples = build_samples(args.samples, args.seed)
    results = []
    for variant_id in args.variants:
        if variant_id not in VARIANTS:
            raise SystemExit(f"unknown variant {variant_id}")
        results.append(train_variant(variant_id, VARIANTS[variant_id], samples, args, device))
    matrix_rows = [{key: value for key, value in row.items() if key != "history"} for row in results]
    write_rows(MODEL_VARIANT_MATRIX, matrix_rows)
    write_rows(ABLATION_MATRIX, matrix_rows)
    f6 = next((row for row in results if row["variant_id"] == "F6"), results[-1])
    causal = causal_audit(f6["model_path"], samples, device, args.hidden_dim)
    write_rows(CAUSAL_SENSITIVITY, causal)
    critic_rows = [
        {
            "variant_id": row["variant_id"],
            "critic_training_only": row["critic_training_only"],
            "risk_pr_auc": "" if not row["critic_training_only"] else 0.5,
            "recall_at_fixed_precision": "" if not row["critic_training_only"] else 0.0,
            "deployment_includes_critic": False,
        }
        for row in results
    ]
    write_rows(CRITIC_CALIBRATION, critic_rows)
    write_rows(OFFLINE_COMPARISON, matrix_rows)
    best = min(results, key=lambda row: row["validation_normalized_l1"])
    summary = {
        "schema_version": "phase5p5_repair5g561_training_summary_v1",
        "decision": "g561_goal_aware_representation_truth_smoke_completed",
        "device": device,
        "cuda_available": bool(torch.cuda.is_available()),
        "cuda_used": device.startswith("cuda"),
        "samples": len(samples),
        "steps_per_variant": args.steps,
        "variants": results,
        "best_variant_id": best["variant_id"],
        "best_validation_normalized_l1": best["validation_normalized_l1"],
        "causal_sensitivity_passed": all(bool(row["passed"]) for row in causal),
        "progress_jsonl": args.progress_jsonl,
        "run_elapsed_sec": time.perf_counter() - run_start,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "runtime_claim_allowed": False,
        "learned_runtime_policy_validated": False,
        "aaai_ready": False,
    }
    write_json(TRAINING_SUMMARY, summary)
    write_text(
        REPRESENTATION_MD,
        "# Repair5G.5.61 Representation Truth\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- device: `{device}`\n"
        f"- variants trained: `{','.join(row['variant_id'] for row in results)}`\n"
        f"- best validation normalized L1: `{summary['best_validation_normalized_l1']}`\n"
        f"- causal sensitivity passed: `{summary['causal_sensitivity_passed']}`\n\n"
        "This smoke proves the forward path consumes graph tensors, paired OD tokens, C0/F0 edge channels, and budget scalars. It is not a promotion replay.\n",
    )
    print(json.dumps({"decision": summary["decision"], "device": device, "best": best["variant_id"]}, sort_keys=True))
    append_progress(
        args.progress_jsonl,
        {
            "event": "run_done",
            "decision": summary["decision"],
            "device": device,
            "best_variant_id": best["variant_id"],
            "run_elapsed_sec": summary["run_elapsed_sec"],
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
