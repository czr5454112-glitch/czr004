from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from collections import Counter
from pathlib import Path
from types import SimpleNamespace
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import run_repair5g562_replay_truth as g562  # noqa: E402
from gcst.real_label_graph_dataset import DEFAULT_CONTEXT_DIR, G560_TRAINING_ROWS  # noqa: E402
from run_repair5g565_fresh_solver_panel import infer_thetas, load_contexts, summarize_pairs  # noqa: E402


ROUND = "phase5p5_repair5g565"
REPORTS = ROOT / "outputs/reports"
TABLES = ROOT / "outputs/tables"
LOGS = ROOT / "outputs/logs"


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


def relpath(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def checkpoint_paths_for_expanded_panel(seed: int = 565) -> tuple[list[Path], dict[str, Any]]:
    paths: list[Path] = []
    missing: list[str] = []

    expanded_rows = read_rows(TABLES / f"{ROUND}_expanded_training_rows.csv")
    for row in expanded_rows:
        kind = str(row.get("model_kind") or row.get("method") or "").upper()
        row_seed = str(row.get("seed") or "")
        checkpoint = row.get("checkpoint_path") or ""
        if kind.startswith("E") and row_seed == str(seed) and checkpoint:
            path = resolve(checkpoint)
            if path.exists():
                paths.append(path)
            else:
                missing.append(checkpoint)

    scaling_rows = read_rows(TABLES / f"{ROUND}_scaling_by_fold_seed_size.csv")
    for row in scaling_rows:
        kind = str(row.get("method") or row.get("model_kind") or "").upper()
        row_seed = str(row.get("seed") or "")
        size = str(row.get("size_label") or row.get("size") or "")
        checkpoint = row.get("checkpoint_path") or ""
        if kind in {"B1", "B2"} and row_seed == str(seed) and size == "all" and checkpoint:
            path = resolve(checkpoint)
            if path.exists():
                paths.append(path)
            else:
                missing.append(checkpoint)

    unique: list[Path] = []
    seen: set[Path] = set()
    for path in paths:
        resolved = path.resolve()
        if resolved not in seen:
            unique.append(path)
            seen.add(resolved)

    kinds = Counter()
    for path in unique:
        name = path.name.lower()
        for kind in ["b1", "b2", "e0", "e1", "e2"]:
            if f"_{kind}_" in name:
                kinds[kind.upper()] += 1
    manifest = {
        "seed": seed,
        "checkpoints": [relpath(path) for path in unique],
        "missing_checkpoint_paths": missing,
        "checkpoint_kind_counts": dict(sorted(kinds.items())),
        "has_b1_b2_controls": all(kinds.get(kind, 0) > 0 for kind in ["B1", "B2"]),
        "has_expanded_rich_e0_e1_e2": all(kinds.get(kind, 0) > 0 for kind in ["E0", "E1", "E2"]),
    }
    return unique, manifest


def not_triggered_summary(reason: str, started: float) -> dict[str, Any]:
    return {
        "schema_version": f"{ROUND}_expanded_solver_panel_summary_v1",
        "decision": "g565_expanded_solver_panel_not_triggered",
        "reason": reason,
        "expanded_solver_panel_ran": False,
        "expanded_exact_materialization_passed": False,
        "elapsed_sec": time.perf_counter() - started,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the G5.65 expanded-data fixed exact solver panel.")
    parser.add_argument("--rows-path", type=Path, default=G560_TRAINING_ROWS)
    parser.add_argument("--context-dir", type=Path, default=DEFAULT_CONTEXT_DIR)
    parser.add_argument("--contexts", type=int, default=1000)
    parser.add_argument("--preferred-split", default="validation,heldout,blind,test")
    parser.add_argument("--min-preferred-contexts", type=int, default=400)
    parser.add_argument("--seed", type=int, default=565)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--binary", type=Path, default=Path("build/phase1a-batch/phase1a_batch"))
    parser.add_argument("--max-workers", type=int, default=8)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--resume-existing", action="store_true")
    parser.add_argument("--plan-only", action="store_true")
    args = parser.parse_args(argv)

    import torch

    started = time.perf_counter()
    solver_overwrite = bool(args.overwrite or not args.resume_existing)
    paths = {
        "plan": TABLES / f"{ROUND}_expanded_solver_panel_plan.csv",
        "registry": TABLES / f"{ROUND}_expanded_solver_panel_registry.csv",
        "results": TABLES / f"{ROUND}_expanded_solver_panel_results.csv",
        "raw_results": TABLES / f"{ROUND}_expanded_solver_panel_results.raw.csv",
        "pairs": TABLES / f"{ROUND}_expanded_solver_panel_pairs.csv",
        "summary": REPORTS / f"{ROUND}_expanded_solver_panel_summary.json",
        "scenario_metadata": REPORTS / f"{ROUND}_expanded_solver_panel_scenario_generation.json",
        "log_dir": LOGS / f"{ROUND}_expanded_solver_panel",
        "scenario_dir": resolve(args.context_dir) / "scenarios",
    }
    expansion = read_json(REPORTS / f"{ROUND}_context_expansion_summary.json")
    expanded_training = read_json(REPORTS / f"{ROUND}_expanded_training_summary.json")
    if expansion.get("decision") != "g565_context_expansion_manifest_ready":
        summary = not_triggered_summary(str(expansion.get("decision") or "context expansion not ready"), started)
        write_rows(paths["pairs"], [])
        write_json(paths["summary"], summary)
        print(json.dumps(summary, sort_keys=True))
        return 0
    if expanded_training.get("decision") != "g565_expanded_training_completed":
        summary = not_triggered_summary(str(expanded_training.get("decision") or "expanded training not complete"), started)
        write_rows(paths["pairs"], [])
        write_json(paths["summary"], summary)
        print(json.dumps(summary, sort_keys=True))
        return 0

    manifest_rows = read_rows(TABLES / f"{ROUND}_context_expansion_manifest.csv")
    manifest_uids = {str(row.get("g560_evaluation_uid") or "") for row in manifest_rows if row.get("g560_evaluation_uid")}
    try:
        contexts = load_contexts(resolve(args.rows_path), resolve(args.context_dir), args.contexts, args.preferred_split, args.min_preferred_contexts)
    except ValueError as exc:
        summary = {
            "schema_version": f"{ROUND}_expanded_solver_panel_summary_v1",
            "decision": "g565_expanded_solver_panel_blocked_insufficient_nontrain_contexts",
            "expanded_solver_panel_ran": False,
            "preferred_split": args.preferred_split,
            "min_preferred_contexts": args.min_preferred_contexts,
            "error": str(exc),
            "elapsed_sec": time.perf_counter() - started,
        }
        write_rows(paths["pairs"], [])
        write_json(paths["summary"], summary)
        print(json.dumps(summary, sort_keys=True))
        return 2
    if manifest_uids:
        contexts = [ctx for ctx in contexts if ctx.evaluation_uid in manifest_uids]
    split_counts = dict(Counter(ctx.split for ctx in contexts))
    train_contexts = int(split_counts.get("train", 0))
    ckpts, checkpoint_manifest = checkpoint_paths_for_expanded_panel(seed=args.seed)
    if not ckpts or not checkpoint_manifest["has_b1_b2_controls"] or not checkpoint_manifest["has_expanded_rich_e0_e1_e2"]:
        summary = {
            "schema_version": f"{ROUND}_expanded_solver_panel_summary_v1",
            "decision": "g565_expanded_solver_panel_blocked_missing_checkpoints",
            "expanded_solver_panel_ran": False,
            "checkpoint_manifest": checkpoint_manifest,
            "elapsed_sec": time.perf_counter() - started,
        }
        write_rows(paths["pairs"], [])
        write_json(paths["summary"], summary)
        print(json.dumps(summary, sort_keys=True))
        return 2

    device = "cuda" if args.device == "auto" and torch.cuda.is_available() else ("cpu" if args.device == "auto" else args.device)
    theta_rows = infer_thetas(contexts, ckpts, device=device, batch_size=args.batch_size)
    plan_rows, registry_rows = g562.build_plan_and_registry(contexts, theta_rows, "g565_expanded_solver_panel")
    write_rows(paths["plan"], plan_rows)
    write_rows(paths["registry"], registry_rows)
    if args.plan_only:
        summary = {
            "schema_version": f"{ROUND}_expanded_solver_panel_summary_v1",
            "decision": "g565_expanded_solver_panel_plan_created",
            "expanded_solver_panel_ran": False,
            "contexts": len(contexts),
            "context_split_counts": split_counts,
            "context_selection_train_contexts": train_contexts,
            "planned_rows": len(plan_rows),
            "actor_candidate_rows": len(theta_rows),
            "checkpoints": [relpath(path) for path in ckpts],
            "checkpoint_manifest": checkpoint_manifest,
            "solver_overwrite": solver_overwrite,
            "elapsed_sec": time.perf_counter() - started,
        }
        write_json(paths["summary"], summary)
        print(json.dumps(summary, sort_keys=True))
        return 0

    run_args = SimpleNamespace(binary=args.binary, overwrite=solver_overwrite, max_workers=args.max_workers, phase="g565_expanded_solver_panel")
    rc = g562.run_solver(plan_rows, paths, run_args)
    if rc != 0:
        summary = {
            "schema_version": f"{ROUND}_expanded_solver_panel_summary_v1",
            "decision": "g565_expanded_solver_panel_blocked_solver_not_executed",
            "expanded_solver_panel_ran": False,
            "rc": rc,
            "elapsed_sec": time.perf_counter() - started,
        }
        write_rows(paths["pairs"], [])
        write_json(paths["summary"], summary)
        print(json.dumps(summary, sort_keys=True))
        return rc
    rows = g562.audit_results(g562.read_rows(paths["results"]), plan_rows, paths["scenario_dir"], "g565_expanded_solver_panel")
    write_rows(paths["results"], rows)
    pairs = g562.build_pairs(rows, "g565_expanded_solver_panel")
    write_rows(paths["pairs"], pairs)
    base_summary = summarize_pairs(rows, pairs, plan_rows)
    base_decision = str(base_summary.get("decision") or "")
    if base_decision == "g565_fresh_solver_transfer_positive":
        decision = "g565_expanded_solver_panel_transfer_positive"
    elif base_decision == "g565_fresh_solver_transfer_tail_blocked":
        decision = "g565_expanded_solver_panel_tail_blocked"
    elif base_decision == "g565_fresh_solver_transfer_materialization_incomplete":
        decision = "g565_expanded_solver_panel_materialization_incomplete"
    else:
        decision = f"g565_expanded_solver_panel_{base_decision or 'unknown'}"
    summary = {
        **base_summary,
        "schema_version": f"{ROUND}_expanded_solver_panel_summary_v1",
        "decision": decision,
        "base_fresh_transfer_decision": base_decision,
        "expanded_solver_panel_ran": True,
        "expanded_exact_materialization_passed": base_summary.get("fresh_exact_materialization_passed") is True,
        "device": device,
        "contexts": len(contexts),
        "preferred_split": args.preferred_split,
        "min_preferred_contexts": args.min_preferred_contexts,
        "context_split_counts": split_counts,
        "context_selection_train_contexts": train_contexts,
        "checkpoints": [relpath(path) for path in ckpts],
        "checkpoint_manifest": checkpoint_manifest,
        "solver_overwrite": solver_overwrite,
        "elapsed_sec": time.perf_counter() - started,
    }
    write_json(paths["summary"], summary)
    print(json.dumps({"decision": decision, "actor_rows": summary["actor_candidate_rows"], "pairs": len(pairs)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
