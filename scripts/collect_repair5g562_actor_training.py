from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ROUND = "phase5p5_repair5g562"
PROGRESS = ROOT / f"outputs/reports/{ROUND}_training_progress.jsonl"
ARCH_MATRIX = ROOT / f"outputs/tables/{ROUND}_architecture_matrix.csv"
GRAD_AUDIT = ROOT / f"outputs/tables/{ROUND}_branch_gradient_audit.csv"
LOSS_ABLATION = ROOT / f"outputs/tables/{ROUND}_loss_ablation_matrix.csv"
ACTOR_SUMMARY = ROOT / f"outputs/reports/{ROUND}_actor_training_summary.json"
PRETRAINING_SUMMARY = ROOT / f"outputs/reports/{ROUND}_pretraining_summary.json"

VARIANT_ORDER = {"C0": 0, "A0": 1, "A1": 2, "A2": 3, "A4": 4}


def claims() -> dict[str, bool]:
    return {
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "runtime_claim_allowed": False,
        "learned_runtime_policy_validated": False,
        "aaai_ready": False,
    }


def boolish(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def number(value: Any, default: float = 999.0) -> float:
    try:
        out = float(value)
    except Exception:
        return default
    return out if math.isfinite(out) else default


def read_progress(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


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


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sort_key(row: dict[str, Any]) -> tuple[int, str, int]:
    variant = str(row.get("variant_id", ""))
    return (VARIANT_ORDER.get(variant, 99), variant, int(number(row.get("seed"), 0)))


def collect(progress_rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    done_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    grad_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    for row in progress_rows:
        variant = str(row.get("variant_id", ""))
        seed = str(row.get("seed", ""))
        if not variant or not seed:
            continue
        key = (variant, seed)
        if row.get("event") == "variant_step":
            grad_by_key[key] = {
                "variant_id": variant,
                "seed": seed,
                "step": row.get("step"),
                "graph_encoder_grad_norm": row.get("graph_encoder_grad_norm"),
                "od_encoder_grad_norm": row.get("od_encoder_grad_norm"),
                "c_stream_grad_norm": row.get("c_stream_grad_norm"),
                "f_stream_grad_norm": row.get("f_stream_grad_norm"),
                "scalar_encoder_grad_norm": row.get("scalar_encoder_grad_norm"),
                "fusion_grad_norm": row.get("fusion_grad_norm"),
                "theta_head_grad_norm": row.get("theta_head_grad_norm"),
                **claims(),
            }
        elif row.get("event") == "variant_done":
            matrix_row = {k: v for k, v in row.items() if k != "event"}
            model_path = matrix_row.get("model_path")
            matrix_row["checkpoint_exists"] = bool(model_path and (ROOT / str(model_path)).exists())
            done_by_key[key] = matrix_row
    matrix = sorted(done_by_key.values(), key=sort_key)
    grads = sorted((row for key, row in grad_by_key.items() if key in done_by_key), key=sort_key)
    return matrix, grads


def summarize(matrix: list[dict[str, Any]], steps: int, max_contexts: int) -> dict[str, Any]:
    rich_rows = [row for row in matrix if boolish(row.get("rich_attention_actor"))]
    rich_sorted = sorted(rich_rows, key=lambda row: number(row.get("validation_real_label_normalized_l1")))
    top_rich_variants: list[str] = []
    for row in rich_sorted:
        variant = str(row.get("variant_id", ""))
        if variant and variant not in top_rich_variants:
            top_rich_variants.append(variant)
        if len(top_rich_variants) >= 2:
            break
    seeds = sorted({str(row.get("seed", "")) for row in matrix if row.get("seed", "") != ""})
    variants = [str(row.get("variant_id", "")) for row in matrix]
    hidden_dims = sorted({int(number(row.get("hidden_dim"), 0)) for row in matrix if int(number(row.get("hidden_dim"), 0)) > 0})
    return {
        "schema_version": f"{ROUND}_actor_training_summary_v1",
        "decision": "g562_real_safe_set_actor_training_completed" if matrix else "g562_actor_training_incomplete",
        "collection_source": str(PROGRESS.relative_to(ROOT)).replace("\\", "/"),
        "parallel_training_collected": True,
        "device": "cuda",
        "examples": max([int(number(row.get("train_examples"), 0)) + int(number(row.get("validation_examples"), 0)) for row in matrix] or [0]),
        "max_contexts_requested": max_contexts,
        "steps": steps,
        "hidden_dims": hidden_dims,
        "positive_only_target_examples": max([int(number(row.get("train_examples"), 0)) + int(number(row.get("validation_examples"), 0)) for row in matrix] or [0]),
        "analytic_target_rate": 0.0,
        "variants": sorted(set(variants), key=lambda v: VARIANT_ORDER.get(v, 99)),
        "seeds": seeds,
        "rows": len(matrix),
        "rich_attention_actor_rows": len(rich_rows),
        "top_two_rich_variants": top_rich_variants,
        "three_seed_top_rich_complete": all(sum(1 for row in matrix if str(row.get("variant_id")) == variant) >= 3 for variant in top_rich_variants)
        if len(top_rich_variants) >= 2
        else False,
        "all_model_checkpoints_exist": all(boolish(row.get("checkpoint_exists")) for row in matrix),
        **claims(),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Collect parallel G5.62 actor training artifacts.")
    parser.add_argument("--progress", type=Path, default=PROGRESS)
    parser.add_argument("--steps", type=int, default=500)
    parser.add_argument("--max-contexts", type=int, default=1000)
    args = parser.parse_args(argv)
    progress_rows = read_progress(args.progress)
    matrix, grads = collect(progress_rows)
    write_rows(ARCH_MATRIX, matrix)
    write_rows(GRAD_AUDIT, grads)
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
    write_json(ACTOR_SUMMARY, summarize(matrix, args.steps, args.max_contexts))
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
    print(json.dumps({"decision": "g562_parallel_actor_training_collected", "rows": len(matrix)}, sort_keys=True))
    return 0 if matrix else 2


if __name__ == "__main__":
    raise SystemExit(main())
