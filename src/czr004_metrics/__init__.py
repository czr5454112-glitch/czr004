"""Shared Phase2 metrics harness for czr004 experiments."""

from .core import lower_bound_from_distances, sum_of_loss, sum_of_loss_ratio
from .incumbent import IncumbentEvent, anytime_auc, parse_incumbent_events
from .schema import normalize_run_row, validate_run_row
from .summary import (
    MAP_ORDER,
    phase1a_gate,
    summarize_by_group,
    summarize_paired_methods,
    summarize_planning_execution,
)

__all__ = [
    "IncumbentEvent",
    "MAP_ORDER",
    "anytime_auc",
    "lower_bound_from_distances",
    "normalize_run_row",
    "parse_incumbent_events",
    "phase1a_gate",
    "sum_of_loss",
    "sum_of_loss_ratio",
    "summarize_by_group",
    "summarize_paired_methods",
    "summarize_planning_execution",
    "validate_run_row",
]
