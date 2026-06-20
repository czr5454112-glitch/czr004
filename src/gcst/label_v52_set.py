"""Label-v5.2 set-valued adapter for G5.63.

This module deliberately wraps the existing real Label-v5.1 rows instead of
creating a new solver label source.  The important repair is semantic: preserve
all candidate rows per MAPF context, expose positive/safe/harmful/censored sets,
and never collapse a multimodal safe set into an arithmetic average target.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np

from .real_label_graph_dataset import boolish, number, row_is_safe
from .theta_schema import BASELINE_G556, THETA_NUMERIC_COLUMNS, theta_vector_from_row


POSITIVE_SUPPORTED = "POSITIVE_SUPPORTED"
SAFE_NONIMPROVING_SUPPORTED = "SAFE_NONIMPROVING_SUPPORTED"
HARMFUL_SUPPORTED = "HARMFUL_SUPPORTED"
CENSORED_UNKNOWN = "CENSORED_UNKNOWN"
MIXED_FRONTIER = "MIXED_FRONTIER"

ROW_POSITIVE = "positive_safe_improving"
ROW_SAFE_NONIMPROVING = "safe_nonimproving"
ROW_HARMFUL_REGRESSION = "harmful_success_regression"
ROW_HARMFUL_QUALITY = "harmful_quality_loss"
ROW_CENSORED = "censored_unknown"


@dataclass(frozen=True)
class CandidateLabel:
    """One original solver outcome row with Label-v5.2 state semantics."""

    row_uid: str
    evaluation_uid: str
    theta: np.ndarray
    row_state: str
    original_row: dict[str, Any]
    quality_delta_vs_g556: float | None = None
    weight: float = 1.0

    @property
    def positive(self) -> bool:
        return self.row_state == ROW_POSITIVE

    @property
    def safe_nonimproving(self) -> bool:
        return self.row_state == ROW_SAFE_NONIMPROVING

    @property
    def harmful(self) -> bool:
        return self.row_state in {ROW_HARMFUL_REGRESSION, ROW_HARMFUL_QUALITY}

    @property
    def censored(self) -> bool:
        return self.row_state == ROW_CENSORED


@dataclass(frozen=True)
class LabelV52Context:
    """Set-valued supervision object for one independent MAPF context."""

    evaluation_uid: str
    instance_uid: str
    split: str
    physical_map_sha256: str
    map_name: str
    map_family: str
    agent_count: int
    budget_ms: int
    candidates: tuple[CandidateLabel, ...]
    label_state: str
    coverage: dict[str, Any] = field(default_factory=dict)
    noise_margin: float = 0.0

    @property
    def original_row_count(self) -> int:
        return len(self.candidates)

    @property
    def positive_candidates(self) -> tuple[CandidateLabel, ...]:
        return tuple(row for row in self.candidates if row.positive)

    @property
    def safe_nonimproving_candidates(self) -> tuple[CandidateLabel, ...]:
        return tuple(row for row in self.candidates if row.safe_nonimproving)

    @property
    def safe_candidates(self) -> tuple[CandidateLabel, ...]:
        return tuple(row for row in self.candidates if row.positive or row.safe_nonimproving)

    @property
    def harmful_candidates(self) -> tuple[CandidateLabel, ...]:
        return tuple(row for row in self.candidates if row.harmful)

    @property
    def censored_candidates(self) -> tuple[CandidateLabel, ...]:
        return tuple(row for row in self.candidates if row.censored)

    def theta_matrix(self, rows: Sequence[CandidateLabel]) -> np.ndarray:
        if not rows:
            return np.zeros((0, len(THETA_NUMERIC_COLUMNS)), dtype=np.float32)
        return np.stack([row.theta for row in rows]).astype(np.float32)

    @property
    def positive_thetas(self) -> np.ndarray:
        return self.theta_matrix(self.positive_candidates)

    @property
    def safe_thetas(self) -> np.ndarray:
        return self.theta_matrix(self.safe_candidates)

    @property
    def harmful_thetas(self) -> np.ndarray:
        return self.theta_matrix(self.harmful_candidates)

    @property
    def positive_weights(self) -> np.ndarray:
        rows = self.positive_candidates
        if not rows:
            return np.zeros((0,), dtype=np.float32)
        return np.asarray([row.weight for row in rows], dtype=np.float32)

    @property
    def harmful_weights(self) -> np.ndarray:
        rows = self.harmful_candidates
        if not rows:
            return np.zeros((0,), dtype=np.float32)
        return np.asarray([row.weight for row in rows], dtype=np.float32)

    @property
    def baseline_theta(self) -> np.ndarray:
        return BASELINE_G556.astype(np.float32)


def finite_float(value: Any, default: float = 0.0) -> float:
    try:
        out = float(value)
    except Exception:
        return default
    return out if math.isfinite(out) else default


def row_quality_delta(row: dict[str, Any]) -> float | None:
    if not boolish(row.get("labelv51_comparable_quality")):
        return None
    return finite_float(row.get("quality_delta_vs_g556"), 0.0)


def candidate_row_uid(row: dict[str, Any], ordinal: int = 0) -> str:
    explicit = (
        row.get("generated_theta_uid")
        or row.get("candidate_uid")
        or row.get("theta_uid")
        or row.get("g560_candidate_uid")
    )
    if explicit:
        return str(explicit)
    payload = {
        "evaluation_uid": row.get("g560_evaluation_uid") or row.get("evaluation_uid"),
        "ordinal": ordinal,
        "theta": [row.get(col, "") for col in THETA_NUMERIC_COLUMNS],
    }
    text = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def classify_candidate_row(row: dict[str, Any], quality_margin: float = 0.0) -> tuple[str, float | None, float]:
    """Classify one real solver row without treating censoring as negative."""

    delta = row_quality_delta(row)
    success_regression = boolish(row.get("labelv51_success_regression"))
    success_gain = boolish(row.get("labelv51_success_gain"))
    safe = row_is_safe(row)
    margin = max(0.0, float(quality_margin))

    if success_regression:
        return ROW_HARMFUL_REGRESSION, delta, 4.0
    if delta is not None and delta > margin:
        return ROW_HARMFUL_QUALITY, delta, min(4.0, 1.0 + abs(delta))
    if safe and (success_gain or (delta is not None and delta < -margin)):
        return ROW_POSITIVE, delta, min(4.0, max(0.05, 1.0 - float(delta or 0.0)))
    if safe and delta is not None:
        return ROW_SAFE_NONIMPROVING, delta, 1.0
    return ROW_CENSORED, delta, 1.0


def context_state_from_counts(
    positive_count: int,
    safe_nonimproving_count: int,
    harmful_count: int,
    censored_count: int,
    total_count: int,
    min_verified_coverage: int = 4,
) -> tuple[str, dict[str, Any]]:
    """Return the context-level Label-v5.2 state and coverage descriptors."""

    verified_no_positive = (
        total_count >= int(min_verified_coverage)
        and positive_count == 0
        and harmful_count == 0
        and censored_count == 0
        and safe_nonimproving_count > 0
    )
    if positive_count > 0 and harmful_count > 0:
        state = MIXED_FRONTIER
    elif positive_count > 0:
        state = POSITIVE_SUPPORTED
    elif harmful_count > 0:
        state = HARMFUL_SUPPORTED
    elif verified_no_positive:
        state = SAFE_NONIMPROVING_SUPPORTED
    else:
        state = CENSORED_UNKNOWN
    coverage = {
        "candidate_rows": int(total_count),
        "positive_rows": int(positive_count),
        "safe_nonimproving_rows": int(safe_nonimproving_count),
        "harmful_rows": int(harmful_count),
        "censored_rows": int(censored_count),
        "min_verified_coverage": int(min_verified_coverage),
        "verified_no_positive_requires_coverage": True,
        "verified_no_positive_supported": bool(verified_no_positive),
        "candidate_rows_count_as_independent_contexts": False,
    }
    return state, coverage


def context_from_rows(
    evaluation_uid: str,
    rows: Sequence[dict[str, Any]],
    *,
    quality_margin: float = 0.0,
    min_verified_coverage: int = 4,
) -> LabelV52Context:
    if not rows:
        raise ValueError("Label-v5.2 context requires at least one original row")
    first = dict(rows[0])
    candidates = []
    for idx, row in enumerate(rows):
        state, delta, weight = classify_candidate_row(dict(row), quality_margin=quality_margin)
        candidates.append(
            CandidateLabel(
                row_uid=candidate_row_uid(dict(row), idx),
                evaluation_uid=evaluation_uid,
                theta=theta_vector_from_row(dict(row)),
                row_state=state,
                original_row=dict(row),
                quality_delta_vs_g556=delta,
                weight=float(weight),
            )
        )
    counts = Counter(candidate.row_state for candidate in candidates)
    label_state, coverage = context_state_from_counts(
        positive_count=counts[ROW_POSITIVE],
        safe_nonimproving_count=counts[ROW_SAFE_NONIMPROVING],
        harmful_count=counts[ROW_HARMFUL_REGRESSION] + counts[ROW_HARMFUL_QUALITY],
        censored_count=counts[ROW_CENSORED],
        total_count=len(candidates),
        min_verified_coverage=min_verified_coverage,
    )
    return LabelV52Context(
        evaluation_uid=evaluation_uid,
        instance_uid=str(first.get("g560_instance_uid") or first.get("instance_uid") or ""),
        split=str(first.get("split", "unassigned")),
        physical_map_sha256=str(first.get("g560_physical_map_sha256") or first.get("physical_map_sha256") or ""),
        map_name=str(first.get("map") or first.get("map_name") or ""),
        map_family=str(first.get("map_family") or ""),
        agent_count=int(number(first.get("agent_count"), 0)),
        budget_ms=int(number(first.get("nominal_budget_ms", first.get("budget_ms")), 0)),
        candidates=tuple(candidates),
        label_state=label_state,
        coverage=coverage,
        noise_margin=float(max(0.0, quality_margin)),
    )


def contexts_from_groups(
    groups: Iterable[Any],
    *,
    quality_margin: float = 0.0,
    min_verified_coverage: int = 4,
) -> list[LabelV52Context]:
    contexts: list[LabelV52Context] = []
    for group in groups:
        evaluation_uid = str(getattr(group, "evaluation_uid", ""))
        rows = list(getattr(group, "rows", []))
        if not evaluation_uid and rows:
            evaluation_uid = str(rows[0].get("g560_evaluation_uid") or rows[0].get("evaluation_uid") or "")
        if not rows:
            continue
        contexts.append(
            context_from_rows(
                evaluation_uid,
                rows,
                quality_margin=quality_margin,
                min_verified_coverage=min_verified_coverage,
            )
        )
    return contexts


def contexts_from_csv(
    path: str | Path,
    *,
    max_contexts: int = 0,
    quality_margin: float = 0.0,
    min_verified_coverage: int = 4,
) -> list[LabelV52Context]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    with Path(path).open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            uid = row.get("g560_evaluation_uid") or row.get("evaluation_uid") or ""
            if uid:
                grouped[uid].append(dict(row))
    contexts = []
    for uid in sorted(grouped):
        contexts.append(
            context_from_rows(
                uid,
                grouped[uid],
                quality_margin=quality_margin,
                min_verified_coverage=min_verified_coverage,
            )
        )
        if max_contexts and len(contexts) >= max_contexts:
            break
    return contexts


def context_manifest_row(context: LabelV52Context) -> dict[str, Any]:
    row = {
        "evaluation_uid": context.evaluation_uid,
        "instance_uid": context.instance_uid,
        "split": context.split,
        "physical_map_sha256": context.physical_map_sha256,
        "map": context.map_name,
        "map_family": context.map_family,
        "agent_count": context.agent_count,
        "budget_ms": context.budget_ms,
        "label_state": context.label_state,
        "original_row_count": context.original_row_count,
        "positive_rows": len(context.positive_candidates),
        "safe_nonimproving_rows": len(context.safe_nonimproving_candidates),
        "safe_rows": len(context.safe_candidates),
        "harmful_rows": len(context.harmful_candidates),
        "censored_rows": len(context.censored_candidates),
        "noise_margin": context.noise_margin,
    }
    row.update(context.coverage)
    return row


def candidate_manifest_rows(context: LabelV52Context) -> list[dict[str, Any]]:
    out = []
    for candidate in context.candidates:
        row = {
            "evaluation_uid": context.evaluation_uid,
            "row_uid": candidate.row_uid,
            "row_state": candidate.row_state,
            "label_state": context.label_state,
            "quality_delta_vs_g556": "" if candidate.quality_delta_vs_g556 is None else candidate.quality_delta_vs_g556,
            "weight": candidate.weight,
            "original_row_preserved": True,
        }
        for idx, col in enumerate(THETA_NUMERIC_COLUMNS):
            row[col] = float(candidate.theta[idx])
        out.append(row)
    return out


def label_v52_summary(contexts: Sequence[LabelV52Context]) -> dict[str, Any]:
    state_counts = Counter(context.label_state for context in contexts)
    total_candidate_rows = sum(context.original_row_count for context in contexts)
    return {
        "schema_version": "label_v52_set_summary_v1",
        "contexts": len(contexts),
        "candidate_rows": total_candidate_rows,
        "candidate_rows_count_as_independent_contexts": False,
        "independent_contexts": len(contexts),
        "state_counts": dict(sorted(state_counts.items())),
        "positive_contexts": sum(len(context.positive_candidates) > 0 for context in contexts),
        "harmful_contexts": sum(len(context.harmful_candidates) > 0 for context in contexts),
        "censored_contexts": sum(len(context.censored_candidates) > 0 for context in contexts),
        "original_rows_losslessly_preserved": True,
        "positive_set_is_not_averaged": True,
        "censored_rows_are_negative": False,
        "no_positive_observed_is_automatically_noop": False,
    }


def context_dataset_sha256(contexts: Sequence[LabelV52Context]) -> str:
    payload = [context_manifest_row(context) for context in contexts]
    text = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
