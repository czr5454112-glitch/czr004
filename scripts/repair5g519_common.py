"""Shared helpers for Repair5G.5.19 full-primary ranker diagnostics."""

from __future__ import annotations

import csv
import json
import math
import random
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from repair5g512_common import (
    ADDITIVE_CANDIDATE,
    DEFAULT_MARGIN,
    STATIC_ABSTAIN_CANDIDATE,
    STATIC_FLOW_SHIELD_CANDIDATE,
    boolish,
    csv_number,
    finite_number,
    leakage_scan,
    map_family,
    mean,
    observed_id_flags,
    observed_id_guard,
    read_csv_rows,
    read_json,
    repo_root,
    resolve,
    score_from_probe,
    split_for_seed,
    write_csv_rows,
    write_json,
    write_text,
)
from repair5g518_common import (
    CandidateParams,
    G518_DECISION_SUMMARY,
    G518_FULL_PRIMARY_INTEGRITY_SUMMARY,
    G518_FULL_PRIMARY_ORACLE_SUMMARY,
    G518_SELECTED_CSV,
    candidate_params,
    family_for_candidate,
    old14_candidate_ids,
    param_distance,
    selected_rows,
)


G519_CLOSED_CLAIMS = {
    "phase5p5_allowed": False,
    "phase6_allowed": False,
    "aaai_ready": False,
    "runtime_claim_allowed": False,
    "learned_runtime_policy_validated": False,
}

RISK_LAMBDAS = [0.05, 0.10, 0.20]
PRIMARY_BUDGETS = [1000, 2000]
SEED = 20260608

G519_PLAN_MD = "czr004_repair5g519_full_primary_new_lattice_ranker_plan.md"
G519_VERIFY_SUMMARY = "outputs/reports/phase5p5_repair5g519_g518_artifact_verification_summary.json"
G519_VERIFY_REPORT = "outputs/reports/phase5p5_repair5g519_g518_artifact_verification.md"
G519_TARGETS_CSV = "outputs/tables/phase5p5_repair5g519_full_primary_candidate_targets.csv"
G519_TARGET_BUDGET_AUDIT_CSV = "outputs/tables/phase5p5_repair5g519_full_primary_candidate_budget_audit.csv"
G519_TARGETS_REPORT = "outputs/reports/phase5p5_repair5g519_full_primary_candidate_targets.md"
G519_TARGETS_SUMMARY = "outputs/reports/phase5p5_repair5g519_full_primary_candidate_targets_summary.json"
G519_CANDIDATE_DISTRIBUTION_CSV = "outputs/tables/phase5p5_repair5g519_full_primary_candidate_distribution.csv"
G519_ORACLE_BY_CONTEXT_CSV = "outputs/tables/phase5p5_repair5g519_full_primary_oracle_by_context.csv"
G519_CANDIDATE_SPACE_REPORT = "outputs/reports/phase5p5_repair5g519_full_primary_candidate_space.md"
G519_CANDIDATE_SPACE_SUMMARY = "outputs/reports/phase5p5_repair5g519_full_primary_candidate_space_summary.json"
G519_FEATURE_MATRIX_CSV = "outputs/tables/phase5p5_repair5g519_candidate_feature_matrix_v8.csv"
G519_FEATURE_MATRIX_REPORT = "outputs/reports/phase5p5_repair5g519_candidate_feature_matrix_v8.md"
G519_FEATURE_MATRIX_SUMMARY = "outputs/reports/phase5p5_repair5g519_candidate_feature_matrix_v8_summary.json"
G519_FEATURE_SIGNAL_REPORT = "outputs/reports/phase5p5_repair5g519_feature_signal_v8.md"
G519_FEATURE_SIGNAL_SUMMARY = "outputs/reports/phase5p5_repair5g519_feature_signal_v8_summary.json"
G519_MODEL_JSON = "outputs/reports/phase5p5_repair5g519_full_primary_ranker_suite_model.json"
G519_TRAIN_REPORT = "outputs/reports/phase5p5_repair5g519_full_primary_ranker_suite_train.md"
G519_TRAIN_SUMMARY = "outputs/reports/phase5p5_repair5g519_full_primary_ranker_suite_train_summary.json"
G519_EVAL_CSV = "outputs/tables/phase5p5_repair5g519_ranker_suite_eval.csv"
G519_CONTEXT_DECISIONS_CSV = "outputs/tables/phase5p5_repair5g519_ranker_context_decisions.csv"
G519_BOOTSTRAP_CSV = "outputs/tables/phase5p5_repair5g519_ranker_bootstrap.csv"
G519_CALIBRATION_CSV = "outputs/tables/phase5p5_repair5g519_ranker_calibration.csv"
G519_EVAL_REPORT = "outputs/reports/phase5p5_repair5g519_ranker_suite_eval.md"
G519_EVAL_SUMMARY = "outputs/reports/phase5p5_repair5g519_ranker_suite_eval_summary.json"
G519_AUTOPSY_REPORT = "outputs/reports/phase5p5_repair5g519_ranker_failure_autopsy.md"
G519_AUTOPSY_SUMMARY = "outputs/reports/phase5p5_repair5g519_ranker_failure_autopsy_summary.json"
G519_FAILURE_CONTEXTS_CSV = "outputs/tables/phase5p5_repair5g519_ranker_failure_contexts.csv"
G519_NEW_WIN_CONTEXTS_CSV = "outputs/tables/phase5p5_repair5g519_new_candidate_win_contexts.csv"
G519_DECISION_REPORT = "outputs/reports/phase5p5_repair5g519_decision.md"
G519_DECISION_SUMMARY = "outputs/reports/phase5p5_repair5g519_decision_summary.json"

G518_FULL_PRIMARY_RESULTS = "outputs/tables/phase5p5_repair5g518_full_primary_probe_results.csv"
G515_V5_MATRIX = "outputs/tables/phase5p5_repair5g515_candidate_feature_matrix_v5.csv"
G514_RICH_CONTEXT_FEATURES = "outputs/tables/phase5p5_repair5g514_rich_context_features_by_context.csv"


def suffix_for_lambda(lam: float) -> str:
    return f"{lam:.2f}".replace(".", "p")


def as_jsonable(value: float) -> float | None:
    return float(value) if math.isfinite(value) else None


def rows_by_context(rows: Iterable[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row.get("normalized_context_key", ""))].append(row)
    return dict(grouped)


def map_agent_key(row: dict[str, Any]) -> str:
    return f"{row.get('map', '')}|a{row.get('agents', '')}"


def map_family_key(row: dict[str, Any]) -> str:
    return map_family(str(row.get("map", "")))


def row_key(row: dict[str, Any]) -> str:
    return f"{row.get('normalized_context_key', '')}|{row.get('candidate_id', '')}"


def context_budget_key(row: dict[str, Any]) -> tuple[str, int]:
    return (str(row.get("normalized_context_key", "")), int(finite_number(row.get("short_budget_ms"), -1)))


def read_rows(path: Path | str) -> list[dict[str, Any]]:
    return read_csv_rows(resolve(path, repo_root()))


def read_json_file(path: Path | str) -> Any:
    return read_json(resolve(path, repo_root()))


def write_rows(path: Path | str, rows: Iterable[dict[str, Any]]) -> None:
    write_csv_rows(resolve(path, repo_root()), rows)


def write_json_file(path: Path | str, payload: Any) -> None:
    write_json(resolve(path, repo_root()), payload)


def write_text_file(path: Path | str, text: str) -> None:
    write_text(resolve(path, repo_root()), text)


def candidate_param_dict(candidate_id: str) -> dict[str, Any]:
    params = candidate_params(candidate_id)
    if params is None:
        return {
            "alpha_cong_committed": "",
            "alpha_cong_blocked": "",
            "alpha_flow_progress": "",
            "alpha_flow_wait_or_nonprogress": "",
            "rho_cong": "",
            "rho_flow": "",
            "flow_shield_beta": "",
            "max_flow_shield": "",
            "c_only": "",
        }
    return {
        "alpha_cong_committed": params.alpha_cong_committed,
        "alpha_cong_blocked": params.alpha_cong_blocked,
        "alpha_flow_progress": params.alpha_flow_progress,
        "alpha_flow_wait_or_nonprogress": params.alpha_flow_wait_or_nonprogress,
        "rho_cong": params.rho_cong,
        "rho_flow": params.rho_flow,
        "flow_shield_beta": params.flow_shield_beta,
        "max_flow_shield": params.max_flow_shield,
        "c_only": params.c_only,
    }


def numeric_candidate_param_dict(candidate_id: str) -> dict[str, float]:
    params = candidate_params(candidate_id)
    if params is None:
        return {
            "alpha_cong_committed": 1.0,
            "alpha_cong_blocked": 1.0,
            "alpha_flow_progress": 0.0,
            "alpha_flow_wait_or_nonprogress": 1.0,
            "rho_cong": 1.0,
            "rho_flow": 1.0,
            "flow_shield_beta": 0.0,
            "max_flow_shield": 0.0,
            "c_only": 0.0,
        }
    return {
        "alpha_cong_committed": params.alpha_cong_committed,
        "alpha_cong_blocked": params.alpha_cong_blocked,
        "alpha_flow_progress": params.alpha_flow_progress,
        "alpha_flow_wait_or_nonprogress": params.alpha_flow_wait_or_nonprogress,
        "rho_cong": params.rho_cong,
        "rho_flow": params.rho_flow,
        "flow_shield_beta": params.flow_shield_beta,
        "max_flow_shield": params.max_flow_shield,
        "c_only": 1.0 if params.c_only else 0.0,
    }


def candidate_role(candidate_id: str, old_ids: set[str], new_ids: set[str]) -> str:
    if candidate_id in old_ids:
        return "old14"
    if candidate_id in new_ids:
        return "g518_new"
    return "unknown"


def full_primary_candidate_ids(rows: list[dict[str, Any]]) -> list[str]:
    return sorted({str(row.get("candidate_id", "")) for row in rows if str(row.get("candidate_id", ""))})


def selected_new_candidate_ids_from_results(rows: list[dict[str, Any]], old_ids: set[str]) -> list[str]:
    return sorted(candidate for candidate in full_primary_candidate_ids(rows) if candidate not in old_ids)


def selected_metadata_by_candidate(rows: list[dict[str, Any]] | None = None) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in rows if rows is not None else selected_rows():
        candidate = str(row.get("candidate_id", ""))
        if candidate and candidate not in out:
            out[candidate] = row
    return out


def nearest_old_candidate(candidate_id: str, old_ids: Iterable[str]) -> tuple[str, float]:
    params = candidate_params(candidate_id)
    best = ("", math.inf)
    for old_id in old_ids:
        distance = param_distance(params, candidate_params(old_id))
        if distance < best[1] or (distance == best[1] and old_id < best[0]):
            best = (old_id, distance)
    return best


def finite_score(row: dict[str, Any] | None) -> float:
    return score_from_probe(row or {})


def best_row(rows: Iterable[dict[str, Any]]) -> dict[str, Any] | None:
    candidates = [row for row in rows if math.isfinite(finite_score(row))]
    if not candidates:
        return None
    return min(candidates, key=lambda row: (finite_score(row), str(row.get("candidate_id", ""))))


def percentile(values: Iterable[float], pct: float) -> float:
    finite = sorted(value for value in values if math.isfinite(value))
    if not finite:
        return math.inf
    if len(finite) == 1:
        return finite[0]
    index = (len(finite) - 1) * pct
    lower = int(math.floor(index))
    upper = int(math.ceil(index))
    if lower == upper:
        return finite[lower]
    return finite[lower] * (upper - index) + finite[upper] * (index - lower)


def safe_mean(values: Iterable[float]) -> float:
    return mean(values)


def policy_metric_row(policy: str, selected: list[dict[str, Any]], *, eval_scope: str) -> dict[str, Any]:
    contexts = len(selected)
    static_deltas = [finite_number(row.get("mean_delta_vs_static_primary"), math.inf) for row in selected]
    additive_deltas = [finite_number(row.get("mean_delta_vs_additive_primary"), math.inf) for row in selected]
    harmful = [1.0 if value >= DEFAULT_MARGIN else 0.0 for value in static_deltas]
    helpful = [1.0 if value <= -DEFAULT_MARGIN else 0.0 for value in static_deltas]
    coverage = [0.0 if str(row.get("candidate_id", "")) == STATIC_FLOW_SHIELD_CANDIDATE else 1.0 for row in selected]
    new_flags = [1.0 if boolish(row.get("is_new_candidate")) else 0.0 for row in selected]
    new_harmful = [
        1.0
        for row, value in zip(selected, static_deltas)
        if boolish(row.get("is_new_candidate")) and value >= DEFAULT_MARGIN
    ]
    new_helpful = [
        1.0
        for row, value in zip(selected, static_deltas)
        if boolish(row.get("is_new_candidate")) and value <= -DEFAULT_MARGIN
    ]
    old14_regrets = [finite_number(row.get("old14_oracle_regret_primary"), math.inf) for row in selected]
    new22_regrets = [finite_number(row.get("new22_oracle_regret_primary"), math.inf) for row in selected]
    old14_capture = [1.0 if boolish(row.get("is_old14_oracle_winner")) else 0.0 for row in selected]
    new22_capture = [1.0 if boolish(row.get("is_new22_oracle_winner")) else 0.0 for row in selected]
    missed_helpful = [1.0 if finite_number(row.get("new22_oracle_score_primary"), math.inf) <= finite_number(row.get("static_score_primary"), math.inf) - DEFAULT_MARGIN and finite_number(row.get("mean_delta_vs_static_primary"), math.inf) > -DEFAULT_MARGIN else 0.0 for row in selected]
    static_near_nonstatic = [1.0 if boolish(row.get("static_near_oracle")) and str(row.get("candidate_id", "")) != STATIC_FLOW_SHIELD_CANDIDATE else 0.0 for row in selected]
    row = {
        "row_type": "policy_summary",
        "eval_scope": eval_scope,
        "policy": policy,
        "contexts": contexts,
        "mean_delta_vs_static": safe_mean(static_deltas),
        "mean_delta_vs_additive": safe_mean(additive_deltas),
        "harmful_vs_static_rate": safe_mean(harmful),
        "false_positive_count": int(sum(harmful)),
        "helpful_vs_static_rate": safe_mean(helpful),
        "coverage": safe_mean(coverage),
        "fallback_rate": 1.0 - safe_mean(coverage),
        "new_candidate_selection_rate": safe_mean(new_flags),
        "new_candidate_selection_count": int(sum(new_flags)),
        "new_candidate_helpful_selection_count": int(sum(new_helpful)),
        "new_candidate_harmful_selection_count": int(sum(new_harmful)),
        "new_candidate_selection_harmful_rate": (
            len(new_harmful) / int(sum(new_flags)) if int(sum(new_flags)) else 0.0
        ),
        "oracle_capture_rate_old14": safe_mean(old14_capture),
        "oracle_capture_rate_new22": safe_mean(new22_capture),
        "regret_to_old14_oracle": safe_mean(old14_regrets),
        "regret_to_new22_oracle": safe_mean(new22_regrets),
        "missed_helpful_context_count": int(sum(missed_helpful)),
        "static_near_oracle_nonstatic_selected": int(sum(static_near_nonstatic)),
    }
    for lam in RISK_LAMBDAS:
        row[f"risk_adjusted_utility_lambda_{suffix_for_lambda(lam)}"] = (
            finite_number(row["mean_delta_vs_static"], math.inf)
            + lam * finite_number(row["harmful_vs_static_rate"], math.inf)
        )
    return row


def context_decision_row(
    policy: str,
    selected: dict[str, Any],
    *,
    eval_scope: str,
    fold_id: str = "",
    selection_reason: str = "",
    predicted_delta: Any = "",
    predicted_risk: Any = "",
    predicted_margin: Any = "",
    predicted_best_candidate_id: str = "",
) -> dict[str, Any]:
    delta = finite_number(selected.get("mean_delta_vs_static_primary"), math.inf)
    candidate = str(selected.get("candidate_id", ""))
    return {
        "row_type": "context_decision",
        "eval_scope": eval_scope,
        "fold_id": fold_id,
        "policy": policy,
        "normalized_context_key": selected.get("normalized_context_key", ""),
        "map": selected.get("map", ""),
        "agents": selected.get("agents", ""),
        "seed": selected.get("seed", ""),
        "iteration": selected.get("iteration", ""),
        "traffic_before_hash_full": selected.get("traffic_before_hash_full", ""),
        "selected_candidate_id": candidate,
        "selected_candidate_family": selected.get("candidate_family", ""),
        "selected_candidate_source": selected.get("candidate_source", ""),
        "is_new_candidate": selected.get("is_new_candidate", ""),
        "selection_reason": selection_reason,
        "predicted_delta": predicted_delta,
        "predicted_harmful_risk": predicted_risk,
        "predicted_margin": predicted_margin,
        "predicted_best_candidate_id": predicted_best_candidate_id,
        "mean_delta_vs_static": delta,
        "mean_delta_vs_additive": selected.get("mean_delta_vs_additive_primary", ""),
        "harmful_vs_static": 1.0 if delta >= DEFAULT_MARGIN else 0.0,
        "helpful_vs_static": 1.0 if delta <= -DEFAULT_MARGIN else 0.0,
        "old14_oracle_regret_primary": selected.get("old14_oracle_regret_primary", ""),
        "new22_oracle_regret_primary": selected.get("new22_oracle_regret_primary", ""),
        "oracle_candidate_old14_for_context": selected.get("oracle_candidate_old14_for_context", ""),
        "oracle_candidate_new22_for_context": selected.get("oracle_candidate_new22_for_context", ""),
        "is_old14_oracle_winner": selected.get("is_old14_oracle_winner", ""),
        "is_new22_oracle_winner": selected.get("is_new22_oracle_winner", ""),
    }


def feature_columns(rows: list[dict[str, Any]]) -> list[str]:
    return [name for name in rows[0] if name.startswith("feature_")] if rows else []


def perf_feature_columns(rows: list[dict[str, Any]]) -> list[str]:
    return [
        name
        for name in feature_columns(rows)
        if not name.startswith("feature_audit_")
        and "surrogate" not in name.lower()
        and "nearest_old" not in name.lower()
    ]


def candidate_param_feature_columns(rows: list[dict[str, Any]]) -> list[str]:
    return [name for name in perf_feature_columns(rows) if name.startswith("feature_candidate_")]


def context_feature_columns(rows: list[dict[str, Any]]) -> list[str]:
    return [
        name
        for name in perf_feature_columns(rows)
        if name.startswith("feature_map_") or name.startswith("feature_rich_")
    ]


def no_rich_feature_columns(rows: list[dict[str, Any]]) -> list[str]:
    return [
        name
        for name in perf_feature_columns(rows)
        if not name.startswith("feature_rich_")
        and not name.startswith("feature_interaction_rich_")
        and not name.startswith("feature_interaction_centered_")
    ]


def no_rich_interaction_feature_columns(rows: list[dict[str, Any]]) -> list[str]:
    return [
        name
        for name in perf_feature_columns(rows)
        if not name.startswith("feature_interaction_rich_")
        and not name.startswith("feature_interaction_centered_")
    ]


def ranker_feature_columns(rows: list[dict[str, Any]]) -> list[str]:
    return [
        name
        for name in perf_feature_columns(rows)
        if name.startswith("feature_candidate_")
        or name.startswith("feature_interaction_")
        or name.startswith("feature_centered_")
    ]


def matrix(rows: list[dict[str, Any]], features: list[str]) -> np.ndarray:
    if not features:
        return np.zeros((len(rows), 1), dtype=float)
    return np.array(
        [[finite_number(row.get(feature), 0.0) for feature in features] for row in rows],
        dtype=float,
    )


def target_array(rows: list[dict[str, Any]], field: str) -> np.ndarray:
    return np.array([finite_number(row.get(field), 0.0) for row in rows], dtype=float)


def sample_weights(rows: list[dict[str, Any]]) -> np.ndarray:
    return np.array([max(0.1, finite_number(row.get("target_weight"), 1.0)) for row in rows], dtype=float)


def fit_ridge(X: np.ndarray, y: np.ndarray, w: np.ndarray | None = None, alpha: float = 1.0) -> dict[str, Any]:
    if X.size == 0:
        return {"coef": [], "intercept": float(np.mean(y)) if y.size else 0.0}
    X_aug = np.column_stack([np.ones(X.shape[0]), X])
    if w is None:
        w = np.ones(X.shape[0], dtype=float)
    sw = np.sqrt(np.maximum(w, 0.0))
    Xw = X_aug * sw[:, None]
    yw = y * sw
    reg = np.eye(X_aug.shape[1], dtype=float) * float(alpha)
    reg[0, 0] = 0.0
    beta = np.linalg.pinv(Xw.T @ Xw + reg) @ Xw.T @ yw
    return {"intercept": float(beta[0]), "coef": [float(value) for value in beta[1:]]}


def predict_ridge(model: dict[str, Any], X: np.ndarray) -> np.ndarray:
    coef = np.array(model.get("coef", []), dtype=float)
    if X.shape[1] != len(coef):
        if len(coef) == 0:
            return np.full(X.shape[0], float(model.get("intercept", 0.0)), dtype=float)
        raise ValueError(f"feature/model width mismatch: {X.shape[1]} vs {len(coef)}")
    return float(model.get("intercept", 0.0)) + X @ coef


def random_feature_matrix(rows: list[dict[str, Any]], *, width: int = 32, seed: int = SEED) -> np.ndarray:
    rng = random.Random(seed)
    by_key = {}
    for row in rows:
        key = row_key(row)
        rng.seed(f"{seed}|{key}")
        by_key[key] = [rng.uniform(-1.0, 1.0) for _ in range(width)]
    return np.array([by_key[row_key(row)] for row in rows], dtype=float)


def select_candidate(group: list[dict[str, Any]], candidate_id: str) -> dict[str, Any]:
    by_id = {str(row.get("candidate_id", "")): row for row in group}
    return by_id.get(candidate_id) or by_id.get(STATIC_FLOW_SHIELD_CANDIDATE) or group[0]


def oracle_new22_row(group: list[dict[str, Any]]) -> dict[str, Any]:
    finite = [row for row in group if math.isfinite(finite_number(row.get("new22_oracle_regret_primary"), math.inf))]
    return min(finite or group, key=lambda row: (finite_number(row.get("new22_oracle_regret_primary"), math.inf), str(row.get("candidate_id", ""))))


def oracle_old14_row(group: list[dict[str, Any]]) -> dict[str, Any]:
    old_rows = [row for row in group if boolish(row.get("is_old14_candidate"))]
    finite = [row for row in (old_rows or group) if math.isfinite(finite_number(row.get("old14_oracle_regret_primary"), math.inf))]
    return min(finite or old_rows or group, key=lambda row: (finite_number(row.get("old14_oracle_regret_primary"), math.inf), str(row.get("candidate_id", ""))))


def selected_for_fixed(rows: list[dict[str, Any]], candidate_id: str) -> list[dict[str, Any]]:
    return [select_candidate(group, candidate_id) for _, group in sorted(rows_by_context(rows).items())]


def candidate_train_stats(rows: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row.get("candidate_id", ""))].append(row)
    out = {}
    for candidate, group in grouped.items():
        deltas = [finite_number(row.get("mean_delta_vs_static_primary"), math.inf) for row in group]
        harmful = [1.0 if value >= DEFAULT_MARGIN else 0.0 for value in deltas]
        helpful = [1.0 if value <= -DEFAULT_MARGIN else 0.0 for value in deltas]
        out[candidate] = {
            "mean_delta_vs_static": safe_mean(deltas),
            "mean_delta_vs_additive": safe_mean(finite_number(row.get("mean_delta_vs_additive_primary"), math.inf) for row in group),
            "harmful_rate": safe_mean(harmful),
            "helpful_count": float(sum(helpful)),
            "oracle_win_count": float(sum(1 for row in group if boolish(row.get("is_new22_oracle_winner")))),
            "rows": float(len(group)),
        }
    return out


def best_candidate_by_train(
    train_rows: list[dict[str, Any]],
    *,
    candidates: Iterable[str] | None = None,
    prefer_new: bool | None = None,
    metric: str = "mean_delta_vs_static",
) -> str:
    stats = candidate_train_stats(train_rows)
    allowed = set(candidates) if candidates is not None else set(stats)
    ranked = []
    for candidate, value in stats.items():
        if candidate not in allowed:
            continue
        if prefer_new is True and not any(boolish(row.get("is_new_candidate")) for row in train_rows if row.get("candidate_id") == candidate):
            continue
        if prefer_new is False and not any(boolish(row.get("is_old14_candidate")) for row in train_rows if row.get("candidate_id") == candidate):
            continue
        if metric == "oracle_wins":
            score = -value["oracle_win_count"]
        elif metric == "risk_adjusted":
            score = value["mean_delta_vs_static"] + 0.10 * value["harmful_rate"]
        else:
            score = value["mean_delta_vs_static"]
        ranked.append((score, value["harmful_rate"], candidate))
    return min(ranked)[2] if ranked else STATIC_FLOW_SHIELD_CANDIDATE


def grouped_by_map_agent_candidate(rows: list[dict[str, Any]]) -> dict[str, dict[str, dict[str, float]]]:
    grouped: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    for row in rows:
        grouped[map_agent_key(row)][str(row.get("candidate_id", ""))].append(row)
    out: dict[str, dict[str, dict[str, float]]] = {}
    for key, by_candidate in grouped.items():
        out[key] = {}
        for candidate, group in by_candidate.items():
            deltas = [finite_number(row.get("mean_delta_vs_static_primary"), math.inf) for row in group]
            out[key][candidate] = {
                "mean_delta_vs_static": safe_mean(deltas),
                "harmful_rate": safe_mean(1.0 if value >= DEFAULT_MARGIN else 0.0 for value in deltas),
                "rows": float(len(group)),
            }
    return out


def best_safe_candidate(stats: dict[str, dict[str, float]], *, allow_new: bool = True, rows: list[dict[str, Any]] | None = None) -> str:
    new_by_candidate: dict[str, bool] = {}
    if rows:
        for row in rows:
            new_by_candidate[str(row.get("candidate_id", ""))] = boolish(row.get("is_new_candidate"))
    ranked = []
    for candidate, value in stats.items():
        if not allow_new and new_by_candidate.get(candidate, False):
            continue
        if candidate == STATIC_FLOW_SHIELD_CANDIDATE:
            continue
        if value["mean_delta_vs_static"] <= -DEFAULT_MARGIN and value["harmful_rate"] <= 0.05:
            ranked.append((value["mean_delta_vs_static"] + 0.10 * value["harmful_rate"], candidate))
    return min(ranked)[1] if ranked else STATIC_FLOW_SHIELD_CANDIDATE


def bootstrap_metric_rows(policy_selected: dict[str, list[dict[str, Any]]], *, samples: int = 1000, seed: int = SEED) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    metrics = [
        "mean_delta_vs_static",
        "mean_delta_vs_additive",
        "harmful_vs_static_rate",
        "new_candidate_selection_rate",
        "regret_to_new22_oracle",
        "risk_adjusted_utility_lambda_0p05",
        "risk_adjusted_utility_lambda_0p10",
        "risk_adjusted_utility_lambda_0p20",
    ]
    out = []
    for policy, rows in sorted(policy_selected.items()):
        if not rows:
            continue
        by_metric = {metric: [] for metric in metrics}
        for _ in range(samples):
            sample = [rows[rng.randrange(len(rows))] for _ in rows]
            summary = policy_metric_row(policy, sample, eval_scope="bootstrap")
            for metric in metrics:
                by_metric[metric].append(finite_number(summary.get(metric), math.nan))
        for metric, values in by_metric.items():
            finite = sorted(value for value in values if math.isfinite(value))
            out.append(
                {
                    "row_type": "bootstrap_ci",
                    "policy": policy,
                    "metric": metric,
                    "estimate": safe_mean(values),
                    "ci_low": percentile(finite, 0.025),
                    "ci_high": percentile(finite, 0.975),
                    "samples": samples,
                }
            )
    return out


def calibration_bucket_rows(context_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    bins = [(0.0, 0.05), (0.05, 0.10), (0.10, 0.20), (0.20, 0.50), (0.50, 1.01)]
    out = []
    policies = sorted({str(row.get("policy", "")) for row in context_rows if row.get("eval_scope") == "seed_oof"})
    for policy in policies:
        rows = [row for row in context_rows if row.get("policy") == policy and row.get("eval_scope") == "seed_oof"]
        for low, high in bins:
            bucket = [
                row
                for row in rows
                if low <= max(0.0, min(1.0, finite_number(row.get("predicted_harmful_risk"), math.nan))) < high
            ]
            preds = [max(0.0, min(1.0, finite_number(row.get("predicted_harmful_risk"), math.nan))) for row in bucket]
            actual = [finite_number(row.get("harmful_vs_static"), math.nan) for row in bucket]
            out.append(
                {
                    "row_type": "risk_calibration_bucket",
                    "policy": policy,
                    "risk_bucket_low": low,
                    "risk_bucket_high": high,
                    "contexts": len(bucket),
                    "mean_predicted_harmful_risk": safe_mean(preds),
                    "actual_harmful_rate": safe_mean(actual),
                    "ece_abs_error": abs(safe_mean(preds) - safe_mean(actual)) if bucket else "",
                }
            )
    return out


def group_metric_rows(policy_selected: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    out = []
    for policy, rows in sorted(policy_selected.items()):
        for group_type in ["map_agent", "map_family", "candidate"]:
            grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
            for row in rows:
                if group_type == "map_agent":
                    key = map_agent_key(row)
                elif group_type == "map_family":
                    key = map_family_key(row)
                else:
                    key = str(row.get("candidate_id", ""))
                grouped[key].append(row)
            for key, values in sorted(grouped.items()):
                metric = policy_metric_row(policy, values, eval_scope=f"group_{group_type}")
                metric["row_type"] = "group_summary"
                metric["group_type"] = group_type
                metric["group_key"] = key
                out.append(metric)
    return out


def enforce_reserved_guard_rejects_166() -> bool:
    try:
        observed_id_guard([166], label="G5.19 reserved guard validation")
    except ValueError:
        return True
    return False


def compact_counter(rows: Iterable[dict[str, Any]], field: str) -> dict[str, int]:
    return dict(sorted(Counter(str(row.get(field, "")) for row in rows).items()))


def forbidden_feature_scan(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return leakage_scan(perf_feature_columns(rows))


__all__ = [
    "ADDITIVE_CANDIDATE",
    "DEFAULT_MARGIN",
    "G514_RICH_CONTEXT_FEATURES",
    "G515_V5_MATRIX",
    "G518_DECISION_SUMMARY",
    "G518_FULL_PRIMARY_INTEGRITY_SUMMARY",
    "G518_FULL_PRIMARY_ORACLE_SUMMARY",
    "G518_FULL_PRIMARY_RESULTS",
    "G518_SELECTED_CSV",
    "G519_AUTOPSY_REPORT",
    "G519_AUTOPSY_SUMMARY",
    "G519_BOOTSTRAP_CSV",
    "G519_CALIBRATION_CSV",
    "G519_CANDIDATE_DISTRIBUTION_CSV",
    "G519_CANDIDATE_SPACE_REPORT",
    "G519_CANDIDATE_SPACE_SUMMARY",
    "G519_CLOSED_CLAIMS",
    "G519_CONTEXT_DECISIONS_CSV",
    "G519_DECISION_REPORT",
    "G519_DECISION_SUMMARY",
    "G519_EVAL_CSV",
    "G519_EVAL_REPORT",
    "G519_EVAL_SUMMARY",
    "G519_FAILURE_CONTEXTS_CSV",
    "G519_FEATURE_MATRIX_CSV",
    "G519_FEATURE_MATRIX_REPORT",
    "G519_FEATURE_MATRIX_SUMMARY",
    "G519_FEATURE_SIGNAL_REPORT",
    "G519_FEATURE_SIGNAL_SUMMARY",
    "G519_MODEL_JSON",
    "G519_NEW_WIN_CONTEXTS_CSV",
    "G519_ORACLE_BY_CONTEXT_CSV",
    "G519_PLAN_MD",
    "G519_TARGETS_CSV",
    "G519_TARGETS_REPORT",
    "G519_TARGETS_SUMMARY",
    "G519_TARGET_BUDGET_AUDIT_CSV",
    "G519_TRAIN_REPORT",
    "G519_TRAIN_SUMMARY",
    "G519_VERIFY_REPORT",
    "G519_VERIFY_SUMMARY",
    "PRIMARY_BUDGETS",
    "RISK_LAMBDAS",
    "SEED",
    "STATIC_ABSTAIN_CANDIDATE",
    "STATIC_FLOW_SHIELD_CANDIDATE",
    "as_jsonable",
    "best_candidate_by_train",
    "best_row",
    "best_safe_candidate",
    "boolish",
    "bootstrap_metric_rows",
    "calibration_bucket_rows",
    "candidate_param_dict",
    "candidate_param_feature_columns",
    "candidate_params",
    "candidate_role",
    "candidate_train_stats",
    "compact_counter",
    "context_budget_key",
    "context_decision_row",
    "context_feature_columns",
    "csv_number",
    "enforce_reserved_guard_rejects_166",
    "family_for_candidate",
    "feature_columns",
    "finite_number",
    "finite_score",
    "forbidden_feature_scan",
    "full_primary_candidate_ids",
    "group_metric_rows",
    "grouped_by_map_agent_candidate",
    "leakage_scan",
    "map_agent_key",
    "map_family",
    "map_family_key",
    "matrix",
    "mean",
    "nearest_old_candidate",
    "no_rich_feature_columns",
    "no_rich_interaction_feature_columns",
    "numeric_candidate_param_dict",
    "observed_id_flags",
    "old14_candidate_ids",
    "oracle_new22_row",
    "oracle_old14_row",
    "perf_feature_columns",
    "policy_metric_row",
    "predict_ridge",
    "random_feature_matrix",
    "ranker_feature_columns",
    "read_json_file",
    "read_rows",
    "repo_root",
    "resolve",
    "row_key",
    "rows_by_context",
    "sample_weights",
    "score_from_probe",
    "select_candidate",
    "selected_for_fixed",
    "selected_metadata_by_candidate",
    "selected_new_candidate_ids_from_results",
    "selected_rows",
    "split_for_seed",
    "suffix_for_lambda",
    "target_array",
    "write_json_file",
    "write_rows",
    "write_text_file",
]
