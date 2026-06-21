from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

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


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def read_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run G5.65 expanded training only when expansion was triggered.")
    parser.add_argument("--rows-path", type=Path, default=G560_TRAINING_ROWS)
    parser.add_argument("--context-dir", type=Path, default=DEFAULT_CONTEXT_DIR)
    parser.add_argument("--max-contexts", type=int, default=0)
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--min-epochs", type=int, default=30)
    parser.add_argument("--early-stop-patience", type=int, default=10)
    parser.add_argument("--hidden-dim", type=int, default=64)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--seed", type=int, default=565)
    parser.add_argument("--seeds", default="565,566,567")
    parser.add_argument("--architectures", default="E0,E1,E2")
    parser.add_argument("--amp-bf16", action="store_true")
    parser.add_argument("--device", default="auto")
    args = parser.parse_args(argv)

    import torch

    started = time.perf_counter()
    expansion = read_json(REPORTS / f"{ROUND}_context_expansion_summary.json")
    manifest = read_rows(TABLES / f"{ROUND}_context_expansion_manifest.csv")
    if expansion.get("decision") != "g565_context_expansion_manifest_ready" or not manifest:
        summary = {
            "schema_version": f"{ROUND}_expanded_training_summary_v1",
            "decision": "g565_expanded_training_not_triggered",
            "context_expansion_decision": expansion.get("decision"),
            "manifest_rows": len(manifest),
            "elapsed_sec": time.perf_counter() - started,
        }
        write_rows(TABLES / f"{ROUND}_expanded_training_rows.csv", [])
        write_json(REPORTS / f"{ROUND}_expanded_training_summary.json", summary)
        print(json.dumps(summary, sort_keys=True))
        return 0
    device = "cuda" if args.device == "auto" and torch.cuda.is_available() else ("cpu" if args.device == "auto" else args.device)
    manifest_uids = {str(row.get("g560_evaluation_uid", "")) for row in manifest if row.get("g560_evaluation_uid")}
    effective_max_contexts = max(int(args.max_contexts), len(manifest_uids)) if int(args.max_contexts) > 0 else 0
    all_examples = load_examples(resolve(args.rows_path), resolve(args.context_dir), max_contexts=effective_max_contexts)
    examples = [ex for ex in all_examples if ex.evaluation_uid in manifest_uids]
    missing_manifest_uids = sorted(manifest_uids - {ex.evaluation_uid for ex in examples})
    if missing_manifest_uids:
        summary = {
            "schema_version": f"{ROUND}_expanded_training_summary_v1",
            "decision": "g565_expanded_training_blocked_missing_manifest_contexts",
            "context_expansion_decision": expansion.get("decision"),
            "manifest_rows": len(manifest),
            "manifest_uids": len(manifest_uids),
            "requested_max_contexts": args.max_contexts,
            "effective_max_contexts": effective_max_contexts,
            "loaded_examples": len(all_examples),
            "matched_manifest_examples": len(examples),
            "missing_manifest_contexts": len(missing_manifest_uids),
            "missing_manifest_context_samples": missing_manifest_uids[:20],
            "elapsed_sec": time.perf_counter() - started,
        }
        write_rows(TABLES / f"{ROUND}_expanded_training_rows.csv", [])
        write_json(REPORTS / f"{ROUND}_expanded_training_summary.json", summary)
        print(json.dumps(summary, sort_keys=True))
        return 2
    valid = [ex for idx, ex in enumerate(examples) if idx % 5 == 0]
    train = [ex for idx, ex in enumerate(examples) if idx % 5 != 0]
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    seeds = [int(token) for token in args.seeds.split(",") if token.strip()] if args.seeds else [int(args.seed)]
    architectures = [token.strip().upper() for token in args.architectures.split(",") if token.strip()]
    for arch in architectures:
        for seed in seeds:
            model, metrics = train_model(
                arch,
                train,
                valid,
                cfg=DEFAULT_REPAIRED_RISK,
                seed=seed,
                epochs=args.epochs,
                lr=5.0e-4,
                hidden_dim=args.hidden_dim,
                batch_size=args.batch_size,
                device=device,
                weight_decay=0.0,
                min_epochs=args.min_epochs,
                early_stop_patience=args.early_stop_patience,
                amp_bf16=args.amp_bf16,
            )
            risk, _ = evaluate_model(arch, model, valid, cfg=DEFAULT_REPAIRED_RISK, device=device, batch_size=args.batch_size)
            ckpt = MODEL_DIR / f"{ROUND}_expanded_{arch.lower()}_seed{seed}.pt"
            torch.save(checkpoint_payload(arch, model, metrics, DEFAULT_REPAIRED_RISK, args.hidden_dim), ckpt)
            rows.append({"model_kind": arch, "seed": seed, "validation_risk": risk, "checkpoint_path": str(ckpt.relative_to(ROOT)).replace("\\", "/"), **metrics})
    summary = {
        "schema_version": f"{ROUND}_expanded_training_summary_v1",
        "decision": "g565_expanded_training_completed",
        "device": device,
        "train_contexts": len(train),
        "validation_contexts": len(valid),
        "manifest_rows": len(manifest),
        "manifest_uids": len(manifest_uids),
        "requested_max_contexts": args.max_contexts,
        "effective_max_contexts": effective_max_contexts,
        "loaded_examples": len(all_examples),
        "matched_manifest_examples": len(examples),
        "rows": len(rows),
        "seeds": seeds,
        "architectures": architectures,
        "epochs": args.epochs,
        "min_epochs": args.min_epochs,
        "early_stop_patience": args.early_stop_patience,
        "amp_bf16": bool(args.amp_bf16),
        "elapsed_sec": time.perf_counter() - started,
    }
    write_rows(TABLES / f"{ROUND}_expanded_training_rows.csv", rows)
    write_json(REPORTS / f"{ROUND}_expanded_training_summary.json", summary)
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
