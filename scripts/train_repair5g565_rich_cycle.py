from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import time
from dataclasses import replace
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gcst.label_v52_set import context_dataset_sha256, contexts_from_groups  # noqa: E402
from gcst.real_label_graph_dataset import DEFAULT_CONTEXT_DIR, G560_TRAINING_ROWS, load_label_groups  # noqa: E402
from gcst.repaired_set_risk import DEFAULT_REPAIRED_RISK  # noqa: E402
from gcst.exact_replay_dataset import exact_pair_to_label_row  # noqa: E402
from gcst.opportunity_labels import (  # noqa: E402
    MIXED_SAFETY_BOUNDARY,
    NONTRIVIAL_OPPORTUNITY,
    TRIVIAL_G556_OPTIMAL,
    UNSUPPORTED_CENSORED,
)
from gcst.replay_label_merge import merge_rows_by_context, replay_merge_summary  # noqa: E402
from gcst.rich_training_g565 import checkpoint_payload, evaluate_model, load_examples, train_model  # noqa: E402


ROUND = "phase5p5_repair5g565"
REPORTS = ROOT / "outputs/reports"
TABLES = ROOT / "outputs/tables"
MODEL_DIR = ROOT / "artifacts/models/gcst"


def resolve(path: str | Path) -> Path:
    p = Path(path)
    return p if p.is_absolute() else ROOT / p


def read_rows(path: Path) -> list[dict[str, str]]:
    p = resolve(path)
    if not p.exists():
        return []
    with p.open(newline="", encoding="utf-8") as handle:
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


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


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


def source_pair_files() -> list[Path]:
    return [
        Path("outputs/tables/phase5p5_repair5g561_development_replay_pairs.csv"),
        Path("outputs/tables/phase5p5_repair5g561_hard_negative_finetune_panel_pairs.csv"),
        Path("outputs/tables/phase5p5_repair5g562_cycle1_pairs.csv"),
        Path("outputs/tables/phase5p5_repair5g562_cycle2_pairs.csv"),
        Path("outputs/tables/phase5p5_repair5g562_cycle3_pairs.csv"),
        Path("outputs/tables/phase5p5_repair5g562_alpha_response_panel_pairs.csv"),
        Path("outputs/tables/phase5p5_repair5g565_fresh_solver_panel_pairs.csv"),
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Merge exact replay rows and retrain G5.65 rich actors before/after merge.")
    parser.add_argument("--rows-path", type=Path, default=G560_TRAINING_ROWS)
    parser.add_argument("--context-dir", type=Path, default=DEFAULT_CONTEXT_DIR)
    parser.add_argument("--max-contexts", type=int, default=256)
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--hidden-dim", type=int, default=64)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--seed", type=int, default=565)
    parser.add_argument("--seeds", default="")
    parser.add_argument("--architectures", default="E0,E1,E2")
    parser.add_argument("--min-epochs", type=int, default=30)
    parser.add_argument("--early-stop-patience", type=int, default=10)
    parser.add_argument("--amp-bf16", action="store_true")
    parser.add_argument("--device", default="auto")
    args = parser.parse_args(argv)

    import torch

    device = "cuda" if args.device == "auto" and torch.cuda.is_available() else ("cpu" if args.device == "auto" else args.device)
    started = time.perf_counter()
    groups = load_label_groups(resolve(args.rows_path), resolve(args.context_dir), max_contexts=args.max_contexts)
    base_contexts = contexts_from_groups(groups)
    base_rows = [row for group in groups for row in group.rows]
    loaded = {context.evaluation_uid for context in base_contexts}
    replay_rows = []
    provenance_rows = []
    for path in source_pair_files():
        rows = read_rows(path)
        for row in rows:
            converted = exact_pair_to_label_row(row, str(resolve(path)).replace("\\", "/"))
            if converted["g560_evaluation_uid"] in loaded:
                replay_rows.append(converted)
                provenance_rows.append(
                    {
                        "source_path": converted["g565_source_replay_pair"],
                        "evaluation_uid": converted["g560_evaluation_uid"],
                        "candidate_uid": converted["candidate_uid"],
                    }
                )
    merged_contexts = merge_rows_by_context(base_rows, replay_rows)
    merge = replay_merge_summary(base_contexts, merged_contexts)
    base_hash = context_dataset_sha256(base_contexts)
    merged_hash = context_dataset_sha256(merged_contexts)
    merge.update(
        {
            "schema_version": f"{ROUND}_exact_replay_merge_summary_v1",
            "decision": "g565_exact_replay_merge_completed" if replay_rows and base_hash != merged_hash else "g565_exact_replay_merge_no_effect",
            "source_files": [str(resolve(path)).replace("\\", "/") for path in source_pair_files() if resolve(path).exists()],
            "merged_replay_rows": len(replay_rows),
            "base_dataset_sha256": base_hash,
            "merged_dataset_sha256": merged_hash,
            "dataset_sha_changed": base_hash != merged_hash,
        }
    )
    write_rows(TABLES / f"{ROUND}_exact_replay_merged_rows.csv", provenance_rows)
    write_json(REPORTS / f"{ROUND}_exact_replay_merge_summary.json", merge)
    by_uid = {context.evaluation_uid: context for context in merged_contexts}
    base_examples = load_examples(resolve(args.rows_path), resolve(args.context_dir), max_contexts=args.max_contexts)
    merged_examples = [replace(ex, label_context=by_uid.get(ex.evaluation_uid, ex.label_context)) for ex in base_examples]
    valid = [ex for idx, ex in enumerate(base_examples) if idx % 5 == 0]
    train_base = [ex for idx, ex in enumerate(base_examples) if idx % 5 != 0]
    train_merged = [ex for idx, ex in enumerate(merged_examples) if idx % 5 != 0]
    seeds = [int(token) for token in args.seeds.split(",") if token.strip()] if args.seeds else [args.seed]
    architectures = [token.strip().upper() for token in args.architectures.split(",") if token.strip()]
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    cycle_rows = []
    detail_rows = []
    for arch in architectures:
        for seed in seeds:
            for label, train in [("base", train_base), ("merged", train_merged)]:
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
                risk, details = evaluate_model(arch, model, valid, cfg=DEFAULT_REPAIRED_RISK, device=device, batch_size=args.batch_size)
                ckpt = MODEL_DIR / f"{ROUND}_rich_cycle_{arch.lower()}_{label}_seed{seed}.pt"
                torch.save(checkpoint_payload(arch, model, metrics, DEFAULT_REPAIRED_RISK, args.hidden_dim), ckpt)
                detail_metrics = aggregate_validation_details(details)
                cycle_rows.append(
                    {
                        "model_kind": arch,
                        "cycle_label": label,
                        "seed": seed,
                        "checkpoint_path": str(ckpt.relative_to(ROOT)).replace("\\", "/"),
                        "checkpoint_sha256": sha256_file(ckpt),
                        "validation_risk": risk,
                        "train_contexts": len(train),
                        "validation_contexts": len(valid),
                        "loss_config_sha256": DEFAULT_REPAIRED_RISK.sha256,
                        **detail_metrics,
                        **metrics,
                    }
                )
                for detail in details:
                    detail_rows.append(
                        {
                            "model_kind": arch,
                            "cycle_label": label,
                            "seed": seed,
                            "checkpoint_path": str(ckpt.relative_to(ROOT)).replace("\\", "/"),
                            **detail,
                        }
                    )
    improved = []
    for arch in architectures:
        for seed in seeds:
            base = next(row for row in cycle_rows if row["model_kind"] == arch and row["cycle_label"] == "base" and row["seed"] == seed)
            merged = next(row for row in cycle_rows if row["model_kind"] == arch and row["cycle_label"] == "merged" and row["seed"] == seed)
            improved.append(float(merged["validation_risk"]) <= float(base["validation_risk"]))
    merged_opportunity_regrets = [
        float(row["opportunity_context_normalized_regret"])
        for row in cycle_rows
        if row["cycle_label"] == "merged" and row.get("opportunity_context_normalized_regret") is not None
    ]
    summary = {
        "schema_version": f"{ROUND}_rich_retraining_cycle_summary_v1",
        "decision": "g565_rich_retraining_improved" if any(improved) and base_hash != merged_hash else "g565_rich_retraining_no_gain",
        "device": device,
        "base_dataset_sha256": base_hash,
        "merged_dataset_sha256": merged_hash,
        "dataset_sha_changed": base_hash != merged_hash,
        "validation_manifest_unchanged": True,
        "merged_rows_recorded_in_provenance": bool(provenance_rows),
        "validation_detail_rows": len(detail_rows),
        "post_merge_validation_opportunity_regret_reported": bool(merged_opportunity_regrets),
        "post_merge_validation_opportunity_regret_mean": mean_or_none(merged_opportunity_regrets),
        "seeds": seeds,
        "architectures": architectures,
        "cycle_rows": len(cycle_rows),
        "elapsed_sec": time.perf_counter() - started,
    }
    write_rows(TABLES / f"{ROUND}_rich_retraining_cycle_rows.csv", cycle_rows)
    write_rows(TABLES / f"{ROUND}_rich_retraining_cycle_validation_details.csv", detail_rows)
    write_json(REPORTS / f"{ROUND}_rich_retraining_cycle_summary.json", summary)
    print(json.dumps({"decision": summary["decision"], "merged_rows": len(replay_rows)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
