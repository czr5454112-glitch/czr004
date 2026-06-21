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

from gcst.real_label_graph_dataset import DEFAULT_CONTEXT_DIR, G560_TRAINING_ROWS  # noqa: E402
from gcst.opportunity_labels import (  # noqa: E402
    MIXED_SAFETY_BOUNDARY,
    NONTRIVIAL_OPPORTUNITY,
    TRIVIAL_G556_OPTIMAL,
    UNSUPPORTED_CENSORED,
)
from gcst.repaired_set_risk import DEFAULT_REPAIRED_RISK  # noqa: E402
from gcst.rich_training_g565 import checkpoint_payload, evaluate_model, load_examples, train_model  # noqa: E402
from gcst.scaling_dataset import stable_hash, validation_manifest_sha256  # noqa: E402


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


def physical_folds(examples, folds: int, seed: int):
    groups = sorted({ex.physical_map_sha256 for ex in examples}, key=lambda key: stable_hash(key, seed))
    out = []
    for fold in range(folds):
        valid_groups = {group for idx, group in enumerate(groups) if idx % folds == fold}
        valid = [ex for ex in examples if ex.physical_map_sha256 in valid_groups]
        train = [ex for ex in examples if ex.physical_map_sha256 not in valid_groups]
        out.append((fold, train, valid))
    return out


def parse_fold_indices(raw: str) -> set[int] | None:
    tokens = [token.strip() for token in raw.split(",") if token.strip()]
    if not tokens:
        return None
    indices = {int(token) for token in tokens}
    if any(index < 0 for index in indices):
        raise ValueError("--fold-indices must be non-negative")
    return indices


def nested_prefix(train, sizes: list[str], seed: int):
    ordered = sorted(train, key=lambda ex: stable_hash(ex.evaluation_uid, seed))
    out: list[tuple[str, list[Any]]] = []
    for token in sizes:
        if token == "all":
            out.append(("all", ordered))
        else:
            size = min(int(token), len(ordered))
            out.append((str(size), ordered[:size]))
    return out


def mean_or_none(values: list[float]) -> float | None:
    finite = [float(value) for value in values if np.isfinite(float(value))]
    return float(np.mean(finite)) if finite else None


def variance_or_none(values: list[float]) -> float | None:
    finite = [float(value) for value in values if np.isfinite(float(value))]
    return float(np.var(finite)) if finite else None


def aggregate_validation_details(details: list[dict[str, Any]]) -> dict[str, Any]:
    opportunity = [row for row in details if row.get("opportunity_category") == NONTRIVIAL_OPPORTUNITY]
    mixed = [row for row in details if row.get("opportunity_category") == MIXED_SAFETY_BOUNDARY]
    trivial = [row for row in details if row.get("opportunity_category") == TRIVIAL_G556_OPTIMAL]
    censored = [row for row in details if row.get("opportunity_category") == UNSUPPORTED_CENSORED]
    positive_rows = [row for row in details if float(row.get("positive_loss", 0.0)) > 0.0 or float(row.get("oracle_gap", 0.0)) > 0.0]
    return {
        "all_context_repaired_risk": mean_or_none([float(row.get("actor_risk", 0.0)) for row in details]),
        "opportunity_context_normalized_regret": mean_or_none([float(row.get("normalized_oracle_regret", 0.0)) for row in opportunity]),
        "mixed_boundary_harmful_violation": mean_or_none([float(row.get("harmful_loss", 0.0)) for row in mixed]),
        "trivial_context_false_deviation": mean_or_none([float(row.get("distance_to_g556", 0.0)) for row in trivial]),
        "censored_context_trust": mean_or_none([float(row.get("trust_loss", 0.0)) for row in censored]),
        "positive_mode_mean_loss": mean_or_none([float(row.get("positive_loss", 0.0)) for row in positive_rows]),
        "positive_mode_capture_rate": mean_or_none([1.0 if float(row.get("positive_loss", 0.0)) <= 1.0e-4 else 0.0 for row in positive_rows]),
        "theta_distance_variance": variance_or_none([float(row.get("distance_to_g556", 0.0)) for row in details]),
        "opportunity_contexts_evaluated": len(opportunity),
        "mixed_boundary_contexts_evaluated": len(mixed),
        "trivial_contexts_evaluated": len(trivial),
        "censored_contexts_evaluated": len(censored),
    }


def size_sort_key(value: str) -> int:
    return 10**9 if str(value) == "all" else int(value)


def paired_bootstrap_ci(values: list[float], *, seed: int = 565, reps: int = 2000) -> tuple[float | None, float | None]:
    finite = [float(value) for value in values if np.isfinite(float(value))]
    if not finite:
        return None, None
    rng = np.random.default_rng(seed)
    arr = np.asarray(finite, dtype=np.float64)
    means = []
    for _ in range(int(reps)):
        sample = arr[rng.integers(0, len(arr), size=len(arr))]
        means.append(float(np.mean(sample)))
    means.sort()
    return float(means[int(0.025 * (len(means) - 1))]), float(means[int(0.975 * (len(means) - 1))])


def paired_first_last_effects(method_rows: list[dict[str, Any]], labels: list[str]) -> list[dict[str, Any]]:
    if len(labels) < 2:
        return []
    first, last = labels[0], labels[-1]
    by_key: dict[tuple[Any, Any], dict[str, list[float]]] = {}
    for row in method_rows:
        label = str(row["size_label"])
        if label not in {first, last}:
            continue
        key = (row.get("fold"), row.get("seed"))
        by_key.setdefault(key, {}).setdefault(label, []).append(float(row["validation_risk"]))
    effects: list[dict[str, Any]] = []
    for (fold, seed), buckets in sorted(by_key.items()):
        if first in buckets and last in buckets:
            first_risk = float(np.median(buckets[first]))
            last_risk = float(np.median(buckets[last]))
            effects.append({"fold": fold, "seed": seed, "first_risk": first_risk, "last_risk": last_risk, "effect": first_risk - last_risk})
    return effects


def method_stats(rows: list[dict[str, Any]]) -> dict[str, Any]:
    stats: dict[str, Any] = {"schema_version": f"{ROUND}_scaling_statistics_v1", "methods": {}}
    for method in sorted({row["model_kind"] for row in rows}):
        method_rows = [row for row in rows if row["model_kind"] == method]
        by_size: dict[str, list[float]] = {}
        for row in method_rows:
            by_size.setdefault(str(row["size_label"]), []).append(float(row["validation_risk"]))
        labels = sorted(by_size, key=size_sort_key)
        medians = [float(np.median(by_size[label])) for label in labels]
        first_last = (medians[0] - medians[-1]) if len(medians) >= 2 else 0.0
        paired = paired_first_last_effects(method_rows, labels)
        paired_effects = [float(row["effect"]) for row in paired]
        ci_low, ci_high = paired_bootstrap_ci(paired_effects)
        by_fold_effect: dict[Any, list[float]] = {}
        by_seed_effect: dict[Any, list[float]] = {}
        for item in paired:
            by_fold_effect.setdefault(item["fold"], []).append(float(item["effect"]))
            by_seed_effect.setdefault(item["seed"], []).append(float(item["effect"]))
        fold_effects = [float(np.median(values)) for values in by_fold_effect.values()]
        seed_effects = [float(np.median(values)) for values in by_seed_effect.values()]
        folds_improved_fraction = sum(effect > 0.0 for effect in fold_effects) / max(1, len(fold_effects)) if fold_effects else None
        seeds_improved_fraction = sum(effect > 0.0 for effect in seed_effects) / max(1, len(seed_effects)) if seed_effects else None
        paired_mean = float(np.mean(paired_effects)) if paired_effects else None
        valid_scaling_gate = bool(len(medians) >= 2 and medians[-1] < medians[0] and folds_improved_fraction is not None and folds_improved_fraction > 0.5 and ci_low is not None and ci_low > 0.0)
        stats["methods"][method] = {
            "size_labels": labels,
            "median_validation_risk_by_size": {label: med for label, med in zip(labels, medians)},
            "seed_variance_validation_risk_by_size": {label: float(np.var(by_size[label])) for label in labels},
            "first_to_last_validation_risk_reduction": float(first_last),
            "paired_fold_seed_effects": paired,
            "paired_bootstrap_first_to_last_effect_mean": paired_mean,
            "paired_bootstrap_first_to_last_effect_ci95": [ci_low, ci_high],
            "fold_effects": {str(key): float(np.median(values)) for key, values in by_fold_effect.items()},
            "seed_effects": {str(key): float(np.median(values)) for key, values in by_seed_effect.items()},
            "fold_effect_variance": float(np.var(fold_effects)) if fold_effects else None,
            "seed_effect_variance": float(np.var(seed_effects)) if seed_effects else None,
            "scaling_positive": bool(len(medians) >= 2 and medians[-1] < medians[0]),
            "folds_improved_fraction": folds_improved_fraction,
            "seeds_improved_fraction": seeds_improved_fraction,
            "effect_exceeds_seed_fold_noise": bool(ci_low is not None and ci_low > 0.0),
            "valid_scaling_gate_passed": valid_scaling_gate,
        }
    return stats


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run G5.65 current-bank matched-control scaling.")
    parser.add_argument("--rows-path", type=Path, default=G560_TRAINING_ROWS)
    parser.add_argument("--context-dir", type=Path, default=DEFAULT_CONTEXT_DIR)
    parser.add_argument("--max-contexts", type=int, default=1000)
    parser.add_argument("--folds", type=int, default=4)
    parser.add_argument("--fold-indices", default="")
    parser.add_argument("--sizes", default="64,128,256,512,all")
    parser.add_argument("--seeds", default="565,566,567")
    parser.add_argument("--methods", default="B0,B1,B2,E0,E1,E2")
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--min-epochs", type=int, default=30)
    parser.add_argument("--early-stop-patience", type=int, default=10)
    parser.add_argument("--hidden-dim", type=int, default=64)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--lr", type=float, default=5.0e-4)
    parser.add_argument("--artifact-prefix", default=ROUND)
    parser.add_argument("--stage-label", default="confirmatory")
    parser.add_argument("--amp-bf16", action="store_true")
    parser.add_argument("--device", default="auto")
    args = parser.parse_args(argv)

    import torch

    device = "cuda" if args.device == "auto" and torch.cuda.is_available() else ("cpu" if args.device == "auto" else args.device)
    started = time.perf_counter()
    examples = load_examples(resolve(args.rows_path), resolve(args.context_dir), max_contexts=args.max_contexts)
    seeds = [int(token) for token in args.seeds.split(",") if token.strip()]
    methods = [token.strip().upper() for token in args.methods.split(",") if token.strip()]
    size_tokens = [token.strip() for token in args.sizes.split(",") if token.strip()]
    fold_indices = parse_fold_indices(args.fold_indices)
    if fold_indices is not None and any(index >= args.folds for index in fold_indices):
        raise ValueError("--fold-indices entries must be smaller than --folds")
    result_rows: list[dict[str, Any]] = []
    comparison_rows: list[dict[str, Any]] = []
    detail_rows: list[dict[str, Any]] = []
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    for fold, train_all, valid in physical_folds(examples, args.folds, seed=565):
        if fold_indices is not None and fold not in fold_indices:
            continue
        valid_ids = [ex.evaluation_uid for ex in valid]
        valid_sha = validation_manifest_sha256(valid_ids)
        for size_label, train_subset in nested_prefix(train_all, size_tokens, seed=565 + fold):
            if not train_subset or not valid:
                continue
            for seed in seeds:
                fold_rows = []
                for method in methods:
                    model, metrics = train_model(
                        method,
                        train_subset,
                        valid,
                        cfg=DEFAULT_REPAIRED_RISK,
                        seed=seed,
                        epochs=args.epochs,
                        lr=args.lr,
                        hidden_dim=args.hidden_dim,
                        batch_size=args.batch_size,
                        device=device,
                        weight_decay=0.0,
                        min_epochs=args.min_epochs,
                        early_stop_patience=args.early_stop_patience,
                        amp_bf16=args.amp_bf16,
                    )
                    risk, details = evaluate_model(method, model, valid, cfg=DEFAULT_REPAIRED_RISK, device=device, batch_size=args.batch_size)
                    ckpt = MODEL_DIR / f"{args.artifact_prefix}_scaling_{method.lower()}_fold{fold}_{size_label}_seed{seed}.pt"
                    torch.save(checkpoint_payload(method, model, metrics, DEFAULT_REPAIRED_RISK, args.hidden_dim), ckpt)
                    detail_metrics = aggregate_validation_details(details)
                    row = {
                        "fold": fold,
                        "size_label": size_label,
                        "size": len(train_subset),
                        "seed": seed,
                        "model_kind": method,
                        "stage_label": args.stage_label,
                        "hidden_dim": args.hidden_dim,
                        "train_contexts": len(train_subset),
                        "validation_contexts": len(valid),
                        "validation_manifest_sha256": valid_sha,
                        "epochs": args.epochs if method != "B0" else 0,
                        "min_epochs": args.min_epochs,
                        "early_stop_patience": args.early_stop_patience,
                        "amp_bf16": bool(args.amp_bf16),
                        "validation_risk": risk,
                        "checkpoint_path": str(ckpt.relative_to(ROOT)).replace("\\", "/"),
                        "checkpoint_sha256": sha256_file(ckpt),
                        "loss_config_sha256": DEFAULT_REPAIRED_RISK.sha256,
                        **detail_metrics,
                        **metrics,
                    }
                    result_rows.append(row)
                    fold_rows.append(row)
                    for detail in details:
                        detail_rows.append(
                            {
                                "fold": fold,
                                "size_label": size_label,
                                "size": len(train_subset),
                                "seed": seed,
                                "model_kind": method,
                                "stage_label": args.stage_label,
                                "validation_manifest_sha256": valid_sha,
                                "checkpoint_path": str(ckpt.relative_to(ROOT)).replace("\\", "/"),
                                **detail,
                            }
                        )
                    print(json.dumps({"event": "scaling", "fold": fold, "size": size_label, "seed": seed, "method": method, "risk": risk}, sort_keys=True), flush=True)
                rich = [row for row in fold_rows if row["model_kind"].startswith("E")]
                controls = [row for row in fold_rows if row["model_kind"] in {"B0", "B1", "B2"}]
                if rich and controls:
                    best_rich = min(rich, key=lambda row: float(row["validation_risk"]))
                    best_control = min(controls, key=lambda row: float(row["validation_risk"]))
                    comparison_rows.append(
                        {
                            "fold": fold,
                            "size_label": size_label,
                            "seed": seed,
                            "best_rich_model": best_rich["model_kind"],
                            "best_rich_validation_risk": best_rich["validation_risk"],
                            "best_control_model": best_control["model_kind"],
                            "best_control_validation_risk": best_control["validation_risk"],
                            "rich_beats_matched_control": float(best_rich["validation_risk"]) < float(best_control["validation_risk"]),
                        }
                    )
    stats = method_stats(result_rows)
    rich_methods = [method for method in stats["methods"] if method.startswith("E")]
    rich_supported = any(stats["methods"][method].get("valid_scaling_gate_passed") for method in rich_methods)
    win_rate = sum(bool(row["rich_beats_matched_control"]) for row in comparison_rows) / max(1, len(comparison_rows))
    summary = {
        "schema_version": f"{ROUND}_current_bank_scaling_summary_v1",
        "decision": (
            "g565_current_bank_rich_scaling_no_rows_error"
            if not result_rows
            else "g565_current_bank_rich_scaling_supported"
            if rich_supported and win_rate > 0.5
            else "g565_current_bank_rich_scaling_flat"
        ),
        "device": device,
        "contexts_loaded": len(examples),
        "folds": args.folds,
        "fold_indices": sorted(fold_indices) if fold_indices is not None else None,
        "seeds": seeds,
        "methods": methods,
        "size_labels": size_tokens,
        "epochs": args.epochs,
        "min_epochs": args.min_epochs,
        "early_stop_patience": args.early_stop_patience,
        "hidden_dim": args.hidden_dim,
        "stage_label": args.stage_label,
        "artifact_prefix": args.artifact_prefix,
        "amp_bf16": bool(args.amp_bf16),
        "results_rows": len(result_rows),
        "validation_detail_rows": len(detail_rows),
        "matched_initialization": True,
        "loss_config_sha256": DEFAULT_REPAIRED_RISK.sha256,
        "rich_beats_matched_controls_rate": win_rate,
        "rich_vs_control_decision": "g565_rich_actor_beats_matched_controls" if win_rate > 0.5 else "g565_rich_actor_not_better_than_controls",
        "elapsed_sec": time.perf_counter() - started,
    }
    write_rows(TABLES / f"{args.artifact_prefix}_scaling_by_fold_seed_size.csv", result_rows)
    write_rows(TABLES / f"{args.artifact_prefix}_scaling_validation_details.csv", detail_rows)
    write_rows(TABLES / f"{args.artifact_prefix}_matched_control_comparison.csv", comparison_rows)
    write_json(REPORTS / f"{args.artifact_prefix}_scaling_statistics.json", stats)
    write_json(REPORTS / f"{args.artifact_prefix}_current_bank_scaling_summary.json", summary)
    print(json.dumps({"decision": summary["decision"], "rows": len(result_rows), "win_rate": win_rate}, sort_keys=True))
    if not result_rows:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
