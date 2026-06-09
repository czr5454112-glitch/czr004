"""Shared helpers for Repair5G.5.4 semantic replay diagnostics."""

from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any, Iterable

from repair5g3_common import git_value, number, read_jsonl, repo_root, resolve, write_csv_rows, write_json
from repair5g51_common import write_text


RESERVED_ID_MIN = 166
RESERVED_ID_MAX = 205
OBSERVED_ID_MAX = 165

G54_CANDIDATES = [
    "additive_ltm",
    "repair5g2_best_frozen_static_candidate",
    "repair5g2_frozen_static_or_selector",
    "repair5g2_c_equiv_best_frozen_baseline",
    "repair5g1_shield_c100_b125_w075_d100_beta0p35_max0p75",
    "repair5g1_shield_c125_b125_w075_d095_beta0p2_max0p5",
    "repair5g1_shield_c125_b125_w075_d095_beta0p35_max0p75",
]

G54_ALLOWED_RUNTIME_FEATURES = {
    "agents",
    "map_width",
    "map_height",
    "obstacle_ratio",
    "free_cells",
    "density",
    "ltm_iterations",
    "returned_solutions_count_so_far",
    "has_incumbent_before",
    "best_ratio_before",
    "improved_last_iteration",
    "committed_count",
    "blocked_count",
    "wait_event_count",
    "progress_committed_count",
    "nonprogress_committed_count",
    "blocked_per_committed",
    "wait_per_committed",
    "blocked_per_agent",
    "committed_per_agent",
    "progress_ratio",
    "c_update_count",
    "f_update_count",
    "c_nonzero_edges",
    "f_nonzero_edges",
    "c_flow_update_ratio",
    "cost_min",
    "cost_max",
    "cost_span",
    "cost_bounds_respected",
}

G54_FORBIDDEN_LABEL_FIELDS = {
    "action",
    "actions",
    "action_logits",
    "priority",
    "priority_override",
    "priority_overrides",
    "restart",
    "restart_node",
    "h_i",
    "heuristic",
    "candidate_deletion",
    "delete_candidate",
    "final_full_run_outcome",
}


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def boolish(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def parse_instance_id_tokens(tokens: Iterable[Any]) -> list[int]:
    values: list[int] = []
    for token_obj in tokens:
        token = str(token_obj).strip()
        if not token:
            continue
        match = re.fullmatch(r"(\d+)\s*(?:\.\.|-|:)\s*(\d+)", token)
        if match:
            start, end = int(match.group(1)), int(match.group(2))
            step = 1 if end >= start else -1
            values.extend(range(start, end + step, step))
            continue
        values.append(int(token))
    return list(dict.fromkeys(values))


def validate_observed_instance_ids(instance_ids: Iterable[int], *, label: str = "Repair5G.5.4") -> list[int]:
    ids = [int(value) for value in instance_ids]
    reserved = [value for value in ids if RESERVED_ID_MIN <= value <= RESERVED_ID_MAX]
    if reserved:
        raise SystemExit(f"{label} may not run reserved IDs 166..205: {reserved}")
    fresh = [value for value in ids if value > OBSERVED_ID_MAX]
    if fresh:
        raise SystemExit(f"{label} may only run observed IDs <=165: {fresh}")
    return ids


def compact_gate_md(gates: dict[str, Any]) -> str:
    return "\n".join(f"- `{key}`: `{value}`" for key, value in gates.items()) + "\n"


def semantic_prior_passed(transform_summary: dict[str, Any]) -> bool:
    return bool(transform_summary.get("gates", {}).get("update_transform_equivalence_passed"))


def score_from_label(row: dict[str, Any]) -> float:
    if not boolish(row.get("probe_solution_found")) or not boolish(row.get("probe_feasible")):
        return math.inf
    value = number(row.get("probe_sum_of_loss_ratio"), math.inf)
    return value if math.isfinite(value) else math.inf


def summarize_identity() -> dict[str, Any]:
    root = repo_root()
    return {
        "branch": git_value(["branch", "--show-current"], root),
        "commit": git_value(["rev-parse", "--short", "HEAD"], root),
    }
