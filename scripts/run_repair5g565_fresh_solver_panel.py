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

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import run_repair5g562_replay_truth as g562  # noqa: E402
from gcst.goal_aware_actor import make_graph_batch, pad_od_tokens, scalar_features  # noqa: E402
from gcst.real_label_graph_dataset import DEFAULT_CONTEXT_DIR, G560_TRAINING_ROWS, build_example, load_label_groups  # noqa: E402
from gcst.rich_training_g565 import make_model, move_graph_batch  # noqa: E402
from gcst.theta_schema import THETA_NUMERIC_COLUMNS, mode_columns  # noqa: E402


ROUND = "phase5p5_repair5g565"
REPORTS = ROOT / "outputs/reports"
TABLES = ROOT / "outputs/tables"
LOGS = ROOT / "outputs/logs"


def resolve(path: str | Path) -> Path:
    p = Path(path)
    return p if p.is_absolute() else ROOT / p


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


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


def read_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def recalibrate_label_margin_after_fresh() -> dict[str, Any]:
    import calibrate_repair5g565_label_margin as margin  # noqa: WPS433

    rc = margin.main([])
    if rc != 0:
        raise RuntimeError(f"G5.65 label margin recalibration failed with rc={rc}")
    return read_json(REPORTS / f"{ROUND}_label_margin_summary.json")


def load_contexts(rows_path: Path, context_dir: Path, max_contexts: int, preferred_split: str, min_preferred_contexts: int = 400) -> list[g562.ReplayContext]:
    g562.register_external_maps(context_dir)
    groups = load_label_groups(resolve(rows_path), resolve(context_dir), max_contexts=0)
    if preferred_split != "any":
        wanted = {token.strip() for token in preferred_split.split(",") if token.strip()}
        preferred = [group for group in groups if group.split in wanted]
        minimum = min(int(max_contexts), int(min_preferred_contexts)) if max_contexts else int(min_preferred_contexts)
        if len(preferred) < minimum:
            raise ValueError(f"fresh solver preferred split has {len(preferred)} contexts, below required minimum {minimum}: {preferred_split}")
        if preferred:
            groups = preferred
    contexts: list[g562.ReplayContext] = []
    for idx, group in enumerate(groups):
        built = build_example(group)
        graph_t = g562.graph_with_edge_features(built.graph, built.traffic["edge_features"])
        feature_row = {
            "agent_count": group.agent_count,
            "agents": group.agent_count,
            "nominal_budget_ms": group.budget_ms,
            "budget_ms": group.budget_ms,
            "base_time_limit_sec": group.rows[0].get("base_time_limit_sec", 1.0),
            "ltm_max_iterations": group.rows[0].get("ltm_max_iterations", 3),
            "agent_density": group.rows[0].get("agent_density", 0.0),
            **built.traffic["summary"],
        }
        contexts.append(
            g562.ReplayContext(
                dataset_row_id=f"g565_real_graph_{idx:06d}",
                evaluation_uid=group.evaluation_uid,
                instance_uid=group.instance_uid,
                split=group.split,
                map=group.map,
                map_family=group.map_family,
                agents=group.agent_count,
                seed=group.seed,
                budget_ms=group.budget_ms,
                base_time_limit_sec=float(g562.number(group.rows[0].get("base_time_limit_sec"), max(0.5, group.budget_ms / 1000.0))),
                ltm_max_iterations=max(1, int(g562.number(group.rows[0].get("ltm_max_iterations"), 3))),
                horizon_id=group.horizon_id,
                scenario_sha256=group.scenario_sha256_expected,
                physical_map_sha256=group.physical_map_sha256_expected,
                graph_with_traffic=graph_t,
                assignment=built.assignment,
                feature_row=feature_row,
            )
        )
        if max_contexts and len(contexts) >= max_contexts:
            break
    return contexts


def checkpoint_paths(patterns: list[str]) -> list[Path]:
    out: list[Path] = []
    for pattern in patterns:
        paths = sorted(ROOT.glob(pattern))
        out.extend(path for path in paths if path.is_file())
    unique = []
    seen = set()
    for path in out:
        if path not in seen:
            unique.append(path)
            seen.add(path)
    return unique


def relpath(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def screening_rich_all_paths() -> list[Path]:
    return [
        ROOT / "artifacts/models/gcst" / f"{ROUND}_screening_scaling_{arch.lower()}_fold0_all_seed565.pt"
        for arch in ["E0", "E1", "E2"]
    ]


def complete_required_rich_checkpoints(paths: list[Path]) -> tuple[list[Path], list[Path], list[Path]]:
    out = list(paths)
    seen = {path.resolve() for path in out}
    added: list[Path] = []
    missing: list[Path] = []
    for path in screening_rich_all_paths():
        if path.exists():
            resolved = path.resolve()
            if resolved not in seen:
                out.append(path)
                seen.add(resolved)
                added.append(path)
        else:
            missing.append(path)
    return out, added, missing


def current_manifest_checkpoint_paths() -> tuple[set[Path], dict[str, Any]]:
    allowed: set[Path] = set()
    scaling_rows = read_rows(TABLES / f"{ROUND}_scaling_by_fold_seed_size.csv")
    for row in scaling_rows:
        checkpoint = row.get("checkpoint_path", "")
        if checkpoint and str(row.get("size_label", "")) == "all" and str(row.get("seed", "")) == "565":
            allowed.add(resolve(checkpoint).resolve())

    screening_paths = screening_rich_all_paths()
    for path in screening_paths:
        allowed.add(path.resolve())

    cycle_rows = read_rows(TABLES / f"{ROUND}_rich_retraining_cycle_rows.csv")
    for row in cycle_rows:
        checkpoint = row.get("checkpoint_path", "")
        if checkpoint and str(row.get("cycle_label", "")) == "merged" and str(row.get("seed", "")) == "565":
            allowed.add(resolve(checkpoint).resolve())

    manifest = {
        "confirmatory_scaling_rows": len(scaling_rows),
        "confirmatory_all_seed565_checkpoints": sum(
            1
            for row in scaling_rows
            if row.get("checkpoint_path") and str(row.get("size_label", "")) == "all" and str(row.get("seed", "")) == "565"
        ),
        "required_screening_rich_checkpoints": [relpath(path) for path in screening_paths],
        "rich_cycle_rows": len(cycle_rows),
        "rich_cycle_merged_seed565_checkpoints": sum(
            1
            for row in cycle_rows
            if row.get("checkpoint_path") and str(row.get("cycle_label", "")) == "merged" and str(row.get("seed", "")) == "565"
        ),
    }
    return allowed, manifest


def filter_current_checkpoints(paths: list[Path]) -> tuple[list[Path], list[Path], dict[str, Any]]:
    allowed, manifest = current_manifest_checkpoint_paths()
    accepted: list[Path] = []
    rejected: list[Path] = []
    for path in paths:
        if path.resolve() in allowed:
            accepted.append(path)
        else:
            rejected.append(path)
    manifest["accepted_checkpoints"] = [relpath(path) for path in accepted]
    manifest["rejected_non_manifest_checkpoints"] = [relpath(path) for path in rejected]
    return accepted, rejected, manifest


def infer_thetas(contexts: list[g562.ReplayContext], ckpts: list[Path], *, device: str, batch_size: int) -> list[dict[str, Any]]:
    import torch

    rows: list[dict[str, Any]] = []
    for ckpt_path in ckpts:
        payload = torch.load(ckpt_path, map_location=device, weights_only=False)
        model_kind = str(payload.get("model_kind", "")).upper()
        if model_kind not in {"B1", "B2", "E0", "E1", "E2"}:
            continue
        model = make_model(model_kind, hidden_dim=int(payload.get("hidden_dim", 64)), device=device)
        state = payload.get("actor_state_dict")
        if state is not None:
            model.load_state_dict(state)
        model.eval()
        for start in range(0, len(contexts), batch_size):
            batch = contexts[start : start + batch_size]
            with torch.no_grad():
                if model_kind == "B1":
                    theta = model(len(batch)).detach().cpu().numpy()
                elif model_kind == "B2":
                    scalar_x = torch.tensor(
                        np.stack([__import__("gcst.leakage_free_features", fromlist=["leakage_free_scalar_vector"]).leakage_free_scalar_vector(ctx.feature_row) for ctx in batch]),
                        dtype=torch.float32,
                        device=device,
                    )
                    theta = model(scalar_x).detach().cpu().numpy()
                else:
                    graph_batch = move_graph_batch(make_graph_batch([ctx.graph_with_traffic for ctx in batch]), device)
                    od_tokens, od_mask = pad_od_tokens([ctx.assignment for ctx in batch])
                    scalar_x = torch.tensor(np.stack([scalar_features(ctx.feature_row) for ctx in batch]), dtype=torch.float32, device=device)
                    theta = model(graph_batch, od_tokens.to(device), od_mask.to(device), scalar_x).detach().cpu().numpy()
            for ctx, values in zip(batch, theta):
                row = {col: float(values[idx]) for idx, col in enumerate(THETA_NUMERIC_COLUMNS)}
                row.update(mode_columns("flow_shield"))
                rows.append(
                    {
                        "phase": "g565_fresh_solver_panel",
                        "context_id": ctx.dataset_row_id,
                        "dataset_row_id": ctx.dataset_row_id,
                        "g562_evaluation_uid": ctx.evaluation_uid,
                        "variant_id": model_kind,
                        "variant_name": model_kind,
                        "seed": payload.get("metrics", {}).get("seed", ""),
                        "method": f"g565_{model_kind}_{ckpt_path.stem}",
                        "model_path": str(ckpt_path.relative_to(ROOT)).replace("\\", "/"),
                        **row,
                    }
                )
    return rows


def summarize_pairs(rows: list[dict[str, Any]], pairs: list[dict[str, Any]], plan_rows: list[dict[str, Any]]) -> dict[str, Any]:
    actor_rows = [row for row in rows if g562.boolish(row.get("is_actor_row"))]
    exact = sum(g562.boolish(row.get("fulltheta_fingerprint_match_strict")) for row in actor_rows)
    recognized = sum(g562.boolish(row.get("candidate_recognized_bool")) for row in actor_rows)
    scenario = sum(g562.boolish(row.get("scenario_sha256_match")) for row in actor_rows)
    identity = sum(g562.boolish(row.get("identity_retained")) for row in actor_rows)
    force_additive_false = sum(g562.boolish(row.get("force_additive_false")) for row in actor_rows)
    dual_channel_enabled = sum(g562.boolish(row.get("dual_channel_enabled")) for row in actor_rows)
    regressions = sum(g562.boolish(row.get("success_regression")) for row in pairs)
    gains = sum(g562.boolish(row.get("success_gain")) for row in pairs)
    finite = [g562.finite_float(row.get("quality_delta_vs_g556")) for row in pairs]
    finite = [value for value in finite if value is not None]
    heldout_pairs = [row for row in pairs if str(row.get("split")) in {"validation", "heldout", "blind"}]
    materialized = bool(
        actor_rows
        and exact == len(actor_rows)
        and recognized == len(actor_rows)
        and scenario == len(actor_rows)
        and identity == len(actor_rows)
        and force_additive_false == len(actor_rows)
        and dual_channel_enabled == len(actor_rows)
    )
    worse_count = sum(value > 0.0 for value in finite)
    better_count = sum(value < 0.0 for value in finite)
    harmful_tail_q90 = float(np.quantile(finite, 0.90)) if finite else None
    harmful_tail_q95 = float(np.quantile(finite, 0.95)) if finite else None
    tail_values = [value for value in finite if value > 0.0]
    harmful_cvar = float(np.mean(sorted(tail_values, reverse=True)[: max(1, int(np.ceil(0.10 * len(tail_values))))])) if tail_values else 0.0
    harmful_tail_present = bool(regressions > 0 or worse_count > 0)
    by_variant: dict[str, dict[str, Any]] = {}
    for pair in pairs:
        variant_id = str(pair.get("variant_id", "") or "unknown")
        model_path = str(pair.get("model_path", "") or "")
        method = str(pair.get("method", "") or "")
        variant = f"{variant_id}::{model_path or method or 'unknown'}"
        bucket = by_variant.setdefault(
            variant,
            {
                "variant_id": variant_id,
                "model_path": model_path,
                "method": method,
                "pairs": 0,
                "success_regressions": 0,
                "success_gains": 0,
                "better_count_vs_g556": 0,
                "worse_count_vs_g556": 0,
                "quality_delta_vs_g556": [],
            },
        )
        bucket["pairs"] += 1
        bucket["success_regressions"] += int(g562.boolish(pair.get("success_regression")))
        bucket["success_gains"] += int(g562.boolish(pair.get("success_gain")))
        value = g562.finite_float(pair.get("quality_delta_vs_g556"))
        if value is not None:
            bucket["quality_delta_vs_g556"].append(value)
            bucket["better_count_vs_g556"] += int(value < 0.0)
            bucket["worse_count_vs_g556"] += int(value > 0.0)
    per_variant: dict[str, dict[str, Any]] = {}
    supporting_rich_variants: list[str] = []
    for variant, bucket in sorted(by_variant.items()):
        values = bucket.pop("quality_delta_vs_g556")
        rich_variant = str(bucket.get("variant_id", "")).upper().startswith("E")
        supported = bool(rich_variant and bucket["pairs"] and bucket["success_regressions"] == 0 and bucket["worse_count_vs_g556"] == 0 and bucket["success_gains"] > 0)
        if supported:
            supporting_rich_variants.append(variant)
        per_variant[variant] = {
            **bucket,
            "rich_variant": rich_variant,
            "mean_quality_delta_vs_g556": float(np.mean(values)) if values else None,
            "median_quality_delta_vs_g556": float(np.median(values)) if values else None,
            "strict_transfer_positive_vs_g556": supported,
        }
    if not materialized:
        decision = "g565_fresh_solver_transfer_materialization_incomplete"
    elif supporting_rich_variants:
        decision = "g565_fresh_solver_transfer_positive"
    else:
        decision = "g565_fresh_solver_transfer_tail_blocked"
    return {
        "schema_version": f"{ROUND}_fresh_solver_panel_summary_v1",
        "decision": decision,
        "fresh_solver_panel_ran": True,
        "planned_rows": len(plan_rows),
        "executed_rows": len(rows),
        "actor_candidate_rows": len(actor_rows),
        "new_exact_diagnostic_rows": len(actor_rows),
        "candidate_recognized_rate": recognized / max(1, len(actor_rows)),
        "fingerprint_exact_rate": exact / max(1, len(actor_rows)),
        "scenario_hash_match_rate": scenario / max(1, len(actor_rows)),
        "identity_retention_rate": identity / max(1, len(actor_rows)),
        "force_additive_false_rate": force_additive_false / max(1, len(actor_rows)),
        "dual_channel_enabled_rate": dual_channel_enabled / max(1, len(actor_rows)),
        "fresh_exact_materialization_passed": materialized,
        "replay_pairs": len(pairs),
        "nontrain_replay_pairs": len(heldout_pairs),
        "success_regressions": regressions,
        "success_gains": gains,
        "mean_quality_delta_vs_g556": float(np.mean(finite)) if finite else None,
        "median_quality_delta_vs_g556": float(np.median(finite)) if finite else None,
        "better_count_vs_g556": better_count,
        "worse_count_vs_g556": worse_count,
        "harmful_quality_tail_present": harmful_tail_present,
        "harmful_quality_delta_q90_vs_g556": harmful_tail_q90,
        "harmful_quality_delta_q95_vs_g556": harmful_tail_q95,
        "harmful_quality_delta_cvar_top10_vs_g556": harmful_cvar,
        "per_variant_transfer": per_variant,
        "supporting_rich_variants": supporting_rich_variants,
        "fresh_solver_panel_is_new_execution": True,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run G5.65 fresh exact solver transfer panel.")
    parser.add_argument("--rows-path", type=Path, default=G560_TRAINING_ROWS)
    parser.add_argument("--context-dir", type=Path, default=DEFAULT_CONTEXT_DIR)
    parser.add_argument("--contexts", type=int, default=1000)
    parser.add_argument("--preferred-split", default="validation,heldout,blind,test")
    parser.add_argument("--min-preferred-contexts", type=int, default=400)
    parser.add_argument("--checkpoint-glob", nargs="*", default=["artifacts/models/gcst/phase5p5_repair5g565_scaling_*_all_seed565.pt"])
    parser.add_argument("--device", default="auto")
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--binary", type=Path, default=Path("build/phase1a-batch/phase1a_batch"))
    parser.add_argument("--max-workers", type=int, default=8)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--resume-existing", action="store_true")
    parser.add_argument("--plan-only", action="store_true")
    args = parser.parse_args(argv)

    import torch

    device = "cuda" if args.device == "auto" and torch.cuda.is_available() else ("cpu" if args.device == "auto" else args.device)
    solver_overwrite = bool(args.overwrite or not args.resume_existing)
    started = time.perf_counter()
    try:
        contexts = load_contexts(resolve(args.rows_path), resolve(args.context_dir), args.contexts, args.preferred_split, args.min_preferred_contexts)
    except ValueError as exc:
        summary = {
            "schema_version": f"{ROUND}_fresh_solver_panel_summary_v1",
            "decision": "g565_fresh_solver_transfer_blocked_insufficient_nontrain_contexts",
            "fresh_solver_panel_ran": False,
            "preferred_split": args.preferred_split,
            "min_preferred_contexts": args.min_preferred_contexts,
            "error": str(exc),
        }
        write_json(REPORTS / f"{ROUND}_fresh_solver_panel_summary.json", summary)
        print(json.dumps(summary, sort_keys=True))
        return 2
    split_counts = dict(Counter(ctx.split for ctx in contexts))
    train_contexts = int(split_counts.get("train", 0))
    ckpts = checkpoint_paths(args.checkpoint_glob)
    ckpts, auto_added_ckpts, missing_screening_rich_ckpts = complete_required_rich_checkpoints(ckpts)
    if not ckpts:
        summary = {"schema_version": f"{ROUND}_fresh_solver_panel_summary_v1", "decision": "g565_fresh_solver_transfer_blocked_missing_checkpoints", "fresh_solver_panel_ran": False}
        write_json(REPORTS / f"{ROUND}_fresh_solver_panel_summary.json", summary)
        print(json.dumps(summary, sort_keys=True))
        return 2
    if missing_screening_rich_ckpts:
        summary = {
            "schema_version": f"{ROUND}_fresh_solver_panel_summary_v1",
            "decision": "g565_fresh_solver_transfer_blocked_missing_screening_rich_checkpoints",
            "fresh_solver_panel_ran": False,
            "missing_screening_rich_checkpoints": [str(path.relative_to(ROOT)).replace("\\", "/") for path in missing_screening_rich_ckpts],
        }
        write_json(REPORTS / f"{ROUND}_fresh_solver_panel_summary.json", summary)
        print(json.dumps(summary, sort_keys=True))
        return 2
    ckpts, rejected_non_manifest_ckpts, checkpoint_manifest = filter_current_checkpoints(ckpts)
    if not ckpts:
        summary = {
            "schema_version": f"{ROUND}_fresh_solver_panel_summary_v1",
            "decision": "g565_fresh_solver_transfer_blocked_no_current_manifest_checkpoints",
            "fresh_solver_panel_ran": False,
            "checkpoint_manifest_filter": checkpoint_manifest,
        }
        write_json(REPORTS / f"{ROUND}_fresh_solver_panel_summary.json", summary)
        print(json.dumps(summary, sort_keys=True))
        return 2
    theta_rows = infer_thetas(contexts, ckpts, device=device, batch_size=args.batch_size)
    plan_rows, registry_rows = g562.build_plan_and_registry(contexts, theta_rows, "g565_fresh_solver_panel")
    paths = {
        "plan": TABLES / f"{ROUND}_fresh_solver_panel_plan.csv",
        "registry": TABLES / f"{ROUND}_fresh_solver_panel_registry.csv",
        "results": TABLES / f"{ROUND}_fresh_solver_panel_results.csv",
        "raw_results": TABLES / f"{ROUND}_fresh_solver_panel_results.raw.csv",
        "pairs": TABLES / f"{ROUND}_fresh_solver_panel_pairs.csv",
        "summary": REPORTS / f"{ROUND}_fresh_solver_panel_summary.json",
        "scenario_metadata": REPORTS / f"{ROUND}_fresh_solver_panel_scenario_generation.json",
        "log_dir": LOGS / f"{ROUND}_fresh_solver_panel",
        "scenario_dir": resolve(args.context_dir) / "scenarios",
    }
    write_rows(paths["plan"], plan_rows)
    write_rows(paths["registry"], registry_rows)
    if args.plan_only:
        summary = {
            "schema_version": f"{ROUND}_fresh_solver_panel_summary_v1",
            "decision": "g565_fresh_solver_panel_plan_created",
            "fresh_solver_panel_ran": False,
            "contexts": len(contexts),
            "preferred_split": args.preferred_split,
            "min_preferred_contexts": args.min_preferred_contexts,
            "context_split_counts": split_counts,
            "context_selection_train_contexts": train_contexts,
            "checkpoints": [str(path.relative_to(ROOT)).replace("\\", "/") for path in ckpts],
            "auto_added_screening_rich_checkpoints": [str(path.relative_to(ROOT)).replace("\\", "/") for path in auto_added_ckpts],
            "rejected_non_manifest_checkpoints": [relpath(path) for path in rejected_non_manifest_ckpts],
            "checkpoint_manifest_filter": checkpoint_manifest,
            "planned_rows": len(plan_rows),
            "actor_candidate_rows": len(theta_rows),
            "solver_overwrite": solver_overwrite,
        }
        write_json(paths["summary"], summary)
        print(json.dumps(summary, sort_keys=True))
        return 0
    run_args = SimpleNamespace(binary=args.binary, overwrite=solver_overwrite, max_workers=args.max_workers, phase="g565_fresh_solver_panel")
    rc = g562.run_solver(plan_rows, paths, run_args)
    if rc != 0:
        summary = {"schema_version": f"{ROUND}_fresh_solver_panel_summary_v1", "decision": "g565_fresh_solver_transfer_blocked_solver_not_executed", "fresh_solver_panel_ran": False, "rc": rc}
        write_json(paths["summary"], summary)
        print(json.dumps(summary, sort_keys=True))
        return rc
    rows = g562.audit_results(g562.read_rows(paths["results"]), plan_rows, paths["scenario_dir"], "g565_fresh_solver_panel")
    write_rows(paths["results"], rows)
    pairs = g562.build_pairs(rows, "g565_fresh_solver_panel")
    write_rows(paths["pairs"], pairs)
    label_margin = recalibrate_label_margin_after_fresh()
    summary = summarize_pairs(rows, pairs, plan_rows)
    summary.update(
        {
            "device": device,
            "contexts": len(contexts),
            "preferred_split": args.preferred_split,
            "min_preferred_contexts": args.min_preferred_contexts,
            "context_split_counts": split_counts,
            "context_selection_train_contexts": train_contexts,
            "checkpoints": [str(path.relative_to(ROOT)).replace("\\", "/") for path in ckpts],
            "auto_added_screening_rich_checkpoints": [str(path.relative_to(ROOT)).replace("\\", "/") for path in auto_added_ckpts],
            "rejected_non_manifest_checkpoints": [relpath(path) for path in rejected_non_manifest_ckpts],
            "checkpoint_manifest_filter": checkpoint_manifest,
            "label_margin_recalibrated_after_fresh": True,
            "label_margin_fresh_g565_pairs_included": label_margin.get("fresh_g565_pairs_included"),
            "label_margin_exact_pair_rows": label_margin.get("exact_pair_rows"),
            "label_margin_recommended_positive_margin": label_margin.get("recommended_positive_margin"),
            "solver_overwrite": solver_overwrite,
            "elapsed_sec": time.perf_counter() - started,
        }
    )
    write_json(paths["summary"], summary)
    print(json.dumps({"decision": summary["decision"], "actor_rows": summary["actor_candidate_rows"], "pairs": len(pairs)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
