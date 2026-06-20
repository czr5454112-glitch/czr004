from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gcst.leakage_free_features import PRE_SOLVER_SCALAR_FEATURES, audit_feature_schema, leakage_report_dict  # noqa: E402
from gcst.real_label_graph_dataset import DEFAULT_CONTEXT_DIR, G560_TRAINING_ROWS  # noqa: E402
from gcst.rich_actor_training_g564 import load_rich_set_examples, split_by_ids, train_rich, train_scalar  # noqa: E402
from gcst.scaling_dataset import (  # noqa: E402
    assert_split_hashes_disjoint,
    fixed_validation_ids,
    make_grouped_split_manifest,
    nested_stratified_subsets,
    validation_manifest_sha256,
)


ROUND = "phase5p5_repair5g564"
REPORTS = ROOT / "outputs/reports"
TABLES = ROOT / "outputs/tables"


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


def manifest_rows(examples) -> list[dict[str, Any]]:
    rows = []
    for ex in examples:
        rows.append(
            {
                "evaluation_uid": ex.evaluation_uid,
                "physical_map_sha256": ex.physical_map_sha256,
                "map_family": ex.map_family,
                "agent_count": ex.scalar_context.get("agent_count", 0),
                "budget_ms": ex.scalar_context.get("nominal_budget_ms", ex.scalar_context.get("budget_ms", 0)),
            }
        )
    return rows


def fit_curve(rows: list[dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {"schema_version": f"{ROUND}_scaling_curve_fit_v1", "methods": {}}
    for method in sorted({str(row["method"]) for row in rows}):
        by_size: dict[int, list[float]] = {}
        for row in rows:
            if row["method"] == method:
                by_size.setdefault(int(row["size"]), []).append(float(row["final_validation_loss"]))
        sizes = sorted(by_size)
        medians = [float(np.median(by_size[size])) for size in sizes]
        if len(sizes) >= 2:
            slope = float(np.polyfit(np.log(np.asarray(sizes, dtype=np.float64)), np.asarray(medians), 1)[0])
        else:
            slope = 0.0
        out["methods"][method] = {
            "sizes": sizes,
            "median_final_validation_loss_by_size": {str(size): med for size, med in zip(sizes, medians)},
            "log_size_loss_slope": slope,
            "scaling_positive": bool(len(medians) >= 2 and medians[-1] < medians[0]),
        }
    return out


def paired_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_key: dict[tuple[int, int], dict[str, dict[str, Any]]] = {}
    for row in rows:
        key = (int(row["size"]), int(row["seed"]))
        by_key.setdefault(key, {})[str(row["method"])] = row
    out = []
    for (size, seed), methods in sorted(by_key.items()):
        rich = methods.get("rich_graph_actor")
        scalar = methods.get("scalar_pre_solver_control")
        if not rich or not scalar:
            continue
        out.append(
            {
                "size": size,
                "seed": seed,
                "rich_final_validation_loss": rich["final_validation_loss"],
                "scalar_final_validation_loss": scalar["final_validation_loss"],
                "rich_minus_scalar_final_validation_loss": float(rich["final_validation_loss"]) - float(scalar["final_validation_loss"]),
                "rich_beats_scalar": float(rich["final_validation_loss"]) < float(scalar["final_validation_loss"]),
            }
        )
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run G5.64 leakage-free rich scaling study.")
    parser.add_argument("--rows-path", type=Path, default=G560_TRAINING_ROWS)
    parser.add_argument("--context-dir", type=Path, default=DEFAULT_CONTEXT_DIR)
    parser.add_argument("--max-contexts", type=int, default=192)
    parser.add_argument("--sizes", default="32,64,128")
    parser.add_argument("--seeds", default="564,565")
    parser.add_argument("--steps", type=int, default=60)
    parser.add_argument("--lr", type=float, default=5.0e-4)
    parser.add_argument("--hidden-dim", type=int, default=36)
    parser.add_argument("--batch-size", type=int, default=6)
    parser.add_argument("--device", default="auto")
    args = parser.parse_args(argv)

    import torch

    device = "cuda" if args.device == "auto" and torch.cuda.is_available() else ("cpu" if args.device == "auto" else args.device)
    started = time.perf_counter()
    examples = load_rich_set_examples(resolve(args.rows_path), resolve(args.context_dir), max_contexts=args.max_contexts)
    examples = [ex for ex in examples if len(ex.label_context.positive_candidates) or len(ex.label_context.harmful_candidates)]
    if len(examples) < 8:
        raise SystemExit("need at least eight labeled contexts for G5.64 rich scaling")
    manifest = make_grouped_split_manifest(manifest_rows(examples), seed=564, split_key="g564_split")
    assert_split_hashes_disjoint(manifest, split_key="g564_split")
    train_manifest = [row for row in manifest if row["g564_split"] == "train"]
    valid_ids = fixed_validation_ids(manifest, split_key="g564_split")
    if not valid_ids:
        valid_ids = [row["evaluation_uid"] for idx, row in enumerate(manifest) if idx % 5 == 0]
        train_manifest = [row for idx, row in enumerate(manifest) if idx % 5 != 0]
    sizes = [int(token) for token in args.sizes.split(",") if token.strip()]
    seeds = [int(token) for token in args.seeds.split(",") if token.strip()]
    nested = nested_stratified_subsets(train_manifest, sizes, seed=564)
    rows: list[dict[str, Any]] = []
    for size in sorted(nested):
        train_ids = nested[size]
        train_examples, valid_examples = split_by_ids(examples, train_ids, valid_ids)
        if not train_examples or not valid_examples:
            continue
        for seed in seeds:
            for method in ["scalar", "rich"]:
                if method == "scalar":
                    _model, metrics = train_scalar(
                        train_examples,
                        valid_examples,
                        seed=seed,
                        steps=args.steps,
                        lr=args.lr,
                        hidden_dim=args.hidden_dim,
                        batch_size=args.batch_size,
                        device=device,
                    )
                else:
                    _model, metrics = train_rich(
                        train_examples,
                        valid_examples,
                        seed=seed,
                        steps=args.steps,
                        lr=args.lr,
                        hidden_dim=args.hidden_dim,
                        batch_size=args.batch_size,
                        device=device,
                    )
                row = {
                    "size": len(train_examples),
                    "requested_size": size,
                    "seed": seed,
                    "device": device,
                    "train_contexts": len(train_examples),
                    "fixed_validation_contexts": len(valid_examples),
                    "fixed_validation_manifest_sha256": validation_manifest_sha256(valid_ids),
                    "steps": args.steps,
                    **metrics,
                }
                rows.append(row)
                print(json.dumps({"event": "scaling_row", "method": row["method"], "size": row["size"], "seed": seed, "final_validation_loss": row["final_validation_loss"]}, sort_keys=True), flush=True)
    curve = fit_curve(rows)
    pairs = paired_rows(rows)
    rich_curve = curve["methods"].get("rich_graph_actor", {})
    pair_win_rate = sum(bool(row["rich_beats_scalar"]) for row in pairs) / max(1, len(pairs))
    leak_audit = audit_feature_schema(PRE_SOLVER_SCALAR_FEATURES).as_dict()
    decision = "g564_rich_scaling_positive" if rich_curve.get("scaling_positive") else "g564_rich_scaling_flat"
    summary = {
        "schema_version": f"{ROUND}_rich_scaling_summary_v1",
        "decision": decision,
        "device": device,
        "contexts_loaded": len(examples),
        "train_contexts_available": len(train_manifest),
        "fixed_validation_contexts": len(valid_ids),
        "fixed_validation_manifest_sha256": validation_manifest_sha256(valid_ids),
        "sizes": sorted({int(row["size"]) for row in rows}),
        "seeds": seeds,
        "results_rows": len(rows),
        "rich_actor_used_for_primary": True,
        "scalar_control_uses_label_leakage_features": False,
        "feature_schema_audit": leak_audit,
        "g563_leakage_audit": leakage_report_dict(),
        "rich_vs_scalar_pair_rows": len(pairs),
        "rich_beats_scalar_pair_win_rate": pair_win_rate,
        "rich_vs_scalar_decision": "g564_rich_actor_beats_scalar_control" if pair_win_rate > 0.5 else "g564_scalar_control_matches_rich_actor",
        "elapsed_sec": time.perf_counter() - started,
    }
    write_rows(TABLES / f"{ROUND}_rich_scaling_results.csv", rows)
    write_rows(TABLES / f"{ROUND}_rich_vs_scalar_by_fold.csv", pairs)
    write_json(REPORTS / f"{ROUND}_scaling_curve_fit.json", curve)
    write_json(REPORTS / f"{ROUND}_rich_scaling_summary.json", summary)
    print(json.dumps({"decision": decision, "rows": len(rows), "rich_pair_win_rate": pair_win_rate}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
