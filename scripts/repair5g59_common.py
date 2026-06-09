"""Shared helpers for Repair5G.5.9 offline G6 autopsy work."""

from __future__ import annotations

import hashlib
import json
import math
import random
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

from repair5g58_common import (  # noqa: F401
    G56_ADDITIVE_CANDIDATE,
    G56_STATIC_CANDIDATE,
    G58_CLOSED_STATUS,
    count_by,
    finite_number,
    is_true,
    labels_scores_by_context_candidate,
    load_json,
    map_agent_key,
    maybe_float,
    number_or_nan,
    read_csv_rows,
    repo_root,
    resolve,
    score_from_label,
    validate_observed_rows,
    write_csv_rows,
    write_json,
    write_text,
)


G59_CLOSED_STATUS = {
    "phase5p5_allowed": False,
    "phase6_allowed": False,
    "aaai_ready": False,
    "runtime_claim_allowed": False,
}

G59_DEFAULT_MARGIN = 0.005
G59_THRESHOLDS = [0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90]
G59_METADATA_COLUMNS = {
    "context_id",
    "normalized_context_key",
    "map",
    "agents",
    "seed",
    "iteration",
    "traffic_before_hash_full",
    "margin_threshold",
    "label_class",
    "target_candidate_id",
    "training_eligible",
    "train_weight",
    "stable_static_or_abstain",
}
G59_REQUIRED_G58_ARTIFACTS = [
    "deep-research-report.md",
    "phase4_6_laur_ltm_codex_execution_plan.md",
    "docs/aaai_quality_requirements.md",
    "czr004_repair5g58_targeted_confidence_expansion_offline_g6_plan.md",
    "outputs/reports/phase5p5_repair5g58_protocol_overview.md",
    "outputs/reports/phase5p5_repair5g58_decision.md",
    "outputs/reports/phase5p5_repair5g58_decision_summary.json",
    "outputs/reports/phase5p5_repair5g58_primary_pair_confidence_expansion_summary.json",
    "outputs/reports/phase5p5_repair5g58_confidence_weighted_targets_summary.json",
    "outputs/reports/phase5p5_repair5g58_training_label_threshold_decision_summary.json",
    "outputs/reports/phase5p5_repair5g58_warehouse_abstention_policy_summary.json",
    "outputs/reports/phase5p5_repair5g58_g6_feature_matrix_summary.json",
    "outputs/reports/phase5p5_repair5g58_offline_safe_mixture_train_summary.json",
    "outputs/reports/phase5p5_repair5g58_offline_safe_mixture_eval_summary.json",
    "outputs/tables/phase5p5_repair5g58_confidence_weighted_targets.csv",
    "outputs/tables/phase5p5_repair5g58_g6_features_perf_safe.csv",
    "outputs/tables/phase5p5_repair5g58_offline_safe_mixture_eval.csv",
    "outputs/tables/phase5p5_repair5g56_counterfactual_update_labels.csv",
    "scripts/repair5g58_common.py",
    "scripts/train_repair5g58_offline_safe_mixture.py",
    "scripts/eval_repair5g58_offline_safe_mixture.py",
]


def missing_required_g58_artifacts(root: Path) -> list[str]:
    return [path for path in G59_REQUIRED_G58_ARTIFACTS if not (root / path).exists()]


def seed_value(row: dict[str, Any]) -> int:
    try:
        return int(float(row.get("seed") or 0))
    except (TypeError, ValueError):
        return 0


def row_split(row: dict[str, Any]) -> str:
    return "train" if seed_value(row) <= 150 else "dev"


def context_id(row: dict[str, Any]) -> str:
    return str(row.get("context_id") or "")


def context_key(row: dict[str, Any]) -> str:
    return str(row.get("normalized_context_key") or context_id(row))


def mean(values: Iterable[float]) -> float:
    finite = [value for value in values if math.isfinite(value)]
    return sum(finite) / len(finite) if finite else math.inf


def quantiles(values: Iterable[float]) -> dict[str, float | None]:
    finite = sorted(value for value in values if math.isfinite(value))
    if not finite:
        return {"min": None, "p25": None, "median": None, "p75": None, "max": None}

    def pick(frac: float) -> float:
        index = min(len(finite) - 1, max(0, round((len(finite) - 1) * frac)))
        return finite[index]

    return {
        "min": finite[0],
        "p25": pick(0.25),
        "median": pick(0.50),
        "p75": pick(0.75),
        "max": finite[-1],
    }


def as_jsonable(value: float) -> float | None:
    return value if math.isfinite(value) else None


def feature_names_from_summary(summary: dict[str, Any], rows: list[dict[str, Any]]) -> list[str]:
    names = [str(name) for name in summary.get("perf_safe_features", [])]
    if names:
        return names
    return sorted(key for key in {name for row in rows for name in row} if key not in G59_METADATA_COLUMNS)


def default_threshold_targets(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        row
        for row in rows
        if abs(finite_number(row.get("margin_threshold"), math.nan) - G59_DEFAULT_MARGIN) < 1.0e-12
    ]


def training_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [row for row in rows if is_true(row.get("training_eligible"))]


def target_classes(rows: list[dict[str, Any]]) -> list[str]:
    return sorted({str(row.get("target_candidate_id", "")) for row in rows if row.get("target_candidate_id")})


def stable_nonstatic_candidate(rows: list[dict[str, Any]]) -> str:
    counts: dict[str, int] = defaultdict(int)
    for row in rows:
        if row.get("label_class") == "stable_high_confidence_nonstatic":
            counts[str(row.get("target_candidate_id", ""))] += 1
    if not counts:
        return ""
    return max(counts, key=counts.get)


def train_only_majority(rows: list[dict[str, Any]]) -> str:
    counts: dict[str, int] = defaultdict(int)
    for row in rows:
        if row_split(row) == "train" and is_true(row.get("training_eligible")):
            counts[str(row.get("target_candidate_id", ""))] += 1
    return max(counts, key=counts.get) if counts else G56_STATIC_CANDIDATE


def train_only_map_agent_prior(rows: list[dict[str, Any]]) -> dict[str, str]:
    counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for row in rows:
        if row_split(row) != "train" or not is_true(row.get("training_eligible")):
            continue
        key = map_agent_key(row)
        counts[key][str(row.get("target_candidate_id", ""))] += 1
    return {key: max(values, key=values.get) for key, values in counts.items()}


def score_table_from_labels(rows: list[dict[str, Any]], *, budget_ms: float = 1000.0) -> dict[str, dict[str, float]]:
    selected = [
        row
        for row in rows
        if abs(finite_number(row.get("short_budget_ms"), math.nan) - budget_ms) < 1.0e-12
    ]
    return labels_scores_by_context_candidate(selected)


def candidate_score(scores: dict[str, float], candidate: str, fallback: float = math.inf) -> float:
    value = scores.get(candidate, fallback)
    return value if math.isfinite(value) else fallback


def oracle_score(scores: dict[str, float], candidates: Iterable[str] | None = None) -> tuple[str, float]:
    items = [(candidate, score) for candidate, score in scores.items() if math.isfinite(score)]
    if candidates is not None:
        allowed = set(candidates)
        items = [(candidate, score) for candidate, score in items if candidate in allowed]
    if not items:
        return "", math.inf
    return min(items, key=lambda item: (item[1], item[0]))


def deterministic_random_values(row: dict[str, Any], count: int, *, salt: str) -> list[float]:
    seed_text = f"{context_id(row)}|{salt}"
    digest = hashlib.sha256(seed_text.encode("utf-8")).hexdigest()
    seed = int(digest[:16], 16)
    rng = random.Random(seed)
    return [rng.uniform(-1.0, 1.0) for _ in range(count)]


def row_vector(row: dict[str, Any], feature_names: list[str], *, random_features: bool = False, salt: str = "") -> list[float]:
    if random_features:
        return deterministic_random_values(row, len(feature_names), salt=salt or "repair5g59_random_features")
    return [finite_number(row.get(name), 0.0) for name in feature_names]


def train_normalizer(rows: list[dict[str, Any]], feature_names: list[str], *, random_features: bool = False, salt: str = "") -> tuple[list[float], list[float]]:
    vectors = [row_vector(row, feature_names, random_features=random_features, salt=salt) for row in rows]
    if not vectors:
        return [0.0 for _ in feature_names], [1.0 for _ in feature_names]
    means = [sum(col) / len(col) for col in zip(*vectors)]
    stds = []
    for index, value in enumerate(means):
        var = sum((vector[index] - value) ** 2 for vector in vectors) / max(1, len(vectors))
        stds.append(math.sqrt(var) or 1.0)
    return means, stds


def normalized_vector(
    row: dict[str, Any],
    feature_names: list[str],
    means: list[float],
    stds: list[float],
    *,
    random_features: bool = False,
    salt: str = "",
) -> list[float]:
    raw = row_vector(row, feature_names, random_features=random_features, salt=salt)
    return [
        (raw[index] - means[index]) / (stds[index] or 1.0)
        for index in range(len(feature_names))
    ]


def softmax(logits: list[float]) -> list[float]:
    if not logits:
        return []
    top = max(logits)
    exps = [math.exp(value - top) for value in logits]
    total = sum(exps) or 1.0
    return [value / total for value in exps]


def train_multinomial_model(
    rows: list[dict[str, Any]],
    feature_names: list[str],
    classes: list[str],
    *,
    label_field: str,
    seed: int,
    epochs: int = 220,
    learning_rate: float = 0.035,
    random_features: bool = False,
    salt: str = "",
    labels_override: list[str] | None = None,
) -> dict[str, Any]:
    rng = random.Random(seed)
    if not rows or not feature_names or not classes:
        return {
            "model_type": "empty_multinomial_logistic",
            "feature_names": feature_names,
            "classes": classes,
            "means": [],
            "stds": [],
            "weights": [],
            "biases": [],
            "random_features": random_features,
            "salt": salt,
        }
    means, stds = train_normalizer(rows, feature_names, random_features=random_features, salt=salt)
    class_index = {name: index for index, name in enumerate(classes)}
    weights = [[0.0 for _name in feature_names] for _class in classes]
    biases = [0.0 for _class in classes]
    labels = labels_override or [str(row.get(label_field, "")) for row in rows]
    samples = list(zip(rows, labels))
    for _epoch in range(epochs):
        rng.shuffle(samples)
        for row, label in samples:
            if label not in class_index:
                continue
            x = normalized_vector(row, feature_names, means, stds, random_features=random_features, salt=salt)
            logits = [
                biases[c] + sum(weights[c][j] * x[j] for j in range(len(x)))
                for c in range(len(classes))
            ]
            probs = softmax(logits)
            gold = class_index[label]
            row_weight = finite_number(row.get("train_weight"), 1.0)
            for c in range(len(classes)):
                grad = (probs[c] - (1.0 if c == gold else 0.0)) * row_weight
                biases[c] -= learning_rate * grad
                for j in range(len(x)):
                    weights[c][j] -= learning_rate * grad * x[j]
    return {
        "model_type": "multinomial_logistic_regression_sgd",
        "feature_names": feature_names,
        "classes": classes,
        "means": means,
        "stds": stds,
        "weights": weights,
        "biases": biases,
        "random_features": random_features,
        "salt": salt,
        "normalization": "train_rows_only",
    }


def predict_model(model: dict[str, Any], row: dict[str, Any]) -> tuple[str, float]:
    classes = [str(item) for item in model.get("classes", [])]
    feature_names = [str(item) for item in model.get("feature_names", [])]
    if not classes or not feature_names:
        return G56_STATIC_CANDIDATE, 0.0
    means = [float(value) for value in model.get("means", [])]
    stds = [float(value) for value in model.get("stds", [])]
    weights = [[float(value) for value in row_values] for row_values in model.get("weights", [])]
    biases = [float(value) for value in model.get("biases", [])]
    x = normalized_vector(
        row,
        feature_names,
        means,
        stds,
        random_features=bool(model.get("random_features")),
        salt=str(model.get("salt", "")),
    )
    logits = [
        biases[c] + sum(weights[c][j] * x[j] for j in range(len(x)))
        for c in range(len(classes))
    ]
    probs = softmax(logits)
    best = max(range(len(classes)), key=lambda index: probs[index])
    return classes[best], probs[best]


def metric_summary(rows: list[dict[str, Any]], *, harmful_margin: float = G59_DEFAULT_MARGIN) -> dict[str, Any]:
    selected_scores = [finite_number(row.get("selected_score"), math.inf) for row in rows]
    static_scores = [finite_number(row.get("static_score"), math.inf) for row in rows]
    additive_scores = [finite_number(row.get("additive_score"), math.inf) for row in rows]
    oracle_scores = [finite_number(row.get("oracle_score"), math.inf) for row in rows]
    mean_selected = mean(selected_scores)
    mean_static = mean(static_scores)
    mean_additive = mean(additive_scores)
    mean_oracle = mean(oracle_scores)
    harmful = [
        row
        for row in rows
        if finite_number(row.get("selected_score"), math.inf) > finite_number(row.get("static_score"), math.inf) + harmful_margin
    ]
    helpful = [
        row
        for row in rows
        if finite_number(row.get("selected_score"), math.inf) < finite_number(row.get("static_score"), math.inf) - harmful_margin
    ]
    nonstatic = [row for row in rows if str(row.get("selected_candidate_id", "")) != G56_STATIC_CANDIDATE]
    return {
        "rows": len(rows),
        "mean_selected_score": as_jsonable(mean_selected),
        "mean_static_score": as_jsonable(mean_static),
        "mean_additive_score": as_jsonable(mean_additive),
        "mean_oracle_score": as_jsonable(mean_oracle),
        "mean_delta_vs_static": as_jsonable(mean_selected - mean_static if math.isfinite(mean_selected) and math.isfinite(mean_static) else math.inf),
        "mean_delta_vs_additive": as_jsonable(mean_selected - mean_additive if math.isfinite(mean_selected) and math.isfinite(mean_additive) else math.inf),
        "oracle_regret": as_jsonable(mean_selected - mean_oracle if math.isfinite(mean_selected) and math.isfinite(mean_oracle) else math.inf),
        "harmful_vs_static_count": len(harmful),
        "harmful_vs_static_rate": len(harmful) / len(rows) if rows else None,
        "helpful_vs_static_count": len(helpful),
        "helpful_vs_static_rate": len(helpful) / len(rows) if rows else None,
        "nonstatic_selection_rate": len(nonstatic) / len(rows) if rows else None,
    }


def calibration_bins(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    bins = [
        ("lt_0p50", 0.0, 0.50),
        ("0p50_0p75", 0.50, 0.75),
        ("0p75_0p90", 0.75, 0.90),
        ("ge_0p90", 0.90, 1.01),
    ]
    out = []
    for name, low, high in bins:
        selected = [
            row
            for row in rows
            if low <= finite_number(row.get("confidence"), math.nan) < high
        ]
        correct = [
            row
            for row in selected
            if str(row.get("selected_candidate_id", "")) == str(row.get("target_candidate_id", ""))
        ]
        out.append(
            {
                "bin": name,
                "low": low,
                "high": high,
                "count": len(selected),
                "accuracy": len(correct) / len(selected) if selected else "",
            }
        )
    return out


def write_simple_report(path: Path, title: str, bullets: list[tuple[str, Any]], body: str = "") -> None:
    lines = [f"# {title}", ""]
    for key, value in bullets:
        lines.append(f"- {key}: `{value}`")
    if body:
        lines.extend(["", body.strip(), ""])
    write_text(path, "\n".join(lines).rstrip() + "\n")


__all__ = [
    "G56_ADDITIVE_CANDIDATE",
    "G56_STATIC_CANDIDATE",
    "G59_CLOSED_STATUS",
    "G59_DEFAULT_MARGIN",
    "G59_METADATA_COLUMNS",
    "G59_REQUIRED_G58_ARTIFACTS",
    "G59_THRESHOLDS",
    "as_jsonable",
    "calibration_bins",
    "candidate_score",
    "context_id",
    "context_key",
    "count_by",
    "default_threshold_targets",
    "feature_names_from_summary",
    "finite_number",
    "is_true",
    "load_json",
    "map_agent_key",
    "mean",
    "metric_summary",
    "missing_required_g58_artifacts",
    "oracle_score",
    "predict_model",
    "quantiles",
    "read_csv_rows",
    "repo_root",
    "resolve",
    "row_split",
    "score_table_from_labels",
    "seed_value",
    "stable_nonstatic_candidate",
    "target_classes",
    "train_multinomial_model",
    "train_only_majority",
    "train_only_map_agent_prior",
    "training_rows",
    "validate_observed_rows",
    "write_csv_rows",
    "write_json",
    "write_simple_report",
    "write_text",
]
