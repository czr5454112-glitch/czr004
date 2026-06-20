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

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gcst.label_v52_set import context_dataset_sha256, contexts_from_groups  # noqa: E402
from gcst.real_label_graph_dataset import DEFAULT_CONTEXT_DIR, G560_TRAINING_ROWS, load_label_groups  # noqa: E402
from gcst.replay_label_merge import merge_rows_by_context, replay_merge_summary  # noqa: E402
from gcst.rich_actor_training_g564 import load_rich_set_examples, train_scalar  # noqa: E402
from gcst.theta_schema import THETA_NUMERIC_COLUMNS  # noqa: E402


ROUND = "phase5p5_repair5g564"
REPORTS = ROOT / "outputs/reports"
TABLES = ROOT / "outputs/tables"
MODEL_DIR = ROOT / "artifacts/models/gcst"


def resolve(path: str | Path) -> Path:
    p = Path(path)
    return p if p.is_absolute() else ROOT / p


def read_rows(path: Path, limit: int = 0) -> list[dict[str, str]]:
    if not path.exists():
        return []
    rows = []
    with path.open(newline="", encoding="utf-8") as handle:
        for idx, row in enumerate(csv.DictReader(handle)):
            rows.append(dict(row))
            if limit and idx + 1 >= limit:
                break
    return rows


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


def boolish(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def convert_replay_pair(row: dict[str, str]) -> dict[str, Any]:
    out: dict[str, Any] = {
        "g560_evaluation_uid": row.get("g562_evaluation_uid", ""),
        "g560_instance_uid": row.get("g562_dataset_row_id", row.get("g562_evaluation_uid", "")),
        "split": row.get("split", "unassigned"),
        "g560_physical_map_sha256": row.get("g562_physical_map_sha256", row.get("g562_identity_digest", "")),
        "map": row.get("map", ""),
        "map_family": row.get("map_family", ""),
        "agent_count": row.get("agents", row.get("agent_count", "")),
        "nominal_budget_ms": row.get("budget_ms", ""),
        "base_time_limit_sec": row.get("base_time_limit_sec", ""),
        "ltm_max_iterations": row.get("ltm_max_iterations", ""),
        "horizon_id": row.get("horizon_id", ""),
        "generated_theta_uid": row.get("theta_id", row.get("generated_theta_uid", "")),
        "candidate_uid": row.get("theta_id", row.get("generated_theta_uid", "")),
        "labelv51_development_safe": str(
            (not boolish(row.get("success_regression")))
            and boolish(row.get("candidate_recognized", "true"))
            and boolish(row.get("fingerprint_match", "true"))
            and boolish(row.get("scenario_hash_match", "true"))
        ),
        "labelv51_comparable_quality": str(boolish(row.get("both_success"))),
        "quality_delta_vs_g556": row.get("quality_delta_vs_g556", ""),
        "labelv51_success_gain": row.get("success_gain", "False"),
        "labelv51_success_regression": row.get("success_regression", "False"),
        "g564_source_replay_pair": True,
    }
    for col in THETA_NUMERIC_COLUMNS:
        out[col] = row.get(col, "")
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Merge exact replay rows and run a small true retraining cycle for G5.64.")
    parser.add_argument("--rows-path", type=Path, default=G560_TRAINING_ROWS)
    parser.add_argument("--context-dir", type=Path, default=DEFAULT_CONTEXT_DIR)
    parser.add_argument("--replay-pairs", type=Path, default=Path("outputs/tables/phase5p5_repair5g562_cycle3_pairs.csv"))
    parser.add_argument("--max-contexts", type=int, default=64)
    parser.add_argument("--max-replay-rows", type=int, default=0)
    parser.add_argument("--steps", type=int, default=24)
    parser.add_argument("--seed", type=int, default=564)
    parser.add_argument("--device", default="auto")
    args = parser.parse_args(argv)

    import torch

    started = time.perf_counter()
    device = "cuda" if args.device == "auto" and torch.cuda.is_available() else ("cpu" if args.device == "auto" else args.device)
    groups = load_label_groups(resolve(args.rows_path), resolve(args.context_dir), max_contexts=args.max_contexts)
    base_contexts = contexts_from_groups(groups)
    loaded_uids = {context.evaluation_uid for context in base_contexts}
    base_rows = [row for group in groups for row in group.rows]
    raw_replay = read_rows(resolve(args.replay_pairs), limit=args.max_replay_rows)
    replay_rows = [convert_replay_pair(row) for row in raw_replay if row.get("g562_evaluation_uid", "") in loaded_uids]
    merged_contexts = merge_rows_by_context(base_rows, replay_rows)
    merge_summary = replay_merge_summary(base_contexts, merged_contexts)
    base_hash = context_dataset_sha256(base_contexts)
    merged_hash = context_dataset_sha256(merged_contexts)
    merge_summary.update(
        {
            "schema_version": f"{ROUND}_replay_merge_summary_v1",
            "decision": "g564_replay_rows_merged" if replay_rows and base_hash != merged_hash else "g564_replay_merge_no_effect",
            "replay_pairs_path": str(resolve(args.replay_pairs)).replace("\\", "/"),
            "raw_replay_rows_read": len(raw_replay),
            "replay_rows_matching_loaded_contexts": len(replay_rows),
            "base_dataset_sha256": base_hash,
            "merged_dataset_sha256": merged_hash,
            "replay_merge_changes_dataset_hash": base_hash != merged_hash,
        }
    )
    write_json(REPORTS / f"{ROUND}_replay_merge_summary.json", merge_summary)

    by_uid = {context.evaluation_uid: context for context in merged_contexts}
    base_examples = load_rich_set_examples(resolve(args.rows_path), resolve(args.context_dir), max_contexts=args.max_contexts)
    merged_examples = [replace(ex, label_context=by_uid.get(ex.evaluation_uid, ex.label_context)) for ex in base_examples]
    train_base = [ex for ex in base_examples if len(ex.label_context.positive_candidates) or len(ex.label_context.harmful_candidates)]
    train_merged = [ex for ex in merged_examples if len(ex.label_context.positive_candidates) or len(ex.label_context.harmful_candidates)]
    train_base = train_base[: min(32, len(train_base))]
    train_merged = train_merged[: min(32, len(train_merged))]
    base_model_path = MODEL_DIR / f"{ROUND}_true_cycle_base_scalar_seed{args.seed}.pt"
    merged_model_path = MODEL_DIR / f"{ROUND}_true_cycle_merged_scalar_seed{args.seed}.pt"
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    if train_base and train_merged:
        base_model, base_metrics = train_scalar(
            train_base,
            train_base,
            seed=args.seed,
            steps=args.steps,
            lr=5.0e-4,
            hidden_dim=32,
            batch_size=min(8, len(train_base)),
            device=device,
        )
        merged_model, merged_metrics = train_scalar(
            train_merged,
            train_merged,
            seed=args.seed,
            steps=args.steps,
            lr=5.0e-4,
            hidden_dim=32,
            batch_size=min(8, len(train_merged)),
            device=device,
        )
        torch.save({"dataset_sha256": base_hash, "model_state_dict": base_model.state_dict(), "metrics": base_metrics}, base_model_path)
        torch.save({"dataset_sha256": merged_hash, "model_state_dict": merged_model.state_dict(), "metrics": merged_metrics}, merged_model_path)
        base_ckpt_hash = sha256_file(base_model_path)
        merged_ckpt_hash = sha256_file(merged_model_path)
    else:
        base_metrics = {}
        merged_metrics = {}
        base_ckpt_hash = ""
        merged_ckpt_hash = ""
    true_cycle_completed = bool(replay_rows and base_hash != merged_hash and base_ckpt_hash and base_ckpt_hash != merged_ckpt_hash)
    true_cycle = {
        "schema_version": f"{ROUND}_true_cycle_summary_v1",
        "decision": "g564_true_retraining_cycle_completed" if true_cycle_completed else "g564_true_retraining_cycle_blocked",
        "device": device,
        "base_dataset_sha256": base_hash,
        "merged_dataset_sha256": merged_hash,
        "replay_merge_changes_dataset_hash": base_hash != merged_hash,
        "base_checkpoint_path": str(base_model_path.relative_to(ROOT)).replace("\\", "/") if base_ckpt_hash else "",
        "merged_checkpoint_path": str(merged_model_path.relative_to(ROOT)).replace("\\", "/") if merged_ckpt_hash else "",
        "base_checkpoint_sha256": base_ckpt_hash,
        "merged_checkpoint_sha256": merged_ckpt_hash,
        "retraining_changes_checkpoint_hash": bool(base_ckpt_hash and base_ckpt_hash != merged_ckpt_hash),
        "train_examples": len(train_merged),
        "steps": args.steps,
        "base_train_loss": base_metrics.get("final_train_loss"),
        "merged_train_loss": merged_metrics.get("final_train_loss"),
        "elapsed_sec": time.perf_counter() - started,
    }
    write_json(REPORTS / f"{ROUND}_true_cycle_summary.json", true_cycle)

    fixed_pairs = raw_replay[: min(len(raw_replay), 200)]
    write_rows(TABLES / f"{ROUND}_fixed_solver_panel_pairs.csv", fixed_pairs)
    fixed_summary = {
        "schema_version": f"{ROUND}_fixed_solver_panel_summary_v1",
        "decision": "g564_offline_scaling_solver_transfer_blocked",
        "fixed_solver_panel_pairs": len(fixed_pairs),
        "source_panel": str(resolve(args.replay_pairs)).replace("\\", "/"),
        "new_g564_solver_panel_ran": False,
        "gate_block_reason": "G5.64 ran offline loss-geometry/rich-scaling repair; no new fixed solver panel was launched in this script.",
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "runtime_claim_allowed": False,
        "learned_runtime_policy_validated": False,
        "aaai_ready": False,
    }
    write_json(REPORTS / f"{ROUND}_fixed_solver_panel_summary.json", fixed_summary)
    print(json.dumps({"decision": true_cycle["decision"], "replay_rows": len(replay_rows), "checkpoint_changed": true_cycle["retraining_changes_checkpoint_hash"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
