"""Token builders for LAU-StableAttention-v1 datasets."""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from typing import Any

from czr004_teacher.token_features_laur import (
    EXECUTABLE_RULE_IDS,
    RULE_FAMILY_BY_RULE,
    RULE_FAMILY_IDS,
    finite_float,
    safe_ratio,
    stable_softmax,
)
from czr004_teacher.topology_features_laur import TokenMapTopology
from models.laur_ltm import DEFAULT_RULE_PARAMS


STABLE_ATTENTION_DATASET_SCHEMA_VERSION = "phase4_laur_stable_attention_dataset_v1"
STABLE_ATTENTION_FEATURE_SET = "stable_attention_tokens_v1"
MODEL_FAMILY_NAME = "LAU-StableAttention-v1"
SET_RULE_TRANSFORMER_NAME = "LAU-SetRuleTransformer-v1"
EDGE_TRACE_TRANSFORMER_NAME = "LAU-EdgeTraceTransformer-v3"

GLOBAL_FEATURE_NAMES = [
    "agents",
    "density",
    "map_width",
    "map_height",
    "obstacle_ratio",
    "iteration",
    "has_incumbent_before_update",
    "best_ratio_before_update",
    "ratio_this_iteration",
    "improved_this_iteration",
    "returned_solutions_count_so_far",
    "time_to_first_solution_ms_or_minus1",
    "committed_count",
    "blocked_count",
    "wait_event_count",
    "goal_wait_ignored_count",
    "blocked_per_committed",
    "wait_per_committed",
    "traffic_before_nonzero_edges",
    "traffic_before_max_raw",
    "traffic_before_entropy",
    "traffic_after_additive_estimated_entropy",
]

EDGE_FEATURE_NAMES = [
    "from_id_hash",
    "to_id_hash",
    "from_x_norm",
    "from_y_norm",
    "to_x_norm",
    "to_y_norm",
    "direction_left",
    "direction_right",
    "direction_up",
    "direction_down",
    "direction_wait",
    "from_degree",
    "to_degree",
    "is_reverse_of_top_edge",
    "raw_before",
    "normalized_before",
    "committed_count_on_edge",
    "blocked_count_on_edge",
    "wait_spillover_count_on_edge",
    "blocked_minus_committed",
    "blocked_per_committed_edge",
    "additive_delta_raw",
    "would_decay_095_delta",
    "would_decay_090_delta",
    "local_corridor_score",
    "local_intersection_score",
    "local_obstacle_boundary_score",
]

TRACE_FEATURE_NAMES = [
    "edge_index_within_topk_or_neg1",
    "kind_committed",
    "kind_blocked",
    "is_wait",
    "at_goal",
    "count",
    "first_event_index_bucket",
    "last_event_index_bucket",
    "agent_count_unique_on_edge",
]

RULE_FEATURE_NAMES = [
    "alpha_commit",
    "alpha_block",
    "alpha_wait",
    "rho_decay",
    "saturation_scale",
    "contraflow_penalty",
    "is_additive",
    "is_commit_rule",
    "is_block_rule",
    "is_wait_rule",
    "is_decay_rule",
    "rule_family_id_norm",
]


def finite(value: Any, default: float = 0.0) -> float:
    return finite_float(value, default)


def entropy(values: list[float]) -> float:
    positive = [float(value) for value in values if float(value) > 0.0]
    total = sum(positive)
    if total <= 0.0:
        return 0.0
    return -sum((value / total) * math.log(value / total) for value in positive)


def executable_rule_id(rule_id: str | None) -> str:
    value = str(rule_id or "")
    if value == "neutral_additive":
        return "additive_ltm"
    return value if value in EXECUTABLE_RULE_IDS else "additive_ltm"


def rule_family(rule_id: str | None) -> str:
    return RULE_FAMILY_BY_RULE.get(str(rule_id or ""), "additive")


def rule_family_index(rule_id: str | None) -> int:
    return RULE_FAMILY_IDS.index(rule_family(rule_id))


def _edge_key(edge: dict[str, Any]) -> tuple[int, int]:
    return int(edge.get("from_id", -1)), int(edge.get("to_id", -1))


def _edge_raw_lookup(edges: list[dict[str, Any]], *, value_key: str = "raw") -> dict[tuple[int, int], float]:
    return {_edge_key(edge): finite(edge.get(value_key, edge.get("raw"))) for edge in edges}


def _hash_id(vertex_id: int) -> float:
    value = (int(vertex_id) * 2654435761) & 0xFFFFFFFF
    return float(value) / 4294967295.0


def _coord_norm(
    vertex_id: int,
    topology: TokenMapTopology | None,
) -> tuple[float, float]:
    if topology is None:
        return 0.0, 0.0
    coord = topology.coord(vertex_id)
    if coord is None:
        return 0.0, 0.0
    x, y = coord
    return safe_ratio(float(x), float(max(1, topology.width - 1))), safe_ratio(
        float(y), float(max(1, topology.height - 1))
    )


def _direction_onehot(
    from_id: int,
    to_id: int,
    topology: TokenMapTopology | None,
) -> list[float]:
    if from_id == to_id:
        return [0.0, 0.0, 0.0, 0.0, 1.0]
    if topology is None:
        return [0.0, 0.0, 0.0, 0.0, 0.0]
    src = topology.coord(from_id)
    dst = topology.coord(to_id)
    if src is None or dst is None:
        return [0.0, 0.0, 0.0, 0.0, 0.0]
    dx = dst[0] - src[0]
    dy = dst[1] - src[1]
    return [
        1.0 if dx < 0 else 0.0,
        1.0 if dx > 0 else 0.0,
        1.0 if dy < 0 else 0.0,
        1.0 if dy > 0 else 0.0,
        0.0,
    ]


def _edge_event_counts(trace_rows: list[dict[str, Any]] | None) -> dict[tuple[int, int], Counter[str]]:
    counts: dict[tuple[int, int], Counter[str]] = defaultdict(Counter)
    for row in trace_rows or []:
        key = (int(row.get("from_id", -1)), int(row.get("to_id", -1)))
        if str(row.get("kind")) == "committed":
            counts[key]["committed"] += 1
        if str(row.get("kind")) == "blocked":
            counts[key]["blocked"] += 1
        if bool(row.get("is_wait")) and not bool(row.get("at_goal")):
            counts[key]["wait"] += 1
    return counts


def build_global_features(
    checkpoint_row: dict[str, Any],
    *,
    topology: TokenMapTopology | None = None,
) -> list[float]:
    agents = finite(checkpoint_row.get("agents"))
    free_cells = float(topology.free_cells) if topology is not None else max(1.0, finite(checkpoint_row.get("agents")))
    width = float(topology.width) if topology is not None else 0.0
    height = float(topology.height) if topology is not None else 0.0
    obstacle_ratio = topology.obstacle_ratio if topology is not None else 0.0
    ratio_this = finite(checkpoint_row.get("sum_of_loss_ratio_this_iteration"), -1.0)
    has_incumbent = 1.0 if checkpoint_row.get("sum_of_loss_ratio_this_iteration") is not None else 0.0
    raw_before = [finite(edge.get("raw")) for edge in checkpoint_row.get("raw_before_topk", [])]
    raw_after = [finite(edge.get("raw")) for edge in checkpoint_row.get("raw_after_topk", [])]
    committed = finite(checkpoint_row.get("committed_count"))
    blocked = finite(checkpoint_row.get("blocked_count"))
    wait = finite(checkpoint_row.get("wait_event_count"))
    return [
        agents,
        safe_ratio(agents, free_cells),
        width,
        height,
        obstacle_ratio,
        finite(checkpoint_row.get("iteration")),
        has_incumbent,
        ratio_this,
        ratio_this,
        1.0 if bool(checkpoint_row.get("solution_found_this_iteration")) else 0.0,
        1.0 if checkpoint_row.get("sum_of_loss_this_iteration") is not None else 0.0,
        finite(checkpoint_row.get("time_to_first_solution_ms"), -1.0),
        committed,
        blocked,
        wait,
        finite(checkpoint_row.get("goal_wait_ignored_count")),
        safe_ratio(blocked, committed),
        safe_ratio(wait, committed),
        finite(checkpoint_row.get("traffic_before_nonzero_edges")),
        finite(checkpoint_row.get("traffic_before_max_raw")),
        entropy(raw_before),
        entropy(raw_after),
    ]


def edge_candidate_count(checkpoint_row: dict[str, Any]) -> int:
    raw_before = _edge_raw_lookup(list(checkpoint_row.get("raw_before_topk", [])))
    raw_after = _edge_raw_lookup(list(checkpoint_row.get("raw_after_topk", [])))
    normalized = _edge_raw_lookup(list(checkpoint_row.get("normalized_after_topk", [])), value_key="weight")
    return len(set(raw_before) | set(raw_after) | set(normalized))


def build_edge_tokens(
    checkpoint_row: dict[str, Any],
    *,
    topology: TokenMapTopology | None = None,
    trace_rows: list[dict[str, Any]] | None = None,
    max_edge_tokens: int = 64,
) -> list[list[float]]:
    raw_before = _edge_raw_lookup(list(checkpoint_row.get("raw_before_topk", [])))
    raw_after = _edge_raw_lookup(list(checkpoint_row.get("raw_after_topk", [])))
    normalized_after = _edge_raw_lookup(
        list(checkpoint_row.get("normalized_after_topk", [])),
        value_key="weight",
    )
    event_counts = _edge_event_counts(trace_rows)
    candidates = set(raw_before) | set(raw_after) | set(normalized_after) | set(event_counts)
    sorted_edges = sorted(
        candidates,
        key=lambda key: (
            raw_before.get(key, 0.0),
            event_counts[key]["blocked"],
            event_counts[key]["committed"],
            abs(raw_after.get(key, 0.0) - raw_before.get(key, 0.0)),
            event_counts[key]["wait"],
            raw_after.get(key, 0.0),
            -key[0],
            -key[1],
        ),
        reverse=True,
    )
    limit = max(0, int(max_edge_tokens))
    top_edges = sorted_edges[:limit]
    top_edge = top_edges[0] if top_edges else None
    before_max = max(1.0, finite(checkpoint_row.get("traffic_before_max_raw")))
    tokens: list[list[float]] = []
    for from_id, to_id in top_edges:
        from_x, from_y = _coord_norm(from_id, topology)
        to_x, to_y = _coord_norm(to_id, topology)
        committed = float(event_counts[(from_id, to_id)]["committed"])
        blocked = float(event_counts[(from_id, to_id)]["blocked"])
        wait = float(event_counts[(from_id, to_id)]["wait"])
        before = raw_before.get((from_id, to_id), 0.0)
        after = raw_after.get((from_id, to_id), normalized_after.get((from_id, to_id), 0.0))
        from_degree = float(topology.degree(from_id)) if topology is not None else 0.0
        to_degree = float(topology.degree(to_id)) if topology is not None else 0.0
        is_reverse = 1.0 if top_edge is not None and (from_id, to_id) == (top_edge[1], top_edge[0]) else 0.0
        degree_mean = (from_degree + to_degree) * 0.5
        boundary = 0.0
        if topology is not None:
            boundary = (
                topology.local_obstacle_boundary_score(from_id)
                + topology.local_obstacle_boundary_score(to_id)
            ) * 0.5
        tokens.append(
            [
                _hash_id(from_id),
                _hash_id(to_id),
                from_x,
                from_y,
                to_x,
                to_y,
                *_direction_onehot(from_id, to_id, topology),
                from_degree,
                to_degree,
                is_reverse,
                before,
                safe_ratio(before, before_max),
                committed,
                blocked,
                wait,
                blocked - committed,
                safe_ratio(blocked, committed),
                after - before,
                before * 0.95 - before,
                before * 0.90 - before,
                1.0 if degree_mean <= 2.0 and from_id != to_id else 0.0,
                1.0 if max(from_degree, to_degree) >= 3.0 else 0.0,
                boundary,
            ]
        )
    return tokens


def build_trace_tokens(
    checkpoint_row: dict[str, Any],
    *,
    edge_index: dict[tuple[int, int], int] | None = None,
    trace_rows: list[dict[str, Any]] | None = None,
    max_trace_tokens: int = 128,
) -> list[list[float]]:
    limit = max(0, int(max_trace_tokens))
    if trace_rows:
        grouped: dict[tuple[tuple[int, int], str, bool, bool], dict[str, Any]] = {}
        for row in trace_rows:
            edge = (int(row.get("from_id", -1)), int(row.get("to_id", -1)))
            key = (edge, str(row.get("kind", "")), bool(row.get("is_wait")), bool(row.get("at_goal")))
            bucket = grouped.setdefault(
                key,
                {
                    "count": 0,
                    "first": int(row.get("event_index", 0)),
                    "last": int(row.get("event_index", 0)),
                    "agents": set(),
                },
            )
            bucket["count"] += 1
            bucket["first"] = min(int(bucket["first"]), int(row.get("event_index", 0)))
            bucket["last"] = max(int(bucket["last"]), int(row.get("event_index", 0)))
            bucket["agents"].add(int(row.get("agent_id", -1)))
        total_events = max(1.0, float(len(trace_rows)))
        tokens = []
        for (edge, kind, is_wait, at_goal), bucket in sorted(
            grouped.items(),
            key=lambda item: (
                0 if item[0][1] == "blocked" else 1 if item[0][2] else 2,
                item[1]["first"],
            ),
        )[:limit]:
            tokens.append(
                [
                    float((edge_index or {}).get(edge, -1)),
                    1.0 if kind == "committed" else 0.0,
                    1.0 if kind == "blocked" else 0.0,
                    1.0 if is_wait else 0.0,
                    1.0 if at_goal else 0.0,
                    float(bucket["count"]),
                    safe_ratio(float(bucket["first"]), total_events),
                    safe_ratio(float(bucket["last"]), total_events),
                    float(len(bucket["agents"])),
                ]
            )
        return tokens

    aggregate = [
        ("committed", False, False, finite(checkpoint_row.get("committed_count"))),
        ("blocked", False, False, finite(checkpoint_row.get("blocked_count"))),
        ("committed", True, False, finite(checkpoint_row.get("wait_event_count"))),
        ("committed", True, True, finite(checkpoint_row.get("goal_wait_ignored_count"))),
    ]
    tokens: list[list[float]] = []
    agents = max(1.0, finite(checkpoint_row.get("agents"), 1.0))
    for kind, is_wait, at_goal, count in aggregate:
        if count <= 0.0:
            continue
        tokens.append(
            [
                -1.0,
                1.0 if kind == "committed" else 0.0,
                1.0 if kind == "blocked" else 0.0,
                1.0 if is_wait else 0.0,
                1.0 if at_goal else 0.0,
                count,
                0.0,
                1.0,
                min(agents, count),
            ]
        )
    return tokens[:limit]


def rule_feature_vector(rule_id: str) -> list[float]:
    params = DEFAULT_RULE_PARAMS.get(rule_id, DEFAULT_RULE_PARAMS["additive_ltm"])
    family = rule_family(rule_id)
    family_index = RULE_FAMILY_IDS.index(family)
    return [
        finite(params.get("alpha_commit"), 1.0),
        finite(params.get("alpha_block"), 1.0),
        finite(params.get("alpha_wait"), 1.0),
        finite(params.get("rho_decay"), 1.0),
        finite(params.get("saturation_scale"), 1.0),
        finite(params.get("contraflow_penalty"), 0.0),
        1.0 if family == "additive" else 0.0,
        1.0 if family == "commit" else 0.0,
        1.0 if family == "block" else 0.0,
        1.0 if family == "wait" else 0.0,
        1.0 if family == "decay" else 0.0,
        safe_ratio(float(family_index), float(max(1, len(RULE_FAMILY_IDS) - 1))),
    ]


def build_rule_tokens(rule_ids: list[str] | None = None) -> list[list[float]]:
    return [rule_feature_vector(rule_id) for rule_id in (rule_ids or EXECUTABLE_RULE_IDS)]


def rule_delta_vector(probe_rows: list[dict[str, Any]], rule_ids: list[str] | None = None) -> list[float]:
    rules = rule_ids or EXECUTABLE_RULE_IDS
    lookup = {str(row.get("rule_id")): finite(row.get("delta_ratio_vs_additive")) for row in probe_rows}
    return [lookup.get(rule_id, 0.0) for rule_id in rules]


def rule_harmful_vector(probe_rows: list[dict[str, Any]], rule_ids: list[str] | None = None) -> list[int]:
    rules = rule_ids or EXECUTABLE_RULE_IDS
    lookup = {str(row.get("rule_id")): 1 if row.get("harmful") else 0 for row in probe_rows}
    return [lookup.get(rule_id, 0) for rule_id in rules]


def soft_probe_target(delta_vector: list[float], *, temperature: float) -> list[float]:
    return stable_softmax(delta_vector, temperature)


def soft_stable_target(
    delta_vector: list[float],
    *,
    stable_index: int,
    temperature: float,
    hard_mix: float,
) -> list[float]:
    soft = stable_softmax(delta_vector, temperature)
    hard = [0.0] * len(delta_vector)
    if 0 <= stable_index < len(hard):
        hard[stable_index] = 1.0
    mix = min(1.0, max(0.0, float(hard_mix)))
    return [mix * hard_value + (1.0 - mix) * soft_value for hard_value, soft_value in zip(hard, soft)]


def best_minus_second_margin(delta_vector: list[float]) -> float:
    if len(delta_vector) < 2:
        return 0.0
    values = sorted((float(value) for value in delta_vector), reverse=True)
    return values[0] - values[1]


def best_minus_additive_margin(delta_vector: list[float]) -> float:
    if not delta_vector:
        return 0.0
    additive_index = EXECUTABLE_RULE_IDS.index("additive_ltm")
    return max(float(value) for value in delta_vector) - float(delta_vector[additive_index])
