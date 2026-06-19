from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from types import SimpleNamespace
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from run_repair5g561_materialization_contract import claims, sha256_file  # noqa: E402
from train_repair5g561_goal_aware_actor import (  # noqa: E402
    MODEL_DIR,
    TRAINING_SUMMARY,
    VARIANTS,
    build_samples,
    causal_audit,
    train_variant,
)


ROUND = "phase5p5_repair5g561"
PRIMARY_VARIANTS = ["F0", "F1", "F4", "F6", "F7"]
PRIMARY_SEEDS = [561, 562, 563]
MATRIX_CSV = Path(f"outputs/tables/{ROUND}_primary_seed_training_matrix.csv")
CAUSAL_CSV = Path(f"outputs/tables/{ROUND}_primary_seed_causal_audit.csv")
PROGRESS_JSONL = Path(f"outputs/reports/{ROUND}_primary_seed_training_progress.jsonl")
SUMMARY_JSON = Path(f"outputs/reports/{ROUND}_primary_seed_training_summary.json")
REPORT_MD = Path(f"outputs/reports/{ROUND}_primary_seed_training.md")


def resolve(path: str | Path) -> Path:
    p = Path(path)
    return p if p.is_absolute() else ROOT / p


def read_json(path: str | Path) -> dict[str, Any]:
    p = resolve(path)
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


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
    p.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: str | Path, text: str) -> None:
    p = resolve(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def primary_seed_plan(seeds: list[int] | None = None, variants: list[str] | None = None) -> list[dict[str, Any]]:
    seeds = seeds or PRIMARY_SEEDS
    variants = variants or PRIMARY_VARIANTS
    return [
        {
            "seed": int(seed),
            "variant_id": variant,
            "variant_name": VARIANTS[variant]["name"],
            "required_primary_variant": variant in PRIMARY_VARIANTS,
        }
        for seed in seeds
        for variant in variants
    ]


def existing_seed561_rows() -> dict[str, dict[str, Any]]:
    summary = read_json(TRAINING_SUMMARY)
    out: dict[str, dict[str, Any]] = {}
    for row in summary.get("variants", []):
        variant = str(row.get("variant_id", ""))
        if variant in PRIMARY_VARIANTS and resolve(str(row.get("model_path", ""))).exists():
            copied = dict(row)
            copied["seed"] = int(row.get("seed") or 561)
            copied["training_source"] = "existing_g561_training_summary_seed561"
            copied["model_sha256"] = sha256_file(resolve(str(row.get("model_path", ""))))
            out[variant] = copied
    return out


def make_args(seed: int, args: argparse.Namespace, progress_jsonl: str) -> SimpleNamespace:
    return SimpleNamespace(
        seed=seed,
        steps=args.steps,
        batch_size=args.batch_size,
        hidden_dim=args.hidden_dim,
        lr=args.lr,
        progress_interval=args.progress_interval,
        progress_jsonl=progress_jsonl,
    )


def train_missing_rows(args: argparse.Namespace, device: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    causal_rows: list[dict[str, Any]] = []
    existing = existing_seed561_rows()
    progress_path = resolve(PROGRESS_JSONL)
    progress_path.parent.mkdir(parents=True, exist_ok=True)
    progress_path.write_text("", encoding="utf-8")
    for seed in args.seeds:
        samples = build_samples(args.samples, int(seed))
        train_args = make_args(int(seed), args, str(PROGRESS_JSONL))
        for variant in args.variants:
            if variant not in VARIANTS:
                raise SystemExit(f"unknown variant {variant}")
            if int(seed) == 561 and variant in existing:
                row = dict(existing[variant])
            else:
                row = train_variant(variant, VARIANTS[variant], samples, train_args, device)
                row["training_source"] = "new_primary_seed_training"
                row["model_sha256"] = sha256_file(resolve(row["model_path"]))
            row.update({"seed": int(seed), **claims()})
            rows.append(row)
        f6 = next((row for row in rows if row["seed"] == int(seed) and row["variant_id"] == "F6"), None)
        if f6 and resolve(str(f6.get("model_path", ""))).exists():
            for audit in causal_audit(str(f6["model_path"]), samples, device, args.hidden_dim):
                causal_rows.append({"seed": int(seed), "variant_id": "F6", **audit, **claims()})
    return rows, causal_rows


def summarize(rows: list[dict[str, Any]], causal_rows: list[dict[str, Any]], args: argparse.Namespace, device: str, elapsed: float) -> dict[str, Any]:
    by_variant: dict[str, set[int]] = defaultdict(set)
    by_seed: dict[int, set[str]] = defaultdict(set)
    for row in rows:
        by_variant[str(row.get("variant_id", ""))].add(int(row.get("seed", 0)))
        by_seed[int(row.get("seed", 0))].add(str(row.get("variant_id", "")))
    missing = [
        {"variant_id": variant, "missing_seeds": sorted(set(args.seeds) - by_variant.get(variant, set()))}
        for variant in args.variants
        if set(args.seeds) - by_variant.get(variant, set())
    ]
    validation_by_variant = []
    for variant in args.variants:
        group = [row for row in rows if row.get("variant_id") == variant]
        values = [float(row.get("validation_normalized_l1", 0.0)) for row in group if str(row.get("validation_normalized_l1", "")).strip()]
        validation_by_variant.append(
            {
                "variant_id": variant,
                "seeds": sorted(by_variant.get(variant, set())),
                "seed_count": len(by_variant.get(variant, set())),
                "mean_validation_normalized_l1": sum(values) / len(values) if values else None,
                "best_validation_normalized_l1": min(values) if values else None,
            }
        )
    causal_passed = bool(causal_rows) and all(bool(row.get("passed")) for row in causal_rows)
    all_primary_variants = set(PRIMARY_VARIANTS).issubset({str(row.get("variant_id")) for row in rows})
    three_seed_gate = not missing and all(len(by_variant.get(variant, set())) >= 3 for variant in args.variants)
    return {
        "schema_version": f"{ROUND}_primary_seed_training_summary_v1",
        "decision": "g561_primary_seed_training_completed" if three_seed_gate and causal_passed else "g561_primary_seed_training_incomplete_continue",
        "device": device,
        "cuda_used": str(device).startswith("cuda"),
        "seeds": list(map(int, args.seeds)),
        "variants": args.variants,
        "primary_variant_count": len(set(args.variants)),
        "all_required_primary_variants_present": all_primary_variants,
        "three_training_seeds_complete": three_seed_gate,
        "missing_seed_coverage": missing,
        "steps_per_new_training": args.steps,
        "samples_per_seed": args.samples,
        "training_rows": len(rows),
        "new_training_rows": sum(1 for row in rows if row.get("training_source") == "new_primary_seed_training"),
        "reused_seed561_rows": sum(1 for row in rows if row.get("training_source") == "existing_g561_training_summary_seed561"),
        "causal_sensitivity_passed": causal_passed,
        "causal_audit_rows": len(causal_rows),
        "validation_by_variant": validation_by_variant,
        "seed_variant_counts": {str(seed): len(values) for seed, values in sorted(by_seed.items())},
        "progress_jsonl": str(PROGRESS_JSONL).replace("\\", "/"),
        "run_elapsed_sec": elapsed,
        "next_required_gate": "write final failure attribution/fine-tune decision from multi-seed + replay evidence",
        **claims(),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Train/evaluate three seeds for G5.61 primary variants.")
    parser.add_argument("--seeds", nargs="*", type=int, default=PRIMARY_SEEDS)
    parser.add_argument("--variants", nargs="*", default=PRIMARY_VARIANTS)
    parser.add_argument("--samples", type=int, default=128)
    parser.add_argument("--steps", type=int, default=500)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--hidden-dim", type=int, default=32)
    parser.add_argument("--lr", type=float, default=2.0e-4)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--progress-interval", type=int, default=250)
    parser.add_argument("--plan-only", action="store_true")
    args = parser.parse_args(argv)
    if args.plan_only:
        plan = primary_seed_plan(args.seeds, args.variants)
        print(json.dumps({"decision": "g561_primary_seed_training_plan_created", "jobs": len(plan), "plan": plan}, sort_keys=True))
        return 0

    import torch

    start = time.perf_counter()
    device = args.device if args.device != "auto" else ("cuda" if torch.cuda.is_available() else "cpu")
    rows, causal_rows = train_missing_rows(args, device)
    summary = summarize(rows, causal_rows, args, device, time.perf_counter() - start)
    matrix = [{key: value for key, value in row.items() if key != "history"} for row in rows]
    write_rows(MATRIX_CSV, matrix)
    write_rows(CAUSAL_CSV, causal_rows)
    write_json(SUMMARY_JSON, summary)
    write_text(
        REPORT_MD,
        "# Repair5G.5.61 Primary Seed Training\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- variants: `{','.join(args.variants)}`\n"
        f"- seeds: `{','.join(map(str, args.seeds))}`\n"
        f"- three-seed gate: `{summary['three_training_seeds_complete']}`\n"
        f"- new training rows: `{summary['new_training_rows']}`\n"
        f"- reused seed561 rows: `{summary['reused_seed561_rows']}`\n"
        f"- causal sensitivity passed: `{summary['causal_sensitivity_passed']}`\n\n"
        "This is primary-variant seed coverage evidence. It does not open Phase5.5, Phase6, runtime, learned-policy, or AAAI claims.\n",
    )
    print(
        json.dumps(
            {
                "decision": summary["decision"],
                "training_rows": summary["training_rows"],
                "three_training_seeds_complete": summary["three_training_seeds_complete"],
                "device": device,
            },
            sort_keys=True,
        )
    )
    return 0 if summary["decision"] == "g561_primary_seed_training_completed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
