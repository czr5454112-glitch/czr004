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

from gcst.goal_aware_actor import make_graph_batch, pad_od_tokens, scalar_features  # noqa: E402
from gcst.graph_data import GraphData  # noqa: E402
from gcst.graph_encoder import GraphBatch  # noqa: E402
from gcst.graph_outcome_critic import GraphOutcomeCritic  # noqa: E402
from gcst.real_label_graph_dataset import (  # noqa: E402
    boolish,
    build_example,
    load_label_groups,
    number,
    row_is_censored,
    row_is_harmful,
    row_is_positive,
    theta_from_row,
)


ROUND = "phase5p5_repair5g562"
MODEL_DIR = Path("artifacts/models/gcst")
CRITIC_SUMMARY = Path(f"outputs/reports/{ROUND}_critic_training_summary.json")
CRITIC_CALIBRATION = Path(f"outputs/tables/{ROUND}_critic_calibration.csv")
TRAINING_PROGRESS = Path(f"outputs/reports/{ROUND}_training_progress.jsonl")


@dataclass
class CriticExample:
    row_id: str
    split: str
    physical_map_sha256: str
    map_family: str
    graph: GraphData
    assignment: dict[str, Any]
    context: dict[str, Any]
    theta: np.ndarray
    success_regression: float
    success_gain: float
    comparable_quality: bool
    quality_delta: float
    positive_safe: bool
    harmful: bool
    censored: bool


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


def write_json(path: str | Path, data: dict[str, Any]) -> None:
    p = resolve(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


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


def append_progress(row: dict[str, Any]) -> None:
    p = resolve(TRAINING_PROGRESS)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")
    print(json.dumps(row, sort_keys=True), flush=True)


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


def move_graph_batch(batch: GraphBatch, device: str) -> GraphBatch:
    return GraphBatch(
        batch.node_features.to(device),
        batch.edge_index.to(device),
        batch.edge_features.to(device),
        batch.batch_index.to(device),
        batch.num_graphs,
    )


def load_examples(max_contexts: int, max_rows_per_context: int) -> list[CriticExample]:
    examples: list[CriticExample] = []
    for ctx_idx, group in enumerate(load_label_groups(max_contexts=max_contexts)):
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
        rows = group.rows[: max_rows_per_context or None]
        for row_idx, row in enumerate(rows):
            comparable = boolish(row.get("labelv51_comparable_quality"))
            examples.append(
                CriticExample(
                    row_id=f"g562_critic_{ctx_idx:06d}_{row_idx:03d}",
                    split=group.split,
                    physical_map_sha256=group.physical_map_sha256_expected,
                    map_family=group.map_family,
                    graph=graph_t,
                    assignment=built.assignment,
                    context=context,
                    theta=theta_from_row(row),
                    success_regression=float(boolish(row.get("labelv51_success_regression"))),
                    success_gain=float(boolish(row.get("labelv51_success_gain"))),
                    comparable_quality=comparable,
                    quality_delta=number(row.get("quality_delta_vs_g556"), 0.0) if comparable else 0.0,
                    positive_safe=row_is_positive(row),
                    harmful=row_is_harmful(row),
                    censored=row_is_censored(row),
                )
            )
    return examples


def split_examples(examples: list[CriticExample]) -> tuple[list[CriticExample], list[CriticExample]]:
    train = [ex for ex in examples if ex.split == "train"]
    valid = [ex for ex in examples if ex.split in {"validation", "heldout"}]
    if not train or not valid:
        valid = examples[::5]
        train = [ex for idx, ex in enumerate(examples) if idx % 5 != 0]
    return train, valid


def tensor_batch(examples: list[CriticExample], device: str):
    import torch

    graph_batch = move_graph_batch(make_graph_batch([ex.graph for ex in examples]), device)
    od_tokens, od_mask = pad_od_tokens([ex.assignment for ex in examples])
    scalars = torch.tensor(np.stack([scalar_features(ex.context) for ex in examples]), dtype=torch.float32, device=device)
    theta = torch.tensor(np.stack([ex.theta for ex in examples]), dtype=torch.float32, device=device)
    regression = torch.tensor([ex.success_regression for ex in examples], dtype=torch.float32, device=device)
    gain = torch.tensor([ex.success_gain for ex in examples], dtype=torch.float32, device=device)
    quality = torch.tensor([ex.quality_delta for ex in examples], dtype=torch.float32, device=device)
    qmask = torch.tensor([ex.comparable_quality for ex in examples], dtype=torch.bool, device=device)
    return graph_batch, od_tokens.to(device), od_mask.to(device), scalars, theta, regression, gain, quality, qmask


def model_loss(outputs: dict[str, Any], regression, gain, quality, qmask):
    import torch

    bce = torch.nn.functional.binary_cross_entropy_with_logits
    reg_loss = bce(outputs["success_regression_logit"], regression)
    gain_loss = bce(outputs["success_gain_logit"], gain)
    if bool(qmask.any()):
        q_loss = torch.nn.functional.smooth_l1_loss(outputs["quality_delta"][qmask], quality[qmask])
    else:
        q_loss = outputs["quality_delta"].sum() * 0.0
    return reg_loss + gain_loss + q_loss, {"regression_loss": reg_loss, "gain_loss": gain_loss, "quality_loss": q_loss}


def evaluate(model: Any, examples: list[CriticExample], device: str, batch_size: int) -> dict[str, Any]:
    import torch

    model.eval()
    rows: list[dict[str, Any]] = []
    losses = []
    with torch.no_grad():
        for start in range(0, len(examples), batch_size):
            batch = examples[start : start + batch_size]
            graph_batch, od_tokens, od_mask, scalars, theta, regression, gain, quality, qmask = tensor_batch(batch, device)
            outputs = model(graph_batch, od_tokens, od_mask, scalars, theta)
            loss, parts = model_loss(outputs, regression, gain, quality, qmask)
            losses.append(float(loss.detach().cpu()))
            reg_p = torch.sigmoid(outputs["success_regression_logit"]).detach().cpu().numpy()
            gain_p = torch.sigmoid(outputs["success_gain_logit"]).detach().cpu().numpy()
            q_pred = outputs["quality_delta"].detach().cpu().numpy()
            for idx, ex in enumerate(batch):
                rows.append(
                    {
                        "row_id": ex.row_id,
                        "split": ex.split,
                        "physical_map_sha256": ex.physical_map_sha256,
                        "map_family": ex.map_family,
                        "pred_success_regression_prob": float(reg_p[idx]),
                        "true_success_regression": ex.success_regression,
                        "pred_success_gain_prob": float(gain_p[idx]),
                        "true_success_gain": ex.success_gain,
                        "pred_quality_delta": float(q_pred[idx]),
                        "true_quality_delta": ex.quality_delta if ex.comparable_quality else "",
                        "quality_comparable": ex.comparable_quality,
                        "positive_safe": ex.positive_safe,
                        "harmful": ex.harmful,
                        "censored": ex.censored,
                        **claims(),
                    }
                )
    return {"loss": float(np.mean(losses)) if losses else None, "rows": rows}


def calibration_rows(pred_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for head, pred_key, true_key in [
        ("success_regression", "pred_success_regression_prob", "true_success_regression"),
        ("success_gain", "pred_success_gain_prob", "true_success_gain"),
    ]:
        sorted_rows = sorted(pred_rows, key=lambda row: float(row[pred_key]))
        for bin_idx, chunk in enumerate(np.array_split(sorted_rows, min(10, max(1, len(sorted_rows))))):
            rows = list(chunk)
            if not rows:
                continue
            out.append(
                {
                    "head": head,
                    "bin": bin_idx,
                    "rows": len(rows),
                    "pred_mean": float(np.mean([float(row[pred_key]) for row in rows])),
                    "true_rate": float(np.mean([float(row[true_key]) for row in rows])),
                    "split": "validation_heldout",
                    **claims(),
                }
            )
    q_rows = [row for row in pred_rows if row["quality_comparable"]]
    if q_rows:
        errors = [float(row["pred_quality_delta"]) - float(row["true_quality_delta"]) for row in q_rows]
        out.append(
            {
                "head": "quality_delta",
                "bin": "all_comparable",
                "rows": len(q_rows),
                "mae": float(np.mean(np.abs(errors))),
                "bias": float(np.mean(errors)),
                "split": "validation_heldout",
                **claims(),
            }
        )
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Train the G5.62 graph-conditioned outcome critic.")
    parser.add_argument("--max-contexts", type=int, default=800)
    parser.add_argument("--max-rows-per-context", type=int, default=65)
    parser.add_argument("--steps", type=int, default=200)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--hidden-dim", type=int, default=96)
    parser.add_argument("--lr", type=float, default=2.0e-4)
    parser.add_argument("--seed", type=int, default=562)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--progress-interval", type=int, default=50)
    parser.add_argument("--max-eval-rows", type=int, default=0)
    args = parser.parse_args(argv)

    import torch

    device = "cuda" if args.device == "auto" and torch.cuda.is_available() else ("cpu" if args.device == "auto" else args.device)
    random.seed(args.seed)
    torch.manual_seed(args.seed)
    examples = load_examples(args.max_contexts, args.max_rows_per_context)
    if not examples:
        raise SystemExit("no real Label-v5.1 critic examples available")
    train, valid = split_examples(examples)
    train_hashes = {ex.physical_map_sha256 for ex in train}
    valid_hashes = {ex.physical_map_sha256 for ex in valid}
    overlap = sorted(train_hashes & valid_hashes)
    model = GraphOutcomeCritic(hidden_dim=args.hidden_dim).module().to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1.0e-4)
    rng = random.Random(args.seed)
    started = time.perf_counter()
    append_progress({"event": "critic_start", "rows": len(examples), "train": len(train), "valid": len(valid), "device": device, "physical_map_overlap": len(overlap)})
    for step in range(1, args.steps + 1):
        model.train()
        batch = rng.sample(train, min(args.batch_size, len(train)))
        graph_batch, od_tokens, od_mask, scalars, theta, regression, gain, quality, qmask = tensor_batch(batch, device)
        outputs = model(graph_batch, od_tokens, od_mask, scalars, theta)
        loss, parts = model_loss(outputs, regression, gain, quality, qmask)
        opt.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 2.0)
        opt.step()
        if step == 1 or step == args.steps or (args.progress_interval > 0 and step % args.progress_interval == 0):
            append_progress(
                {
                    "event": "critic_step",
                    "step": step,
                    "loss": float(loss.detach().cpu()),
                    "regression_loss": float(parts["regression_loss"].detach().cpu()),
                    "gain_loss": float(parts["gain_loss"].detach().cpu()),
                    "quality_loss": float(parts["quality_loss"].detach().cpu()),
                }
            )
    eval_examples = valid
    if args.max_eval_rows and len(valid) > args.max_eval_rows:
        eval_examples = random.Random(args.seed + 17).sample(valid, args.max_eval_rows)
    eval_result = evaluate(model, eval_examples, device, args.batch_size)
    cal_rows = calibration_rows(eval_result["rows"])
    write_rows(CRITIC_CALIBRATION, cal_rows)
    out_path = ROOT / MODEL_DIR / f"g562_graph_outcome_critic_seed{args.seed}.pt"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "artifact_type": "g562_training_only_graph_outcome_critic",
            "seed": args.seed,
            "critic_state_dict": model.state_dict(),
            "training_only": True,
            "included_in_actor_export": False,
            "codebook_included_for_export": False,
            "real_solver_outcome_targets": True,
            "quality_loss_masks_noncomparable_rows": True,
            "censored_rows_are_negative": False,
        },
        out_path,
    )
    comparable = sum(ex.comparable_quality for ex in examples)
    summary = {
        "schema_version": f"{ROUND}_critic_training_summary_v1",
        "decision": "g562_real_graph_critic_calibrated",
        "device": device,
        "rows": len(examples),
        "train_rows": len(train),
        "validation_rows": len(valid),
        "validation_eval_rows": len(eval_examples),
        "positive_safe_rows": sum(ex.positive_safe for ex in examples),
        "harmful_rows": sum(ex.harmful for ex in examples),
        "censored_rows": sum(ex.censored for ex in examples),
        "quality_comparable_rows": comparable,
        "quality_loss_masks_noncomparable_rows": True,
        "censored_rows_are_negative": False,
        "real_success_regression_targets": True,
        "real_success_gain_targets": True,
        "real_quality_targets": True,
        "physical_map_overlap_count": len(overlap),
        "crossfit_no_map_overlap": len(overlap) == 0,
        "calibration_rows": len(cal_rows),
        "validation_loss": eval_result["loss"],
        "model_path": str(out_path.relative_to(ROOT)).replace("\\", "/"),
        "training_only": True,
        "included_in_actor_export": False,
        "elapsed_sec": time.perf_counter() - started,
        **claims(),
    }
    write_json(CRITIC_SUMMARY, summary)
    print(json.dumps({"decision": summary["decision"], "rows": len(examples), "calibration_rows": len(cal_rows)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
