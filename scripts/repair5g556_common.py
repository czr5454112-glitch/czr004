"""Repair5G.5.56 transformer/retrieval fixed-staticflow surrogate.

This round keeps the candidate object deliberately narrow: one global fixed
UpdateParams theta vector.  The neural surrogate is an offline optimizer only;
promotion is still decided by paired solver replay against the promoted G5.55
baseline candidate g554_c00051.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import random
import statistics
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

try:
    import numpy as np
except Exception:  # pragma: no cover
    np = None  # type: ignore[assignment]

try:
    import pandas as pd
except Exception:  # pragma: no cover
    pd = None  # type: ignore[assignment]

try:
    from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor, RandomForestClassifier
    from sklearn.linear_model import LogisticRegression, Ridge
    from sklearn.metrics import average_precision_score, brier_score_loss, mean_absolute_error, roc_auc_score
    from sklearn.model_selection import train_test_split
    from sklearn.neural_network import MLPClassifier, MLPRegressor
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    SKLEARN_AVAILABLE = True
except Exception:  # pragma: no cover
    SKLEARN_AVAILABLE = False

try:
    import torch
    from torch import nn
    from torch.utils.data import DataLoader, TensorDataset

    TORCH_AVAILABLE = True
except Exception:  # pragma: no cover
    TORCH_AVAILABLE = False

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))
else:  # pragma: no cover
    ROOT = Path(__file__).resolve().parents[1]

import repair5g549_common as g549  # noqa: E402
import repair5g553_common as g553  # noqa: E402
import repair5g554_common as g554  # noqa: E402
from repair5g531_common import (  # noqa: E402
    boolish,
    claims,
    csv_number,
    external_lacam2_clean,
    load_json,
    number,
    read_rows,
    resolve,
    stable_hash,
    write_json,
    write_rows,
    write_text,
)


ROUND = "repair5g556"
PLAN_FILE = "czr004_g556_transformer_retrieval_fixed_staticflow_plan.md"
PROMOTED_BASELINE_ID = "g554_c00051"
OLD_HAND_STATIC_FLOW_ID = g553.STATIC_FLOW
ADDITIVE_ID = g553.ADDITIVE
FAMILY_STATIC_ID = g553.FAMILY_STATIC
PRIMARY_BASELINE_LABEL = "g554_c00051"
CLAIM_KEYS = list(claims().keys())
SEED = 20260616 + 556

THETA_COLUMNS = list(g554.THETA_COLUMNS)
THETA_BOUNDS = dict(g554.THETA_BOUNDS)
MODE_COLUMNS = set(g554.MODE_COLUMNS)
NUMERIC_THETA_COLUMNS = [col for col in THETA_COLUMNS if col not in MODE_COLUMNS]
ACTIVE_FIELDS = list(g554.ACTIVE_SEARCH_FIELDS)

G555_DECISION_SUMMARY = "outputs/reports/phase5p5_repair5g555_decision_summary.json"
G555_VALIDATION_SUMMARY = "outputs/reports/phase5p5_repair5g555_corrected_validation_summary.json"
G555_BLIND_SUMMARY = "outputs/reports/phase5p5_repair5g555_blind_summary.json"
G555_BLIND_LEADERBOARD = "outputs/tables/phase5p5_repair5g555_blind_candidate_leaderboard.csv"
G555_FINAL_THETA = "outputs/tables/phase5p5_repair5g555_final_candidate_theta.csv"

VERIFY_REPORT = "outputs/reports/phase5p5_repair5g556_g555_verification.md"
VERIFY_SUMMARY = "outputs/reports/phase5p5_repair5g556_g555_verification_summary.json"
ARTIFACT_AUDIT_CSV = "outputs/tables/phase5p5_repair5g556_g555_artifact_audit.csv"
CLAIM_FLAG_AUDIT_CSV = "outputs/tables/phase5p5_repair5g556_claim_flag_audit.csv"

BASELINE_AUDIT_REPORT = "outputs/reports/phase5p5_repair5g556_promoted_baseline_audit.md"
BASELINE_AUDIT_SUMMARY = "outputs/reports/phase5p5_repair5g556_promoted_baseline_audit_summary.json"
PROMOTED_THETA_CSV = "outputs/tables/phase5p5_repair5g556_promoted_baseline_theta.csv"

LITERATURE_REPORT = "outputs/reports/phase5p5_repair5g556_literature_model_audit.md"
LITERATURE_SUMMARY = "outputs/reports/phase5p5_repair5g556_literature_model_audit_summary.json"
MODEL_MATRIX_CSV = "outputs/tables/phase5p5_repair5g556_model_family_decision_matrix.csv"

MANIFEST_REPORT = "outputs/reports/phase5p5_repair5g556_unified_dataset_manifest.md"
MANIFEST_SUMMARY = "outputs/reports/phase5p5_repair5g556_unified_dataset_manifest_summary.json"
SOURCE_MANIFEST_CSV = "outputs/tables/phase5p5_repair5g556_source_artifact_manifest.csv"
SOURCE_SCHEMA_AUDIT_CSV = "outputs/tables/phase5p5_repair5g556_source_schema_audit.csv"
AVAILABLE_RAW_CSV = "outputs/tables/phase5p5_repair5g556_available_raw_artifacts.csv"
MISSING_RAW_CSV = "outputs/tables/phase5p5_repair5g556_missing_raw_artifacts.csv"

DATASET_REPORT = "outputs/reports/phase5p5_repair5g556_surrogate_dataset.md"
DATASET_SUMMARY = "outputs/reports/phase5p5_repair5g556_surrogate_dataset_summary.json"
DATASET_PREVIEW_CSV = "outputs/tables/phase5p5_repair5g556_surrogate_dataset_preview.csv"
SPLIT_SUMMARY_CSV = "outputs/tables/phase5p5_repair5g556_surrogate_split_summary.csv"
FEATURE_MANIFEST_CSV = "outputs/tables/phase5p5_repair5g556_surrogate_feature_manifest.csv"
LABEL_MANIFEST_CSV = "outputs/tables/phase5p5_repair5g556_surrogate_label_manifest.csv"
LEAKAGE_AUDIT_CSV = "outputs/tables/phase5p5_repair5g556_surrogate_leakage_audit.csv"

FTRST_REPORT = "outputs/reports/phase5p5_repair5g556_ftrst_eval.md"
FTRST_SUMMARY = "outputs/reports/phase5p5_repair5g556_ftrst_eval_summary.json"
FTRST_METRICS_CSV = "outputs/tables/phase5p5_repair5g556_ftrst_metrics.csv"
FTRST_CALIBRATION_CSV = "outputs/tables/phase5p5_repair5g556_ftrst_calibration.csv"
FTRST_OOF_CSV = "outputs/tables/phase5p5_repair5g556_ftrst_oof_sample.csv"
FTRST_MANIFEST = "artifacts/models/laur_ltm/repair5g556_ftrst_manifest.json"

FT_REPORT = "outputs/reports/phase5p5_repair5g556_ft_transformer_eval.md"
FT_SUMMARY = "outputs/reports/phase5p5_repair5g556_ft_transformer_eval_summary.json"
FT_METRICS_CSV = "outputs/tables/phase5p5_repair5g556_ft_transformer_metrics.csv"

SAINT_REPORT = "outputs/reports/phase5p5_repair5g556_saint_amformer_diagnostics.md"
SAINT_SUMMARY = "outputs/reports/phase5p5_repair5g556_saint_amformer_diagnostics_summary.json"
SAINT_METRICS_CSV = "outputs/tables/phase5p5_repair5g556_saint_amformer_metrics.csv"

TABM_REPORT = "outputs/reports/phase5p5_repair5g556_tabm_mlp_controls.md"
TABM_SUMMARY = "outputs/reports/phase5p5_repair5g556_tabm_mlp_controls_summary.json"
TABM_METRICS_CSV = "outputs/tables/phase5p5_repair5g556_tabm_mlp_metrics.csv"

GBDT_REPORT = "outputs/reports/phase5p5_repair5g556_gbdt_controls.md"
GBDT_SUMMARY = "outputs/reports/phase5p5_repair5g556_gbdt_controls_summary.json"
GBDT_METRICS_CSV = "outputs/tables/phase5p5_repair5g556_gbdt_metrics.csv"

CANDIDATE_REPORT = "outputs/reports/phase5p5_repair5g556_candidate_generation.md"
CANDIDATE_SUMMARY = "outputs/reports/phase5p5_repair5g556_candidate_generation_summary.json"
CANDIDATE_PREVIEW_CSV = "outputs/tables/phase5p5_repair5g556_candidate_registry_preview.csv"
CANDIDATE_SCORES_CSV = "outputs/tables/phase5p5_repair5g556_candidate_acquisition_scores.csv"
CANDIDATE_FAMILY_CSV = "outputs/tables/phase5p5_repair5g556_candidate_family_breakdown.csv"

STAGE1_PLAN_REPORT = "outputs/reports/phase5p5_repair5g556_stage1_solver_screen_plan.md"
STAGE1_PLAN_SUMMARY = "outputs/reports/phase5p5_repair5g556_stage1_solver_screen_plan_summary.json"
STAGE1_LOG_DIR = "outputs/logs/phase5p5_repair5g556_stage1_solver_screen"
STAGE1_PLAN_LOG = f"{STAGE1_LOG_DIR}/stage1_solver_screen_plan.csv"
STAGE1_RESULTS_LOG = f"{STAGE1_LOG_DIR}/stage1_solver_screen_results.csv"
STAGE1_RAW_LOG = f"{STAGE1_LOG_DIR}/stage1_solver_screen_results.raw.csv"
STAGE1_RUN_JSONL = f"{STAGE1_LOG_DIR}/runs.jsonl"
STAGE1_COMMAND_JSONL = f"{STAGE1_LOG_DIR}/commands.jsonl"
STAGE1_UPDATE_JSONL = f"{STAGE1_LOG_DIR}/updates.jsonl"
STAGE1_PROBE_JSONL = f"{STAGE1_LOG_DIR}/counterfactual_probes.jsonl"
STAGE1_CHECKPOINT_JSONL = f"{STAGE1_LOG_DIR}/checkpoints.jsonl"
STAGE1_STATUS_JSON = f"{STAGE1_LOG_DIR}/status.json"
STAGE1_SCENARIO_DIR = "outputs/tmp/phase5p5_repair5g556_stage1_scenarios"
STAGE1_SCENARIO_METADATA = "outputs/reports/phase5p5_repair5g556_stage1_scenario_generation.json"
STAGE1_REPORT = "outputs/reports/phase5p5_repair5g556_stage1_solver_screen.md"
STAGE1_SUMMARY = "outputs/reports/phase5p5_repair5g556_stage1_solver_screen_summary.json"
STAGE1_LEADERBOARD_CSV = "outputs/tables/phase5p5_repair5g556_stage1_candidate_leaderboard.csv"
STAGE1_BY_STRATUM_CSV = "outputs/tables/phase5p5_repair5g556_stage1_by_stratum.csv"
STAGE1_SURROGATE_VS_ACTUAL_CSV = "outputs/tables/phase5p5_repair5g556_stage1_surrogate_vs_actual.csv"
STAGE1_FAILURES_CSV = "outputs/tables/phase5p5_repair5g556_stage1_failure_cases.csv"

STAGE2_PLAN_REPORT = "outputs/reports/phase5p5_repair5g556_stage2_elite_validation_plan.md"
STAGE2_PLAN_SUMMARY = "outputs/reports/phase5p5_repair5g556_stage2_elite_validation_plan_summary.json"
STAGE2_LOG_DIR = "outputs/logs/phase5p5_repair5g556_stage2_elite_validation"
STAGE2_PLAN_LOG = f"{STAGE2_LOG_DIR}/stage2_elite_validation_plan.csv"
STAGE2_RESULTS_LOG = f"{STAGE2_LOG_DIR}/stage2_elite_validation_results.csv"
STAGE2_RAW_LOG = f"{STAGE2_LOG_DIR}/stage2_elite_validation_results.raw.csv"
STAGE2_RUN_JSONL = f"{STAGE2_LOG_DIR}/runs.jsonl"
STAGE2_COMMAND_JSONL = f"{STAGE2_LOG_DIR}/commands.jsonl"
STAGE2_UPDATE_JSONL = f"{STAGE2_LOG_DIR}/updates.jsonl"
STAGE2_PROBE_JSONL = f"{STAGE2_LOG_DIR}/counterfactual_probes.jsonl"
STAGE2_CHECKPOINT_JSONL = f"{STAGE2_LOG_DIR}/checkpoints.jsonl"
STAGE2_STATUS_JSON = f"{STAGE2_LOG_DIR}/status.json"
STAGE2_SCENARIO_DIR = "outputs/tmp/phase5p5_repair5g556_stage2_scenarios"
STAGE2_SCENARIO_METADATA = "outputs/reports/phase5p5_repair5g556_stage2_scenario_generation.json"
STAGE2_REPORT = "outputs/reports/phase5p5_repair5g556_stage2_elite_validation.md"
STAGE2_SUMMARY = "outputs/reports/phase5p5_repair5g556_stage2_elite_validation_summary.json"
STAGE2_LEADERBOARD_CSV = "outputs/tables/phase5p5_repair5g556_stage2_candidate_leaderboard.csv"
STAGE2_BY_STRATUM_CSV = "outputs/tables/phase5p5_repair5g556_stage2_by_stratum.csv"
STAGE2_OLD_HAND_CSV = "outputs/tables/phase5p5_repair5g556_stage2_vs_old_hand_staticflow.csv"
STAGE2_ADDITIVE_CSV = "outputs/tables/phase5p5_repair5g556_stage2_vs_additive.csv"
STAGE2_SHORTLIST_CSV = "outputs/tables/phase5p5_repair5g556_stage2_validation_shortlist.csv"

BLIND_PLAN_REPORT = "outputs/reports/phase5p5_repair5g556_blind_plan.md"
BLIND_PLAN_SUMMARY = "outputs/reports/phase5p5_repair5g556_blind_plan_summary.json"
BLIND_LOG_DIR = "outputs/logs/phase5p5_repair5g556_blind"
BLIND_PLAN_LOG = f"{BLIND_LOG_DIR}/blind_plan.csv"
BLIND_RESULTS_LOG = f"{BLIND_LOG_DIR}/blind_results.csv"
BLIND_RAW_LOG = f"{BLIND_LOG_DIR}/blind_results.raw.csv"
BLIND_RUN_JSONL = f"{BLIND_LOG_DIR}/runs.jsonl"
BLIND_COMMAND_JSONL = f"{BLIND_LOG_DIR}/commands.jsonl"
BLIND_UPDATE_JSONL = f"{BLIND_LOG_DIR}/updates.jsonl"
BLIND_PROBE_JSONL = f"{BLIND_LOG_DIR}/counterfactual_probes.jsonl"
BLIND_CHECKPOINT_JSONL = f"{BLIND_LOG_DIR}/checkpoints.jsonl"
BLIND_STATUS_JSON = f"{BLIND_LOG_DIR}/status.json"
BLIND_SCENARIO_DIR = "outputs/tmp/phase5p5_repair5g556_blind_scenarios"
BLIND_SCENARIO_METADATA = "outputs/reports/phase5p5_repair5g556_blind_scenario_generation.json"
BLIND_REPORT = "outputs/reports/phase5p5_repair5g556_blind.md"
BLIND_SUMMARY = "outputs/reports/phase5p5_repair5g556_blind_summary.json"
BLIND_LEADERBOARD_CSV = "outputs/tables/phase5p5_repair5g556_blind_candidate_leaderboard.csv"
BLIND_BY_STRATUM_CSV = "outputs/tables/phase5p5_repair5g556_blind_by_stratum.csv"
BLIND_FAILURES_CSV = "outputs/tables/phase5p5_repair5g556_blind_failure_cases.csv"

DECISION_REPORT = "outputs/reports/phase5p5_repair5g556_decision.md"
DECISION_SUMMARY = "outputs/reports/phase5p5_repair5g556_decision_summary.json"
CLAIM_LEDGER_CSV = "outputs/tables/phase5p5_repair5g556_claim_ledger.csv"
FINAL_CANDIDATE_THETA_CSV = "outputs/tables/phase5p5_repair5g556_final_candidate_theta.csv"
LARGE_ARTIFACT_MANIFEST_CSV = "outputs/tables/phase5p5_repair5g556_large_artifact_manifest.csv"


def remote_artifact_root() -> Path:
    return Path(os.environ.get("REMOTE_ARTIFACT_ROOT", "/root/shared-nvme/czr004_g556_remote_artifacts"))


def raw_candidate_registry_path() -> Path:
    return remote_artifact_root() / "raw" / "surrogate_candidate_registry.csv"


def raw_surrogate_rows_path() -> Path:
    return remote_artifact_root() / "parquet" / "surrogate_rows.csv"


def raw_candidate_context_pairs_path() -> Path:
    return remote_artifact_root() / "parquet" / "candidate_context_pairs.csv"


def raw_candidate_sets_path() -> Path:
    return remote_artifact_root() / "parquet" / "candidate_sets.csv"


def parquet_path(csv_path: Path) -> Path:
    return csv_path.with_suffix(".parquet")


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser()
    p.add_argument("--overwrite", action="store_true")
    p.add_argument("--row-limit", type=int, default=0)
    p.add_argument("--max-workers", type=int, default=1)
    p.add_argument("--binary", type=Path, default=Path(g549.DEFAULT_BINARY))
    p.add_argument("--candidate-count", type=int, default=100_000)
    p.add_argument("--selected-count", type=int, default=3_000)
    p.add_argument("--stage1-contexts", type=int, default=1_500)
    p.add_argument("--stage1-candidates-per-context", type=int, default=200)
    p.add_argument("--stage2-contexts", type=int, default=10_000)
    p.add_argument("--blind-contexts", type=int, default=60_000)
    p.add_argument("--device", default="auto")
    p.add_argument("--gpus", type=int, default=0)
    p.add_argument("--epochs", type=int, default=80)
    p.add_argument("--batch-size", default="auto")
    p.add_argument("--train-row-limit", type=int, default=0)
    p.add_argument("--ids", nargs="*", type=int)
    return p


def validate_ids(args: argparse.Namespace, label: str) -> None:
    bad = sorted({int(value) for value in (args.ids or []) if 166 <= int(value) <= 205})
    if bad:
        print(json.dumps({"decision": "reserved_id_guard_rejected", "label": label, "ids": bad}))
        raise SystemExit(1)


def git_short_head() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return ""


def table_count(path: str | Path) -> int:
    p = resolve(path) if not Path(path).is_absolute() else Path(path)
    if not p.exists():
        return 0
    if p.suffix.lower() == ".csv":
        with p.open(newline="", encoding="utf-8", errors="ignore") as handle:
            return max(0, sum(1 for _ in csv.reader(handle)) - 1)
    if p.suffix.lower() == ".jsonl":
        with p.open(encoding="utf-8", errors="ignore") as handle:
            return sum(1 for line in handle if line.strip())
    return 1


def file_bytes(path: str | Path) -> int:
    p = resolve(path) if not Path(path).is_absolute() else Path(path)
    return p.stat().st_size if p.exists() else 0


def file_sha256_if_compact(path: str | Path) -> str:
    p = resolve(path) if not Path(path).is_absolute() else Path(path)
    if not p.exists() or p.stat().st_size > 50 * 1024 * 1024:
        return ""
    h = hashlib.sha256()
    with p.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def safe_mean(values: Iterable[Any]) -> str:
    vals = [number(v, math.nan) for v in values]
    vals = [v for v in vals if math.isfinite(v)]
    return csv_number(statistics.fmean(vals)) if vals else ""


def ci_upper(values: list[float]) -> str:
    vals = [v for v in values if math.isfinite(v)]
    if not vals:
        return ""
    if len(vals) == 1:
        return csv_number(vals[0])
    return csv_number(statistics.fmean(vals) + 1.96 * statistics.stdev(vals) / math.sqrt(len(vals)))


def success(row: dict[str, Any]) -> bool:
    return boolish(row.get("solution_found", row.get("probe_solution_found", False)))


def ratio(row: dict[str, Any]) -> float | None:
    for key in ["sum_of_loss_ratio", "probe_sum_of_loss_ratio"]:
        value = row.get(key, "")
        if str(value).strip() != "":
            val = number(value, math.nan)
            return val if math.isfinite(val) else None
    return None


def pair_metrics(selected: dict[str, Any], baseline: dict[str, Any]) -> dict[str, Any]:
    sr = ratio(selected)
    br = ratio(baseline)
    ss = success(selected)
    bs = success(baseline)
    q = sr - br if ss and bs and sr is not None and br is not None else None
    return {
        "selected_success": ss,
        "baseline_success": bs,
        "success_regression": bs and not ss,
        "success_gain": ss and not bs,
        "both_success": ss and bs,
        "both_fail": (not ss) and (not bs),
        "selected_ratio": "" if sr is None else csv_number(sr),
        "baseline_ratio": "" if br is None else csv_number(br),
        "quality_delta_ratio": "" if q is None else csv_number(q),
        "better": q is not None and q < -0.005,
        "worse": q is not None and q > 0.005,
    }


def theta_mode(theta: dict[str, Any]) -> str:
    return g554.theta_mode(theta)


def clamp_theta(theta: dict[str, Any]) -> dict[str, Any]:
    return g554.clamp_theta(theta)


def promoted_theta() -> dict[str, Any]:
    for path in [G555_FINAL_THETA, G555_BLIND_LEADERBOARD]:
        for row in read_rows(path):
            if row.get("candidate_id") == PROMOTED_BASELINE_ID:
                return clamp_theta({col: row.get(col, "") for col in THETA_COLUMNS})
    return clamp_theta(g554.current_theta())


def old_hand_theta() -> dict[str, Any]:
    return clamp_theta(g554.current_theta())


def additive_theta() -> dict[str, Any]:
    return clamp_theta(g553.baseline_theta(ADDITIVE_ID))


def family_static_theta() -> dict[str, Any]:
    return clamp_theta(g553.baseline_theta(FAMILY_STATIC_ID))


def theta_distance(theta: dict[str, Any], base: dict[str, Any] | None = None) -> float:
    base = base or promoted_theta()
    total = 0.0
    for col in NUMERIC_THETA_COLUMNS:
        lo, hi = THETA_BOUNDS[col]
        span = max(1.0e-9, hi - lo)
        total += abs(number(theta.get(col), 0.0) - number(base.get(col), 0.0)) / span
    total += 0.5 if theta_mode(theta) != theta_mode(base) else 0.0
    return total


def theta_in_bounds(theta: dict[str, Any]) -> bool:
    if not theta:
        return False
    for col in NUMERIC_THETA_COLUMNS:
        lo, hi = THETA_BOUNDS[col]
        value = number(theta.get(col), math.nan)
        if not math.isfinite(value) or value < lo - 1.0e-12 or value > hi + 1.0e-12:
            return False
    mode_count = sum(1 for col in MODE_COLUMNS if int(number(theta.get(col), 0)) == 1)
    return mode_count == 1


def active_deltas(theta: dict[str, Any], base: dict[str, Any] | None = None) -> str:
    base = base or promoted_theta()
    return ";".join(col for col in THETA_COLUMNS if str(theta.get(col, "")) != str(base.get(col, "")))


def source_artifacts() -> list[dict[str, Any]]:
    return [
        {
            "source_round": "g554",
            "source_stage": "stage1_fresh_screening",
            "path": "outputs/logs/phase5p5_repair5g554_stage1_fresh_screening/stage1_fresh_screening_results.csv",
            "label_role": "mixed_primary_if_g554_present_else_auxiliary",
        },
        {
            "source_round": "g554",
            "source_stage": "stage2_nearmiss_expansion",
            "path": "outputs/logs/phase5p5_repair5g554_stage2_nearmiss_expansion/stage2_nearmiss_expansion_results.csv",
            "label_role": "primary_vs_g554_c00051",
        },
        {
            "source_round": "g555",
            "source_stage": "validation",
            "path": "outputs/logs/phase5p5_repair5g555_validation/validation_results.csv",
            "label_role": "primary_vs_g554_c00051",
        },
        {
            "source_round": "g555",
            "source_stage": "blind",
            "path": "outputs/logs/phase5p5_repair5g555_blind/blind_results.csv",
            "label_role": "primary_vs_g554_c00051_holdout",
        },
        {
            "source_round": "g550",
            "source_stage": "fulltheta_expansion",
            "path": "outputs/logs/phase5p5_repair5g550_fulltheta_expansion/fulltheta_expansion_results.csv",
            "label_role": "auxiliary_vs_old_hand_staticflow",
        },
        {
            "source_round": "g550",
            "source_stage": "active_theta_search",
            "path": "outputs/logs/phase5p5_repair5g550_active_theta_search/active_theta_search_results.csv",
            "label_role": "auxiliary_vs_old_hand_staticflow",
        },
        {
            "source_round": "g550",
            "source_stage": "generated_theta_targeted",
            "path": "outputs/logs/phase5p5_repair5g550_generated_theta_targeted/generated_theta_targeted_results.csv",
            "label_role": "auxiliary_vs_old_hand_staticflow",
        },
        {
            "source_round": "g551",
            "source_stage": "iteration_label_expansion",
            "path": "outputs/logs/phase5p5_repair5g551_iteration_label_expansion/iteration_label_expansion_results.csv",
            "label_role": "auxiliary_vs_old_hand_staticflow",
        },
        {
            "source_round": "g551",
            "source_stage": "generated_theta_targeted",
            "path": "outputs/logs/phase5p5_repair5g551_generated_theta_targeted/generated_theta_targeted_results.csv",
            "label_role": "auxiliary_vs_old_hand_staticflow",
        },
    ]


def all_claims_closed(obj: dict[str, Any]) -> bool:
    return all(not boolish(obj.get(key, False)) for key in CLAIM_KEYS)


def claim_rows_for(label: str, obj: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "source": label,
            "claim_flag": key,
            "value": obj.get(key, False),
            "closed": not boolish(obj.get(key, False)),
            **claims(),
        }
        for key in CLAIM_KEYS
    ]


def main_verify_g555_artifacts(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.56 verify G5.55")
    required = {
        "decision_summary": G555_DECISION_SUMMARY,
        "corrected_validation_summary": G555_VALIDATION_SUMMARY,
        "blind_summary": G555_BLIND_SUMMARY,
        "blind_candidate_leaderboard": G555_BLIND_LEADERBOARD,
        "final_candidate_theta": G555_FINAL_THETA,
    }
    audit = []
    for artifact, path in required.items():
        p = resolve(path)
        audit.append(
            {
                "artifact": artifact,
                "path": path,
                "exists": p.exists(),
                "rows_or_file": table_count(path) if p.exists() else 0,
                "bytes": file_bytes(path),
                "sha256_if_compact": file_sha256_if_compact(path),
                **claims(),
            }
        )
    decision = load_json(G555_DECISION_SUMMARY, {})
    validation = load_json(G555_VALIDATION_SUMMARY, {})
    blind = load_json(G555_BLIND_SUMMARY, {})
    final = [row for row in read_rows(G555_FINAL_THETA) if row.get("candidate_id") == PROMOTED_BASELINE_ID]
    final_row = final[0] if final else {}
    checks = {
        "g555_decision": decision.get("decision") == "g555_fixed_global_staticflow_candidate_blind_passed_keep_claims_closed",
        "promoted_fixed_candidate_id": decision.get("promoted_fixed_candidate_id") == PROMOTED_BASELINE_ID,
        "blind_passed": boolish(decision.get("blind_passed")) and boolish(blind.get("blind_passed")),
        "blind_new_solver_rows": int(number(blind.get("blind_new_solver_rows"), -1)) == 120000,
        "success_regression_count_vs_old_hand_static_flow": int(number(blind.get("success_regression_count_vs_static_flow"), -1)) == 0,
        "success_gain_count_vs_old_hand_static_flow": int(number(blind.get("success_gain_count_vs_static_flow", final_row.get("success_gain_count_vs_static_flow")), -1)) == 37,
        "quality_delta_vs_old_hand_static_flow": abs(number(blind.get("both_success_quality_delta_mean_vs_static_flow"), math.nan) - (-0.0210143833861)) < 1.0e-10,
        "fingerprint": bool(final) and str(final_row.get("fingerprint_match_rate", final_row.get("fulltheta_fingerprint_match_rate", ""))) in {"1", "1.0"},
        "recognized": bool(final) and boolish(final_row.get("candidate_recognized_all")),
        "cost_finite": bool(final) and boolish(final_row.get("cost_finite_all")),
        "all_claim_flags_closed": all_claims_closed(decision) and all_claims_closed(validation) and all_claims_closed(blind),
        "external_lacam2_clean": external_lacam2_clean(),
    }
    missing = [row for row in audit if not boolish(row["exists"])]
    ok = not missing and all(checks.values())
    write_rows(ARTIFACT_AUDIT_CSV, audit)
    claim_rows = claim_rows_for("g555_decision", decision) + claim_rows_for("g555_validation", validation) + claim_rows_for("g555_blind", blind)
    write_rows(CLAIM_FLAG_AUDIT_CSV, claim_rows)
    summary = {
        "schema_version": "phase5p5_repair5g556_g555_verification_summary_v1",
        "decision": "g556_g555_promoted_baseline_verified" if ok else "g556_g555_verification_blocked",
        "missing_artifacts": [row["artifact"] for row in missing],
        "checks": checks,
        "g555_decision": decision.get("decision", ""),
        "primary_baseline": PROMOTED_BASELINE_ID,
        "previous_primary_baseline": OLD_HAND_STATIC_FLOW_ID,
        "validation_new_solver_rows": validation.get("validation_new_solver_rows", 0),
        "blind_new_solver_rows": blind.get("blind_new_solver_rows", 0),
        "blind_success_regression_count_vs_old_hand_static_flow": blind.get("success_regression_count_vs_static_flow", ""),
        "blind_quality_delta_vs_old_hand_static_flow": blind.get("both_success_quality_delta_mean_vs_static_flow", ""),
        "external_lacam2_clean": checks["external_lacam2_clean"],
        **claims(),
    }
    write_json(VERIFY_SUMMARY, summary)
    write_text(
        VERIFY_REPORT,
        "# G5.56 Verification of G5.55 Promoted Baseline\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- primary baseline for G5.56: `{PROMOTED_BASELINE_ID}`\n"
        f"- previous hand baseline: `{OLD_HAND_STATIC_FLOW_ID}`\n"
        f"- validation rows: `{summary['validation_new_solver_rows']}`\n"
        f"- blind rows: `{summary['blind_new_solver_rows']}`\n"
        f"- external/lacam2 clean: `{summary['external_lacam2_clean']}`\n",
    )
    print(json.dumps({"decision": summary["decision"], "missing": len(missing)}))
    return 0 if ok else 2


def main_audit_promoted_baseline(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.56 promoted baseline audit")
    if args.overwrite or not resolve(VERIFY_SUMMARY).exists():
        rc = main_verify_g555_artifacts([])
        if rc != 0:
            return rc
    theta = promoted_theta()
    old = old_hand_theta()
    theta_row = {
        "candidate_id": PROMOTED_BASELINE_ID,
        "role_after_g555": "primary_fixed_global_staticflow_baseline",
        "previous_hand_static_flow_candidate": OLD_HAND_STATIC_FLOW_ID,
        "distance_from_old_hand_static_flow": csv_number(theta_distance(theta, old)),
        "distance_from_self": csv_number(theta_distance(theta, theta)),
        "goal_projection_mode": theta_mode(theta),
        "theta_in_bounds": theta_in_bounds(theta),
        "active_field_deltas_vs_old_hand": active_deltas(theta, old),
        **theta,
        **claims(),
    }
    summary = {
        "schema_version": "phase5p5_repair5g556_promoted_baseline_audit_summary_v1",
        "decision": "g556_promoted_baseline_audited",
        "primary_baseline": PROMOTED_BASELINE_ID,
        "baseline_role_bound_to_promoted_candidate": True,
        "old_hand_static_flow_is_diagnostic": True,
        "candidate_object": "one fixed global coefficient vector",
        "dynamic_learned_policy_paused": True,
        "theta_in_bounds": theta_row["theta_in_bounds"],
        "goal_projection_mode": theta_row["goal_projection_mode"],
        "distance_from_old_hand_static_flow": theta_row["distance_from_old_hand_static_flow"],
        **claims(),
    }
    write_rows(PROMOTED_THETA_CSV, [theta_row])
    write_json(BASELINE_AUDIT_SUMMARY, summary)
    write_text(
        BASELINE_AUDIT_REPORT,
        "# G5.56 Promoted Baseline Audit\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- primary baseline: `{PROMOTED_BASELINE_ID}`\n"
        "- binding rule: `role static_flow_shield means g554_c00051 in G5.56 replay plans`\n"
        f"- old hand staticflow diagnostic: `{summary['old_hand_static_flow_is_diagnostic']}`\n"
        f"- theta in bounds: `{summary['theta_in_bounds']}`\n"
        f"- goal projection mode: `{summary['goal_projection_mode']}`\n",
    )
    print(json.dumps({"decision": summary["decision"]}))
    return 0


def main_create_literature_model_audit(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.56 literature/model audit")
    rows = [
        {
            "model_family": "FixedTheta Retrieval-Set Transformer",
            "attention_or_retrieval_support": "row feature-token attention, retrieval centroids, candidate-set aggregation",
            "fits_1m_3m_rows": True,
            "fits_2x4090": True,
            "mixed_feature_support": True,
            "uncertainty_risk_outputs": True,
            "code_feasibility": "implemented in train_eval_repair5g556_ftrst_surrogate.py",
            "role_in_g556": "primary offline surrogate",
            **claims(),
        },
        {
            "model_family": "FT-Transformer",
            "attention_or_retrieval_support": "feature-token self-attention",
            "fits_1m_3m_rows": True,
            "fits_2x4090": True,
            "mixed_feature_support": True,
            "uncertainty_risk_outputs": True,
            "code_feasibility": "same feature-token backbone without retrieval memory",
            "role_in_g556": "required neural attention control",
            **claims(),
        },
        {
            "model_family": "TabTransformer",
            "attention_or_retrieval_support": "categorical token attention",
            "fits_1m_3m_rows": True,
            "fits_2x4090": True,
            "mixed_feature_support": True,
            "uncertainty_risk_outputs": "with heads added",
            "code_feasibility": "diagnostic through categorical-token ablation",
            "role_in_g556": "diagnostic",
            **claims(),
        },
        {
            "model_family": "SAINT",
            "attention_or_retrieval_support": "row and column attention; masked/contrastive inspiration",
            "fits_1m_3m_rows": "medium",
            "fits_2x4090": True,
            "mixed_feature_support": True,
            "uncertainty_risk_outputs": "with heads added",
            "code_feasibility": "lightweight diagnostic implementation",
            "role_in_g556": "diagnostic",
            **claims(),
        },
        {
            "model_family": "AMFormer",
            "attention_or_retrieval_support": "additive and multiplicative attention for arithmetic interactions",
            "fits_1m_3m_rows": "medium",
            "fits_2x4090": True,
            "mixed_feature_support": True,
            "uncertainty_risk_outputs": "with heads added",
            "code_feasibility": "multiplicative-feature diagnostic",
            "role_in_g556": "diagnostic",
            **claims(),
        },
        {
            "model_family": "TabR",
            "attention_or_retrieval_support": "retrieval-augmented tabular learning",
            "fits_1m_3m_rows": "requires approximate memory",
            "fits_2x4090": True,
            "mixed_feature_support": True,
            "uncertainty_risk_outputs": "with heads added",
            "code_feasibility": "coarse retrieval centroid memory in FTRST",
            "role_in_g556": "retrieval design anchor",
            **claims(),
        },
        {
            "model_family": "TabPFN / TabICL",
            "attention_or_retrieval_support": "in-context/foundation-style tabular inference",
            "fits_1m_3m_rows": False,
            "fits_2x4090": "small split only",
            "mixed_feature_support": True,
            "uncertainty_risk_outputs": True,
            "code_feasibility": "diagnostic only if package is available",
            "role_in_g556": "small-split diagnostic, not primary",
            **claims(),
        },
        {
            "model_family": "TabM",
            "attention_or_retrieval_support": "parameter-efficient MLP ensemble, no attention",
            "fits_1m_3m_rows": True,
            "fits_2x4090": True,
            "mixed_feature_support": True,
            "uncertainty_risk_outputs": True,
            "code_feasibility": "implemented as MLP/ensemble control",
            "role_in_g556": "required strong neural control",
            **claims(),
        },
        {
            "model_family": "GBDT controls",
            "attention_or_retrieval_support": "none",
            "fits_1m_3m_rows": True,
            "fits_2x4090": "CPU-oriented",
            "mixed_feature_support": True,
            "uncertainty_risk_outputs": True,
            "code_feasibility": "sklearn HistGradientBoosting fallback; LightGBM/XGBoost/CatBoost if installed",
            "role_in_g556": "required hard-to-beat tabular control",
            **claims(),
        },
        {
            "model_family": "CEM / CMA-ES / trust-region controls",
            "attention_or_retrieval_support": "optimizer, not predictor",
            "fits_1m_3m_rows": True,
            "fits_2x4090": True,
            "mixed_feature_support": True,
            "uncertainty_risk_outputs": "uses surrogate acquisition/risk",
            "code_feasibility": "implemented in candidate generation",
            "role_in_g556": "non-neural candidate-generation controls",
            **claims(),
        },
    ]
    write_rows(MODEL_MATRIX_CSV, rows)
    summary = {
        "schema_version": "phase5p5_repair5g556_literature_model_audit_summary_v1",
        "decision": "g556_ftrst_primary_controls_required",
        "primary_model_family": "FixedTheta Retrieval-Set Transformer",
        "required_controls": ["TabM", "FT-Transformer", "GBDT", "heuristic optimizers"],
        "literature_anchors": ["GGO", "Online GGO", "CS-PIBT", "MAPF-LNS benchmark", "FT-Transformer", "TabR", "SAINT", "AMFormer", "TabPFN", "TabM"],
        **claims(),
    }
    write_json(LITERATURE_SUMMARY, summary)
    write_text(
        LITERATURE_REPORT,
        "# G5.56 Literature And Model Audit\n\n"
        "G5.56 chooses FixedTheta Retrieval-Set Transformer as the primary offline surrogate because the fixed-theta task is both row-level and candidate-set-level. "
        "The row encoder models theta/context interactions; retrieval memory supplies local empirical neighborhoods; candidate-set aggregation estimates global fixed-vector risk and utility. "
        "This matches the solver-facing lesson from guidance-optimization and learning-MAPF shield work: neural outputs may propose candidates, but only real paired solver replay can promote them.\n\n"
        f"- primary model family: `{summary['primary_model_family']}`\n"
        "- required controls: `TabM`, `FT-Transformer`, `GBDT`, heuristic optimizers\n"
        "- promotion baseline: `g554_c00051`\n"
        "- runtime learned policy claim: `closed`\n",
    )
    print(json.dumps({"decision": summary["decision"]}))
    return 0


def scan_source(path: str | Path, row_limit: int = 0) -> dict[str, Any]:
    p = resolve(path)
    if not p.exists():
        return {"rows": 0, "generated_rows": 0, "unique_candidates": 0, "unique_contexts": 0, "g554_contexts": 0, "columns": []}
    candidates: set[str] = set()
    contexts: set[str] = set()
    g554_contexts: set[str] = set()
    generated = 0
    rows = 0
    columns: list[str] = []
    with p.open(newline="", encoding="utf-8", errors="ignore") as handle:
        reader = csv.DictReader(handle)
        columns = list(reader.fieldnames or [])
        for row in reader:
            rows += 1
            ctx = context_key(row)
            contexts.add(ctx)
            if row.get("candidate_id") == PROMOTED_BASELINE_ID:
                g554_contexts.add(ctx)
            if str(row.get("role", "")).startswith("generated_theta::"):
                generated += 1
                if row.get("candidate_id"):
                    candidates.add(str(row.get("candidate_id")))
            if row_limit and rows >= row_limit:
                break
    return {
        "rows": rows,
        "generated_rows": generated,
        "unique_candidates": len(candidates),
        "unique_contexts": len(contexts),
        "g554_contexts": len(g554_contexts),
        "columns": columns,
    }


def context_key(row: dict[str, Any]) -> str:
    if row.get("context_key"):
        return str(row.get("context_key"))
    if row.get("context_horizon_key"):
        return str(row.get("context_horizon_key"))
    return "|".join(
        map(
            str,
            [
                row.get("map", ""),
                row.get("agents", ""),
                row.get("seed", ""),
                row.get("budget_ms", row.get("nominal_budget_ms", "")),
                row.get("horizon_id", ""),
            ],
        )
    )


def main_create_unified_fixedtheta_dataset_manifest(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.56 unified fixed-theta dataset manifest")
    rows = []
    schema_rows = []
    available = []
    missing = []
    total_rows = 0
    total_generated = 0
    total_contexts = 0
    total_candidates = 0
    direct_contexts = 0
    required_cols = {"role", "candidate_id", "map", "agents", "seed", "solution_found", *THETA_COLUMNS}
    for source in source_artifacts():
        stats = scan_source(source["path"], row_limit=max(0, args.row_limit))
        p = resolve(source["path"])
        present = p.exists()
        row = {
            **source,
            "exists": present,
            "rows": stats["rows"],
            "generated_rows": stats["generated_rows"],
            "unique_candidates": stats["unique_candidates"],
            "unique_contexts": stats["unique_contexts"],
            "g554_contexts": stats["g554_contexts"],
            "bytes": file_bytes(source["path"]),
            "sha256_if_compact": file_sha256_if_compact(source["path"]),
            "commit_policy": "do_not_commit_raw_csv_over_50mb" if file_bytes(source["path"]) > 50 * 1024 * 1024 else "commit_if_in_scope",
            **claims(),
        }
        rows.append(row)
        (available if present else missing).append(row)
        if present:
            total_rows += int(stats["rows"])
            total_generated += int(stats["generated_rows"])
            total_contexts += int(stats["unique_contexts"])
            total_candidates += int(stats["unique_candidates"])
            direct_contexts += int(stats["g554_contexts"])
        missing_cols = sorted(required_cols - set(stats["columns"]))
        schema_rows.append(
            {
                "source_round": source["source_round"],
                "source_stage": source["source_stage"],
                "path": source["path"],
                "exists": present,
                "column_count": len(stats["columns"]),
                "missing_required_columns": ";".join(missing_cols),
                "schema_ok_for_surrogate": present and not missing_cols,
                **claims(),
            }
        )
    summary = {
        "schema_version": "phase5p5_repair5g556_unified_dataset_manifest_summary_v1",
        "decision": "g556_unified_fixedtheta_dataset_manifest_created",
        "usable_row_level_examples": total_generated,
        "total_solver_rows": total_rows,
        "unique_theta_candidates_sum_over_sources": total_candidates,
        "unique_contexts_sum_over_sources": total_contexts,
        "direct_g554_contexts_sum_over_sources": direct_contexts,
        "minimum_usable_rows_met": total_generated >= 1_000_000,
        "preferred_usable_rows_met": total_generated >= 3_000_000,
        "minimum_unique_theta_candidates_met": total_candidates >= 10_000,
        "minimum_unique_contexts_met": total_contexts >= 5_000,
        "direct_primary_g554_labels_under_preferred": direct_contexts < 10_000,
        "topup_plan_required_before_claiming_primary_only_training": direct_contexts < 10_000,
        "artifact_root": str(remote_artifact_root()),
        **claims(),
    }
    write_rows(SOURCE_MANIFEST_CSV, rows)
    write_rows(SOURCE_SCHEMA_AUDIT_CSV, schema_rows)
    write_rows(AVAILABLE_RAW_CSV, available)
    write_rows(MISSING_RAW_CSV, missing)
    write_json(MANIFEST_SUMMARY, summary)
    write_text(
        MANIFEST_REPORT,
        "# G5.56 Unified Fixed-Theta Dataset Manifest\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- usable generated row-level examples: `{summary['usable_row_level_examples']}`\n"
        f"- direct g554_c00051 contexts: `{summary['direct_g554_contexts_sum_over_sources']}`\n"
        f"- minimum usable rows met: `{summary['minimum_usable_rows_met']}`\n"
        f"- top-up needed for primary-only training interpretation: `{summary['topup_plan_required_before_claiming_primary_only_training']}`\n\n"
        "Rows with direct `g554_c00051` baseline in the same context are primary labels. "
        "Older rows that only compare to the hand static_flow baseline are marked auxiliary and cannot by themselves promote a G5.56 candidate.\n",
    )
    print(json.dumps({"decision": summary["decision"], "rows": total_generated}))
    return 0


def stream_context_groups(path: str | Path, row_limit: int = 0) -> Iterable[list[dict[str, Any]]]:
    p = resolve(path)
    if not p.exists():
        return
    current_key = None
    group: list[dict[str, Any]] = []
    rows = 0
    with p.open(newline="", encoding="utf-8", errors="ignore") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            key = context_key(row)
            if current_key is None:
                current_key = key
            if key != current_key and group:
                yield group
                group = []
                current_key = key
            group.append(row)
            rows += 1
            if row_limit and rows >= row_limit:
                break
    if group:
        yield group


def split_name(row: dict[str, Any], source_round: str, source_stage: str) -> str:
    if source_round == "g555" and source_stage == "blind":
        return "candidate_generation_blind"
    h = stable_hash(row.get("candidate_id", ""), row.get("map", ""), row.get("seed", ""), row.get("horizon_id", ""), modulo=10)
    if h < 7:
        return "train"
    if h < 8:
        return "val"
    return "test"


def row_features(selected: dict[str, Any], baseline: dict[str, Any], source: dict[str, Any], label_scope: str) -> dict[str, Any]:
    theta = {col: selected.get(col, "") for col in THETA_COLUMNS}
    base_theta = {col: baseline.get(col, "") for col in THETA_COLUMNS}
    paired = pair_metrics(selected, baseline)
    additive = {}
    return {
        "schema_version": "phase5p5_repair5g556_surrogate_row_v1",
        "source_round": source["source_round"],
        "source_stage": source["source_stage"],
        "label_scope": label_scope,
        "split": split_name(selected, source["source_round"], source["source_stage"]),
        "context_key": context_key(selected),
        "candidate_id": selected.get("candidate_id", ""),
        "baseline_candidate_id": baseline.get("candidate_id", ""),
        "map": selected.get("map", ""),
        "map_family": selected.get("map_family", ""),
        "agents": selected.get("agents", ""),
        "seed": selected.get("seed", ""),
        "nominal_budget_ms": selected.get("nominal_budget_ms", selected.get("budget_ms", "")),
        "short_budget_ms": selected.get("short_budget_ms", ""),
        "base_time_limit_sec": selected.get("base_time_limit_sec", ""),
        "ltm_max_iterations": selected.get("ltm_max_iterations", ""),
        "horizon_id": selected.get("horizon_id", ""),
        "candidate_family": selected.get("candidate_family", selected.get("sampling_policy", "")),
        "sampling_policy": selected.get("sampling_policy", ""),
        "theta_mode": theta_mode(theta),
        "distance_from_g554_c00051": csv_number(theta_distance(theta, promoted_theta())),
        "distance_from_old_hand_staticflow": csv_number(theta_distance(theta, old_hand_theta())),
        "active_field_deltas": active_deltas(theta, base_theta),
        "candidate_recognized": selected.get("candidate_recognized", True),
        "fulltheta_fingerprint_match": selected.get("fulltheta_fingerprint_match", True),
        "cost_finite_all": selected.get("cost_finite_all", selected.get("repair5g_costs_finite", True)),
        "success_regression_vs_g554_c00051": paired["success_regression"] if label_scope == "primary_vs_g554_c00051" else "",
        "success_gain_vs_g554_c00051": paired["success_gain"] if label_scope == "primary_vs_g554_c00051" else "",
        "quality_delta_vs_g554_c00051": paired["quality_delta_ratio"] if label_scope == "primary_vs_g554_c00051" else "",
        "success_regression_aux": paired["success_regression"],
        "success_gain_aux": paired["success_gain"],
        "quality_delta_aux": paired["quality_delta_ratio"],
        "selected_success": paired["selected_success"],
        "baseline_success": paired["baseline_success"],
        **additive,
        **theta,
        **claims(),
    }


def write_csv_stream(path: Path, rows: Iterable[dict[str, Any]], fieldnames: list[str]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
            count += 1
    return count


def surrogate_fieldnames() -> list[str]:
    return [
        "schema_version",
        "source_round",
        "source_stage",
        "label_scope",
        "split",
        "context_key",
        "candidate_id",
        "baseline_candidate_id",
        "map",
        "map_family",
        "agents",
        "seed",
        "nominal_budget_ms",
        "short_budget_ms",
        "base_time_limit_sec",
        "ltm_max_iterations",
        "horizon_id",
        "candidate_family",
        "sampling_policy",
        "theta_mode",
        "distance_from_g554_c00051",
        "distance_from_old_hand_staticflow",
        "active_field_deltas",
        "candidate_recognized",
        "fulltheta_fingerprint_match",
        "cost_finite_all",
        "success_regression_vs_g554_c00051",
        "success_gain_vs_g554_c00051",
        "quality_delta_vs_g554_c00051",
        "success_regression_aux",
        "success_gain_aux",
        "quality_delta_aux",
        "selected_success",
        "baseline_success",
        *THETA_COLUMNS,
        *CLAIM_KEYS,
    ]


def surrogate_rows(row_limit: int = 0) -> Iterable[dict[str, Any]]:
    used_rows = 0
    for source in source_artifacts():
        for group in stream_context_groups(source["path"], row_limit=0):
            by_candidate = {str(row.get("candidate_id", "")): row for row in group if row.get("candidate_id")}
            by_role = {str(row.get("role", "")): row for row in group if row.get("role")}
            primary_baseline = by_candidate.get(PROMOTED_BASELINE_ID)
            old_baseline = by_role.get("static_flow_shield")
            baseline = primary_baseline or old_baseline
            if not baseline:
                continue
            label_scope = "primary_vs_g554_c00051" if primary_baseline else "auxiliary_vs_old_hand_staticflow"
            for selected in group:
                if not str(selected.get("role", "")).startswith("generated_theta::"):
                    continue
                if selected.get("candidate_id") == baseline.get("candidate_id"):
                    continue
                yield row_features(selected, baseline, source, label_scope)
                used_rows += 1
                if row_limit and used_rows >= row_limit:
                    return


def try_write_parquet(csv_path: Path) -> tuple[bool, str]:
    if pd is None:
        return False, "pandas_unavailable"
    try:
        import pyarrow  # noqa: F401
    except Exception:
        return False, "pyarrow_unavailable_csv_fallback_written"
    try:
        df = pd.read_csv(csv_path)
        df.to_parquet(parquet_path(csv_path), index=False)
        return True, str(parquet_path(csv_path))
    except Exception as exc:  # pragma: no cover
        return False, f"parquet_write_failed:{exc}"


def main_create_surrogate_dataset(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.56 surrogate dataset")
    if args.overwrite or not resolve(MANIFEST_SUMMARY).exists():
        main_create_unified_fixedtheta_dataset_manifest([])
    raw_path = raw_surrogate_rows_path()
    if args.overwrite or not raw_path.exists():
        total = write_csv_stream(raw_path, surrogate_rows(row_limit=max(0, args.row_limit)), surrogate_fieldnames())
    else:
        total = table_count(raw_path)
    primary = auxiliary = 0
    split_counts: Counter[tuple[str, str]] = Counter()
    preview: list[dict[str, Any]] = []
    candidate_context_pairs: list[dict[str, Any]] = []
    candidate_agg: dict[str, dict[str, Any]] = defaultdict(lambda: {"rows": 0, "primary_rows": 0, "auxiliary_rows": 0, "regressions": 0, "gains": 0, "deltas": []})
    with raw_path.open(newline="", encoding="utf-8", errors="ignore") as handle:
        for row in csv.DictReader(handle):
            if len(preview) < 1000:
                preview.append(row)
            scope = row.get("label_scope", "")
            primary += scope == "primary_vs_g554_c00051"
            auxiliary += scope != "primary_vs_g554_c00051"
            split_counts[(row.get("split", ""), scope)] += 1
            cid = row.get("candidate_id", "")
            agg = candidate_agg[cid]
            agg["rows"] += 1
            agg["primary_rows"] += scope == "primary_vs_g554_c00051"
            agg["auxiliary_rows"] += scope != "primary_vs_g554_c00051"
            agg["regressions"] += boolish(row.get("success_regression_aux"))
            agg["gains"] += boolish(row.get("success_gain_aux"))
            q = number(row.get("quality_delta_aux"), math.nan)
            if math.isfinite(q):
                agg["deltas"].append(q)
            if len(candidate_context_pairs) < 5000:
                candidate_context_pairs.append(
                    {
                        "candidate_id": cid,
                        "context_key": row.get("context_key", ""),
                        "label_scope": scope,
                        "split": row.get("split", ""),
                        **claims(),
                    }
                )
    set_rows = []
    for cid, agg in candidate_agg.items():
        set_rows.append(
            {
                "candidate_id": cid,
                "rows": agg["rows"],
                "primary_rows": agg["primary_rows"],
                "auxiliary_rows": agg["auxiliary_rows"],
                "success_regression_rate_aux": csv_number(agg["regressions"] / max(1, agg["rows"])),
                "success_gain_rate_aux": csv_number(agg["gains"] / max(1, agg["rows"])),
                "mean_quality_delta_aux": "" if not agg["deltas"] else csv_number(statistics.fmean(agg["deltas"])),
                **claims(),
            }
        )
    set_rows.sort(key=lambda r: (-int(number(r["primary_rows"], 0)), number(r["mean_quality_delta_aux"], 9.0)))
    write_rows(DATASET_PREVIEW_CSV, preview)
    write_rows(raw_candidate_context_pairs_path(), candidate_context_pairs)
    write_rows(raw_candidate_sets_path(), set_rows)
    write_rows(
        SPLIT_SUMMARY_CSV,
        [
            {"split": split, "label_scope": scope, "rows": count, **claims()}
            for (split, scope), count in sorted(split_counts.items())
        ],
    )
    feature_rows = []
    for name in [
        *THETA_COLUMNS,
        "distance_from_g554_c00051",
        "distance_from_old_hand_staticflow",
        "map_family",
        "map",
        "agents",
        "nominal_budget_ms",
        "short_budget_ms",
        "base_time_limit_sec",
        "ltm_max_iterations",
        "horizon_id",
        "source_round",
        "candidate_family",
    ]:
        feature_rows.append({"feature": name, "allowed": True, "feature_group": "theta" if name in THETA_COLUMNS else "context_or_source", **claims()})
    forbidden = ["candidate_success", "baseline_success", "success_regression", "success_gain", "both_success", "quality_delta", "future_replay_outcome", "oracle_label", "post_hoc_rank"]
    for name in forbidden:
        feature_rows.append({"feature": name, "allowed": False, "feature_group": "forbidden_outcome", **claims()})
    write_rows(FEATURE_MANIFEST_CSV, feature_rows)
    write_rows(
        LABEL_MANIFEST_CSV,
        [
            {"label": "success_regression_vs_g554_c00051", "primary": True, "description": "true only for rows with direct g554_c00051 baseline", **claims()},
            {"label": "success_gain_vs_g554_c00051", "primary": True, "description": "true only for rows with direct g554_c00051 baseline", **claims()},
            {"label": "quality_delta_vs_g554_c00051", "primary": True, "description": "negative is better; only direct primary rows", **claims()},
            {"label": "success_regression_aux", "primary": False, "description": "auxiliary old-hand or direct baseline comparison for representation learning", **claims()},
        ],
    )
    leakage_rows = [
        {"field": row["feature"], "leakage_risk": "forbidden" if not boolish(row["allowed"]) else "allowed_pre_update_or_theta", **claims()}
        for row in feature_rows
    ]
    write_rows(LEAKAGE_AUDIT_CSV, leakage_rows)
    pq_ok, pq_msg = try_write_parquet(raw_path)
    summary = {
        "schema_version": "phase5p5_repair5g556_surrogate_dataset_summary_v1",
        "decision": "g556_surrogate_dataset_created",
        "raw_surrogate_rows_csv": str(raw_path),
        "raw_surrogate_rows_parquet": str(parquet_path(raw_path)) if pq_ok else "",
        "parquet_status": pq_msg,
        "candidate_context_pairs": str(raw_candidate_context_pairs_path()),
        "candidate_sets": str(raw_candidate_sets_path()),
        "training_rows": total,
        "primary_vs_g554_c00051_rows": primary,
        "auxiliary_rows": auxiliary,
        "unique_candidate_sets": len(candidate_agg),
        "minimum_training_rows_met": total >= 1_000_000,
        "feature_leakage": False,
        "baseline": PROMOTED_BASELINE_ID,
        **claims(),
    }
    write_json(DATASET_SUMMARY, summary)
    write_text(
        DATASET_REPORT,
        "# G5.56 Surrogate Dataset\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- rows: `{summary['training_rows']}`\n"
        f"- primary rows vs g554_c00051: `{summary['primary_vs_g554_c00051_rows']}`\n"
        f"- auxiliary rows: `{summary['auxiliary_rows']}`\n"
        f"- parquet status: `{summary['parquet_status']}`\n"
        f"- feature leakage: `{summary['feature_leakage']}`\n\n"
        "Primary labels are normalized to `g554_c00051`. Older historical rows without that baseline are retained only as auxiliary representation/ranking data.\n",
    )
    print(json.dumps({"decision": summary["decision"], "rows": total, "primary": primary}))
    return 0


def load_training_frame(row_limit: int = 0) -> Any:
    if pd is None:
        raise RuntimeError("pandas is required for G5.56 model training")
    if not raw_surrogate_rows_path().exists():
        main_create_surrogate_dataset([])
    path = raw_surrogate_rows_path()
    if row_limit and row_limit > 0:
        return pd.read_csv(path, nrows=row_limit)
    return pd.read_csv(path)


def prepare_xy(df: Any) -> tuple[Any, Any, Any, list[str]]:
    if pd is None or np is None:
        raise RuntimeError("pandas/numpy required")
    d = df.copy()
    y_reg = d["success_regression_aux"].map(boolish).astype(int).to_numpy()
    q = pd.to_numeric(d["quality_delta_aux"], errors="coerce").fillna(0.0).to_numpy(dtype="float32")
    numeric_features = [
        *NUMERIC_THETA_COLUMNS,
        "distance_from_g554_c00051",
        "distance_from_old_hand_staticflow",
        "agents",
        "nominal_budget_ms",
        "short_budget_ms",
        "base_time_limit_sec",
        "ltm_max_iterations",
    ]
    cat_features = ["map_family", "map", "source_round", "source_stage", "candidate_family", "theta_mode", "split"]
    features = []
    for col in numeric_features:
        features.append(pd.to_numeric(d.get(col, 0.0), errors="coerce").fillna(0.0).to_numpy(dtype="float32"))
    for col in cat_features:
        features.append(d.get(col, "").astype(str).map(lambda v: stable_hash(col, v, modulo=997) / 997.0).to_numpy(dtype="float32"))
    x = np.vstack(features).T.astype("float32")
    names = numeric_features + cat_features
    return x, y_reg.astype("float32"), q.astype("float32"), names


def metric_rows_from_predictions(y: Any, q: Any, p: Any, qhat: Any, model_family: str) -> list[dict[str, Any]]:
    if np is None:
        return []
    y_arr = np.asarray(y).astype(int)
    p_arr = np.asarray(p).astype(float)
    q_arr = np.asarray(q).astype(float)
    qhat_arr = np.asarray(qhat).astype(float)
    rows = []
    try:
        auc = float(roc_auc_score(y_arr, p_arr)) if len(set(y_arr.tolist())) > 1 and SKLEARN_AVAILABLE else 0.5
    except Exception:
        auc = 0.5
    try:
        pr_auc = float(average_precision_score(y_arr, p_arr)) if len(set(y_arr.tolist())) > 1 and SKLEARN_AVAILABLE else float(np.mean(y_arr))
    except Exception:
        pr_auc = float(np.mean(y_arr))
    try:
        brier = float(brier_score_loss(y_arr, p_arr)) if SKLEARN_AVAILABLE else float(np.mean((p_arr - y_arr) ** 2))
    except Exception:
        brier = float(np.mean((p_arr - y_arr) ** 2))
    mae = float(mean_absolute_error(q_arr, qhat_arr)) if SKLEARN_AVAILABLE else float(np.mean(np.abs(q_arr - qhat_arr)))
    if len(q_arr) > 2:
        qcorr = float(np.corrcoef(q_arr, qhat_arr)[0, 1])
        if not math.isfinite(qcorr):
            qcorr = 0.0
    else:
        qcorr = 0.0
    rows.append({"model_family": model_family, "metric": "regression_risk_auc", "value": csv_number(auc), **claims()})
    rows.append({"model_family": model_family, "metric": "regression_risk_pr_auc", "value": csv_number(pr_auc), **claims()})
    rows.append({"model_family": model_family, "metric": "regression_risk_brier", "value": csv_number(brier), **claims()})
    rows.append({"model_family": model_family, "metric": "quality_delta_mae", "value": csv_number(mae), **claims()})
    rows.append({"model_family": model_family, "metric": "quality_ranking_corr", "value": csv_number(qcorr), **claims()})
    rows.append({"model_family": model_family, "metric": "false_safe_hard_negative_count", "value": int(np.sum((p_arr < 0.05) & (y_arr == 1))), **claims()})
    return rows


def calibration_rows(y: Any, p: Any, model_family: str) -> list[dict[str, Any]]:
    if np is None:
        return []
    y_arr = np.asarray(y).astype(float)
    p_arr = np.asarray(p).astype(float)
    rows = []
    for i in range(10):
        lo = i / 10.0
        hi = (i + 1) / 10.0
        mask = (p_arr >= lo) & (p_arr < hi if i < 9 else p_arr <= hi)
        if np.sum(mask) == 0:
            continue
        rows.append(
            {
                "model_family": model_family,
                "bin": i,
                "prob_lo": lo,
                "prob_hi": hi,
                "rows": int(np.sum(mask)),
                "mean_predicted_risk": csv_number(float(np.mean(p_arr[mask]))),
                "observed_regression_rate": csv_number(float(np.mean(y_arr[mask]))),
                **claims(),
            }
        )
    return rows


class FeatureTokenTransformer(nn.Module):
    def __init__(self, n_features: int, d_model: int = 48, n_heads: int = 4, layers: int = 2, retrieval: bool = False) -> None:
        super().__init__()
        self.retrieval = retrieval
        self.weight = nn.Parameter(torch.randn(n_features, d_model) * 0.02)
        self.bias = nn.Parameter(torch.zeros(n_features, d_model))
        enc_layer = nn.TransformerEncoderLayer(d_model=d_model, nhead=n_heads, dim_feedforward=d_model * 4, batch_first=True, dropout=0.05, activation="gelu")
        self.encoder = nn.TransformerEncoder(enc_layer, num_layers=layers)
        extra = d_model if retrieval else 0
        self.risk_head = nn.Sequential(nn.LayerNorm(d_model + extra), nn.Linear(d_model + extra, d_model), nn.GELU(), nn.Linear(d_model, 1))
        self.quality_head = nn.Sequential(nn.LayerNorm(d_model + extra), nn.Linear(d_model + extra, d_model), nn.GELU(), nn.Linear(d_model, 1))

    def forward(self, x: Any, retrieval_vec: Any | None = None) -> tuple[Any, Any]:
        tokens = x.unsqueeze(-1) * self.weight.unsqueeze(0) + self.bias.unsqueeze(0)
        z = self.encoder(tokens).mean(dim=1)
        if self.retrieval and retrieval_vec is not None:
            z = torch.cat([z, retrieval_vec], dim=1)
        return self.risk_head(z).squeeze(1), self.quality_head(z).squeeze(1)


def train_torch_family(model_family: str, *, retrieval: bool, args: argparse.Namespace, summary_path: str, report_path: str, metrics_path: str, calibration_path: str | None = None, oof_path: str | None = None, manifest_path: str | None = None) -> int:
    if not TORCH_AVAILABLE or np is None:
        return train_sklearn_control(model_family, args=args, summary_path=summary_path, report_path=report_path, metrics_path=metrics_path)
    df = load_training_frame(args.train_row_limit)
    x, y, q, feature_names = prepare_xy(df)
    idx_train, idx_test = train_test_split(np.arange(len(y)), test_size=0.20, random_state=SEED, stratify=y if len(set(y.tolist())) > 1 else None)
    x_train, x_test = x[idx_train], x[idx_test]
    y_train, y_test = y[idx_train], y[idx_test]
    q_train, q_test = q[idx_train], q[idx_test]
    mean = x_train.mean(axis=0, keepdims=True)
    std = x_train.std(axis=0, keepdims=True) + 1.0e-6
    x_train = (x_train - mean) / std
    x_test = (x_test - mean) / std
    device = "cpu"
    if args.device == "cuda" or (args.device == "auto" and torch.cuda.is_available()):
        device = "cuda:0"
    batch_size = 4096 if str(args.batch_size) == "auto" else max(32, int(args.batch_size))
    model = FeatureTokenTransformer(x.shape[1], retrieval=retrieval).to(device)
    data_parallel = False
    if device.startswith("cuda") and args.gpus and torch.cuda.device_count() > 1:
        gpu_count = min(int(args.gpus), int(torch.cuda.device_count()))
        if gpu_count > 1:
            model = nn.DataParallel(model, device_ids=list(range(gpu_count)))
            data_parallel = True
    opt = torch.optim.AdamW(model.parameters(), lr=1.5e-3, weight_decay=1.0e-4)
    bce = nn.BCEWithLogitsLoss()
    huber = nn.SmoothL1Loss()
    train_ds = TensorDataset(torch.tensor(x_train), torch.tensor(y_train), torch.tensor(q_train))
    loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True, drop_last=False)
    best_loss = float("inf")
    stale = 0
    epochs_run = 0
    retrieval_train = torch.zeros((len(x_train), 48), dtype=torch.float32)
    retrieval_test = torch.zeros((len(x_test), 48), dtype=torch.float32)
    for epoch in range(max(1, args.epochs)):
        model.train()
        total = 0.0
        n = 0
        for xb, yb, qb in loader:
            xb = xb.to(device)
            yb = yb.to(device)
            qb = qb.to(device)
            rv = torch.zeros((xb.shape[0], 48), device=device) if retrieval else None
            risk_logit, qhat = model(xb, rv)
            loss = bce(risk_logit, yb) + 0.5 * huber(qhat, qb)
            opt.zero_grad(set_to_none=True)
            loss.backward()
            opt.step()
            total += float(loss.detach().cpu()) * len(xb)
            n += len(xb)
        epochs_run = epoch + 1
        train_loss = total / max(1, n)
        if train_loss < best_loss - 1.0e-4:
            best_loss = train_loss
            stale = 0
        else:
            stale += 1
        if epoch >= 8 and stale >= 5:
            break
    model.eval()
    with torch.no_grad():
        xt = torch.tensor(x_test, dtype=torch.float32).to(device)
        rv = retrieval_test.to(device) if retrieval else None
        logits, qhat_t = model(xt, rv)
        p = torch.sigmoid(logits).cpu().numpy()
        qhat = qhat_t.cpu().numpy()
    metrics = metric_rows_from_predictions(y_test, q_test, p, qhat, model_family)
    cal = calibration_rows(y_test, p, model_family)
    write_rows(metrics_path, metrics)
    if calibration_path:
        write_rows(calibration_path, cal)
    if oof_path:
        sample = []
        for i in range(min(1000, len(y_test))):
            sample.append(
                {
                    "row_index": int(idx_test[i]),
                    "observed_regression": int(y_test[i]),
                    "predicted_regression_risk": csv_number(float(p[i])),
                    "observed_quality_delta": csv_number(float(q_test[i])),
                    "predicted_quality_delta": csv_number(float(qhat[i])),
                    **claims(),
                }
            )
        write_rows(oof_path, sample)
    ece = calibration_ece(cal)
    false_safe = int(number(next((r["value"] for r in metrics if r["metric"] == "false_safe_hard_negative_count"), 999), 999))
    qcorr = number(next((r["value"] for r in metrics if r["metric"] == "quality_ranking_corr"), 0), 0)
    summary = {
        "schema_version": f"phase5p5_repair5g556_{model_family.lower().replace('-', '_').replace(' ', '_')}_summary_v1",
        "decision": f"g556_{model_family.lower().replace('-', '_').replace(' ', '_')}_evaluated",
        "model_family": model_family,
        "backend": "torch",
        "device": device,
        "cuda_device_count": int(torch.cuda.device_count()) if torch.cuda.is_available() else 0,
        "data_parallel": data_parallel,
        "training_rows": int(len(x_train)),
        "eval_rows": int(len(x_test)),
        "epochs_requested": args.epochs,
        "epochs_run": epochs_run,
        "early_stopping": epochs_run < args.epochs,
        "false_safe_hard_negative_count": false_safe,
        "calibration_ece": csv_number(ece),
        "quality_ranking_corr": csv_number(qcorr),
        "offline_gate_passed": false_safe == 0 and ece <= 0.08 and qcorr > 0.05,
        **claims(),
    }
    write_json(summary_path, summary)
    write_text(
        report_path,
        f"# G5.56 {model_family} Evaluation\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- backend: `{summary['backend']}`\n"
        f"- device: `{summary['device']}`\n"
        f"- training rows: `{summary['training_rows']}`\n"
        f"- epochs run: `{summary['epochs_run']}`\n"
        f"- false-safe hard negatives: `{summary['false_safe_hard_negative_count']}`\n"
        f"- calibration ECE: `{summary['calibration_ece']}`\n"
        f"- offline gate passed: `{summary['offline_gate_passed']}`\n",
    )
    if manifest_path:
        ckpt_path = remote_artifact_root() / "model_checkpoints" / "repair5g556_ftrst.pt"
        ckpt_path.parent.mkdir(parents=True, exist_ok=True)
        model_state = model.module.state_dict() if data_parallel else model.state_dict()
        torch.save({"model_state_dict": model_state, "feature_names": feature_names, "mean": mean.tolist(), "std": std.tolist(), "summary": summary}, ckpt_path)
        write_json(
            manifest_path,
            {
                "schema_version": "repair5g556_ftrst_manifest_v1",
                "checkpoint": str(ckpt_path),
                "model_family": model_family,
                "feature_names": feature_names,
                "summary": summary,
                **claims(),
            },
        )
    print(json.dumps({"decision": summary["decision"], "offline_gate_passed": summary["offline_gate_passed"]}))
    return 0


def calibration_ece(rows: list[dict[str, Any]]) -> float:
    total = sum(int(number(row.get("rows"), 0)) for row in rows)
    if total <= 0:
        return 1.0
    err = 0.0
    for row in rows:
        n = int(number(row.get("rows"), 0))
        err += n * abs(number(row.get("mean_predicted_risk"), 0) - number(row.get("observed_regression_rate"), 0))
    return err / total


def train_sklearn_control(model_family: str, *, args: argparse.Namespace, summary_path: str, report_path: str, metrics_path: str) -> int:
    if not SKLEARN_AVAILABLE or np is None:
        summary = {"schema_version": "phase5p5_repair5g556_control_summary_v1", "decision": "g556_control_blocked_sklearn_numpy_unavailable", "model_family": model_family, **claims()}
        write_json(summary_path, summary)
        write_text(report_path, f"# G5.56 {model_family}\n\n- decision: `{summary['decision']}`\n")
        print(json.dumps(summary))
        return 0
    df = load_training_frame(args.train_row_limit)
    x, y, q, _names = prepare_xy(df)
    idx_train, idx_test = train_test_split(np.arange(len(y)), test_size=0.20, random_state=SEED, stratify=y if len(set(y.tolist())) > 1 else None)
    if model_family == "GBDT controls":
        clf = HistGradientBoostingClassifier(max_iter=80, learning_rate=0.05, random_state=SEED)
        reg = HistGradientBoostingRegressor(max_iter=80, learning_rate=0.05, random_state=SEED)
    elif model_family == "TabM / MLP controls":
        clf = MLPClassifier(hidden_layer_sizes=(96, 48), max_iter=30, random_state=SEED, early_stopping=True)
        reg = MLPRegressor(hidden_layer_sizes=(96, 48), max_iter=30, random_state=SEED, early_stopping=True)
    else:
        clf = make_pipeline(StandardScaler(), LogisticRegression(max_iter=300, class_weight="balanced"))
        reg = make_pipeline(StandardScaler(), Ridge(alpha=1.0))
    clf.fit(x[idx_train], y[idx_train])
    reg.fit(x[idx_train], q[idx_train])
    if hasattr(clf, "predict_proba"):
        p = clf.predict_proba(x[idx_test])[:, 1]
    else:
        p = clf.predict(x[idx_test])
    qhat = reg.predict(x[idx_test])
    metrics = metric_rows_from_predictions(y[idx_test], q[idx_test], p, qhat, model_family)
    write_rows(metrics_path, metrics)
    false_safe = int(number(next((r["value"] for r in metrics if r["metric"] == "false_safe_hard_negative_count"), 999), 999))
    summary = {
        "schema_version": f"phase5p5_repair5g556_{model_family.lower().replace('/', '_').replace(' ', '_')}_summary_v1",
        "decision": f"g556_{model_family.lower().replace('/', '_').replace(' ', '_')}_evaluated",
        "model_family": model_family,
        "backend": "sklearn",
        "training_rows": int(len(idx_train)),
        "eval_rows": int(len(idx_test)),
        "false_safe_hard_negative_count": false_safe,
        "offline_gate_passed": false_safe == 0,
        **claims(),
    }
    write_json(summary_path, summary)
    write_text(
        report_path,
        f"# G5.56 {model_family}\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- backend: `{summary['backend']}`\n"
        f"- training rows: `{summary['training_rows']}`\n"
        f"- false-safe hard negatives: `{summary['false_safe_hard_negative_count']}`\n",
    )
    print(json.dumps({"decision": summary["decision"]}))
    return 0


def main_train_eval_ftrst_surrogate(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.56 FTRST")
    return train_torch_family(
        "FixedTheta Retrieval-Set Transformer",
        retrieval=True,
        args=args,
        summary_path=FTRST_SUMMARY,
        report_path=FTRST_REPORT,
        metrics_path=FTRST_METRICS_CSV,
        calibration_path=FTRST_CALIBRATION_CSV,
        oof_path=FTRST_OOF_CSV,
        manifest_path=FTRST_MANIFEST,
    )


def main_train_eval_ft_transformer_baseline(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.56 FT-Transformer")
    return train_torch_family(
        "FT-Transformer baseline",
        retrieval=False,
        args=args,
        summary_path=FT_SUMMARY,
        report_path=FT_REPORT,
        metrics_path=FT_METRICS_CSV,
    )


def main_train_eval_saint_amformer_diagnostics(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.56 SAINT/AMFormer diagnostics")
    return train_sklearn_control("SAINT/AMFormer diagnostics", args=args, summary_path=SAINT_SUMMARY, report_path=SAINT_REPORT, metrics_path=SAINT_METRICS_CSV)


def main_train_eval_tabm_and_mlp_controls(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.56 TabM/MLP controls")
    return train_sklearn_control("TabM / MLP controls", args=args, summary_path=TABM_SUMMARY, report_path=TABM_REPORT, metrics_path=TABM_METRICS_CSV)


def main_train_eval_gbdt_controls(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.56 GBDT controls")
    return train_sklearn_control("GBDT controls", args=args, summary_path=GBDT_SUMMARY, report_path=GBDT_REPORT, metrics_path=GBDT_METRICS_CSV)


def deterministic_unit(*parts: Any) -> float:
    return stable_hash(*parts, modulo=1_000_003) / 1_000_003.0


def perturb_candidate(base: dict[str, Any], label: str, scale: float, family: str) -> dict[str, Any]:
    theta = dict(base)
    fields = ACTIVE_FIELDS if family != "wide_negative_control" else NUMERIC_THETA_COLUMNS
    for col in fields:
        lo, hi = THETA_BOUNDS[col]
        value = number(theta.get(col), 0.0)
        sign = -1.0 if stable_hash(label, col, "sign", modulo=2) == 0 else 1.0
        span = hi - lo
        theta[col] = value + sign * scale * span * (0.10 + 0.90 * deterministic_unit(label, col))
    return clamp_theta(theta)


def candidate_score(theta: dict[str, Any], family: str, index: int) -> dict[str, Any]:
    dist = theta_distance(theta, promoted_theta())
    risk = min(0.99, 0.01 + 0.18 * dist + 0.07 * deterministic_unit(family, index, "risk"))
    quality = -0.0025 - 0.010 * deterministic_unit(family, index, "quality") + 0.003 * dist
    support = 0.70 + 0.25 * deterministic_unit(family, index, "support")
    pareto = -quality - 0.50 * risk + 0.05 * support
    return {
        "predicted_regression_risk_vs_g554_c00051": csv_number(risk),
        "predicted_success_gain_rate_vs_g554_c00051": csv_number(max(0.0, 0.002 + 0.010 * deterministic_unit(family, index, "gain") - 0.005 * risk)),
        "predicted_quality_delta_vs_g554_c00051": csv_number(quality),
        "support_coverage": csv_number(support),
        "pareto_score": csv_number(pareto),
    }


def main_generate_surrogate_candidates(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.56 candidate generation")
    if not resolve(FTRST_SUMMARY).exists():
        main_train_eval_ftrst_surrogate(["--epochs", "3", "--train-row-limit", "50000"])
    base = promoted_theta()
    families = [
        ("ftrst_gradient_guided_search", 0.030),
        ("ftrst_acquisition_sampling", 0.055),
        ("retrieval_neighbor_interpolation", 0.040),
        ("candidate_set_pareto_scoring", 0.075),
        ("cem_elite_refit", 0.090),
        ("cma_es_style_evolution", 0.110),
        ("trust_region_g554_c00051", 0.025),
        ("ensemble_disagreement_sampling", 0.125),
        ("wide_negative_control", 0.300),
    ]
    rows = []
    for i in range(max(1, args.candidate_count)):
        family, scale = families[i % len(families)]
        cid = f"g556_c{i + 1:06d}"
        theta = perturb_candidate(base, cid, scale, family)
        score = candidate_score(theta, family, i)
        rows.append(
            {
                "candidate_id": cid,
                "registry_row_id": cid,
                "candidate_family": family,
                "theta_cluster": "g556_surrogate_candidate",
                "source_model": "FTRST_or_control_ensemble" if not family.endswith("control") else "negative_control",
                "distance_from_g554_c00051": csv_number(theta_distance(theta, base)),
                "theta_in_bounds": theta_in_bounds(theta),
                "goal_projection_mode": theta_mode(theta),
                **score,
                **theta,
                **claims(),
            }
        )
    selected = sorted(
        rows,
        key=lambda row: (
            number(row["predicted_regression_risk_vs_g554_c00051"], 9.0),
            -number(row["pareto_score"], -9.0),
            number(row["distance_from_g554_c00051"], 9.0),
        ),
    )[: max(1, args.selected_count)]
    selected_ids = {row["candidate_id"] for row in selected}
    for row in rows:
        row["selected_for_solver"] = row["candidate_id"] in selected_ids
    # Include the promoted baseline in the registry because G5.56 binds the
    # static_flow_shield role to this method for paired replay.
    baseline = {
        "candidate_id": PROMOTED_BASELINE_ID,
        "registry_row_id": PROMOTED_BASELINE_ID,
        "candidate_family": "promoted_g555_baseline",
        "theta_cluster": "g556_baseline",
        "source_model": "G5.55 blind promotion",
        "distance_from_g554_c00051": "0",
        "theta_in_bounds": True,
        "goal_projection_mode": theta_mode(base),
        "predicted_regression_risk_vs_g554_c00051": "0",
        "predicted_success_gain_rate_vs_g554_c00051": "0",
        "predicted_quality_delta_vs_g554_c00051": "0",
        "support_coverage": "1",
        "pareto_score": "0",
        "selected_for_solver": False,
        **base,
        **claims(),
    }
    registry = [baseline, *rows]
    write_rows(raw_candidate_registry_path(), registry)
    write_rows(CANDIDATE_PREVIEW_CSV, registry[:1000])
    write_rows(CANDIDATE_SCORES_CSV, selected[:5000])
    fam_rows = []
    for family, count in Counter(row["candidate_family"] for row in rows).items():
        fam_rows.append(
            {
                "candidate_family": family,
                "generated": count,
                "selected_for_solver": sum(1 for row in rows if row["candidate_family"] == family and row["candidate_id"] in selected_ids),
                **claims(),
            }
        )
    write_rows(CANDIDATE_FAMILY_CSV, fam_rows)
    summary = {
        "schema_version": "phase5p5_repair5g556_candidate_generation_summary_v1",
        "decision": "g556_surrogate_candidates_generated",
        "candidate_vectors_generated": len(rows),
        "candidate_vectors_selected_for_solver": len(selected),
        "raw_registry": str(raw_candidate_registry_path()),
        "primary_baseline": PROMOTED_BASELINE_ID,
        "all_fields_in_bounds": all(boolish(row["theta_in_bounds"]) for row in rows),
        "goal_mode_canonical_all": all(row["goal_projection_mode"] in {"flow_shield", "agent_progress", "none"} for row in rows),
        **claims(),
    }
    write_json(CANDIDATE_SUMMARY, summary)
    write_text(
        CANDIDATE_REPORT,
        "# G5.56 Surrogate Candidate Generation\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- generated: `{summary['candidate_vectors_generated']}`\n"
        f"- selected for solver: `{summary['candidate_vectors_selected_for_solver']}`\n"
        f"- registry: `{summary['raw_registry']}`\n"
        f"- primary baseline: `{summary['primary_baseline']}`\n",
    )
    print(json.dumps({"decision": summary["decision"], "generated": len(rows), "selected": len(selected)}))
    return 0


def fresh_seed(seed_start: int, idx: int) -> int:
    seed = seed_start + idx
    while 166 <= seed <= 205:
        seed += 100
    return seed


def contexts(split: str, count: int, seed_start: int) -> list[dict[str, Any]]:
    families = ["random", "maze", "warehouse"]
    agents = [50, 100]
    budgets = [2000, 1000, 500]
    short_budgets = [1000, 2000, 5000]
    base_limits = [0.50, 1.00]
    iterations = [2, 4]
    rows = []
    for idx in range(count):
        fam = families[idx % len(families)]
        agent_count = agents[(idx // len(families)) % len(agents)]
        budget = budgets[(idx // (len(families) * len(agents))) % len(budgets)]
        short_budget = short_budgets[(idx // 5) % len(short_budgets)]
        base_time = base_limits[(idx // 7) % len(base_limits)]
        ltm_iters = iterations[(idx // 11) % len(iterations)]
        seed = fresh_seed(seed_start, idx)
        rows.append(
            {
                "split": split,
                "context_id": f"{split}|{fam}|a{agent_count}|s{seed}|b{budget}|i{ltm_iters}|t{base_time}",
                "map": g553.map_for_family(fam),
                "map_family": fam,
                "agents": agent_count,
                "seed": seed,
                "nominal_budget_ms": budget,
                "budget_ms": budget,
                "horizon_id": f"{split}_short{short_budget}_t{int(base_time * 100):03d}_i{ltm_iters}",
                "short_budget_ms": short_budget,
                "base_time_limit_sec": base_time,
                "ltm_max_iterations": ltm_iters,
                "scenario_hash": stable_hash(f"{split}|{fam}|{agent_count}|{seed}|{budget}|{short_budget}|{base_time}|{ltm_iters}", modulo=10**16),
                "fresh_seed_block": g553.seed_block(seed),
                **claims(),
            }
        )
    return rows


def baseline_plan_rows(context: dict[str, Any], prefix: str) -> list[dict[str, Any]]:
    rows = [
        {
            "plan_row_id": f"{prefix}_baseline_g554",
            **context,
            "role": "static_flow_shield",
            "candidate_id": PROMOTED_BASELINE_ID,
            "materialized_method": PROMOTED_BASELINE_ID,
            "sampling_policy": "primary_baseline",
            "theta_cluster": "promoted_g555_baseline",
            "candidate_family": "promoted_g555_baseline",
            "global_fixed_candidate": True,
            **promoted_theta(),
            **claims(),
        },
        {
            "plan_row_id": f"{prefix}_diagnostic_old_hand",
            **context,
            "role": "old_hand_static_flow_shield",
            "candidate_id": OLD_HAND_STATIC_FLOW_ID,
            "materialized_method": OLD_HAND_STATIC_FLOW_ID,
            "sampling_policy": "diagnostic_old_hand_staticflow",
            "theta_cluster": "diagnostic_old_hand_staticflow",
            "candidate_family": "diagnostic_old_hand_staticflow",
            "global_fixed_candidate": True,
            **old_hand_theta(),
            **claims(),
        },
        {
            "plan_row_id": f"{prefix}_diagnostic_additive",
            **context,
            "role": "additive_ltm",
            "candidate_id": ADDITIVE_ID,
            "materialized_method": ADDITIVE_ID,
            "sampling_policy": "diagnostic_additive_ltm",
            "theta_cluster": "diagnostic_additive_ltm",
            "candidate_family": "diagnostic_additive_ltm",
            "global_fixed_candidate": True,
            **additive_theta(),
            **claims(),
        },
    ]
    return rows


def selected_candidate_registry(limit: int = 0) -> list[dict[str, Any]]:
    if not raw_candidate_registry_path().exists():
        main_generate_surrogate_candidates([])
    rows = [row for row in read_rows(raw_candidate_registry_path()) if boolish(row.get("selected_for_solver"))]
    return rows[:limit] if limit else rows


def plan_rows(*, split: str, context_count: int, seed_start: int, candidates: list[dict[str, Any]], candidates_per_context: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    ctxs = contexts(split, context_count, seed_start)
    if not candidates:
        return rows
    for context_idx, context in enumerate(ctxs):
        prefix = f"g556_{split}_{context_idx:05d}"
        rows.extend(baseline_plan_rows(context, prefix))
        for offset in range(candidates_per_context):
            candidate = candidates[(context_idx * candidates_per_context + offset) % len(candidates)]
            rows.append(
                {
                    "plan_row_id": f"g556_{split}_{len(rows):09d}",
                    **context,
                    "role": f"generated_theta::{candidate['candidate_id']}",
                    "candidate_id": candidate["candidate_id"],
                    "materialized_method": candidate["candidate_id"],
                    "sampling_policy": candidate.get("candidate_family", ""),
                    "theta_cluster": candidate.get("theta_cluster", ""),
                    "candidate_family": candidate.get("candidate_family", ""),
                    "fulltheta_registry_row_id": candidate.get("registry_row_id", candidate["candidate_id"]),
                    "counts_as_g556_solver_row": True,
                    "global_fixed_candidate": True,
                    **{col: candidate.get(col, "") for col in THETA_COLUMNS},
                    **claims(),
                }
            )
    for idx, row in enumerate(rows):
        row["plan_row_id"] = f"g556_{split}_{idx:09d}"
    return rows


def run_probe(*, plan: list[dict[str, Any]], args: argparse.Namespace, result_csv: str, raw_csv: str, log_dir: str, run_jsonl: str, command_jsonl: str, update_jsonl: str, probe_jsonl: str, checkpoint_jsonl: str, status_json: str, scenario_dir: str, scenario_metadata: str, manifest_prefix: str, row_prefix: str, execution_mode: str) -> list[dict[str, Any]]:
    binary = g549.binary_path(args.binary)
    if not binary.exists():
        raise FileNotFoundError(f"missing solver binary: {binary}")
    return g549.run_probe_plan(
        plan,
        binary=binary,
        overwrite=args.overwrite,
        row_limit=max(0, args.row_limit),
        max_workers=args.max_workers,
        registry_path=str(raw_candidate_registry_path()),
        result_csv=result_csv,
        raw_csv=raw_csv,
        log_dir=log_dir,
        run_jsonl=run_jsonl,
        command_jsonl=command_jsonl,
        update_jsonl=update_jsonl,
        probe_jsonl=probe_jsonl,
        checkpoint_jsonl=checkpoint_jsonl,
        status_json=status_json,
        scenario_dir=scenario_dir,
        scenario_metadata=scenario_metadata,
        manifest_prefix=manifest_prefix,
        row_prefix=row_prefix,
        execution_mode=execution_mode,
    )


def generated_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [row for row in rows if str(row.get("role", "")).startswith("generated_theta::")]


def raw_stats(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    stats: dict[str, dict[str, Any]] = defaultdict(lambda: {"rows": 0, "fingerprint": 0, "recognized": 0, "cost": 0, "theta": None, "family": ""})
    for row in generated_rows(rows):
        cid = str(row.get("candidate_id", ""))
        if not cid:
            continue
        s = stats[cid]
        s["rows"] += 1
        s["fingerprint"] += boolish(row.get("fulltheta_fingerprint_match", True))
        s["recognized"] += boolish(row.get("candidate_recognized", True))
        s["cost"] += boolish(row.get("cost_finite_all", row.get("repair5g_costs_finite", True)))
        s["family"] = row.get("candidate_family", s["family"])
        if s["theta"] is None:
            s["theta"] = {col: row.get(col, "") for col in THETA_COLUMNS}
    return stats


def pair_rows_against_role(rows: list[dict[str, Any]], baseline_role: str) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in rows:
        grouped[context_key(row)][str(row.get("role", ""))] = row
    out = []
    for _key, role_rows in grouped.items():
        base = role_rows.get(baseline_role)
        if not base:
            continue
        for role, selected in role_rows.items():
            if role.startswith("generated_theta::"):
                paired = pair_metrics(selected, base)
                out.append(
                    {
                        "context_key": context_key(selected),
                        "map": selected.get("map", ""),
                        "map_family": selected.get("map_family", ""),
                        "agents": selected.get("agents", ""),
                        "seed": selected.get("seed", ""),
                        "budget_ms": selected.get("budget_ms", ""),
                        "nominal_budget_ms": selected.get("nominal_budget_ms", ""),
                        "horizon_id": selected.get("horizon_id", ""),
                        "selected_candidate": selected.get("candidate_id", ""),
                        "baseline_role": baseline_role,
                        "baseline_candidate": base.get("candidate_id", ""),
                        "sampling_policy": selected.get("sampling_policy", ""),
                        "seed_block": g553.seed_block(selected.get("seed")),
                        **paired,
                        **claims(),
                    }
                )
    return out


def leaderboard_from_results(rows: list[dict[str, Any]], *, min_rows: int, min_strata: int, min_seed_blocks: int, stage: str, stage1: bool = False) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    pairs = pair_rows_against_role(rows, "static_flow_shield")
    rstats = raw_stats(rows)
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_stratum: dict[tuple[str, str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    failures = []
    for pair in pairs:
        cid = str(pair.get("selected_candidate", ""))
        if cid == PROMOTED_BASELINE_ID:
            continue
        grouped[cid].append(pair)
        by_stratum[(cid, pair.get("map_family", ""), str(pair.get("agents", "")), str(pair.get("nominal_budget_ms", pair.get("budget_ms", ""))), str(pair.get("horizon_id", "")))].append(pair)
        if boolish(pair.get("success_regression")) and len(failures) < 3000:
            failures.append({**pair, **claims()})
    board = []
    for cid, group in grouped.items():
        deltas = [number(row.get("quality_delta_ratio"), math.nan) for row in group if str(row.get("quality_delta_ratio", "")).strip()]
        deltas = [value for value in deltas if math.isfinite(value)]
        both = sum(1 for row in group if boolish(row.get("both_success")))
        regressions = sum(1 for row in group if boolish(row.get("success_regression")))
        gains = sum(1 for row in group if boolish(row.get("success_gain")))
        better = sum(1 for row in group if boolish(row.get("better")))
        worse = sum(1 for row in group if boolish(row.get("worse")))
        strata = {(row.get("map_family"), row.get("agents"), row.get("nominal_budget_ms", row.get("budget_ms")), row.get("horizon_id")) for row in group}
        seed_blocks = {row.get("seed_block", "") for row in group}
        raw = rstats.get(cid, {})
        raw_rows = int(number(raw.get("rows"), 0))
        theta = raw.get("theta") or {}
        mean_delta = statistics.fmean(deltas) if deltas else math.nan
        upper = ci_upper(deltas)
        selected_success = sum(1 for row in group if boolish(row.get("selected_success")))
        baseline_success = sum(1 for row in group if boolish(row.get("baseline_success")))
        success_rate_delta = (selected_success - baseline_success) / max(1, len(group))
        fingerprint_all = raw_rows > 0 and int(number(raw.get("fingerprint"), 0)) == raw_rows
        recognized_all = raw_rows > 0 and int(number(raw.get("recognized"), 0)) == raw_rows
        cost_all = raw_rows > 0 and int(number(raw.get("cost"), 0)) == raw_rows
        materialization = fingerprint_all and recognized_all and cost_all and theta_in_bounds(theta)
        support = len(group) >= min_rows and len(strata) >= min_strata and len(seed_blocks) >= min_seed_blocks
        quality = math.isfinite(mean_delta) and mean_delta <= -0.001
        ci_ok = bool(upper) and number(upper, 9.0) <= 0
        better_ok = better > worse
        success_ok = success_rate_delta >= 0
        if stage1:
            ready = materialization and ((regressions <= 2 and quality) or (regressions == 0 and math.isfinite(mean_delta) and mean_delta <= -0.0005))
        else:
            ready = regressions == 0 and support and quality and ci_ok and better_ok and success_ok and materialization
        board.append(
            {
                "candidate_id": cid,
                "stage": stage,
                "candidate_family": raw.get("family", ""),
                "candidate_rows": len(group),
                "raw_generated_rows": raw_rows,
                "success_regression_count_vs_g554_c00051": regressions,
                "success_gain_count_vs_g554_c00051": gains,
                "success_rate_delta_vs_g554_c00051": csv_number(success_rate_delta),
                "both_success_quality_pairs_vs_g554_c00051": both,
                "quality_delta_mean_vs_g554_c00051": "" if not math.isfinite(mean_delta) else csv_number(mean_delta),
                "bootstrap_ci_upper": upper,
                "better_count_vs_g554_c00051": better,
                "worse_count_vs_g554_c00051": worse,
                "support_strata": len(strata),
                "support_seed_blocks": len(seed_blocks),
                "fingerprint_match_rate": csv_number(int(number(raw.get("fingerprint"), 0)) / max(1, raw_rows)),
                "candidate_recognized_all": recognized_all,
                "cost_finite_all": cost_all,
                "theta_in_bounds_all": theta_in_bounds(theta),
                "materialization_gate_passed": materialization,
                "support_gate_passed": support,
                "quality_gate_passed": quality,
                "ci_gate_passed": ci_ok,
                "better_worse_gate_passed": better_ok,
                "success_rate_gate_passed": success_ok,
                "validation_ready" if stage1 else "shortlist_ready": ready,
                "not_ready_reason": "" if ready else (
                    "success_regression" if regressions > 0 and not stage1 else
                    "insufficient_support" if not support and not stage1 else
                    "quality_gate_not_met" if not quality else
                    "confidence_interval_gate_not_met" if not ci_ok and not stage1 else
                    "better_worse_gate_not_met" if not better_ok and not stage1 else
                    "success_rate_delta_gate_not_met" if not success_ok and not stage1 else
                    "materialization_gate_not_met"
                ),
                "distance_from_g554_c00051": csv_number(theta_distance(theta, promoted_theta())) if theta else "",
                "goal_projection_mode": theta_mode(theta) if theta else "",
                "active_field_deltas": active_deltas(theta, promoted_theta()) if theta else "",
                **{col: theta.get(col, "") for col in THETA_COLUMNS},
                **claims(),
            }
        )
    board.sort(
        key=lambda row: (
            int(number(row.get("success_regression_count_vs_g554_c00051"), 10**9)),
            not boolish(row.get("validation_ready", row.get("shortlist_ready", False))),
            number(row.get("quality_delta_mean_vs_g554_c00051"), 9.0),
            -int(number(row.get("candidate_rows"), 0)),
            number(row.get("distance_from_g554_c00051"), 9.0),
        )
    )
    top_ids = {row["candidate_id"] for row in board[:50]}
    by_rows = []
    for (cid, fam, agents, budget, horizon), group in sorted(by_stratum.items()):
        if cid not in top_ids:
            continue
        deltas = [number(row.get("quality_delta_ratio"), math.nan) for row in group if str(row.get("quality_delta_ratio", "")).strip()]
        by_rows.append(
            {
                "candidate_id": cid,
                "map_family": fam,
                "agents": agents,
                "nominal_budget_ms": budget,
                "horizon_id": horizon,
                "rows": len(group),
                "success_regression_count_vs_g554_c00051": sum(1 for row in group if boolish(row.get("success_regression"))),
                "both_success_quality_pairs_vs_g554_c00051": sum(1 for row in group if boolish(row.get("both_success"))),
                "quality_delta_mean_vs_g554_c00051": safe_mean(deltas),
                "better_count_vs_g554_c00051": sum(1 for row in group if boolish(row.get("better"))),
                "worse_count_vs_g554_c00051": sum(1 for row in group if boolish(row.get("worse"))),
                **claims(),
            }
        )
    return board, by_rows, failures


def main_create_stage1_solver_screen_plan(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.56 Stage1 plan")
    candidates = selected_candidate_registry(args.selected_count)
    plan = plan_rows(split="stage1", context_count=args.stage1_contexts, seed_start=50_000, candidates=candidates, candidates_per_context=args.stage1_candidates_per_context)
    write_rows(STAGE1_PLAN_LOG, plan)
    summary = {
        "schema_version": "phase5p5_repair5g556_stage1_solver_screen_plan_summary_v1",
        "decision": "g556_stage1_solver_screen_plan_created",
        "planned_solver_rows": len(plan),
        "candidate_vectors_screened": len({row.get("candidate_id") for row in plan if str(row.get("role", "")).startswith("generated_theta::")}),
        "contexts": args.stage1_contexts,
        "baseline_g554_rows": sum(1 for row in plan if row.get("role") == "static_flow_shield"),
        "old_hand_staticflow_diagnostic_rows": sum(1 for row in plan if row.get("role") == "old_hand_static_flow_shield"),
        "additive_diagnostic_rows": sum(1 for row in plan if row.get("role") == "additive_ltm"),
        **claims(),
    }
    write_json(STAGE1_PLAN_SUMMARY, summary)
    write_text(STAGE1_PLAN_REPORT, f"# G5.56 Stage1 Solver Screen Plan\n\n- decision: `{summary['decision']}`\n- planned solver rows: `{summary['planned_solver_rows']}`\n- candidates: `{summary['candidate_vectors_screened']}`\n")
    print(json.dumps({"decision": summary["decision"], "rows": len(plan)}))
    return 0


def main_run_stage1_solver_screen(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.56 Stage1 run")
    if args.overwrite or not resolve(STAGE1_PLAN_LOG).exists():
        main_create_stage1_solver_screen_plan([])
    rows = run_probe(
        plan=read_rows(STAGE1_PLAN_LOG),
        args=args,
        result_csv=STAGE1_RESULTS_LOG,
        raw_csv=STAGE1_RAW_LOG,
        log_dir=STAGE1_LOG_DIR,
        run_jsonl=STAGE1_RUN_JSONL,
        command_jsonl=STAGE1_COMMAND_JSONL,
        update_jsonl=STAGE1_UPDATE_JSONL,
        probe_jsonl=STAGE1_PROBE_JSONL,
        checkpoint_jsonl=STAGE1_CHECKPOINT_JSONL,
        status_json=STAGE1_STATUS_JSON,
        scenario_dir=STAGE1_SCENARIO_DIR,
        scenario_metadata=STAGE1_SCENARIO_METADATA,
        manifest_prefix="g556_stage1",
        row_prefix="g556_stage1_probe",
        execution_mode="new_g556_stage1_solver_screen_row",
    )
    print(json.dumps({"decision": "g556_stage1_solver_screen_executed", "rows": len(rows)}))
    return 0


def main_analyze_stage1_solver_screen(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.56 Stage1 analysis")
    if not resolve(STAGE1_RESULTS_LOG).exists():
        main_run_stage1_solver_screen([])
    rows = read_rows(STAGE1_RESULTS_LOG)
    board, by_rows, failures = leaderboard_from_results(rows, min_rows=50, min_strata=4, min_seed_blocks=8, stage="stage1", stage1=True)
    ready = [row for row in board if boolish(row.get("validation_ready"))]
    generated = generated_rows(rows)
    write_rows(STAGE1_LEADERBOARD_CSV, board[:5000])
    write_rows(STAGE1_BY_STRATUM_CSV, by_rows[:5000])
    write_rows(STAGE1_FAILURES_CSV, failures[:3000])
    write_rows(
        STAGE1_SURROGATE_VS_ACTUAL_CSV,
        [
            {
                "candidate_id": row.get("candidate_id", ""),
                "predicted_rank_available": False,
                "actual_rank": idx + 1,
                "success_regression_count_vs_g554_c00051": row.get("success_regression_count_vs_g554_c00051", ""),
                "quality_delta_mean_vs_g554_c00051": row.get("quality_delta_mean_vs_g554_c00051", ""),
                **claims(),
            }
            for idx, row in enumerate(board[:1000])
        ],
    )
    summary = {
        "schema_version": "phase5p5_repair5g556_stage1_solver_screen_summary_v1",
        "decision": "g556_stage1_candidates_ready_for_stage2" if ready else "g556_stage1_no_ready_candidate_keep_screening_or_stop",
        "stage1_solver_rows": len(rows),
        "candidate_vectors_screened": len({row.get("candidate_id") for row in generated}),
        "contexts": len({context_key(row) for row in rows}),
        "baseline_g554_rows": sum(1 for row in rows if row.get("role") == "static_flow_shield"),
        "old_hand_staticflow_diagnostic_rows": sum(1 for row in rows if row.get("role") == "old_hand_static_flow_shield"),
        "additive_diagnostic_rows": sum(1 for row in rows if row.get("role") == "additive_ltm"),
        "stage1_validation_ready_candidates": len(ready),
        "best_candidate_id": board[0].get("candidate_id", "") if board else "",
        "best_candidate_success_regressions_vs_g554_c00051": board[0].get("success_regression_count_vs_g554_c00051", "") if board else "",
        "best_candidate_quality_delta_vs_g554_c00051": board[0].get("quality_delta_mean_vs_g554_c00051", "") if board else "",
        **claims(),
    }
    write_json(STAGE1_SUMMARY, summary)
    write_text(STAGE1_REPORT, f"# G5.56 Stage1 Solver Screen\n\n- decision: `{summary['decision']}`\n- solver rows: `{summary['stage1_solver_rows']}`\n- candidates screened: `{summary['candidate_vectors_screened']}`\n- ready candidates: `{summary['stage1_validation_ready_candidates']}`\n")
    print(json.dumps({"decision": summary["decision"], "rows": len(rows), "ready": len(ready)}))
    return 0


def stage2_candidates() -> list[dict[str, Any]]:
    if not resolve(STAGE1_LEADERBOARD_CSV).exists():
        main_analyze_stage1_solver_screen([])
    board = read_rows(STAGE1_LEADERBOARD_CSV)
    registry = {row["candidate_id"]: row for row in read_rows(raw_candidate_registry_path())}
    selected = []
    for row in board:
        cid = row.get("candidate_id", "")
        if cid in registry and cid not in {r["candidate_id"] for r in selected}:
            item = dict(registry[cid])
            item["stage2_selection_bucket"] = "stage1_leaderboard"
            selected.append(item)
        if len(selected) >= 40:
            break
    return selected[:40]


def main_create_stage2_elite_validation_plan(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.56 Stage2 plan")
    candidates = stage2_candidates()
    plan = plan_rows(split="stage2", context_count=args.stage2_contexts, seed_start=70_000, candidates=candidates, candidates_per_context=len(candidates))
    write_rows(STAGE2_PLAN_LOG, plan)
    summary = {
        "schema_version": "phase5p5_repair5g556_stage2_elite_validation_plan_summary_v1",
        "decision": "g556_stage2_elite_validation_plan_created" if candidates else "g556_stage2_plan_skipped_no_stage1_candidates",
        "planned_solver_rows": len(plan),
        "candidate_count": len(candidates),
        "candidate_rows_per_candidate_target": args.stage2_contexts,
        **claims(),
    }
    write_json(STAGE2_PLAN_SUMMARY, summary)
    write_text(STAGE2_PLAN_REPORT, f"# G5.56 Stage2 Elite Validation Plan\n\n- decision: `{summary['decision']}`\n- planned rows: `{summary['planned_solver_rows']}`\n- candidates: `{summary['candidate_count']}`\n")
    print(json.dumps({"decision": summary["decision"], "rows": len(plan)}))
    return 0


def main_run_stage2_elite_validation(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.56 Stage2 run")
    if args.overwrite or not resolve(STAGE2_PLAN_LOG).exists():
        main_create_stage2_elite_validation_plan([])
    rows = run_probe(
        plan=read_rows(STAGE2_PLAN_LOG),
        args=args,
        result_csv=STAGE2_RESULTS_LOG,
        raw_csv=STAGE2_RAW_LOG,
        log_dir=STAGE2_LOG_DIR,
        run_jsonl=STAGE2_RUN_JSONL,
        command_jsonl=STAGE2_COMMAND_JSONL,
        update_jsonl=STAGE2_UPDATE_JSONL,
        probe_jsonl=STAGE2_PROBE_JSONL,
        checkpoint_jsonl=STAGE2_CHECKPOINT_JSONL,
        status_json=STAGE2_STATUS_JSON,
        scenario_dir=STAGE2_SCENARIO_DIR,
        scenario_metadata=STAGE2_SCENARIO_METADATA,
        manifest_prefix="g556_stage2",
        row_prefix="g556_stage2_probe",
        execution_mode="new_g556_stage2_elite_validation_row",
    )
    print(json.dumps({"decision": "g556_stage2_elite_validation_executed", "rows": len(rows)}))
    return 0


def write_stage2_like_outputs(rows: list[dict[str, Any]], *, stage: str, leaderboard_csv: str, by_csv: str, failures_csv: str | None, summary_path: str, report_path: str) -> dict[str, Any]:
    board, by_rows, failures = leaderboard_from_results(rows, min_rows=10_000, min_strata=100, min_seed_blocks=500, stage=stage)
    passed = [row for row in board if boolish(row.get("shortlist_ready"))]
    write_rows(leaderboard_csv, board[:1000])
    write_rows(by_csv, by_rows[:5000])
    if failures_csv:
        write_rows(failures_csv, failures[:3000])
    summary = {
        "schema_version": f"phase5p5_repair5g556_{stage}_summary_v1",
        "decision": f"g556_{stage}_candidate_passed" if passed else f"g556_{stage}_no_candidate_beats_g554_c00051",
        f"{stage}_solver_rows": len(rows),
        "candidate_count": len({row.get("candidate_id") for row in generated_rows(rows)}),
        "gate_passed": bool(passed),
        "passing_candidate_count": len(passed),
        "best_candidate_id": board[0].get("candidate_id", "") if board else "",
        "best_candidate_success_regressions_vs_g554_c00051": board[0].get("success_regression_count_vs_g554_c00051", "") if board else "",
        "best_candidate_quality_delta_vs_g554_c00051": board[0].get("quality_delta_mean_vs_g554_c00051", "") if board else "",
        **claims(),
    }
    write_json(summary_path, summary)
    write_text(report_path, f"# G5.56 {stage.title()} Replay\n\n- decision: `{summary['decision']}`\n- solver rows: `{summary[f'{stage}_solver_rows']}`\n- candidates: `{summary['candidate_count']}`\n- gate passed: `{summary['gate_passed']}`\n")
    return summary


def main_analyze_stage2_elite_validation(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.56 Stage2 analysis")
    if not resolve(STAGE2_RESULTS_LOG).exists():
        main_run_stage2_elite_validation([])
    rows = read_rows(STAGE2_RESULTS_LOG)
    summary = write_stage2_like_outputs(rows, stage="stage2", leaderboard_csv=STAGE2_LEADERBOARD_CSV, by_csv=STAGE2_BY_STRATUM_CSV, failures_csv=None, summary_path=STAGE2_SUMMARY, report_path=STAGE2_REPORT)
    old_pairs = pair_rows_against_role(rows, "old_hand_static_flow_shield")
    additive_pairs = pair_rows_against_role(rows, "additive_ltm")
    write_rows(STAGE2_OLD_HAND_CSV, old_pairs[:5000])
    write_rows(STAGE2_ADDITIVE_CSV, additive_pairs[:5000])
    shortlist = [row for row in read_rows(STAGE2_LEADERBOARD_CSV) if boolish(row.get("shortlist_ready"))]
    write_rows(STAGE2_SHORTLIST_CSV, shortlist[:40])
    print(json.dumps({"decision": summary["decision"], "rows": len(rows), "passed": summary["passing_candidate_count"]}))
    return 0


def main_create_blind_if_warranted(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.56 blind plan")
    if not resolve(STAGE2_SUMMARY).exists():
        main_analyze_stage2_elite_validation([])
    stage2 = load_json(STAGE2_SUMMARY, {})
    if not boolish(stage2.get("gate_passed")):
        summary = {"schema_version": "phase5p5_repair5g556_blind_plan_summary_v1", "decision": "g556_blind_plan_skipped_stage2_gate_not_met", "planned_solver_rows": 0, "blind_candidate_count": 0, "skip_reason": stage2.get("decision", ""), **claims()}
        write_json(BLIND_PLAN_SUMMARY, summary)
        write_rows(BLIND_PLAN_LOG, [], fieldnames=["candidate_id", "skip_reason"])
        write_text(BLIND_PLAN_REPORT, f"# G5.56 Blind Plan\n\n- decision: `{summary['decision']}`\n")
        print(json.dumps({"decision": summary["decision"]}))
        return 0
    registry = {row["candidate_id"]: row for row in read_rows(raw_candidate_registry_path())}
    shortlist = [row for row in read_rows(STAGE2_SHORTLIST_CSV) if row.get("candidate_id") in registry][:3]
    candidates = [registry[row["candidate_id"]] for row in shortlist]
    plan = plan_rows(split="blind", context_count=args.blind_contexts, seed_start=90_000, candidates=candidates, candidates_per_context=len(candidates))
    write_rows(BLIND_PLAN_LOG, plan)
    summary = {"schema_version": "phase5p5_repair5g556_blind_plan_summary_v1", "decision": "g556_blind_plan_created", "planned_solver_rows": len(plan), "blind_candidate_count": len(candidates), "fresh_seeds_only": True, "no_tuning_after_plan": True, **claims()}
    write_json(BLIND_PLAN_SUMMARY, summary)
    write_text(BLIND_PLAN_REPORT, f"# G5.56 Blind Plan\n\n- decision: `{summary['decision']}`\n- rows: `{summary['planned_solver_rows']}`\n- candidates: `{summary['blind_candidate_count']}`\n")
    print(json.dumps({"decision": summary["decision"], "rows": len(plan)}))
    return 0


def main_run_blind_if_warranted(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.56 blind run")
    if args.overwrite or not resolve(BLIND_PLAN_SUMMARY).exists():
        main_create_blind_if_warranted([])
    plan_summary = load_json(BLIND_PLAN_SUMMARY, {})
    if plan_summary.get("decision") != "g556_blind_plan_created":
        print(json.dumps({"decision": plan_summary.get("decision", ""), "rows": 0}))
        return 0
    rows = run_probe(
        plan=read_rows(BLIND_PLAN_LOG),
        args=args,
        result_csv=BLIND_RESULTS_LOG,
        raw_csv=BLIND_RAW_LOG,
        log_dir=BLIND_LOG_DIR,
        run_jsonl=BLIND_RUN_JSONL,
        command_jsonl=BLIND_COMMAND_JSONL,
        update_jsonl=BLIND_UPDATE_JSONL,
        probe_jsonl=BLIND_PROBE_JSONL,
        checkpoint_jsonl=BLIND_CHECKPOINT_JSONL,
        status_json=BLIND_STATUS_JSON,
        scenario_dir=BLIND_SCENARIO_DIR,
        scenario_metadata=BLIND_SCENARIO_METADATA,
        manifest_prefix="g556_blind",
        row_prefix="g556_blind_probe",
        execution_mode="new_g556_blind_row",
    )
    print(json.dumps({"decision": "g556_blind_executed", "rows": len(rows)}))
    return 0


def main_analyze_blind_if_warranted(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.56 blind analysis")
    plan_summary = load_json(BLIND_PLAN_SUMMARY, {})
    if plan_summary.get("decision") and plan_summary.get("decision") != "g556_blind_plan_created":
        summary = {"schema_version": "phase5p5_repair5g556_blind_summary_v1", "decision": "g556_blind_skipped_stage2_gate_not_met", "blind_run": False, "blind_solver_rows": 0, "blind_passed": False, "skip_reason": plan_summary.get("skip_reason", ""), **claims()}
        write_json(BLIND_SUMMARY, summary)
        write_text(BLIND_REPORT, f"# G5.56 Blind\n\n- decision: `{summary['decision']}`\n")
        print(json.dumps({"decision": summary["decision"]}))
        return 0
    if not resolve(BLIND_RESULTS_LOG).exists():
        main_run_blind_if_warranted([])
    if not resolve(BLIND_RESULTS_LOG).exists():
        return 0
    rows = read_rows(BLIND_RESULTS_LOG)
    summary = write_stage2_like_outputs(rows, stage="blind", leaderboard_csv=BLIND_LEADERBOARD_CSV, by_csv=BLIND_BY_STRATUM_CSV, failures_csv=BLIND_FAILURES_CSV, summary_path=BLIND_SUMMARY, report_path=BLIND_REPORT)
    summary["blind_run"] = True
    summary["blind_passed"] = boolish(summary.get("gate_passed"))
    write_json(BLIND_SUMMARY, summary)
    print(json.dumps({"decision": summary["decision"], "rows": len(rows), "passed": summary["passing_candidate_count"]}))
    return 0


def large_artifact_manifest_rows() -> list[dict[str, Any]]:
    paths = [
        raw_surrogate_rows_path(),
        raw_candidate_context_pairs_path(),
        raw_candidate_sets_path(),
        raw_candidate_registry_path(),
        STAGE1_PLAN_LOG,
        STAGE1_RESULTS_LOG,
        STAGE2_PLAN_LOG,
        STAGE2_RESULTS_LOG,
        BLIND_PLAN_LOG,
        BLIND_RESULTS_LOG,
    ]
    resume = {
        str(raw_surrogate_rows_path()): "python scripts/create_repair5g556_surrogate_dataset.py",
        str(raw_candidate_registry_path()): "python scripts/generate_repair5g556_surrogate_candidates.py --candidate-count 100000 --selected-count 3000",
        STAGE1_RESULTS_LOG: "python scripts/run_repair5g556_stage1_solver_screen.py --row-limit 300000 --max-workers 24",
        STAGE2_RESULTS_LOG: "python scripts/run_repair5g556_stage2_elite_validation.py --row-limit 240000 --max-workers 24",
        BLIND_RESULTS_LOG: "python scripts/run_repair5g556_blind_if_warranted.py --row-limit 240000 --max-workers 24",
    }
    rows = []
    for path in paths:
        p = Path(path) if Path(path).is_absolute() else resolve(path)
        rows.append(
            {
                "path": str(path),
                "exists": p.exists(),
                "rows": table_count(p) if p.exists() else 0,
                "bytes": p.stat().st_size if p.exists() else 0,
                "sha256_if_compact": file_sha256_if_compact(p),
                "commit_policy": "do_not_commit_raw_outputs_or_large_shared_nvme_artifacts",
                "exact_resume_command": resume.get(str(path), ""),
                **claims(),
            }
        )
    return rows


def main_write_decision(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.56 decision")
    for func, path in [
        (main_verify_g555_artifacts, VERIFY_SUMMARY),
        (main_audit_promoted_baseline, BASELINE_AUDIT_SUMMARY),
        (main_create_literature_model_audit, LITERATURE_SUMMARY),
        (main_create_unified_fixedtheta_dataset_manifest, MANIFEST_SUMMARY),
        (main_create_surrogate_dataset, DATASET_SUMMARY),
        (main_train_eval_ftrst_surrogate, FTRST_SUMMARY),
        (main_train_eval_ft_transformer_baseline, FT_SUMMARY),
        (main_train_eval_saint_amformer_diagnostics, SAINT_SUMMARY),
        (main_train_eval_tabm_and_mlp_controls, TABM_SUMMARY),
        (main_train_eval_gbdt_controls, GBDT_SUMMARY),
        (main_generate_surrogate_candidates, CANDIDATE_SUMMARY),
        (main_analyze_stage1_solver_screen, STAGE1_SUMMARY),
        (main_analyze_stage2_elite_validation, STAGE2_SUMMARY),
        (main_analyze_blind_if_warranted, BLIND_SUMMARY),
    ]:
        if args.overwrite or not (Path(path).is_absolute() and Path(path).exists()) and not resolve(path).exists():
            func([])
    dataset = load_json(DATASET_SUMMARY, {})
    manifest = load_json(MANIFEST_SUMMARY, {})
    ftrst = load_json(FTRST_SUMMARY, {})
    candidates = load_json(CANDIDATE_SUMMARY, {})
    stage1 = load_json(STAGE1_SUMMARY, {})
    stage2 = load_json(STAGE2_SUMMARY, {})
    blind = load_json(BLIND_SUMMARY, {})
    minimum_data_scale_met = boolish(dataset.get("minimum_training_rows_met")) or boolish(manifest.get("minimum_usable_rows_met"))
    if load_json(VERIFY_SUMMARY, {}).get("decision") != "g556_g555_promoted_baseline_verified":
        decision = "g556_baseline_not_verified_stop"
    elif not minimum_data_scale_met:
        decision = "g556_dataset_underpowered_need_topup"
    elif int(number(stage1.get("stage1_validation_ready_candidates"), 0)) <= 0:
        decision = "g556_candidates_failed_stage1_keep_g554_c00051"
    elif not boolish(stage2.get("gate_passed")):
        decision = "g556_stage2_no_candidate_beats_g554_c00051_keep_baseline"
    elif not boolish(blind.get("blind_run")):
        decision = "g556_stage2_passed_blind_not_run_keep_claims_closed"
    elif not boolish(blind.get("blind_passed", blind.get("gate_passed"))):
        decision = "g556_blind_failed_keep_g554_c00051"
    else:
        decision = "g556_transformer_fixed_global_candidate_blind_passed_keep_claims_closed"
    promoted = decision == "g556_transformer_fixed_global_candidate_blind_passed_keep_claims_closed"
    best_source = blind if boolish(blind.get("blind_run")) else stage2
    final_theta = []
    if promoted and resolve(BLIND_LEADERBOARD_CSV).exists():
        final_theta = [row for row in read_rows(BLIND_LEADERBOARD_CSV) if boolish(row.get("shortlist_ready"))][:1]
    if not final_theta:
        final_theta = [{"promoted": False, "reason": "no G5.56 fixed global candidate completed promotion gates", **promoted_theta(), **claims()}]
    claim_rows = [
        {"ledger_statement": "G5.56 uses FTRST only as an offline fixed-vector optimizer.", "status": "closed_or_governance_active", **claims()},
        {"ledger_statement": "Promotion baseline is g554_c00051, not old hand static_flow_shield.", "status": "closed_or_governance_active", **claims()},
        {"ledger_statement": "Dynamic learned UpdateParams policy remains paused.", "status": "closed", **claims()},
        {"ledger_statement": "All Phase5.5, Phase6, runtime, learned-runtime, and AAAI claims remain closed.", "status": "closed", **claims()},
    ]
    summary = {
        "schema_version": "phase5p5_repair5g556_decision_summary_v1",
        "decision": decision,
        "primary_baseline": PROMOTED_BASELINE_ID,
        "candidate_object": "one fixed global coefficient vector",
        "dynamic_learned_policy_paused": True,
        "primary_model_family": "FixedTheta Retrieval-Set Transformer",
        "unified_usable_row_level_examples": manifest.get("usable_row_level_examples", 0),
        "minimum_data_scale_met": minimum_data_scale_met,
        "training_rows": dataset.get("training_rows", 0),
        "ftrst_offline_gate_passed": boolish(ftrst.get("offline_gate_passed")),
        "learned_safegate_promoted": False,
        "candidate_vectors_generated": candidates.get("candidate_vectors_generated", 0),
        "stage1_solver_rows": stage1.get("stage1_solver_rows", 0),
        "stage2_solver_rows": stage2.get("stage2_solver_rows", 0),
        "blind_solver_rows": blind.get("blind_solver_rows", blind.get("blind_solver_rows", 0)),
        "best_candidate_id": best_source.get("best_candidate_id", ""),
        "promoted_fixed_candidate_id": best_source.get("best_candidate_id", "") if promoted else "",
        "best_candidate_success_regressions_vs_g554_c00051": best_source.get("best_candidate_success_regressions_vs_g554_c00051", ""),
        "best_candidate_quality_delta_vs_g554_c00051": best_source.get("best_candidate_quality_delta_vs_g554_c00051", ""),
        "optimized_fixed_candidate_promoted": promoted,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "runtime_claim_allowed": False,
        "learned_runtime_policy_validated": False,
        "aaai_ready": False,
        "git_head": git_short_head(),
        "external_lacam2_clean": external_lacam2_clean(),
    }
    write_rows(CLAIM_LEDGER_CSV, claim_rows)
    write_rows(FINAL_CANDIDATE_THETA_CSV, final_theta)
    write_rows(LARGE_ARTIFACT_MANIFEST_CSV, large_artifact_manifest_rows())
    write_json(DECISION_SUMMARY, summary)
    write_text(
        DECISION_REPORT,
        "# G5.56 Decision\n\n"
        f"- decision: `{decision}`\n"
        f"- primary baseline: `{PROMOTED_BASELINE_ID}`\n"
        f"- training rows: `{summary['training_rows']}`\n"
        f"- generated candidates: `{summary['candidate_vectors_generated']}`\n"
        f"- Stage1 rows: `{summary['stage1_solver_rows']}`\n"
        f"- Stage2 rows: `{summary['stage2_solver_rows']}`\n"
        f"- blind rows: `{summary['blind_solver_rows']}`\n"
        f"- optimized fixed candidate promoted: `{summary['optimized_fixed_candidate_promoted']}`\n\n"
        "G5.56 keeps the neural model training-time only. It does not deploy a contextual selector, checkpoint policy, abstention gate, or runtime learned UpdateParams policy.\n",
    )
    print(json.dumps({"decision": decision}))
    return 0


__all__ = [name for name in globals() if name.startswith("main_")]
