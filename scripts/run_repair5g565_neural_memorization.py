from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gcst.opportunity_labels import MIXED_SAFETY_BOUNDARY, NONTRIVIAL_OPPORTUNITY, opportunity_metrics  # noqa: E402
from gcst.real_label_graph_dataset import DEFAULT_CONTEXT_DIR, G560_TRAINING_ROWS  # noqa: E402
from gcst.repaired_set_risk import DEFAULT_REPAIRED_RISK  # noqa: E402
from gcst.rich_training_g565 import checkpoint_payload, evaluate_model, load_examples, train_model  # noqa: E402


ROUND = "phase5p5_repair5g565"
REPORTS = ROOT / "outputs/reports"
TABLES = ROOT / "outputs/tables"
MODEL_DIR = ROOT / "artifacts/models/gcst"


def resolve(path: str | Path) -> Path:
    p = Path(path)
    return p if p.is_absolute() else ROOT / p


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def eligible_examples(examples):
    scored = [(opportunity_metrics(ex.label_context, DEFAULT_REPAIRED_RISK), ex) for ex in examples]
    preferred = [ex for metrics, ex in scored if metrics.opportunity_category in {NONTRIVIAL_OPPORTUNITY, MIXED_SAFETY_BOUNDARY}]
    return preferred or [ex for _metrics, ex in scored if len(ex.label_context.positive_candidates) or len(ex.label_context.harmful_candidates)]


def seeds_for_size(size: int, base_seeds: list[int]) -> list[int]:
    return base_seeds if size >= 16 else base_seeds[:1]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run G5.65 strong repaired-loss neural memorization.")
    parser.add_argument("--rows-path", type=Path, default=G560_TRAINING_ROWS)
    parser.add_argument("--context-dir", type=Path, default=DEFAULT_CONTEXT_DIR)
    parser.add_argument("--max-contexts", type=int, default=160)
    parser.add_argument("--sizes", default="1,4,8,16,32")
    parser.add_argument("--architectures", default="B1,B2,E0,E1,E2")
    parser.add_argument("--seeds", default="565,566,567")
    parser.add_argument("--epochs", type=int, default=40)
    parser.add_argument("--min-epochs", type=int, default=30)
    parser.add_argument("--early-stop-patience", type=int, default=10)
    parser.add_argument("--hidden-dim", type=int, default=64)
    parser.add_argument("--hidden-dims", default="")
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--lr", type=float, default=5.0e-4)
    parser.add_argument("--amp-bf16", action="store_true")
    parser.add_argument("--device", default="auto")
    args = parser.parse_args(argv)

    import torch

    device = "cuda" if args.device == "auto" and torch.cuda.is_available() else ("cpu" if args.device == "auto" else args.device)
    started = time.perf_counter()
    examples = eligible_examples(load_examples(resolve(args.rows_path), resolve(args.context_dir), max_contexts=args.max_contexts))
    sizes = [int(token) for token in args.sizes.split(",") if token.strip()]
    archs = [token.strip().upper() for token in args.architectures.split(",") if token.strip()]
    base_seeds = [int(token) for token in args.seeds.split(",") if token.strip()]
    hidden_dims = [int(token) for token in args.hidden_dims.split(",") if token.strip()] if args.hidden_dims else [args.hidden_dim]
    metric_rows: list[dict[str, Any]] = []
    context_rows: list[dict[str, Any]] = []
    closure_rows: list[dict[str, Any]] = []
    grad_rows: list[dict[str, Any]] = []
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    for size in sizes:
        subset = examples[: min(size, len(examples))]
        if not subset:
            continue
        for hidden_dim in hidden_dims:
            for arch in archs:
                if arch == "E2" and size < 8:
                    continue
                for seed in seeds_for_size(size, base_seeds):
                    model, metrics = train_model(
                        arch,
                        subset,
                        subset,
                        cfg=DEFAULT_REPAIRED_RISK,
                        seed=seed,
                        epochs=args.epochs,
                        lr=args.lr,
                        hidden_dim=hidden_dim,
                        batch_size=min(args.batch_size, len(subset)),
                        device=device,
                        weight_decay=0.0,
                        min_epochs=args.min_epochs,
                        early_stop_patience=args.early_stop_patience,
                        amp_bf16=args.amp_bf16,
                    )
                    suffix = f"_h{hidden_dim}" if len(hidden_dims) > 1 else ""
                    ckpt = MODEL_DIR / f"{ROUND}_memorization_{arch.lower()}_n{len(subset)}_seed{seed}{suffix}.pt"
                    torch.save(checkpoint_payload(arch, model, metrics, DEFAULT_REPAIRED_RISK, hidden_dim), ckpt)
                    mean_risk, rows = evaluate_model(arch, model, subset, cfg=DEFAULT_REPAIRED_RISK, device=device, batch_size=args.batch_size)
                    ckpt_hash = sha256_file(ckpt)
                    row = {
                        "model_kind": arch,
                        "hidden_dim": hidden_dim,
                        "size": len(subset),
                        "seed": seed,
                        "checkpoint_path": str(ckpt.relative_to(ROOT)).replace("\\", "/"),
                        "checkpoint_sha256": ckpt_hash,
                        "mean_train_risk": mean_risk,
                        **metrics,
                    }
                    metric_rows.append(row)
                    grad_rows.append({key: row.get(key, 0.0) for key in row if key.endswith("_grad_norm")} | {"model_kind": arch, "hidden_dim": hidden_dim, "size": len(subset), "seed": seed})
                    for detail in rows:
                        detail.update({"model_kind": arch, "hidden_dim": hidden_dim, "size": len(subset), "seed": seed, "checkpoint_sha256": ckpt_hash})
                        context_rows.append(detail)
                        closure_rows.append(
                            {
                                "evaluation_uid": detail["evaluation_uid"],
                                "model_kind": arch,
                                "hidden_dim": hidden_dim,
                                "size": len(subset),
                                "seed": seed,
                                "oracle_gap": detail["oracle_gap"],
                                "normalized_oracle_regret": detail["normalized_oracle_regret"],
                                "opportunity_category": detail["opportunity_category"],
                                "harmful_loss": detail["harmful_loss"],
                            }
                        )
                    print(json.dumps({"event": "memorization", "arch": arch, "hidden_dim": hidden_dim, "size": len(subset), "seed": seed, "risk": mean_risk}, sort_keys=True), flush=True)
    strong_rows = [row for row in context_rows if row["size"] in {16, 32} and row["opportunity_category"] in {NONTRIVIAL_OPPORTUNITY, MIXED_SAFETY_BOUNDARY}]
    regrets = [float(row["normalized_oracle_regret"]) for row in strong_rows]
    rich_beats = {}
    for size in [16, 32]:
        for seed in base_seeds:
            candidates = [row for row in metric_rows if row["size"] == size and row["seed"] == seed and row["model_kind"] in {"E0", "E1", "E2"}]
            controls = [row for row in metric_rows if row["size"] == size and row["seed"] == seed and row["model_kind"] in {"B1", "B2"}]
            if candidates and controls:
                rich_beats[f"{size}_{seed}"] = min(float(r["mean_train_risk"]) for r in candidates) < min(float(c["mean_train_risk"]) for c in controls)
    strong_pass = bool(regrets and float(np.median(regrets)) < 0.85 and all(rich_beats.values() or [True]))
    summary = {
        "schema_version": f"{ROUND}_neural_memorization_summary_v1",
        "decision": "g565_neural_memorization_strong_pass" if strong_pass else "g565_neural_memorization_failed",
        "device": device,
        "eligible_contexts": len(examples),
        "sizes": sorted(set(row["size"] for row in metric_rows)),
        "architectures": sorted(set(row["model_kind"] for row in metric_rows)),
        "seeds": base_seeds,
        "epochs": args.epochs,
        "min_epochs": args.min_epochs,
        "early_stop_patience": args.early_stop_patience,
        "hidden_dims": hidden_dims,
        "amp_bf16": bool(args.amp_bf16),
        "loss_config_sha256": DEFAULT_REPAIRED_RISK.sha256,
        "median_16_32_opportunity_normalized_oracle_regret": float(np.median(regrets)) if regrets else None,
        "rows": len(metric_rows),
        "context_rows": len(context_rows),
        "elapsed_sec": time.perf_counter() - started,
    }
    write_rows(TABLES / f"{ROUND}_neural_memorization_by_context.csv", context_rows)
    write_rows(TABLES / f"{ROUND}_oracle_gap_closure.csv", closure_rows)
    write_rows(TABLES / f"{ROUND}_branch_gradient_audit.csv", grad_rows)
    write_rows(TABLES / f"{ROUND}_neural_memorization_runs.csv", metric_rows)
    write_json(REPORTS / f"{ROUND}_neural_memorization_summary.json", summary)
    print(json.dumps({"decision": summary["decision"], "rows": len(metric_rows)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
