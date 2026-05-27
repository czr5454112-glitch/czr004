"""Token and rule features for Phase4F Repair2 LAU-LTM samples."""

from __future__ import annotations

import math
from collections import Counter
from pathlib import Path
from typing import Any

from czr004_teacher.features_laur import MapTopology
from models.laur_ltm import DEFAULT_RULE_PARAMS


TOKEN_DATASET_SCHEMA_VERSION = "phase4_laur_update_dataset_v2"
TOKEN_FEATURE_SET = "token_rule_context_v2"

EXECUTABLE_RULE_IDS = [
    "additive_ltm",
    "commit_heavy",
    "block_heavy",
    "block_light",
    "wait_light",
    "wait_heavy",
    "decay_095",
    "decay_090",
]

ORIGINAL_EXTRA_RULE_IDS = ["neutral_additive"]

RULE_FAMILY_IDS = ["additive", "commit", "block", "wait", "decay"]
RULE_FAMILY_BY_RULE = {
    "additive_ltm": "additive",
    "neutral_additive": "additive",
    "commit_heavy": "commit",
    "block_heavy": "block",
    "block_light": "block",
    "wait_light": "wait",
    "wait_heavy": "wait",
    "decay_095": "decay",
    "decay_090": "decay",
}

EDGE_FEATURE_NAMES = [
    "from_id_norm",
    "to_id_norm",
    "raw_before",
    "raw_after",
    "raw_delta",
    "normalized_after",
    "source_degree",
    "target_degree",
    "is_wait_edge",
    "is_new_edge",
    "rank_fraction",
    "after_raw_share",
]

TRACE_FEATURE_NAMES = [
    "kind_committed",
    "kind_blocked",
    "kind_wait",
    "kind_goal_wait",
    "event_count",
    "event_count_per_agent",
    "event_ratio",
    "unique_edge_count",
    "topk_overlap_count",
    "topk_overlap_ratio",
    "iteration_norm",
    "is_fallback_count_token",
]

RULE_PARAM_NAMES = [
    "alpha_commit",
    "alpha_block",
    "alpha_wait",
    "rho_decay",
    "saturation_scale",
    "contraflow_penalty",
    "force_additive",
]

RULE_FEATURE_NAMES = [
    "family_additive",
    "family_commit",
    "family_block",
    "family_wait",
    "family_decay",
    *RULE_PARAM_NAMES,
    "commit_minus_base",
    "block_minus_base",
    "wait_minus_base",
    "decay_minus_base",
]


def finite_float(value: Any, default: float = 0.0) -> float:
    if isinstance(value, bool):
        return default
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


def safe_ratio(numerator: float, denominator: float) -> float:
    return float(numerator) / float(denominator) if denominator else 0.0


def executable_rule_id(rule_id: str | None) -> str:
    value = str(rule_id or "")
    if value == "neutral_additive":
        return "additive_ltm"
    if value in EXECUTABLE_RULE_IDS:
        return value
    return "additive_ltm"


def rule_family(rule_id: str | None) -> str:
    return RULE_FAMILY_BY_RULE.get(str(rule_id or ""), "additive")


def rule_family_index(rule_id: str | None) -> int:
    return RULE_FAMILY_IDS.index(rule_family(rule_id))


def rule_param_value(value: Any) -> float:
    if value is True:
        return 1.0
    if value is False:
        return 0.0
    return finite_float(value)


def rule_feature_vector(rule_id: str) -> list[float]:
    family = rule_family(rule_id)
    params = DEFAULT_RULE_PARAMS.get(rule_id, DEFAULT_RULE_PARAMS["additive_ltm"])
    param_values = [rule_param_value(params.get(name, 0.0)) for name in RULE_PARAM_NAMES]
    alpha_commit = param_values[RULE_PARAM_NAMES.index("alpha_commit")]
    alpha_block = param_values[RULE_PARAM_NAMES.index("alpha_block")]
    alpha_wait = param_values[RULE_PARAM_NAMES.index("alpha_wait")]
    rho_decay = param_values[RULE_PARAM_NAMES.index("rho_decay")]
    return [
        *[1.0 if family == candidate else 0.0 for candidate in RULE_FAMILY_IDS],
        *param_values,
        alpha_commit - 1.0,
        alpha_block - 1.0,
        alpha_wait - 1.0,
        rho_decay - 1.0,
    ]


def build_rule_tokens(rule_ids: list[str] | None = None) -> list[list[float]]:
    return [rule_feature_vector(rule_id) for rule_id in (rule_ids or EXECUTABLE_RULE_IDS)]


def _edge_key(edge: dict[str, Any]) -> tuple[int, int]:
    return int(edge.get("from_id", -1)), int(edge.get("to_id", -1))


def _edge_raw_lookup(edges: list[dict[str, Any]]) -> dict[tuple[int, int], float]:
    return {_edge_key(edge): finite_float(edge.get("raw")) for edge in edges}


def _edge_weight_lookup(edges: list[dict[str, Any]]) -> dict[tuple[int, int], float]:
    lookup: dict[tuple[int, int], float] = {}
    for edge in edges:
        key = _edge_key(edge)
        lookup[key] = finite_float(edge.get("weight", edge.get("raw")))
    return lookup


def _vertex_norm(vertex_id: int, free_cells: int) -> float:
    return safe_ratio(float(vertex_id), float(max(1, free_cells - 1)))


def local_map_path(checkpoint_row: dict[str, Any], repo_root: str | Path | None = None) -> Path | None:
    value = checkpoint_row.get("map_path") or checkpoint_row.get("map")
    if not value:
        return None
    path = Path(str(value))
    if path.exists():
        return path
    root = Path(repo_root) if repo_root is not None else Path.cwd()
    if not path.is_absolute() and (root / path).exists():
        return root / path
    fallback = root / "external" / "lacam2" / "scripts" / "map" / path.name
    if fallback.exists():
        return fallback
    return None


def topology_for_token_features(
    checkpoint_row: dict[str, Any],
    cache: dict[Path, MapTopology],
    repo_root: str | Path | None = None,
) -> MapTopology | None:
    path = local_map_path(checkpoint_row, repo_root=repo_root)
    if path is None:
        return None
    resolved = path.resolve()
    if resolved not in cache:
        cache[resolved] = MapTopology(resolved)
    return cache[resolved]


def build_edge_tokens(
    checkpoint_row: dict[str, Any],
    *,
    max_edge_tokens: int = 64,
    topology: MapTopology | None = None,
) -> list[list[float]]:
    raw_before = list(checkpoint_row.get("raw_before_topk", []))
    raw_after = list(checkpoint_row.get("raw_after_topk", []))
    normalized_after = list(checkpoint_row.get("normalized_after_topk", []))
    before_by_edge = _edge_raw_lookup(raw_before)
    after_by_edge = _edge_raw_lookup(raw_after)
    weight_by_edge = _edge_weight_lookup(normalized_after)
    edge_keys = sorted(
        set(before_by_edge) | set(after_by_edge) | set(weight_by_edge),
        key=lambda key: (
            after_by_edge.get(key, 0.0),
            weight_by_edge.get(key, 0.0),
            before_by_edge.get(key, 0.0),
            -key[0],
            -key[1],
        ),
        reverse=True,
    )
    total_after_raw = sum(max(0.0, value) for value in after_by_edge.values())
    free_cells = int(topology.free_cells) if topology is not None else int(
        checkpoint_row.get("traffic_after_nonzero_edges", 0) or 1
    )
    tokens: list[list[float]] = []
    limit = max(0, int(max_edge_tokens))
    for rank, (from_id, to_id) in enumerate(edge_keys[:limit]):
        before = before_by_edge.get((from_id, to_id), 0.0)
        after = after_by_edge.get((from_id, to_id), 0.0)
        weight = weight_by_edge.get((from_id, to_id), 0.0)
        source_degree = float(topology.degree(from_id)) if topology is not None else 0.0
        target_degree = float(topology.degree(to_id)) if topology is not None else 0.0
        tokens.append(
            [
                _vertex_norm(from_id, free_cells),
                _vertex_norm(to_id, free_cells),
                before,
                after,
                after - before,
                weight,
                source_degree,
                target_degree,
                1.0 if from_id == to_id else 0.0,
                1.0 if before <= 0.0 and after > 0.0 else 0.0,
                safe_ratio(float(rank), float(max(1, limit - 1))),
                safe_ratio(max(0.0, after), total_after_raw),
            ]
        )
    return tokens


def build_trace_count_tokens(
    checkpoint_row: dict[str, Any],
    trace_rows: list[dict[str, Any]] | None = None,
    *,
    max_trace_tokens: int = 64,
) -> list[list[float]]:
    agents = float(max(1, int(checkpoint_row.get("agents", 0) or 1)))
    max_iterations = float(max(1, int(checkpoint_row.get("max_iterations", 0) or 1)))
    iteration_norm = safe_ratio(float(checkpoint_row.get("iteration", 0)), max_iterations)
    topk_overlap = float(checkpoint_row.get("topk_blocked_edge_count", 0) or 0)
    unique_edges = float(checkpoint_row.get("blocked_unique_edge_count", 0) or 0)
    counts = {
        "committed": float(checkpoint_row.get("committed_count", 0) or 0),
        "blocked": float(checkpoint_row.get("blocked_count", 0) or 0),
        "wait": float(checkpoint_row.get("wait_event_count", 0) or 0),
        "goal_wait": float(checkpoint_row.get("goal_wait_ignored_count", 0) or 0),
    }

    if trace_rows:
        rows = trace_rows[: max(0, int(max_trace_tokens))]
        total = float(max(1, len(trace_rows)))
        tokens: list[list[float]] = []
        seen_edges = Counter((int(row.get("from_id", -1)), int(row.get("to_id", -1))) for row in trace_rows)
        for row in rows:
            kind = str(row.get("kind", ""))
            is_goal_wait = bool(row.get("is_wait")) and bool(row.get("at_goal"))
            edge_count = float(seen_edges[(int(row.get("from_id", -1)), int(row.get("to_id", -1)))])
            tokens.append(
                [
                    1.0 if kind == "committed" else 0.0,
                    1.0 if kind == "blocked" else 0.0,
                    1.0 if bool(row.get("is_wait")) and not is_goal_wait else 0.0,
                    1.0 if is_goal_wait else 0.0,
                    1.0,
                    safe_ratio(1.0, agents),
                    safe_ratio(1.0, total),
                    edge_count,
                    0.0,
                    0.0,
                    iteration_norm,
                    0.0,
                ]
            )
        return tokens

    total_count = max(1.0, sum(counts.values()))
    kind_order = ["committed", "blocked", "wait", "goal_wait"]
    tokens = []
    for name in kind_order:
        value = counts[name]
        if value <= 0.0:
            continue
        tokens.append(
            [
                1.0 if name == "committed" else 0.0,
                1.0 if name == "blocked" else 0.0,
                1.0 if name == "wait" else 0.0,
                1.0 if name == "goal_wait" else 0.0,
                value,
                safe_ratio(value, agents),
                safe_ratio(value, total_count),
                unique_edges if name == "blocked" else 0.0,
                topk_overlap if name == "blocked" else 0.0,
                safe_ratio(topk_overlap, value) if name == "blocked" else 0.0,
                iteration_norm,
                1.0,
            ]
        )
    return tokens[: max(0, int(max_trace_tokens))]


def stable_softmax(scores: list[float], temperature: float) -> list[float]:
    temp = max(float(temperature), 1e-12)
    finite = [score for score in scores if math.isfinite(score)]
    if not finite:
        return [1.0 / len(scores) for _ in scores] if scores else []
    pivot = max(finite)
    weights = [math.exp((score - pivot) / temp) if math.isfinite(score) else 0.0 for score in scores]
    total = sum(weights)
    return [weight / total if total else 0.0 for weight in weights]


def mixed_soft_rule_target(
    scores: list[float],
    *,
    hard_index: int,
    temperature: float = 0.01,
    hard_mix: float = 0.5,
) -> list[float]:
    mix = min(1.0, max(0.0, float(hard_mix)))
    soft = stable_softmax(scores, temperature)
    hard = [0.0] * len(scores)
    if 0 <= int(hard_index) < len(hard):
        hard[int(hard_index)] = 1.0
    return [mix * hard_value + (1.0 - mix) * soft_value for hard_value, soft_value in zip(hard, soft)]
