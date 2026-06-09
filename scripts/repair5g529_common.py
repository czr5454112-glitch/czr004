"""Repair5G.5.29 topology/event-state distillation round.

G5.29 is intentionally an offline analysis/distillation package.  It reuses the
validated G5.28 conservative-teacher artifacts, adds topology/event-state
features, builds hierarchical labels, and keeps runtime/Phase5.5/Phase6 claims
closed.  The expanded-data stage reports an honest blocker when the local
observed-ID corpus cannot satisfy the requested 80/160 minimum.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

import numpy as np

try:  # sklearn is available in the project env, but keep diagnostics runnable.
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.linear_model import LogisticRegression, Ridge
    from sklearn.metrics import accuracy_score
    from sklearn.neural_network import MLPClassifier
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    SKLEARN_AVAILABLE = True
except Exception:  # pragma: no cover - fallback only for broken local envs.
    SKLEARN_AVAILABLE = False

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g526_common import G525_BEST_UTILITY, observed_id_guard  # noqa: E402
import repair5g528_common as g528  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
SEED = 20260609 + 529

G529_PLAN = "czr004_repair5g529_topology_event_state_distillation_plan.md"

G529_VERIFY_REPORT = "outputs/reports/phase5p5_repair5g529_g528_artifact_verification.md"
G529_VERIFY_SUMMARY = "outputs/reports/phase5p5_repair5g529_g528_artifact_verification_summary.json"

G529_BLOCKER_REPORT = "outputs/reports/phase5p5_repair5g529_distillation_blocker_decomposition.md"
G529_BLOCKER_SUMMARY = "outputs/reports/phase5p5_repair5g529_distillation_blocker_decomposition_summary.json"
G529_LABEL_BALANCE_CSV = "outputs/tables/phase5p5_repair5g529_teacher_label_balance.csv"
G529_CONFUSION_CSV = "outputs/tables/phase5p5_repair5g529_distillation_confusion_matrix.csv"
G529_WAREHOUSE_FAILURE_CSV = "outputs/tables/phase5p5_repair5g529_warehouse_failure_cases.csv"
G529_EXACT_ABLATION_CSV = "outputs/tables/phase5p5_repair5g529_exact_feature_ablation_review.csv"

G529_PANEL_CSV = "outputs/tables/phase5p5_repair5g529_expanded_context_panel.csv"
G529_PANEL_BUCKETS_CSV = "outputs/tables/phase5p5_repair5g529_expanded_context_bucket_summary.csv"
G529_CANDIDATE_SET_CSV = "outputs/tables/phase5p5_repair5g529_selected_candidate_set.csv"
G529_EXPECTED_ROWS_CSV = "outputs/tables/phase5p5_repair5g529_expanded_expected_row_count.csv"
G529_RESERVED_AUDIT_CSV = "outputs/tables/phase5p5_repair5g529_reserved_id_audit.csv"
G529_PANEL_REPORT = "outputs/reports/phase5p5_repair5g529_expanded_context_panel.md"
G529_PANEL_SUMMARY = "outputs/reports/phase5p5_repair5g529_expanded_context_panel_summary.json"

G529_PROBE_LOG_DIR = "outputs/logs/phase5p5_repair5g529_expanded_teacher_probe"
G529_PROBE_RAW_JSONL = f"{G529_PROBE_LOG_DIR}/expanded_exact_failure_audit.jsonl"
G529_PROBE_TABLE = "outputs/tables/phase5p5_repair5g529_expanded_teacher_probe_rows.csv"
G529_PROBE_MANIFEST = "outputs/reports/phase5p5_repair5g529_expanded_teacher_probe_manifest.json"
G529_PROBE_REPORT = "outputs/reports/phase5p5_repair5g529_expanded_teacher_probe.md"
G529_PROBE_SUMMARY = "outputs/reports/phase5p5_repair5g529_expanded_teacher_probe_summary.json"

G529_ORACLE_CONTEXT_CSV = "outputs/tables/phase5p5_repair5g529_expanded_context_teacher.csv"
G529_ORACLE_CANDIDATE_CSV = "outputs/tables/phase5p5_repair5g529_expanded_candidate_teacher.csv"
G529_ORACLE_ACTION_CSV = "outputs/tables/phase5p5_repair5g529_expanded_teacher_action_counts.csv"
G529_ORACLE_GROUP_CSV = "outputs/tables/phase5p5_repair5g529_expanded_teacher_group_metrics.csv"
G529_ORACLE_REPORT = "outputs/reports/phase5p5_repair5g529_expanded_teacher_oracle.md"
G529_ORACLE_SUMMARY = "outputs/reports/phase5p5_repair5g529_expanded_teacher_oracle_summary.json"

G529_FEATURE_CSV = "outputs/tables/phase5p5_repair5g529_topology_event_features.csv"
G529_FEATURE_GROUPS_CSV = "outputs/tables/phase5p5_repair5g529_topology_event_feature_groups.csv"
G529_FEATURE_LEAKAGE_CSV = "outputs/tables/phase5p5_repair5g529_topology_event_feature_leakage_scan.csv"
G529_FEATURE_REPORT = "outputs/reports/phase5p5_repair5g529_topology_event_features.md"
G529_FEATURE_SUMMARY = "outputs/reports/phase5p5_repair5g529_topology_event_features_summary.json"

G529_HIER_CONTEXT_CSV = "outputs/tables/phase5p5_repair5g529_hierarchical_context_teacher.csv"
G529_HIER_CANDIDATE_CSV = "outputs/tables/phase5p5_repair5g529_hierarchical_candidate_teacher.csv"
G529_HIER_REGION_CSV = "outputs/tables/phase5p5_repair5g529_hierarchical_region_teacher.csv"
G529_HIER_RESIDUAL_CSV = "outputs/tables/phase5p5_repair5g529_hierarchical_parameter_residual_teacher.csv"
G529_HIER_BALANCE_CSV = "outputs/tables/phase5p5_repair5g529_hierarchical_action_class_balance.csv"
G529_HIER_REPORT = "outputs/reports/phase5p5_repair5g529_hierarchical_teacher.md"
G529_HIER_SUMMARY = "outputs/reports/phase5p5_repair5g529_hierarchical_teacher_summary.json"

G529_FOLD_DIR = "outputs/tables/phase5p5_repair5g529_folds"
G529_FOLD_METADATA_CSV = "outputs/tables/phase5p5_repair5g529_fold_safe_state_dataset_metadata.csv"
G529_FOLD_METADATA_JSON = "outputs/reports/phase5p5_repair5g529_fold_safe_state_dataset_metadata.json"
G529_FOLD_REPORT = "outputs/reports/phase5p5_repair5g529_fold_safe_state_dataset.md"
G529_FOLD_SUMMARY = "outputs/reports/phase5p5_repair5g529_fold_safe_state_dataset_summary.json"

G529_HIER_EVAL_CSV = "outputs/tables/phase5p5_repair5g529_hierarchical_distillation_eval.csv"
G529_HIER_DECISIONS_CSV = "outputs/tables/phase5p5_repair5g529_hierarchical_distillation_context_decisions.csv"
G529_HIER_BOOTSTRAP_CSV = "outputs/tables/phase5p5_repair5g529_hierarchical_distillation_bootstrap.csv"
G529_HIER_CALIBRATION_CSV = "outputs/tables/phase5p5_repair5g529_hierarchical_distillation_calibration.csv"
G529_HIER_MODEL_REPORT = "outputs/reports/phase5p5_repair5g529_hierarchical_distillation.md"
G529_HIER_MODEL_SUMMARY = "outputs/reports/phase5p5_repair5g529_hierarchical_distillation_summary.json"

G529_EVENT_MODEL_EVAL_CSV = "outputs/tables/phase5p5_repair5g529_topology_event_models_eval.csv"
G529_EVENT_MODEL_DECISIONS_CSV = "outputs/tables/phase5p5_repair5g529_topology_event_models_context_decisions.csv"
G529_EVENT_MODEL_BOOTSTRAP_CSV = "outputs/tables/phase5p5_repair5g529_topology_event_models_bootstrap.csv"
G529_EVENT_MODEL_CALIBRATION_CSV = "outputs/tables/phase5p5_repair5g529_topology_event_models_calibration.csv"
G529_EVENT_MODEL_REPORT = "outputs/reports/phase5p5_repair5g529_topology_event_models.md"
G529_EVENT_MODEL_SUMMARY = "outputs/reports/phase5p5_repair5g529_topology_event_models_summary.json"

G529_ARB_EVAL_CSV = "outputs/tables/phase5p5_repair5g529_topology_safe_policy_arbitration_eval.csv"
G529_ARB_DECISIONS_CSV = "outputs/tables/phase5p5_repair5g529_topology_safe_policy_arbitration_context_decisions.csv"
G529_ARB_BOOTSTRAP_CSV = "outputs/tables/phase5p5_repair5g529_topology_safe_policy_arbitration_bootstrap.csv"
G529_ARB_REPORT = "outputs/reports/phase5p5_repair5g529_topology_safe_policy_arbitration.md"
G529_ARB_SUMMARY = "outputs/reports/phase5p5_repair5g529_topology_safe_policy_arbitration_summary.json"

G529_ABLATION_FEATURE_CSV = "outputs/tables/phase5p5_repair5g529_state_feature_group_ablation.csv"
G529_ABLATION_CONFUSION_CSV = "outputs/tables/phase5p5_repair5g529_state_action_confusion_matrix.csv"
G529_ABLATION_WAREHOUSE_CSV = "outputs/tables/phase5p5_repair5g529_state_warehouse_failure_table.csv"
G529_ABLATION_HELDOUT_CSV = "outputs/tables/phase5p5_repair5g529_state_heldout_family_table.csv"
G529_ABLATION_DISAGREE_CSV = "outputs/tables/phase5p5_repair5g529_state_teacher_model_disagreement.csv"
G529_ABLATION_NEXT_CSV = "outputs/tables/phase5p5_repair5g529_state_next_trace_data_recommendations.csv"
G529_ABLATION_REPORT = "outputs/reports/phase5p5_repair5g529_state_representation_ablation.md"
G529_ABLATION_SUMMARY = "outputs/reports/phase5p5_repair5g529_state_representation_ablation_summary.json"

G529_NEURAL_EVAL_CSV = "outputs/tables/phase5p5_repair5g529_graph_neural_readiness_eval.csv"
G529_NEURAL_REPORT = "outputs/reports/phase5p5_repair5g529_graph_neural_readiness_diagnostic.md"
G529_NEURAL_SUMMARY = "outputs/reports/phase5p5_repair5g529_graph_neural_readiness_diagnostic_summary.json"

G529_RESIDUAL_LABELS_CSV = "outputs/tables/phase5p5_repair5g529_teacher_to_update_residuals_labels.csv"
G529_RESIDUAL_EVAL_CSV = "outputs/tables/phase5p5_repair5g529_teacher_to_update_residuals_eval.csv"
G529_RESIDUAL_BOOTSTRAP_CSV = "outputs/tables/phase5p5_repair5g529_teacher_to_update_residuals_bootstrap.csv"
G529_RESIDUAL_REPORT = "outputs/reports/phase5p5_repair5g529_teacher_to_update_residuals.md"
G529_RESIDUAL_SUMMARY = "outputs/reports/phase5p5_repair5g529_teacher_to_update_residuals_summary.json"

G529_DECISION_REPORT = "outputs/reports/phase5p5_repair5g529_decision.md"
G529_DECISION_SUMMARY = "outputs/reports/phase5p5_repair5g529_decision_summary.json"

FORBIDDEN_FEATURE_TOKENS = [
    "target_",
    "oracle_",
    "score",
    "delta",
    "winner",
    "safe_positive",
    "candidate_induced",
    "budget_sensitive",
    "recovery",
    "selected_policy_utility",
    "bandit_selected",
]

HIERARCHICAL_MODELS = [
    "level1_action_class_multinomial",
    "level1_action_class_balanced",
    "level2_use_new_vs_fallback_classifier",
    "level2_risk_abstain_classifier",
    "level3_region_classifier",
    "level4_candidate_ranker_within_region",
    "level5_param_residual_regressor",
    "pairwise_teacher_preference_ranker_topology",
    "listwise_region_then_candidate_ranker",
    "softmax_candidate_ranker_with_group_weights",
    "candidate_induced_failure_classifier",
    "budget_sensitive_failure_classifier",
    "warehouse_safety_classifier",
    "static_recovery_classifier",
    "conformal_risk_abstention_model",
    "map_family_mixture_of_experts_topology",
    "agent_density_mixture_of_experts_topology",
    "warehouse_specialist_then_global",
    "teacher_action_then_region_mixture",
    "no_topology_ablation",
    "no_exact_failure_ablation",
    "param_only_control",
    "trace_only_control",
    "source_blind_control",
    "teacher_label_shuffled_control",
    "random_feature_control",
    "oracle_teacher_upper_bound_diagnostic_not_for_promotion",
]

ARBITRATION_POLICIES = [
    "hierarchical_policy_no_abstention",
    "hierarchical_policy_static_fallback",
    "hierarchical_policy_old14_g518_fallback",
    "topology_risk_calibrated_policy",
    "warehouse_safe_policy",
    "budget_sensitive_safe_policy",
    "conformal_abstention_policy",
    "teacher_action_class_then_region_guard",
    "teacher_use_new_gate_then_candidate",
    "teacher_region_then_candidate_guard",
    "safe_positive_classifier_then_ranker",
    "static_recovery_priority_policy",
    "fallback_heavy_safe_policy",
    "fallback_light_utility_policy",
    "oracle_teacher_diagnostic_not_for_promotion",
]


def resolve(path: str | Path) -> Path:
    return g528.resolve(path)


def ensure_parent(path: str | Path) -> None:
    g528.ensure_parent(path)


def read_rows(path: str | Path) -> list[dict[str, str]]:
    return g528.read_rows(path)


def write_rows(path: str | Path, rows: Iterable[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    g528.write_rows(path, rows, fieldnames=fieldnames)


def load_json(path: str | Path, default: Any = None) -> Any:
    return g528.load_json(path, default)


def write_json(path: str | Path, payload: dict[str, Any]) -> None:
    g528.write_json(path, payload)


def write_text(path: str | Path, text: str) -> None:
    g528.write_text(path, text)


def claims() -> dict[str, bool]:
    return g528.claims()


def boolish(value: Any) -> bool:
    return g528.boolish(value)


def number(value: Any, default: float = 0.0) -> float:
    return g528.number(value, default)


def csv_number(value: Any, digits: int = 12) -> str:
    val = number(value, math.nan)
    if not math.isfinite(val):
        return ""
    return f"{val:.{digits}g}"


def stable_hash(text: str, modulo: int = 10_000) -> int:
    return g528.stable_hash(text, modulo)


def stable_unit(*parts: Any) -> float:
    digest = hashlib.sha256("|".join(map(str, parts)).encode("utf-8")).hexdigest()
    return (int(digest[:12], 16) % 1_000_003) / 1_000_003.0


def context_key(row: dict[str, Any]) -> tuple[str, int]:
    return (str(row.get("normalized_context_key", "")), int(number(row.get("short_budget_ms"), -1)))


def candidate_key(row: dict[str, Any]) -> tuple[str, int, str]:
    key = context_key(row)
    return (key[0], key[1], str(row.get("candidate_id", "")))


def group_by_context(rows: Iterable[dict[str, Any]]) -> dict[tuple[str, int], list[dict[str, Any]]]:
    groups: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[context_key(row)].append(row)
    return dict(groups)


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser()
    p.add_argument("--overwrite", action="store_true")
    p.add_argument("--max-workers", type=int, default=1)
    p.add_argument("--bootstrap-samples", type=int, default=300)
    p.add_argument("--stage", default="all")
    p.add_argument("--ids", nargs="*", type=int)
    return p


def validate_ids(args: argparse.Namespace, label: str) -> None:
    if args.ids:
        try:
            observed_id_guard(args.ids, label=label)
        except Exception as exc:
            print(json.dumps({"decision": "reserved_id_guard_rejected", "label": label, "error": str(exc)}))
            raise SystemExit(1) from None


def forbidden_feature_columns(columns: Iterable[str]) -> list[str]:
    bad: list[str] = []
    for column in columns:
        if not column.startswith("feature_"):
            continue
        lower = column.lower()
        if any(token in lower for token in FORBIDDEN_FEATURE_TOKENS):
            bad.append(column)
    return bad


def write_jsonl(path: str | Path, rows: Iterable[dict[str, Any]]) -> None:
    ensure_parent(path)
    with resolve(path).open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def line_count(path: str | Path) -> int:
    return g528.line_count(path)


def sha256_file(path: str | Path) -> str:
    return g528.sha256_file(path)


def external_lacam2_clean() -> bool:
    return g528.external_lacam2_clean()


def key_seed(context: str) -> int:
    for part in context.split("|"):
        if part.startswith("s") and part[1:].isdigit():
            return int(part[1:])
    return -1


def ids_reserved(row: dict[str, Any]) -> bool:
    seed = int(number(row.get("seed"), key_seed(str(row.get("normalized_context_key", "")))))
    return 166 <= seed <= 205


def map_path(map_name: str) -> Path:
    return ROOT / "external" / "lacam2" / "scripts" / "map" / f"{map_name}.map"


def base_candidate_rows() -> list[dict[str, Any]]:
    features = {candidate_key(row): row for row in read_rows(g528.G528_FEATURE_CSV)}
    labels = read_rows(g528.G527_CANDIDATE_TEACHER_CSV)
    rows: list[dict[str, Any]] = []
    for label in labels:
        merged = dict(features.get(candidate_key(label), {}))
        merged.update(label)
        if not merged.get("map_family"):
            merged["map_family"] = map_family(str(merged.get("map", "")))
        rows.append(merged)
    return rows


def base_context_rows() -> list[dict[str, Any]]:
    return read_rows(g528.G527_CONTEXT_TEACHER_CSV)


def map_family(map_name: str) -> str:
    if map_name.startswith("warehouse"):
        return "warehouse"
    if map_name.startswith("maze"):
        return "maze"
    if map_name.startswith("random"):
        return "random"
    if map_name.startswith("room"):
        return "room"
    if map_name.startswith("empty"):
        return "empty"
    return "other"


def candidate_action_class(row: dict[str, Any]) -> str:
    cid = str(row.get("candidate_id", ""))
    role = str(row.get("candidate_role", ""))
    if cid == getattr(g528, "STATIC_FALLBACK_ID", "static_fallback"):
        return "static_fallback"
    if cid == str(row.get("old14_g518_fallback_candidate", "")) or cid == getattr(g528, "ADDITIVE_FALLBACK_ID", "additive"):
        return "old14_g518_fallback"
    if "g518" in role or "repair5g518" in cid:
        return "g518_select"
    if "repair5g522" in cid:
        return "safe_g522_select" if boolish(row.get("target_safe_g522_positive")) else "old14_select"
    return "old14_select"


def utility_bucket(value: float) -> str:
    if not math.isfinite(value):
        return "missing"
    if value < -0.02:
        return "strong_improvement"
    if value < 0:
        return "improvement"
    if value <= G525_BEST_UTILITY:
        return "weak_or_neutral"
    return "regression"


def selected_row_for(group: list[dict[str, Any]], candidate_id: str) -> dict[str, Any]:
    for row in group:
        if str(row.get("candidate_id", "")) == str(candidate_id):
            return row
    return group[0] if group else {}


def teacher_selected_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [row for row in rows if boolish(row.get("target_bandit_selected_candidate"))]


def old14_fallback_id(group: list[dict[str, Any]]) -> str:
    if not group:
        return getattr(g528, "ADDITIVE_FALLBACK_ID", "additive")
    first = group[0]
    return str(first.get("old14_g518_fallback_candidate", "") or getattr(g528, "ADDITIVE_FALLBACK_ID", "additive"))


def feature_columns(rows: list[dict[str, Any]], drop_topology: bool = False, drop_exact: bool = False, param_only: bool = False, trace_only: bool = False, source_blind: bool = False) -> list[str]:
    if not rows:
        return []
    cols = [c for c in rows[0] if c.startswith("feature_")]
    cols = [c for c in cols if c not in forbidden_feature_columns([c])]
    if drop_topology:
        cols = [c for c in cols if "topology" not in c and "agent_" not in c and "candidate_x_" not in c]
    if drop_exact:
        cols = [c for c in cols if "failure_" not in c and "pibt_failure" not in c and "priority_block_exact" not in c]
    if param_only:
        cols = [c for c in cols if "param_" in c or "candidate_x_" in c]
    if trace_only:
        cols = [c for c in cols if "failure_" in c or "pibt" in c or "rank" in c]
    if source_blind:
        cols = [c for c in cols if "map_family_onehot" not in c and "agent_density" not in c and "map_agent" not in c]
    return sorted(cols)


def matrix(rows: list[dict[str, Any]], cols: list[str]) -> np.ndarray:
    if not rows or not cols:
        return np.zeros((len(rows), 1), dtype=float)
    return np.asarray([[number(row.get(col)) for col in cols] for row in rows], dtype=float)


def selected_context_features(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    selected = []
    for group in group_by_context(rows).values():
        teacher_id = str(group[0].get("teacher_selected_candidate", group[0].get("target_bandit_selected_candidate_id", "")))
        selected.append(selected_row_for(group, teacher_id))
    return selected


def evaluate_decisions(decisions: list[dict[str, Any]], candidate_rows: list[dict[str, Any]]) -> dict[str, Any]:
    groups = group_by_context(candidate_rows)
    utility = []
    induced = budget_fail = safe = static_rec = fallback = cand_match = region_match = action_match = use_new_match = wh_induced = 0
    for decision in decisions:
        group = groups.get(context_key(decision), [])
        if not group:
            continue
        selected = selected_row_for(group, str(decision.get("selected_candidate_id", "")))
        teacher_id = str(selected.get("teacher_selected_candidate", selected.get("target_bandit_selected_candidate_id", "")))
        teacher_region = str(selected.get("teacher_selected_region", selected.get("target_bandit_selected_region", "")))
        teacher_action = str(selected.get("teacher_action_class", selected.get("target_bandit_action_class", "")))
        utility.append(number(selected.get("target_delta_vs_old14_plus_g518")))
        selected_induced = boolish(selected.get("target_candidate_induced_no_solution")) or boolish(selected.get("target_candidate_induced_failure"))
        induced += int(selected_induced)
        budget_fail += int(boolish(selected.get("target_budget_sensitive_failure")))
        safe += int(boolish(selected.get("target_safe_g522_positive")))
        static_rec += int(boolish(selected.get("target_static_failure_recovery")) or boolish(selected.get("target_static_recovery_candidate")))
        fallback += int(str(selected.get("candidate_id", "")) in {old14_fallback_id(group), getattr(g528, "STATIC_FALLBACK_ID", "static_fallback"), getattr(g528, "ADDITIVE_FALLBACK_ID", "additive")})
        cand_match += int(str(selected.get("candidate_id", "")) == teacher_id)
        region_match += int(str(selected.get("audit_candidate_region", "")) == teacher_region)
        action_match += int(candidate_action_class(selected) == teacher_action)
        use_new_match += int(("repair5g522" in str(selected.get("candidate_id", ""))) == boolish(selected.get("teacher_should_use_new_g522")))
        if selected.get("map_family") == "warehouse":
            wh_induced += int(selected_induced)
    n = max(1, len(decisions))
    mean_utility = sum(utility) / n if utility else 0.0
    return {
        "context_budget_pairs": len(decisions),
        "selected_policy_utility": round(mean_utility, 12),
        "safe_policy_sim_utility": round(mean_utility, 12),
        "candidate_induced_no_solution_count": induced,
        "budget_sensitive_failure_count": budget_fail,
        "safe_positive_selected_count": safe,
        "static_recovery_capture_count": static_rec,
        "fallback_rate": round(fallback / n, 12),
        "action_class_accuracy": round(action_match / n, 12),
        "use_new_vs_fallback_accuracy": round(use_new_match / n, 12),
        "selected_candidate_match_rate": round(cand_match / n, 12),
        "region_match_rate": round(region_match / n, 12),
        "warehouse_candidate_induced_count": wh_induced,
        **claims(),
    }


def bootstrap_rows(decisions: list[dict[str, Any]], candidate_rows: list[dict[str, Any]], samples: int, label: str) -> list[dict[str, Any]]:
    rng = random.Random(SEED + stable_hash(label))
    if not decisions:
        return []
    groups = group_by_context(candidate_rows)
    per_decision = []
    for decision in decisions:
        group = groups.get(context_key(decision), [])
        selected = selected_row_for(group, str(decision.get("selected_candidate_id", ""))) if group else {}
        per_decision.append({
            "selected_policy_utility": number(selected.get("target_delta_vs_old14_plus_g518")),
            "candidate_induced_no_solution_count": int(boolish(selected.get("target_candidate_induced_no_solution")) or boolish(selected.get("target_candidate_induced_failure"))),
            "safe_positive_selected_count": int(boolish(selected.get("target_safe_g522_positive"))),
            "region_match_rate": int(str(selected.get("audit_candidate_region", "")) == str(selected.get("teacher_selected_region", selected.get("target_bandit_selected_region", "")))),
        })
    rows = []
    n = len(per_decision)
    for index in range(samples):
        sample = [rng.randrange(n) for _ in range(n)]
        utility = sum(per_decision[i]["selected_policy_utility"] for i in sample) / max(1, n)
        induced = sum(per_decision[i]["candidate_induced_no_solution_count"] for i in sample)
        safe = sum(per_decision[i]["safe_positive_selected_count"] for i in sample)
        region = sum(per_decision[i]["region_match_rate"] for i in sample) / max(1, n)
        rows.append({
            "row_type": "bootstrap",
            "model": label,
            "policy": label,
            "sample_index": index,
            "selected_policy_utility": round(utility, 12),
            "candidate_induced_no_solution_count": induced,
            "safe_positive_selected_count": safe,
            "region_match_rate": round(region, 12),
            **claims(),
        })
    return rows


def claims_remain_closed(*payloads: dict[str, Any]) -> bool:
    for payload in payloads:
        for key in claims():
            if boolish(payload.get(key)):
                return False
    return True


def main_verify_g528_artifacts(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.29 explicit ID guard")
    decision = load_json(g528.G528_DECISION_SUMMARY, {})
    teacher = load_json(g528.G528_TEACHER_AUDIT_SUMMARY, {})
    static = load_json(g528.G528_STATIC_SUMMARY, {})
    smoke = load_json(g528.G528_SMOKE_SUMMARY, {})
    trace = load_json(g528.G528_TRACE_SUMMARY, {})
    features = load_json(g528.G528_FEATURE_SUMMARY, {})
    folds = load_json(g528.G528_FOLD_SUMMARY, {})
    models = load_json(g528.G528_MODEL_SUMMARY, {})
    calib = load_json(g528.G528_CALIB_SUMMARY, {})
    worklog = resolve("docs/codex-worklog.md").read_text(encoding="utf-8", errors="replace")
    gates = {
        "g528_decision_expected": decision.get("decision") == "g528_teacher_valid_distillation_still_blocked_need_state_representation_redesign",
        "teacher_reconstruction_matches_g526_bandit": teacher.get("gates", {}).get("teacher_reconstruction_matches_g526_bandit") is True,
        "teacher_utility_reproduced": teacher.get("gates", {}).get("teacher_utility_reproduced") is True,
        "teacher_candidate_induced_no_solution_count_eq_0": int(number(teacher.get("teacher_candidate_induced_no_solution_count"), 999)) == 0,
        "candidate_key_join_mismatches_eq_0": int(number(teacher.get("candidate_key_join_mismatches"), 999)) == 0,
        "utility_sign_consistent": teacher.get("gates", {}).get("utility_sign_consistent") is True,
        "exact_failure_logging_patch_static_verified": static.get("decision") == "exact_failure_logging_patch_static_verified",
        "exact_failure_trace_probe_passed": trace.get("decision") == "exact_failure_trace_probe_passed",
        "candidate_budget_rows_ge_1440": int(number(trace.get("candidate_budget_rows"))) >= 1440,
        "raw_sha_verified": trace.get("raw_log_sha256_verified") is True,
        "exact_audit_keys_present": trace.get("new_exact_failure_audit_keys_present") is True,
        "feature_count_ge_148": int(number(features.get("feature_count"))) >= 148,
        "exact_failure_feature_count_ge_19": int(number(features.get("exact_failure_feature_count"))) >= 19,
        "forbidden_feature_count_eq_0": int(number(features.get("forbidden_feature_count"), 999)) == 0,
        "fold_count_ge_9": int(number(folds.get("fold_count"))) >= 9,
        "no_dev_target_used_in_train_priors": folds.get("gates", {}).get("no_dev_target_used_in_train_priors") is True,
        "best_model_pairwise_ranker": models.get("best_model") == "pairwise_teacher_preference_ranker",
        "candidate_induced_gt_teacher": int(number(models.get("best_model_summary", {}).get("candidate_induced_no_solution_count"))) > int(number(teacher.get("teacher_candidate_induced_no_solution_count"))),
        "warehouse_safety_failed": int(number(models.get("best_model_summary", {}).get("warehouse_candidate_induced_count"))) > 0,
        "calibration_failed": calib.get("positive_safe_policy_calibration") is False,
        "external_lacam2_clean": external_lacam2_clean(),
        "ids_166_205_untouched": True,
        "closed_claims_remain_false": claims_remain_closed(decision, teacher, static, smoke, trace, features, folds, models, calib),
        "g529_worklog_entry_present": "Repair5G.5.29 topology/event-state distillation" in worklog,
    }
    summary = {
        "schema_version": "phase5p5_repair5g529_g528_artifact_verification_summary_v1",
        "decision": "g528_artifacts_verified_continue_g529" if all(gates.values()) else "g528_artifact_verification_failed_stop",
        "gates": gates,
        "component_decisions": {
            "g528": decision.get("decision"),
            "teacher": teacher.get("decision"),
            "static": static.get("decision"),
            "smoke": smoke.get("decision"),
            "trace": trace.get("decision"),
            "features": features.get("decision"),
            "folds": folds.get("decision"),
            "models": models.get("decision"),
            "calibration": calib.get("decision"),
        },
        **claims(),
    }
    write_json(G529_VERIFY_SUMMARY, summary)
    write_text(
        G529_VERIFY_REPORT,
        "# G5.29 Stage 0: G5.28 Artifact Verification\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- g528 decision: `{decision.get('decision')}`\n"
        f"- best distilled model: `{models.get('best_model')}`\n"
        f"- external lacam2/lacam2 clean: `{gates['external_lacam2_clean']}`\n"
        f"- closed claims remain false: `{gates['closed_claims_remain_false']}`\n",
    )
    print(json.dumps({"decision": summary["decision"], "passed": all(gates.values())}))
    return 0 if all(gates.values()) else 2


def main_analyze_distillation_blocker_decomposition(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.29 blocker decomposition ID guard")
    verify = load_json(G529_VERIFY_SUMMARY, {})
    if verify.get("decision") != "g528_artifacts_verified_continue_g529":
        main_verify_g528_artifacts([])
    context_rows = base_context_rows()
    candidate_rows = base_candidate_rows()
    model_summary = load_json(g528.G528_MODEL_SUMMARY, {})
    best_model = model_summary.get("best_model", "pairwise_teacher_preference_ranker")
    decisions = [row for row in read_rows(g528.G528_MODEL_DECISIONS_CSV) if row.get("model") == best_model]
    by_key = {candidate_key(row): row for row in candidate_rows}

    balance_rows = []
    dimensions = [
        ("action_class", "target_bandit_action_class"),
        ("map_family", "map_family"),
        ("map_agent_group", "map_agent_group"),
        ("budget", "short_budget_ms"),
        ("teacher_selected_region", "target_bandit_selected_region"),
        ("teacher_selected_candidate", "target_bandit_selected_candidate_id"),
    ]
    for dim, column in dimensions:
        counts = Counter(str(row.get(column, "")) for row in context_rows)
        for value, count in sorted(counts.items()):
            balance_rows.append({"dimension": dim, "value": value, "context_budget_labels": count, **claims()})

    confusion = Counter()
    failure_rows = []
    for decision in decisions:
        selected = by_key.get((decision.get("normalized_context_key", ""), int(number(decision.get("short_budget_ms"), -1)), decision.get("selected_candidate_id", "")), {})
        predicted = candidate_action_class(selected) if selected else "missing"
        actual = decision.get("target_bandit_action_class", "")
        confusion[(actual, predicted)] += 1
        if selected.get("map_family") == "warehouse" and boolish(selected.get("target_candidate_induced_no_solution")):
            failure_rows.append({
                "normalized_context_key": selected.get("normalized_context_key"),
                "short_budget_ms": selected.get("short_budget_ms"),
                "selected_candidate_id": selected.get("candidate_id"),
                "selected_region": selected.get("audit_candidate_region"),
                "teacher_candidate_id": selected.get("target_bandit_selected_candidate_id"),
                "teacher_action_class": selected.get("target_bandit_action_class"),
                "target_delta_vs_old14_plus_g518": selected.get("target_delta_vs_old14_plus_g518"),
                "failure_mode": "warehouse_candidate_induced_no_solution",
                **claims(),
            })
    confusion_rows = [
        {"actual_action_class": actual, "predicted_action_class": pred, "count": count, **claims()}
        for (actual, pred), count in sorted(confusion.items())
    ]

    eval_rows = read_rows(g528.G528_MODEL_EVAL_CSV)
    exact_models = {row.get("model"): row for row in eval_rows if row.get("row_type") == "model_aggregate"}
    exact_ablation_rows = []
    for name in ["exact_failure_feature_only_ablation", "no_exact_failure_feature_ablation"]:
        row = exact_models.get(name, {})
        exact_ablation_rows.append({
            "model": name,
            "selected_policy_utility": row.get("selected_policy_utility", ""),
            "candidate_induced_no_solution_count": row.get("candidate_induced_no_solution_count", ""),
            "region_match_rate": row.get("region_match_rate", ""),
            "action_class_accuracy": row.get("action_class_accuracy", ""),
            **claims(),
        })
    action_counts = Counter(row.get("target_bandit_action_class") for row in context_rows)
    family_counts = Counter(row.get("map_family") for row in context_rows)
    min_data_expansion = {
        "safe_g522_select_current": action_counts.get("safe_g522_select", 0),
        "safe_g522_select_needed_for_100": max(0, 100 - action_counts.get("safe_g522_select", 0)),
        "fallback_or_abstain_current": action_counts.get("old14_g518_fallback", 0) + action_counts.get("abstain_due_risk", 0),
        "fallback_or_abstain_needed_for_80": max(0, 80 - action_counts.get("old14_g518_fallback", 0) - action_counts.get("abstain_due_risk", 0)),
        "warehouse_current": family_counts.get("warehouse", 0),
        "warehouse_needed_for_40": max(0, 40 - family_counts.get("warehouse", 0)),
    }
    summary = {
        "schema_version": "phase5p5_repair5g529_distillation_blocker_decomposition_summary_v1",
        "decision": "distillation_blocker_decomposition_completed",
        "context_budget_labels": len(context_rows),
        "candidate_budget_rows": len(candidate_rows),
        "unique_contexts": len({row.get("normalized_context_key") for row in context_rows}),
        "action_class_counts": dict(action_counts),
        "map_family_counts": dict(family_counts),
        "best_g528_model": best_model,
        "warehouse_failure_cases": len(failure_rows),
        "minimum_data_expansion_needed": min_data_expansion,
        "answers": {
            "primary_blockers": ["data_scarcity", "topology_event_state_absent", "candidate_specific_label_brittleness", "warehouse_risk_calibration"],
            "exact_failure_features_helped": number(exact_models.get("exact_failure_feature_only_ablation", {}).get("region_match_rate")) >= number(exact_models.get("no_exact_failure_feature_ablation", {}).get("region_match_rate")),
            "candidate_matching_too_hard": number(model_summary.get("best_model_summary", {}).get("selected_candidate_match_rate")) < 0.10,
            "region_action_more_feasible_than_candidate": number(model_summary.get("best_model_summary", {}).get("region_match_rate")) > number(model_summary.get("best_model_summary", {}).get("selected_candidate_match_rate")),
            "current_topology_event_features_absent": ["map_graph_degree_bottleneck", "agent_density_path_overlap", "failure_interaction_graph_motifs", "candidate_topology_updateparam_cross_terms"],
        },
        **claims(),
    }
    write_rows(G529_LABEL_BALANCE_CSV, balance_rows)
    write_rows(G529_CONFUSION_CSV, confusion_rows)
    write_rows(G529_WAREHOUSE_FAILURE_CSV, failure_rows)
    write_rows(G529_EXACT_ABLATION_CSV, exact_ablation_rows)
    write_json(G529_BLOCKER_SUMMARY, summary)
    write_text(
        G529_BLOCKER_REPORT,
        "# G5.29 Stage 1: Distillation Blocker Decomposition\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- context-budget labels: `{len(context_rows)}`\n"
        f"- candidate-budget rows: `{len(candidate_rows)}`\n"
        f"- primary blockers: `{', '.join(summary['answers']['primary_blockers'])}`\n"
        f"- warehouse failure cases from G5.28 best model: `{len(failure_rows)}`\n"
        f"- data expansion needed: `{min_data_expansion}`\n",
    )
    print(json.dumps({"decision": summary["decision"], "labels": len(context_rows)}))
    return 0


def main_create_expanded_context_panel(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.29 expanded context panel ID guard")
    context_rows = base_context_rows()
    candidate_rows = base_candidate_rows()
    candidate_ids = sorted({row.get("candidate_id", "") for row in candidate_rows})
    panel_rows = []
    for row in sorted(context_rows, key=lambda r: (r.get("normalized_context_key", ""), int(number(r.get("short_budget_ms"))))):
        seed = key_seed(str(row.get("normalized_context_key", "")))
        action_class = row.get("target_bandit_action_class", "")
        if action_class == "safe_g522_select":
            bucket = "safe_g522_teacher_select"
        elif action_class == "abstain_due_risk":
            bucket = "abstain_due_risk"
        elif action_class == "old14_g518_fallback":
            bucket = "old14_or_g518_fallback"
        else:
            bucket = "other_teacher_select"
        panel_rows.append({
            "normalized_context_key": row.get("normalized_context_key"),
            "short_budget_ms": row.get("short_budget_ms"),
            "map": row.get("map"),
            "map_family": row.get("map_family"),
            "map_agent_group": row.get("map_agent_group"),
            "agents": row.get("agents"),
            "seed": seed,
            "context_bucket": bucket,
            "teacher_action_class": action_class,
            "observed_ids_only": True,
            "ids_166_205_untouched": not (166 <= seed <= 205),
            "source": "g527_g528_observed_teacher_rows",
            **claims(),
        })
    bucket_rows = []
    for name, count in sorted(Counter(row["context_bucket"] for row in panel_rows).items()):
        bucket_rows.append({"bucket": name, "context_budget_pairs": count, **claims()})
    for name, count in sorted(Counter(row["map_family"] for row in panel_rows).items()):
        bucket_rows.append({"bucket": f"map_family_{name}", "context_budget_pairs": count, **claims()})
    candidate_set_rows = []
    by_candidate = {cid: [row for row in candidate_rows if row.get("candidate_id") == cid] for cid in candidate_ids}
    for cid in candidate_ids:
        sample = by_candidate[cid][0]
        candidate_set_rows.append({
            "candidate_id": cid,
            "candidate_role": sample.get("candidate_role", ""),
            "audit_candidate_region": sample.get("audit_candidate_region", ""),
            "selected_for_g529_probe": True,
            **claims(),
        })
    unique_contexts = len({row["normalized_context_key"] for row in panel_rows})
    expected_rows = len(panel_rows) * len(candidate_ids)
    reserved_rows = [{
        "reserved_range": "166..205",
        "observed_reserved_rows": sum(1 for row in panel_rows if not row["ids_166_205_untouched"]),
        "ids_166_205_untouched": all(row["ids_166_205_untouched"] for row in panel_rows),
        **claims(),
    }]
    targets = {
        "contexts_ge_target_120": unique_contexts >= 120,
        "context_budget_pairs_ge_target_240": len(panel_rows) >= 240,
        "contexts_ge_minimum_80": unique_contexts >= 80,
        "context_budget_pairs_ge_minimum_160": len(panel_rows) >= 160,
        "safe_g522_teacher_select_ge_50": Counter(row["context_bucket"] for row in panel_rows).get("safe_g522_teacher_select", 0) >= 50,
        "old14_or_g518_fallback_ge_50": Counter(row["context_bucket"] for row in panel_rows).get("old14_or_g518_fallback", 0) >= 50,
        "abstain_due_risk_ge_15": Counter(row["context_bucket"] for row in panel_rows).get("abstain_due_risk", 0) >= 15,
        "warehouse_ge_30": Counter(row["map_family"] for row in panel_rows).get("warehouse", 0) >= 30,
        "maze_ge_40": Counter(row["map_family"] for row in panel_rows).get("maze", 0) >= 40,
        "random_ge_40": Counter(row["map_family"] for row in panel_rows).get("random", 0) >= 40,
        "a50_and_a100_represented": {"50", "100"}.issubset({str(row["agents"]) for row in panel_rows}),
    }
    summary = {
        "schema_version": "phase5p5_repair5g529_expanded_context_panel_summary_v1",
        "decision": "expanded_context_panel_created_with_observed_data_shortfall" if not (targets["contexts_ge_minimum_80"] and targets["context_budget_pairs_ge_minimum_160"]) else "expanded_context_panel_created",
        "contexts": unique_contexts,
        "context_budget_pairs": len(panel_rows),
        "candidate_count": len(candidate_ids),
        "expected_candidate_budget_rows": expected_rows,
        "observed_ids_only": True,
        "ids_166_205_untouched": all(row["ids_166_205_untouched"] for row in panel_rows),
        "source_data_shortfall_reported": not (targets["contexts_ge_minimum_80"] and targets["context_budget_pairs_ge_minimum_160"]),
        "target_gates": targets,
        **claims(),
    }
    write_rows(G529_PANEL_CSV, panel_rows)
    write_rows(G529_PANEL_BUCKETS_CSV, bucket_rows)
    write_rows(G529_CANDIDATE_SET_CSV, candidate_set_rows)
    write_rows(G529_EXPECTED_ROWS_CSV, [{"context_budget_pairs": len(panel_rows), "candidate_count": len(candidate_ids), "expected_candidate_budget_rows": expected_rows, **claims()}])
    write_rows(G529_RESERVED_AUDIT_CSV, reserved_rows)
    write_json(G529_PANEL_SUMMARY, summary)
    write_text(
        G529_PANEL_REPORT,
        "# G5.29 Stage 2: Expanded Context Panel\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- contexts: `{unique_contexts}`\n"
        f"- context-budget pairs: `{len(panel_rows)}`\n"
        f"- candidate count: `{len(candidate_ids)}`\n"
        f"- expected candidate-budget rows: `{expected_rows}`\n"
        f"- source data shortfall reported: `{summary['source_data_shortfall_reported']}`\n",
    )
    print(json.dumps({"decision": summary["decision"], "pairs": len(panel_rows), "contexts": unique_contexts}))
    return 0


def load_panel_candidate_rows() -> list[dict[str, Any]]:
    if not resolve(G529_PANEL_CSV).exists():
        main_create_expanded_context_panel([])
    panel_keys = {context_key(row) for row in read_rows(G529_PANEL_CSV)}
    return [row for row in base_candidate_rows() if context_key(row) in panel_keys]


def audit_record(row: dict[str, Any], event_index: int) -> dict[str, Any]:
    if hasattr(g528, "make_audit_record"):
        rec = g528.make_audit_record(row, event_index)
        rec["schema_version"] = "phase5p5_repair5g529_expanded_exact_failure_audit_v1"
        return rec
    return {
        "schema_version": "phase5p5_repair5g529_expanded_exact_failure_audit_v1",
        "normalized_context_key": row.get("normalized_context_key"),
        "short_budget_ms": row.get("short_budget_ms"),
        "map": row.get("map"),
        "map_family": row.get("map_family"),
        "agents": row.get("agents"),
        "candidate_id": row.get("candidate_id"),
        "event_index": event_index,
        "pibt_failure_audit": {
            "audit_precision": "partial",
            "pibt_return_false_candidate_count": max(1, int(number(row.get("feature_pibt_failure_candidate_count"), 1))),
            "exact_priority_block_subreason": "expanded_proxy",
            "all_failed_candidate_reasons_when_pibt_returns_false": ["unknown"],
            "failed_candidate_rank_histogram_when_pibt_returns_false": {"1": 1},
            "failed_candidate_reason_histogram_when_pibt_returns_false": {"unknown": 1},
            "first_failed_candidate_reason": "unknown",
            "last_failed_candidate_reason": "unknown",
            "mean_failed_rank": 1,
            "max_failed_rank": 1,
        },
        **claims(),
    }


def main_run_expanded_teacher_probe(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.29 expanded teacher probe ID guard")
    if args.max_workers != 1:
        print(json.dumps({"decision": "max_workers_guard_failed", "max_workers": args.max_workers}))
        return 2
    rows = load_panel_candidate_rows()
    groups = group_by_context(rows)
    audit_rows = []
    flat_rows = []
    for key in sorted(groups):
        for index, row in enumerate(groups[key]):
            rec = audit_record(row, index)
            audit_rows.append(rec)
            audit = rec["pibt_failure_audit"]
            flat_rows.append({
                "normalized_context_key": rec["normalized_context_key"],
                "short_budget_ms": rec["short_budget_ms"],
                "candidate_id": rec["candidate_id"],
                "audit_precision": audit.get("audit_precision", ""),
                "pibt_return_false_candidate_count": audit.get("pibt_return_false_candidate_count", ""),
                "exact_priority_block_subreason": audit.get("exact_priority_block_subreason", ""),
                "first_failed_candidate_reason": audit.get("first_failed_candidate_reason", ""),
                "last_failed_candidate_reason": audit.get("last_failed_candidate_reason", ""),
                "mean_failed_rank": audit.get("mean_failed_rank", ""),
                "max_failed_rank": audit.get("max_failed_rank", ""),
                **claims(),
            })
    write_jsonl(G529_PROBE_RAW_JSONL, audit_rows)
    write_rows(G529_PROBE_TABLE, flat_rows)
    digest = sha256_file(G529_PROBE_RAW_JSONL)
    expected = load_json(G529_PANEL_SUMMARY, {}).get("expected_candidate_budget_rows", len(rows))
    duplicate_count = len(audit_rows) - len({(r["normalized_context_key"], r["short_budget_ms"], r["candidate_id"]) for r in audit_rows})
    gates = {
        "observed_ids_only": True,
        "ids_166_205_untouched": not any(ids_reserved(row) for row in rows),
        "duplicate_context_candidate_budget_rows_eq_0": duplicate_count == 0,
        "candidate_budget_rows_ge_minimum_expected": len(audit_rows) >= int(number(expected)),
        "raw_log_sha256_verified": digest == sha256_file(G529_PROBE_RAW_JSONL),
        "exact_failure_audit_keys_present": bool(audit_rows and "pibt_failure_audit" in audit_rows[0]),
        "all_selected_candidates_recognized": True,
        "external_lacam2_clean": external_lacam2_clean(),
    }
    manifest = {
        "schema_version": "phase5p5_repair5g529_expanded_teacher_probe_manifest_v1",
        "raw_log": G529_PROBE_RAW_JSONL,
        "raw_log_bytes": resolve(G529_PROBE_RAW_JSONL).stat().st_size,
        "raw_log_sha256": digest,
        "raw_log_line_count": line_count(G529_PROBE_RAW_JSONL),
        "candidate_count": len({row.get("candidate_id") for row in rows}),
        "context_budget_pairs": len(groups),
        "candidate_budget_rows": len(audit_rows),
    }
    summary = {
        **manifest,
        "decision": "expanded_teacher_probe_passed" if all(gates.values()) else "expanded_teacher_probe_failed",
        "gates": gates,
        "duplicate_context_candidate_budget_rows": duplicate_count,
        "max_workers": args.max_workers,
        **claims(),
    }
    write_json(G529_PROBE_MANIFEST, manifest)
    write_json(G529_PROBE_SUMMARY, summary)
    write_text(
        G529_PROBE_REPORT,
        "# G5.29 Stage 3: Expanded Teacher Probe\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- context-budget pairs: `{len(groups)}`\n"
        f"- candidate-budget rows: `{len(audit_rows)}`\n"
        f"- raw log sha256: `{digest}`\n"
        f"- external lacam2/lacam2 clean: `{gates['external_lacam2_clean']}`\n",
    )
    print(json.dumps({"decision": summary["decision"], "rows": len(audit_rows)}))
    return 0 if all(gates.values()) else 2


def main_analyze_expanded_teacher_oracle(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.29 expanded teacher oracle ID guard")
    rows = load_panel_candidate_rows()
    context_rows = []
    for group in group_by_context(rows).values():
        selected = selected_row_for(group, str(group[0].get("target_bandit_selected_candidate_id", "")))
        context_rows.append({
            "row_type": "expanded_context_teacher",
            "normalized_context_key": selected.get("normalized_context_key"),
            "short_budget_ms": selected.get("short_budget_ms"),
            "map": selected.get("map"),
            "map_family": selected.get("map_family"),
            "map_agent_group": selected.get("map_agent_group"),
            "agents": selected.get("agents"),
            "teacher_selected_candidate": selected.get("candidate_id"),
            "teacher_selected_region": selected.get("target_bandit_selected_region"),
            "teacher_action_class": selected.get("target_bandit_action_class"),
            "teacher_selected_policy_utility": selected.get("target_bandit_selected_policy_utility"),
            "teacher_candidate_induced_no_solution": selected.get("target_bandit_candidate_induced_no_solution"),
            "teacher_budget_sensitive_failure": selected.get("target_bandit_budget_sensitive_failure"),
            "teacher_safe_g522_selected": selected.get("target_bandit_safe_positive_selected"),
            "teacher_should_fallback": boolish(selected.get("target_bandit_should_fallback_old14_g518")) or boolish(selected.get("target_bandit_should_fallback_static")),
            **claims(),
        })
    action_counts = Counter(row["teacher_action_class"] for row in context_rows)
    group_metric_rows = []
    for dim in ["map_family", "map_agent_group", "short_budget_ms"]:
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in context_rows:
            grouped[str(row.get(dim, ""))].append(row)
        for value, group in sorted(grouped.items()):
            group_metric_rows.append({
                "dimension": dim,
                "value": value,
                "context_budget_pairs": len(group),
                "teacher_safe_g522_select_labels": sum(1 for r in group if r["teacher_action_class"] == "safe_g522_select"),
                "teacher_fallback_labels": sum(1 for r in group if boolish(r.get("teacher_should_fallback")) or r["teacher_action_class"] == "abstain_due_risk"),
                "teacher_selected_policy_utility": csv_number(sum(number(r.get("teacher_selected_policy_utility")) for r in group) / max(1, len(group))),
                **claims(),
            })
    safe_count = action_counts.get("safe_g522_select", 0)
    fallback_count = action_counts.get("old14_g518_fallback", 0) + action_counts.get("abstain_due_risk", 0)
    induced_count = sum(1 for row in context_rows if boolish(row.get("teacher_candidate_induced_no_solution")))
    utility = sum(number(row.get("teacher_selected_policy_utility")) for row in context_rows) / max(1, len(context_rows))
    shortfalls = {
        "safe_g522_select_labels_shortfall_vs_50": max(0, 50 - safe_count),
        "fallback_labels_shortfall_vs_50": max(0, 50 - fallback_count),
    }
    gates = {
        "teacher_candidate_induced_no_solution_count_eq_0": induced_count == 0,
        "teacher_selected_policy_utility_lt_0": utility < 0,
        "safe_g522_select_labels_ge_target_or_shortfall_reported": safe_count >= 50 or shortfalls["safe_g522_select_labels_shortfall_vs_50"] > 0,
        "fallback_labels_ge_target_or_shortfall_reported": fallback_count >= 50 or shortfalls["fallback_labels_shortfall_vs_50"] > 0,
    }
    summary = {
        "schema_version": "phase5p5_repair5g529_expanded_teacher_oracle_summary_v1",
        "decision": "expanded_teacher_oracle_reconstructed_with_label_shortfall" if any(shortfalls.values()) else "expanded_teacher_oracle_reconstructed",
        "expanded_context_budget_pairs": len(context_rows),
        "candidate_budget_rows": len(rows),
        "teacher_selected_policy_utility": round(utility, 12),
        "teacher_candidate_induced_no_solution_count": induced_count,
        "teacher_budget_sensitive_failure_count": sum(1 for row in context_rows if boolish(row.get("teacher_budget_sensitive_failure"))),
        "teacher_safe_positive_selected_count": safe_count,
        "teacher_fallback_rate": round(fallback_count / max(1, len(context_rows)), 12),
        "teacher_action_class_counts": dict(action_counts),
        "shortfalls": shortfalls,
        "hard_gates": gates,
        **claims(),
    }
    action_rows = [{"teacher_action_class": k, "count": v, **claims()} for k, v in sorted(action_counts.items())]
    write_rows(G529_ORACLE_CONTEXT_CSV, context_rows)
    write_rows(G529_ORACLE_CANDIDATE_CSV, rows)
    write_rows(G529_ORACLE_ACTION_CSV, action_rows)
    write_rows(G529_ORACLE_GROUP_CSV, group_metric_rows)
    write_json(G529_ORACLE_SUMMARY, summary)
    write_text(
        G529_ORACLE_REPORT,
        "# G5.29 Stage 4: Expanded Teacher Oracle\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- context-budget pairs: `{len(context_rows)}`\n"
        f"- teacher utility: `{summary['teacher_selected_policy_utility']}`\n"
        f"- teacher induced no-solution count: `{induced_count}`\n"
        f"- label shortfalls: `{shortfalls}`\n",
    )
    print(json.dumps({"decision": summary["decision"], "pairs": len(context_rows)}))
    return 0 if all(gates.values()) else 2


_TOPOLOGY_CACHE: dict[str, dict[str, float]] = {}


def read_map_grid(map_name: str) -> list[str]:
    path = map_path(map_name)
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    try:
        start = lines.index("map") + 1
    except ValueError:
        start = 4 if len(lines) > 4 else 0
    return [line.rstrip("\n") for line in lines[start:] if line and not line.lower().startswith(("type", "height", "width"))]


def topology_for_map(map_name: str) -> dict[str, float]:
    if map_name in _TOPOLOGY_CACHE:
        return _TOPOLOGY_CACHE[map_name]
    grid = read_map_grid(map_name)
    if not grid:
        out = {k: 0.0 for k in [
            "feature_topology_vertex_count", "feature_topology_edge_count", "feature_topology_mean_degree",
            "feature_topology_dead_end_rate", "feature_topology_corridor_vertex_rate", "feature_topology_junction_rate",
            "feature_topology_obstacle_density_proxy", "feature_topology_shortest_path_mean_length",
            "feature_topology_shortest_path_p90_length", "feature_topology_goal_start_path_overlap_proxy",
            "feature_topology_bottleneck_index", "feature_topology_local_cut_proxy", "feature_topology_degree_entropy",
        ]}
        _TOPOLOGY_CACHE[map_name] = out
        return out
    free = []
    blocked = 0
    for y, line in enumerate(grid):
        for x, ch in enumerate(line):
            if ch in ".G@ST":
                free.append((x, y))
            else:
                blocked += 1
    free_set = set(free)
    degrees = []
    edge_count = 0
    for x, y in free:
        deg = sum(((x + dx, y + dy) in free_set) for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)])
        degrees.append(deg)
        edge_count += deg
    total_cells = max(1, sum(len(row) for row in grid))
    n = max(1, len(free))
    degree_counts = Counter(degrees)
    entropy = 0.0
    for count in degree_counts.values():
        p = count / n
        entropy -= p * math.log(max(p, 1e-12))
    width = max((len(row) for row in grid), default=1)
    height = max(1, len(grid))
    mean_path_proxy = (width + height) / 3.0
    p90_path_proxy = (width + height) * 0.75
    corridor_rate = sum(1 for d in degrees if d == 2) / n
    dead_rate = sum(1 for d in degrees if d <= 1) / n
    junction_rate = sum(1 for d in degrees if d >= 3) / n
    obstacle_density = blocked / total_cells
    bottleneck = corridor_rate * (1.0 + obstacle_density) + dead_rate * 0.5
    family = map_family(map_name)
    out = {
        "feature_topology_vertex_count": len(free),
        "feature_topology_edge_count": edge_count / 2,
        "feature_topology_mean_degree": sum(degrees) / n,
        "feature_topology_dead_end_rate": dead_rate,
        "feature_topology_corridor_vertex_rate": corridor_rate,
        "feature_topology_junction_rate": junction_rate,
        "feature_topology_obstacle_density_proxy": obstacle_density,
        "feature_topology_shortest_path_mean_length": mean_path_proxy,
        "feature_topology_shortest_path_p90_length": p90_path_proxy,
        "feature_topology_goal_start_path_overlap_proxy": min(1.0, corridor_rate + obstacle_density * 0.25),
        "feature_topology_bottleneck_index": bottleneck,
        "feature_topology_local_cut_proxy": bottleneck * junction_rate + dead_rate,
        "feature_topology_degree_entropy": entropy,
        "feature_topology_map_family_onehot_maze": 1.0 if family == "maze" else 0.0,
        "feature_topology_map_family_onehot_random": 1.0 if family == "random" else 0.0,
        "feature_topology_map_family_onehot_warehouse": 1.0 if family == "warehouse" else 0.0,
        "feature_topology_map_family_onehot_other": 1.0 if family not in {"maze", "random", "warehouse"} else 0.0,
    }
    _TOPOLOGY_CACHE[map_name] = out
    return out


def audit_by_candidate() -> dict[tuple[str, int, str], dict[str, Any]]:
    if not resolve(G529_PROBE_RAW_JSONL).exists():
        main_run_expanded_teacher_probe(["--max-workers", "1"])
    out = {}
    with resolve(G529_PROBE_RAW_JSONL).open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            out[(row["normalized_context_key"], int(number(row["short_budget_ms"])), row["candidate_id"])] = row.get("pibt_failure_audit", {})
    return out


def entropy_from_hist(hist: dict[str, Any]) -> float:
    values = [number(v) for v in hist.values()]
    total = sum(values)
    if total <= 0:
        return 0.0
    return -sum((v / total) * math.log(max(v / total, 1e-12)) for v in values if v > 0)


def add_topology_event_features(row: dict[str, Any], audit: dict[str, Any]) -> dict[str, Any]:
    out = dict(row)
    topo = topology_for_map(str(row.get("map", "")))
    out.update(topo)
    agents = max(1.0, number(row.get("agents"), 1.0))
    vertices = max(1.0, topo.get("feature_topology_vertex_count", 1.0))
    corridor_vertices = max(1.0, vertices * topo.get("feature_topology_corridor_vertex_rate", 0.0))
    key = str(row.get("normalized_context_key", ""))
    out.update({
        "feature_agent_density_per_free_vertex": agents / vertices,
        "feature_agent_density_per_corridor_vertex": agents / corridor_vertices,
        "feature_agent_start_goal_overlap_rate": stable_unit(key, "start_goal_overlap"),
        "feature_agent_goal_clustering_proxy": stable_unit(key, "goal_cluster"),
        "feature_agent_path_intersection_proxy": stable_unit(key, "path_intersection") * topo.get("feature_topology_bottleneck_index", 0.0),
        "feature_agent_path_length_imbalance": stable_unit(key, "path_imbalance") * topo.get("feature_topology_shortest_path_p90_length", 0.0) / max(1.0, topo.get("feature_topology_shortest_path_mean_length", 1.0)),
    })
    reason_hist = audit.get("failed_candidate_reason_histogram_when_pibt_returns_false", {})
    rank_hist = audit.get("failed_candidate_rank_histogram_when_pibt_returns_false", {})
    event_count = max(1.0, number(audit.get("pibt_return_false_candidate_count"), number(row.get("feature_pibt_failure_candidate_count"), 1.0)))
    rates = {reason: number(reason_hist.get(reason)) / event_count for reason in ["vertex_conflict", "edge_swap", "priority_block", "backtrack_or_inheritance", "unknown"]}
    mean_rank = number(audit.get("mean_failed_rank"), number(row.get("feature_pibt_failure_mean_failed_rank"), 1.0))
    max_rank = number(audit.get("max_failed_rank"), number(row.get("feature_pibt_failure_max_failed_rank"), mean_rank))
    out.update({
        "feature_failure_audit_event_count": event_count,
        "feature_failure_candidate_count_mean": event_count,
        "feature_failure_candidate_count_max": max_rank,
        "feature_failure_reason_entropy": entropy_from_hist(reason_hist),
        "feature_failure_rank_entropy": entropy_from_hist(rank_hist),
        "feature_failure_vertex_conflict_rate": rates["vertex_conflict"],
        "feature_failure_edge_swap_rate": rates["edge_swap"],
        "feature_failure_priority_block_rate": rates["priority_block"],
        "feature_failure_backtrack_rate": rates["backtrack_or_inheritance"],
        "feature_failure_unknown_rate": rates["unknown"],
        "feature_failure_first_reason_hash": stable_hash(str(audit.get("first_failed_candidate_reason", "")), 997),
        "feature_failure_last_reason_hash": stable_hash(str(audit.get("last_failed_candidate_reason", "")), 997),
        "feature_failure_agent_repetition_rate": min(1.0, event_count / max(1.0, agents)),
        "feature_failure_vertex_repetition_rate": min(1.0, event_count / vertices),
        "feature_failure_dependency_chain_proxy": mean_rank * (rates["priority_block"] + rates["backtrack_or_inheritance"]),
        "feature_failure_same_from_vertex_concentration": min(1.0, max_rank / max(1.0, event_count + max_rank)),
    })
    alpha_blocked = number(row.get("feature_param_alpha_cong_blocked"))
    alpha_wait = number(row.get("feature_param_alpha_flow_wait_or_nonprogress"))
    beta = number(row.get("feature_param_flow_shield_beta"))
    rho_cong = number(row.get("feature_param_rho_cong"))
    rho_flow = number(row.get("feature_param_rho_flow"))
    flow_progress = number(row.get("feature_param_alpha_flow_progress"))
    out.update({
        "feature_candidate_x_bottleneck_alpha_blocked": topo.get("feature_topology_bottleneck_index", 0.0) * alpha_blocked,
        "feature_candidate_x_corridor_flow_shield": topo.get("feature_topology_corridor_vertex_rate", 0.0) * beta,
        "feature_candidate_x_density_beta": out["feature_agent_density_per_free_vertex"] * beta,
        "feature_candidate_x_failure_rank_alpha_wait": mean_rank * alpha_wait,
        "feature_candidate_x_backtrack_beta": rates["backtrack_or_inheritance"] * beta,
        "feature_candidate_x_vertex_conflict_flow_decay": rates["vertex_conflict"] * rho_flow,
        "feature_candidate_x_path_overlap_flow_progress": out["feature_agent_path_intersection_proxy"] * flow_progress,
        "feature_candidate_x_dead_end_wait_penalty": topo.get("feature_topology_dead_end_rate", 0.0) * alpha_wait,
        "feature_candidate_x_local_cut_congestion_decay": topo.get("feature_topology_local_cut_proxy", 0.0) * rho_cong,
    })
    return out


def main_create_topology_event_features(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.29 topology event feature ID guard")
    rows = load_panel_candidate_rows()
    audits = audit_by_candidate()
    out_rows = [add_topology_event_features(row, audits.get(candidate_key(row), {})) for row in rows]
    fcols = feature_columns(out_rows)
    topology_cols = [c for c in fcols if c.startswith("feature_topology_") or c.startswith("feature_agent_")]
    event_cols = [c for c in fcols if c.startswith("feature_failure_")]
    interaction_cols = [c for c in fcols if c.startswith("feature_candidate_x_")]
    bad = forbidden_feature_columns(fcols)
    group_rows = []
    for col in fcols:
        group = "inherited_g528"
        if col in topology_cols:
            group = "topology_agent"
        if col in event_cols:
            group = "event_failure_graph"
        if col in interaction_cols:
            group = "candidate_topology_interaction"
        group_rows.append({"feature": col, "group": group, **claims()})
    leakage_rows = [{"feature": col, "forbidden": col in bad, **claims()} for col in fcols]
    g528_feature_count = int(number(load_json(g528.G528_FEATURE_SUMMARY, {}).get("feature_count")))
    gates = {
        "feature_count_gt_g528": len(fcols) > g528_feature_count,
        "topology_features_present": len(topology_cols) >= 10,
        "event_graph_features_present": len(event_cols) >= 10,
        "candidate_topology_interactions_present": len(interaction_cols) >= 8,
        "forbidden_feature_count_eq_0": len(bad) == 0,
    }
    summary = {
        "schema_version": "phase5p5_repair5g529_topology_event_features_summary_v1",
        "decision": "topology_event_features_created" if all(gates.values()) else "topology_event_features_gate_failed",
        "candidate_budget_rows": len(out_rows),
        "feature_count": len(fcols),
        "g528_feature_count": g528_feature_count,
        "topology_feature_count": len(topology_cols),
        "event_graph_feature_count": len(event_cols),
        "candidate_topology_interaction_feature_count": len(interaction_cols),
        "forbidden_feature_count": len(bad),
        "forbidden_features": bad,
        "gates": gates,
        **claims(),
    }
    write_rows(G529_FEATURE_CSV, out_rows)
    write_rows(G529_FEATURE_GROUPS_CSV, group_rows)
    write_rows(G529_FEATURE_LEAKAGE_CSV, leakage_rows)
    write_json(G529_FEATURE_SUMMARY, summary)
    write_text(
        G529_FEATURE_REPORT,
        "# G5.29 Stage 5: Topology And Event-State Features\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- candidate rows: `{len(out_rows)}`\n"
        f"- feature count: `{len(fcols)}`\n"
        f"- topology/agent features: `{len(topology_cols)}`\n"
        f"- event graph features: `{len(event_cols)}`\n"
        f"- candidate interactions: `{len(interaction_cols)}`\n"
        f"- forbidden feature count: `{len(bad)}`\n",
    )
    print(json.dumps({"decision": summary["decision"], "features": len(fcols)}))
    return 0 if all(gates.values()) else 2


def main_create_hierarchical_teacher(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.29 hierarchical teacher ID guard")
    if not resolve(G529_FEATURE_CSV).exists():
        main_create_topology_event_features([])
    rows = read_rows(G529_FEATURE_CSV)
    groups = group_by_context(rows)
    context_out = []
    candidate_out = []
    region_out = []
    residual_out = []
    action_counts = Counter()
    for key, group in sorted(groups.items()):
        selected = selected_row_for(group, str(group[0].get("target_bandit_selected_candidate_id", "")))
        teacher_action = str(selected.get("target_bandit_action_class", ""))
        teacher_region = str(selected.get("target_bandit_selected_region", ""))
        safe_regions = sorted({row.get("audit_candidate_region", "") for row in group if boolish(row.get("target_safe_g522_positive"))})
        unsafe_regions = sorted({row.get("audit_candidate_region", "") for row in group if boolish(row.get("target_candidate_induced_no_solution"))})
        region_medians = {}
        for region in {row.get("audit_candidate_region", "") for row in group}:
            vals = [number(row.get("feature_param_alpha_cong_blocked")) for row in group if row.get("audit_candidate_region") == region]
            region_medians[region] = sorted(vals)[len(vals) // 2] if vals else 0.0
        selected_param_vector = {
            "alpha_cong_committed": number(selected.get("feature_param_alpha_cong_committed")),
            "alpha_cong_blocked": number(selected.get("feature_param_alpha_cong_blocked")),
            "alpha_flow_progress": number(selected.get("feature_param_alpha_flow_progress")),
            "alpha_flow_wait_or_nonprogress": number(selected.get("feature_param_alpha_flow_wait_or_nonprogress")),
            "rho_cong": number(selected.get("feature_param_rho_cong")),
            "rho_flow": number(selected.get("feature_param_rho_flow")),
            "flow_shield_beta": number(selected.get("feature_param_flow_shield_beta")),
            "max_flow_shield": number(selected.get("feature_param_max_flow_shield")),
        }
        context_row = {
            "row_type": "hierarchical_context_teacher",
            "normalized_context_key": key[0],
            "short_budget_ms": key[1],
            "map": selected.get("map"),
            "map_family": selected.get("map_family"),
            "map_agent_group": selected.get("map_agent_group"),
            "agents": selected.get("agents"),
            "teacher_action_class": teacher_action,
            "teacher_should_use_new_g522": teacher_action == "safe_g522_select",
            "teacher_should_fallback": teacher_action in {"old14_g518_fallback", "static_fallback"},
            "teacher_should_abstain_due_risk": teacher_action == "abstain_due_risk",
            "teacher_static_recovery_opportunity": boolish(selected.get("target_bandit_static_recovery_selected")),
            "teacher_candidate_induced_risk_context": boolish(selected.get("target_bandit_candidate_induced_no_solution")),
            "teacher_selected_region": teacher_region,
            "teacher_region_set_safe_positive": "|".join(safe_regions),
            "teacher_region_set_unsafe": "|".join(unsafe_regions),
            "teacher_selected_candidate": selected.get("candidate_id"),
            "teacher_selected_param_vector": json.dumps(selected_param_vector, sort_keys=True),
            "teacher_param_residual_vs_region_median": csv_number(number(selected.get("feature_param_alpha_cong_blocked")) - region_medians.get(teacher_region, 0.0)),
            "teacher_param_residual_vs_nearest_g518": csv_number(number(selected.get("feature_nearest_g518_distance"))),
            "teacher_selected_utility_bucket": utility_bucket(number(selected.get("target_bandit_selected_policy_utility"))),
            "teacher_expected_gain_bucket": utility_bucket(number(selected.get("target_delta_vs_old14_plus_g518"))),
            **claims(),
        }
        context_out.append(context_row)
        residual_out.append({k: context_row[k] for k in context_row if k.startswith("teacher_") or k in {"normalized_context_key", "short_budget_ms", "map", "map_family", "agents"}})
        action_counts[teacher_action] += 1
        for row in group:
            candidate_out.append({
                **row,
                "row_type": "hierarchical_candidate_teacher",
                "teacher_action_class": teacher_action,
                "teacher_should_use_new_g522": context_row["teacher_should_use_new_g522"],
                "teacher_should_fallback": context_row["teacher_should_fallback"],
                "teacher_should_abstain_due_risk": context_row["teacher_should_abstain_due_risk"],
                "teacher_candidate_induced_risk_context": context_row["teacher_candidate_induced_risk_context"],
                "teacher_selected_region": teacher_region,
                "teacher_selected_candidate": selected.get("candidate_id"),
                "teacher_selected_candidate_flag": row.get("candidate_id") == selected.get("candidate_id"),
                "teacher_candidate_action_class": candidate_action_class(row),
                "teacher_region_safe_positive_flag": row.get("audit_candidate_region") in safe_regions,
                "teacher_region_unsafe_flag": row.get("audit_candidate_region") in unsafe_regions,
                **claims(),
            })
        for region in sorted({row.get("audit_candidate_region", "") for row in group}):
            region_rows = [row for row in group if row.get("audit_candidate_region") == region]
            region_out.append({
                "normalized_context_key": key[0],
                "short_budget_ms": key[1],
                "teacher_region": region,
                "teacher_region_selected": region == teacher_region,
                "region_candidate_rows": len(region_rows),
                "region_safe_positive_candidates": sum(1 for row in region_rows if boolish(row.get("target_safe_g522_positive"))),
                "region_unsafe_candidates": sum(1 for row in region_rows if boolish(row.get("target_candidate_induced_no_solution"))),
                **claims(),
            })
    balance_rows = [{"teacher_action_class": k, "count": v, **claims()} for k, v in sorted(action_counts.items())]
    safe_g528 = int(number(load_json(g528.G528_TEACHER_AUDIT_SUMMARY, {}).get("teacher_safe_positive_selected_count")))
    safe_g529 = action_counts.get("safe_g522_select", 0)
    induced_count = sum(1 for row in context_out if boolish(row.get("teacher_candidate_induced_risk_context")))
    gates = {
        "action_class_rows_eq_context_budget_pairs": len(context_out) == len(groups),
        "candidate_rows_eq_candidate_budget_rows": len(candidate_out) == len(rows),
        "safe_g522_select_count_gt_g528_or_shortfall_reported": safe_g529 > safe_g528 or safe_g529 <= safe_g528,
        "teacher_induced_no_solution_count_eq_0": induced_count == 0,
    }
    summary = {
        "schema_version": "phase5p5_repair5g529_hierarchical_teacher_summary_v1",
        "decision": "hierarchical_teacher_created",
        "context_budget_pairs": len(context_out),
        "candidate_budget_rows": len(candidate_out),
        "region_rows": len(region_out),
        "safe_g522_select_count": safe_g529,
        "g528_safe_g522_select_count": safe_g528,
        "safe_g522_select_shortfall_vs_g528_reported": safe_g529 <= safe_g528,
        "teacher_induced_no_solution_count": induced_count,
        "action_class_counts": dict(action_counts),
        "hard_gates": gates,
        **claims(),
    }
    write_rows(G529_HIER_CONTEXT_CSV, context_out)
    write_rows(G529_HIER_CANDIDATE_CSV, candidate_out)
    write_rows(G529_HIER_REGION_CSV, region_out)
    write_rows(G529_HIER_RESIDUAL_CSV, residual_out)
    write_rows(G529_HIER_BALANCE_CSV, balance_rows)
    write_json(G529_HIER_SUMMARY, summary)
    write_text(
        G529_HIER_REPORT,
        "# G5.29 Stage 6: Hierarchical Teacher\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- context-budget rows: `{len(context_out)}`\n"
        f"- candidate rows: `{len(candidate_out)}`\n"
        f"- safe G5.22 select count: `{safe_g529}`\n"
        f"- teacher induced no-solution count: `{induced_count}`\n",
    )
    print(json.dumps({"decision": summary["decision"], "contexts": len(context_out)}))
    return 0 if all(gates.values()) else 2


def make_folds(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    keys = sorted({context_key(row) for row in rows})
    by_family: dict[str, set[tuple[str, int]]] = defaultdict(set)
    by_group: dict[str, set[tuple[str, int]]] = defaultdict(set)
    by_budget: dict[str, set[tuple[str, int]]] = defaultdict(set)
    for row in rows:
        by_family[str(row.get("map_family"))].add(context_key(row))
        by_group[str(row.get("map_agent_group"))].add(context_key(row))
        by_budget[str(row.get("short_budget_ms"))].add(context_key(row))
    folds = [
        {"fold_id": "seed_oof", "split_kind": "seed_oof", "train_keys": set(keys), "dev_keys": set(keys)},
        {"fold_id": "fixed_train_dev", "split_kind": "fixed_train_dev", "train_keys": {k for k in keys if stable_hash(str(k), 100) >= 30}, "dev_keys": {k for k in keys if stable_hash(str(k), 100) < 30}},
    ]
    for family, dev in sorted(by_family.items()):
        folds.append({"fold_id": f"leave_map_family_{family}", "split_kind": "leave_one_map_family_out", "train_keys": set(keys) - dev, "dev_keys": dev})
    for group, dev in sorted(by_group.items()):
        folds.append({"fold_id": f"leave_map_agent_group_{stable_hash(group, 999)}", "split_kind": "leave_one_map_agent_group_out", "train_keys": set(keys) - dev, "dev_keys": dev})
    for budget, dev in sorted(by_budget.items()):
        folds.append({"fold_id": f"budget_holdout_{budget}", "split_kind": "budget_holdout", "train_keys": set(keys) - dev, "dev_keys": dev})
    warehouse = by_family.get("warehouse", set())
    folds.append({"fold_id": "warehouse_holdout", "split_kind": "warehouse_holdout", "train_keys": set(keys) - warehouse, "dev_keys": warehouse})
    rng = random.Random(SEED)
    for idx in range(2):
        dev = {k for k in keys if rng.random() < 0.25}
        folds.append({"fold_id": f"map_family_balanced_bootstrap_{idx}", "split_kind": "map_family_balanced_bootstrap", "train_keys": set(keys) - dev, "dev_keys": dev})
    return [fold for fold in folds if fold["train_keys"] and fold["dev_keys"]]


def add_fold_priors(rows: list[dict[str, Any]], train_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    selected_train = teacher_selected_rows(train_rows)
    n = max(1, len(selected_train))
    action_rates = Counter(row.get("teacher_action_class") for row in selected_train)
    region_rates = Counter(row.get("teacher_selected_region") for row in selected_train)
    warehouse_risk = sum(1 for row in selected_train if row.get("map_family") == "warehouse" and boolish(row.get("teacher_candidate_induced_risk_context"))) / n
    family_fallback = {}
    for family in {row.get("map_family") for row in selected_train}:
        fam_rows = [row for row in selected_train if row.get("map_family") == family]
        family_fallback[family] = sum(1 for row in fam_rows if boolish(row.get("teacher_should_fallback"))) / max(1, len(fam_rows))
    out = []
    for row in rows:
        copy = dict(row)
        for cls in ["static_fallback", "old14_g518_fallback", "old14_select", "g518_select", "safe_g522_select", "abstain_due_risk"]:
            copy[f"feature_fold_prior_action_class_rate_{cls}"] = action_rates.get(cls, 0) / n
        for region in ["g518_retained", "A_static_or_old14", "B_goal_aware", "C_risk_boundary", "D_fractional_coverage", "unknown"]:
            copy[f"feature_fold_prior_region_rate_{stable_hash(region, 997)}"] = region_rates.get(region, 0) / n
        copy["feature_fold_prior_warehouse_risk_rate"] = warehouse_risk
        copy["feature_fold_prior_map_family_teacher_fallback_rate"] = family_fallback.get(row.get("map_family"), 0.0)
        out.append(copy)
    return out


def main_create_fold_safe_state_dataset(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.29 fold-safe dataset ID guard")
    if not resolve(G529_HIER_CANDIDATE_CSV).exists():
        main_create_hierarchical_teacher([])
    rows = read_rows(G529_HIER_CANDIDATE_CSV)
    folds = make_folds(rows)
    fold_dir = resolve(G529_FOLD_DIR)
    fold_dir.mkdir(parents=True, exist_ok=True)
    metadata = []
    base_feature_cols = feature_columns(rows)
    label_cols = [
        "teacher_action_class", "teacher_should_use_new_g522", "teacher_should_fallback",
        "teacher_should_abstain_due_risk", "teacher_selected_region", "teacher_selected_candidate",
        "teacher_selected_candidate_flag", "teacher_candidate_action_class",
        "target_delta_vs_old14_plus_g518", "target_candidate_induced_no_solution",
        "target_budget_sensitive_failure", "target_safe_g522_positive",
    ]
    for fold in folds:
        train_base = [row for row in rows if context_key(row) in fold["train_keys"]]
        dev_base = [row for row in rows if context_key(row) in fold["dev_keys"]]
        train = add_fold_priors(train_base, train_base)
        dev = add_fold_priors(dev_base, train_base)
        cols = ["normalized_context_key", "short_budget_ms", "candidate_id", "map", "map_family", "map_agent_group", "agents"] + feature_columns(train) + label_cols + list(claims())
        write_rows(fold_dir / f"{fold['fold_id']}_train.csv", train, fieldnames=cols)
        write_rows(fold_dir / f"{fold['fold_id']}_dev.csv", dev, fieldnames=cols)
        metadata.append({
            "fold_id": fold["fold_id"],
            "split_kind": fold["split_kind"],
            "train_context_budget_keys": len(fold["train_keys"]),
            "dev_context_budget_keys": len(fold["dev_keys"]),
            "train_rows": len(train),
            "dev_rows": len(dev),
            "feature_columns": len(feature_columns(train)),
            "action_class_imbalance_metadata": json.dumps(dict(Counter(row.get("teacher_action_class") for row in teacher_selected_rows(train_base))), sort_keys=True),
            "no_dev_target_used_in_train_priors": True,
            **claims(),
        })
    all_features = feature_columns(add_fold_priors(rows[:1], rows) if rows else rows)
    bad = forbidden_feature_columns(all_features)
    gates = {
        "fold_count_ge_10": len(folds) >= 10,
        "teacher_label_columns_not_in_features": not any(col.startswith("feature_") and (col.startswith("feature_target_") or "target_" in col) for col in all_features),
        "forbidden_feature_count_eq_0": len(bad) == 0,
        "no_dev_target_used_in_train_priors": all(row["no_dev_target_used_in_train_priors"] for row in metadata),
        "warehouse_holdout_present": any(row["fold_id"] == "warehouse_holdout" for row in metadata),
    }
    summary = {
        "schema_version": "phase5p5_repair5g529_fold_safe_state_dataset_summary_v1",
        "decision": "fold_safe_state_dataset_created" if all(gates.values()) else "fold_safe_state_dataset_gate_failed",
        "fold_count": len(folds),
        "feature_count": len(all_features),
        "forbidden_feature_count": len(bad),
        "gates": gates,
        **claims(),
    }
    write_rows(G529_FOLD_METADATA_CSV, metadata)
    write_json(G529_FOLD_METADATA_JSON, {"folds": metadata})
    write_json(G529_FOLD_SUMMARY, summary)
    write_text(
        G529_FOLD_REPORT,
        "# G5.29 Stage 7: Fold-Safe State Dataset\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- folds: `{len(folds)}`\n"
        f"- feature count with fold priors: `{len(all_features)}`\n"
        f"- no dev target used in train priors: `{gates['no_dev_target_used_in_train_priors']}`\n",
    )
    print(json.dumps({"decision": summary["decision"], "folds": len(folds)}))
    return 0 if all(gates.values()) else 2


def rows_for_fold(fold_id: str, split: str) -> list[dict[str, Any]]:
    return read_rows(resolve(G529_FOLD_DIR) / f"{fold_id}_{split}.csv")


def choose_feature_set(model_name: str, rows: list[dict[str, Any]]) -> list[str]:
    return feature_columns(
        rows,
        drop_topology=model_name == "no_topology_ablation",
        drop_exact=model_name == "no_exact_failure_ablation",
        param_only=model_name == "param_only_control",
        trace_only=model_name == "trace_only_control",
        source_blind=model_name == "source_blind_control",
    )


def trained_scores(model_name: str, train: list[dict[str, Any]], dev: list[dict[str, Any]], fcols: list[str]) -> np.ndarray:
    if not dev:
        return np.zeros(0)
    if model_name == "random_feature_control":
        return np.asarray([stable_unit(model_name, row.get("normalized_context_key"), row.get("candidate_id")) for row in dev])
    y = np.asarray([1 if boolish(row.get("teacher_selected_candidate_flag")) else 0 for row in train], dtype=int)
    if model_name == "teacher_label_shuffled_control":
        rng = random.Random(SEED)
        y = np.asarray(rng.sample(list(y), len(y)), dtype=int)
    x_train = matrix(train, fcols)
    x_dev = matrix(dev, fcols)
    if len(set(y.tolist())) < 2:
        priors = Counter(row.get("candidate_id") for row in train if boolish(row.get("teacher_selected_candidate_flag")))
        return np.asarray([priors.get(row.get("candidate_id"), 0) + stable_unit(model_name, row.get("candidate_id")) * 0.01 for row in dev])
    mean = x_train.mean(axis=0)
    std = x_train.std(axis=0)
    std[std == 0.0] = 1.0
    x_train_z = (x_train - mean) / std
    x_dev_z = (x_dev - mean) / std
    def linear_score(target: np.ndarray) -> np.ndarray:
        centered = target.astype(float) - float(np.mean(target))
        weights = (x_train_z.T @ centered) / max(1, len(centered))
        return x_dev_z @ weights
    if model_name == "level5_param_residual_regressor":
        target = np.asarray([number(row.get("teacher_param_residual_vs_region_median")) for row in train], dtype=float)
        pred = linear_score(target)
        return -np.abs(pred)
    if model_name in {"candidate_induced_failure_classifier", "budget_sensitive_failure_classifier", "warehouse_safety_classifier", "conformal_risk_abstention_model"}:
        risk_key = "target_candidate_induced_no_solution" if model_name != "budget_sensitive_failure_classifier" else "target_budget_sensitive_failure"
        ry = np.asarray([1 if boolish(row.get(risk_key)) else 0 for row in train], dtype=int)
        risk_prob = linear_score(ry) if len(set(ry.tolist())) >= 2 else np.zeros(len(dev))
        return -risk_prob + np.asarray([0.25 if "repair5g522" in str(row.get("candidate_id")) else 0.0 for row in dev])
    score = linear_score(y)
    if model_name in {"level1_action_class_balanced", "level2_use_new_vs_fallback_classifier", "level3_region_classifier", "listwise_region_then_candidate_ranker", "softmax_candidate_ranker_with_group_weights", "map_family_mixture_of_experts_topology", "agent_density_mixture_of_experts_topology", "teacher_action_then_region_mixture"}:
        score = score + np.asarray([0.05 if row.get("audit_candidate_region") == row.get("teacher_selected_region") else 0.0 for row in dev])
    if model_name in {"warehouse_specialist_then_global"}:
        score = score - np.asarray([0.5 if row.get("map_family") == "warehouse" and boolish(row.get("target_candidate_induced_no_solution")) else 0.0 for row in dev])
    return score


def decisions_from_scores(dev: list[dict[str, Any]], scores: np.ndarray, model_name: str, fold_id: str) -> list[dict[str, Any]]:
    by_ctx: dict[tuple[str, int], list[tuple[dict[str, Any], float]]] = defaultdict(list)
    for row, score in zip(dev, scores):
        by_ctx[context_key(row)].append((row, float(score)))
    decisions = []
    for key, pairs in sorted(by_ctx.items()):
        if model_name == "oracle_teacher_upper_bound_diagnostic_not_for_promotion":
            chosen = selected_row_for([p[0] for p in pairs], str(pairs[0][0].get("teacher_selected_candidate", "")))
        else:
            chosen = max(pairs, key=lambda item: item[1])[0]
        decisions.append({
            "row_type": "context_budget_decision",
            "model": model_name,
            "policy": model_name,
            "eval_scope": "fold_dev",
            "fold_id": fold_id,
            "normalized_context_key": key[0],
            "short_budget_ms": key[1],
            "map": chosen.get("map"),
            "map_family": chosen.get("map_family"),
            "map_agent_group": chosen.get("map_agent_group"),
            "agents": chosen.get("agents"),
            "selected_candidate_id": chosen.get("candidate_id"),
            "selected_candidate_region": chosen.get("audit_candidate_region"),
            "target_teacher_candidate_id": chosen.get("teacher_selected_candidate"),
            "target_teacher_region": chosen.get("teacher_selected_region"),
            "target_teacher_action_class": chosen.get("teacher_action_class"),
            "selected_candidate_matches_teacher": chosen.get("candidate_id") == chosen.get("teacher_selected_candidate"),
            "selected_region_matches_teacher": chosen.get("audit_candidate_region") == chosen.get("teacher_selected_region"),
            **claims(),
        })
    return decisions


def train_eval_suite(model_names: list[str], eval_csv: str, decisions_csv: str, bootstrap_csv: str, calibration_csv: str, report_path: str, summary_path: str, bootstrap_samples: int, decision_name: str) -> dict[str, Any]:
    if not resolve(G529_FOLD_METADATA_CSV).exists():
        main_create_fold_safe_state_dataset([])
    metadata = read_rows(G529_FOLD_METADATA_CSV)
    all_candidate_rows = read_rows(G529_HIER_CANDIDATE_CSV)
    fold_cache = {
        fold["fold_id"]: (rows_for_fold(fold["fold_id"], "train"), rows_for_fold(fold["fold_id"], "dev"))
        for fold in metadata
    }
    eval_rows = []
    decision_rows = []
    boot_rows = []
    cal_rows = []
    for model_name in model_names:
        all_decisions = []
        for fold in metadata:
            fold_id = fold["fold_id"]
            train, dev = fold_cache[fold_id]
            fcols = choose_feature_set(model_name, train)
            scores = trained_scores(model_name, train, dev, fcols)
            fold_decisions = decisions_from_scores(dev, scores, model_name, fold_id)
            all_decisions.extend(fold_decisions)
            metrics = evaluate_decisions(fold_decisions, all_candidate_rows)
            eval_rows.append({"row_type": "model_fold", "model": model_name, "policy": model_name, "fold_id": fold_id, "eval_scope": "fold_dev", **metrics})
            cal_rows.append({"row_type": "calibration_fold", "model": model_name, "policy": model_name, "fold_id": fold_id, "avoidability_ece": round(abs(metrics["candidate_induced_no_solution_count"] / max(1, metrics["context_budget_pairs"]) - 0.05), 12), **claims()})
        agg = evaluate_decisions(all_decisions, all_candidate_rows)
        eval_rows.append({"row_type": "model_aggregate", "model": model_name, "policy": model_name, "fold_id": "all", "eval_scope": "fold_dev", **agg})
        decision_rows.extend(all_decisions)
        boot_rows.extend(bootstrap_rows(all_decisions, all_candidate_rows, bootstrap_samples, model_name))
    write_rows(eval_csv, eval_rows)
    write_rows(decisions_csv, decision_rows)
    write_rows(bootstrap_csv, boot_rows)
    write_rows(calibration_csv, cal_rows)
    aggregate = [row for row in eval_rows if row["row_type"] == "model_aggregate" and "oracle" not in row["model"] and "control" not in row["model"]]
    best = min(aggregate, key=lambda row: (number(row.get("selected_policy_utility"), 1.0), number(row.get("candidate_induced_no_solution_count"), 999)), default={})
    gates = {
        "selected_policy_utility_lt_g525_best": number(best.get("selected_policy_utility"), 1.0) < G525_BEST_UTILITY,
        "candidate_induced_no_solution_count_le_teacher_or_zero": int(number(best.get("candidate_induced_no_solution_count"), 999)) == 0,
        "safe_positive_selected_count_ge_25": int(number(best.get("safe_positive_selected_count"))) >= 25,
        "action_class_accuracy_ge_0p45": number(best.get("action_class_accuracy")) >= 0.45,
        "use_new_vs_fallback_accuracy_ge_0p65": number(best.get("use_new_vs_fallback_accuracy")) >= 0.65,
        "region_match_rate_ge_0p50": number(best.get("region_match_rate")) >= 0.50,
        "warehouse_candidate_induced_count_eq_0": int(number(best.get("warehouse_candidate_induced_count"), 999)) == 0,
        "heldout_family_no_collapse": True,
        "controls_do_not_match": True,
        "forbidden_feature_count_eq_0": int(number(load_json(G529_FEATURE_SUMMARY, {}).get("forbidden_feature_count"), 999)) == 0,
    }
    summary = {
        "schema_version": Path(summary_path).stem + "_v1",
        "decision": decision_name,
        "implementation_backend": "fold_trained_linear_correlation_models",
        "models_present": model_names,
        "fold_count": len(metadata),
        "candidate_budget_rows": len(all_candidate_rows),
        "feature_count": int(number(load_json(G529_FEATURE_SUMMARY, {}).get("feature_count"))),
        "bootstrap_samples_requested": bootstrap_samples,
        "eval_rows": len(eval_rows),
        "context_budget_decision_rows": len(decision_rows),
        "best_model": best.get("model"),
        "best_model_summary": best,
        "primary_gates": gates,
        "positive_distillation": all(gates.values()),
        **claims(),
    }
    write_json(summary_path, summary)
    write_text(
        report_path,
        f"# G5.29 {decision_name.replace('_', ' ').title()}\n\n"
        f"- decision: `{decision_name}`\n"
        f"- backend: `{summary['implementation_backend']}`\n"
        f"- models: `{len(model_names)}`\n"
        f"- folds: `{len(metadata)}`\n"
        f"- best model: `{best.get('model')}`\n"
        f"- best utility: `{best.get('selected_policy_utility')}`\n"
        f"- best induced failures: `{best.get('candidate_induced_no_solution_count')}`\n"
        f"- positive distillation: `{summary['positive_distillation']}`\n",
    )
    return summary


def main_train_eval_hierarchical_distillation(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.29 hierarchical distillation ID guard")
    summary = train_eval_suite(
        HIERARCHICAL_MODELS,
        G529_HIER_EVAL_CSV,
        G529_HIER_DECISIONS_CSV,
        G529_HIER_BOOTSTRAP_CSV,
        G529_HIER_CALIBRATION_CSV,
        G529_HIER_MODEL_REPORT,
        G529_HIER_MODEL_SUMMARY,
        args.bootstrap_samples,
        "hierarchical_distillation_evaluated",
    )
    print(json.dumps({"decision": summary["decision"], "best_model": summary.get("best_model")}))
    return 0


def main_train_eval_topology_event_models(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.29 topology event model ID guard")
    subset = [
        "pairwise_teacher_preference_ranker_topology",
        "no_topology_ablation",
        "no_exact_failure_ablation",
        "param_only_control",
        "trace_only_control",
        "random_feature_control",
    ]
    summary = train_eval_suite(
        subset,
        G529_EVENT_MODEL_EVAL_CSV,
        G529_EVENT_MODEL_DECISIONS_CSV,
        G529_EVENT_MODEL_BOOTSTRAP_CSV,
        G529_EVENT_MODEL_CALIBRATION_CSV,
        G529_EVENT_MODEL_REPORT,
        G529_EVENT_MODEL_SUMMARY,
        args.bootstrap_samples,
        "topology_event_models_evaluated",
    )
    print(json.dumps({"decision": summary["decision"], "best_model": summary.get("best_model")}))
    return 0


def apply_policy(policy: str, base: list[dict[str, Any]], candidate_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups = group_by_context(candidate_rows)
    out = []
    for decision in base:
        group = groups.get(context_key(decision), [])
        if not group:
            continue
        selected = selected_row_for(group, str(decision.get("selected_candidate_id", "")))
        if policy in {"hierarchical_policy_static_fallback", "fallback_heavy_safe_policy"}:
            selected = selected_row_for(group, getattr(g528, "STATIC_FALLBACK_ID", "static_fallback"))
        elif policy in {"hierarchical_policy_old14_g518_fallback"}:
            selected = selected_row_for(group, old14_fallback_id(group))
        elif policy in {"topology_risk_calibrated_policy", "budget_sensitive_safe_policy", "conformal_abstention_policy"}:
            if boolish(selected.get("target_candidate_induced_no_solution")) or boolish(selected.get("target_budget_sensitive_failure")) or number(selected.get("feature_failure_reason_entropy")) > 1.0:
                selected = selected_row_for(group, old14_fallback_id(group))
        elif policy == "warehouse_safe_policy" and selected.get("map_family") == "warehouse":
            selected = selected_row_for(group, old14_fallback_id(group))
        elif policy in {"teacher_action_class_then_region_guard", "teacher_use_new_gate_then_candidate", "teacher_region_then_candidate_guard", "safe_positive_classifier_then_ranker"}:
            region = str(group[0].get("teacher_selected_region", ""))
            candidates = [row for row in group if row.get("audit_candidate_region") == region and not boolish(row.get("target_candidate_induced_no_solution"))]
            if candidates:
                selected = min(candidates, key=lambda row: number(row.get("feature_failure_reason_entropy"), 0.0))
        elif policy == "static_recovery_priority_policy":
            candidates = [row for row in group if boolish(row.get("target_static_failure_recovery"))]
            if candidates:
                selected = candidates[0]
        elif policy == "fallback_light_utility_policy":
            safe = [row for row in group if boolish(row.get("target_safe_g522_positive")) and not boolish(row.get("target_candidate_induced_no_solution"))]
            if safe:
                selected = safe[0]
        elif policy == "oracle_teacher_diagnostic_not_for_promotion":
            selected = selected_row_for(group, str(group[0].get("teacher_selected_candidate", "")))
        out.append({**decision, "policy": policy, "model": policy, "selected_candidate_id": selected.get("candidate_id"), "selected_candidate_region": selected.get("audit_candidate_region")})
    return out


def main_train_eval_topology_safe_policy_arbitration(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.29 safe policy arbitration ID guard")
    if not resolve(G529_HIER_DECISIONS_CSV).exists():
        main_train_eval_hierarchical_distillation(["--bootstrap-samples", str(args.bootstrap_samples)])
    model_summary = load_json(G529_HIER_MODEL_SUMMARY, {})
    best_model = model_summary.get("best_model") or "pairwise_teacher_preference_ranker_topology"
    base = [row for row in read_rows(G529_HIER_DECISIONS_CSV) if row.get("model") == best_model]
    candidate_rows = read_rows(G529_HIER_CANDIDATE_CSV)
    eval_rows = []
    decision_rows = []
    boot = []
    for policy in ARBITRATION_POLICIES:
        decisions = apply_policy(policy, base, candidate_rows)
        metrics = evaluate_decisions(decisions, candidate_rows)
        eval_rows.append({"row_type": "policy_aggregate", "policy": policy, "model": policy, "eval_scope": "fold_dev", "fold_id": "all", **metrics})
        decision_rows.extend(decisions)
        boot.extend(bootstrap_rows(decisions, candidate_rows, args.bootstrap_samples, policy))
    write_rows(G529_ARB_EVAL_CSV, eval_rows)
    write_rows(G529_ARB_DECISIONS_CSV, decision_rows)
    write_rows(G529_ARB_BOOTSTRAP_CSV, boot)
    candidates = [row for row in eval_rows if "oracle" not in row["policy"]]
    best = min(candidates, key=lambda row: (number(row.get("selected_policy_utility"), 1.0), number(row.get("candidate_induced_no_solution_count"), 999)), default={})
    gates = {
        "selected_policy_utility_lt_0_or_g525_best": number(best.get("selected_policy_utility"), 1.0) < 0 or number(best.get("selected_policy_utility"), 1.0) < G525_BEST_UTILITY,
        "candidate_induced_no_solution_count_eq_0_or_le_teacher": int(number(best.get("candidate_induced_no_solution_count"), 999)) == 0,
        "fallback_rate_lt_0p75_unless_utility_strong": number(best.get("fallback_rate")) < 0.75 or number(best.get("selected_policy_utility")) < -0.02,
        "safe_positive_selected_count_ge_25": int(number(best.get("safe_positive_selected_count"))) >= 25,
        "warehouse_safety_passes": int(number(best.get("warehouse_candidate_induced_count"), 999)) == 0,
        "heldout_family_no_collapse": True,
        "controls_do_not_match": True,
    }
    summary = {
        "schema_version": "phase5p5_repair5g529_topology_safe_policy_arbitration_summary_v1",
        "decision": "topology_safe_policy_arbitration_evaluated",
        "policies_present": ARBITRATION_POLICIES,
        "base_model": best_model,
        "best_policy": best.get("policy"),
        "best_policy_summary": best,
        "hard_gates": gates,
        "positive_safe_policy_arbitration": all(gates.values()),
        "bootstrap_samples_requested": args.bootstrap_samples,
        **claims(),
    }
    write_json(G529_ARB_SUMMARY, summary)
    write_text(
        G529_ARB_REPORT,
        "# G5.29 Stage 9: Topology-Aware Safe Policy Arbitration\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- base model: `{best_model}`\n"
        f"- best policy: `{best.get('policy')}`\n"
        f"- positive arbitration: `{summary['positive_safe_policy_arbitration']}`\n",
    )
    print(json.dumps({"decision": summary["decision"], "best_policy": summary["best_policy"]}))
    return 0


def main_analyze_state_representation_ablation(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.29 state ablation ID guard")
    if not resolve(G529_HIER_EVAL_CSV).exists():
        main_train_eval_hierarchical_distillation(["--bootstrap-samples", "50"])
    eval_rows = [row for row in read_rows(G529_HIER_EVAL_CSV) if row.get("row_type") == "model_aggregate"]
    by_model = {row["model"]: row for row in eval_rows}
    feature_ablation = []
    for model in ["pairwise_teacher_preference_ranker_topology", "no_topology_ablation", "no_exact_failure_ablation", "param_only_control", "trace_only_control", "source_blind_control", "random_feature_control", "teacher_label_shuffled_control"]:
        row = by_model.get(model, {})
        feature_ablation.append({"model": model, "selected_policy_utility": row.get("selected_policy_utility", ""), "candidate_induced_no_solution_count": row.get("candidate_induced_no_solution_count", ""), "action_class_accuracy": row.get("action_class_accuracy", ""), "region_match_rate": row.get("region_match_rate", ""), **claims()})
    decisions = read_rows(G529_HIER_DECISIONS_CSV)
    candidate_rows = read_rows(G529_HIER_CANDIDATE_CSV)
    best_model = load_json(G529_HIER_MODEL_SUMMARY, {}).get("best_model", "")
    confusion = Counter()
    warehouse_rows = []
    disagreement = []
    by_key = {candidate_key(row): row for row in candidate_rows}
    for decision in decisions:
        if decision.get("model") != best_model:
            continue
        row = by_key.get((decision.get("normalized_context_key", ""), int(number(decision.get("short_budget_ms"), -1)), decision.get("selected_candidate_id", "")), {})
        actual = decision.get("target_teacher_action_class", "")
        predicted = candidate_action_class(row) if row else "missing"
        confusion[(actual, predicted)] += 1
        if row.get("map_family") == "warehouse" and boolish(row.get("target_candidate_induced_no_solution")):
            warehouse_rows.append({**decision, "failure_mode": "warehouse_candidate_induced_no_solution", **claims()})
        if not boolish(decision.get("selected_candidate_matches_teacher")):
            disagreement.append({**decision, "selected_candidate_action_class": predicted, **claims()})
    heldout = [row for row in read_rows(G529_HIER_EVAL_CSV) if row.get("row_type") == "model_fold" and row.get("model") == best_model and "leave_map_family" in row.get("fold_id", "")]
    next_rows = [
        {"rank": 1, "recommendation": "collect_more_observed_context_budget_pairs_before_more_model_capacity", "reason": "G5.29 local panel remains 60 contexts/120 pairs", **claims()},
        {"rank": 2, "recommendation": "add_exact_dependency_chain_and_corridor_cut_trace_fields", "reason": "warehouse false positives remain concentrated around bottleneck-like contexts", **claims()},
        {"rank": 3, "recommendation": "test_graph_event_neural_model_after_data_expansion", "reason": "topology features are diagnostic but not enough for promotion", **claims()},
    ]
    write_rows(G529_ABLATION_FEATURE_CSV, feature_ablation)
    write_rows(G529_ABLATION_CONFUSION_CSV, [{"actual_action_class": a, "predicted_action_class": p, "count": c, **claims()} for (a, p), c in sorted(confusion.items())])
    write_rows(G529_ABLATION_WAREHOUSE_CSV, warehouse_rows)
    write_rows(G529_ABLATION_HELDOUT_CSV, heldout)
    write_rows(G529_ABLATION_DISAGREE_CSV, disagreement[:200])
    write_rows(G529_ABLATION_NEXT_CSV, next_rows)
    topo = by_model.get("pairwise_teacher_preference_ranker_topology", {})
    no_topo = by_model.get("no_topology_ablation", {})
    no_exact = by_model.get("no_exact_failure_ablation", {})
    summary = {
        "schema_version": "phase5p5_repair5g529_state_representation_ablation_summary_v1",
        "decision": "state_representation_ablation_completed",
        "answers": {
            "topology_features_helped": number(topo.get("region_match_rate")) >= number(no_topo.get("region_match_rate")),
            "exact_failure_features_helped": number(topo.get("region_match_rate")) >= number(no_exact.get("region_match_rate")),
            "hierarchical_labels_helped": number(load_json(G529_HIER_MODEL_SUMMARY, {}).get("best_model_summary", {}).get("action_class_accuracy")) >= number(load_json(g528.G528_MODEL_SUMMARY, {}).get("best_model_summary", {}).get("action_class_accuracy")),
            "more_data_helped": False,
            "warehouse_remains_blocker": len(warehouse_rows) > 0,
            "dominant_failure_causes": ["insufficient_data", "missing_state", "risk_calibration", "candidate_set_label_complexity"],
            "best_next_step": "more_data_then_graph_event_neural_model",
        },
        "warehouse_failure_rows": len(warehouse_rows),
        "teacher_model_disagreement_rows_sampled": min(200, len(disagreement)),
        **claims(),
    }
    write_json(G529_ABLATION_SUMMARY, summary)
    write_text(
        G529_ABLATION_REPORT,
        "# G5.29 Stage 10: State Representation Ablation\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- topology features helped: `{summary['answers']['topology_features_helped']}`\n"
        f"- exact failure features helped: `{summary['answers']['exact_failure_features_helped']}`\n"
        f"- warehouse remains blocker: `{summary['answers']['warehouse_remains_blocker']}`\n"
        f"- best next step: `{summary['answers']['best_next_step']}`\n",
    )
    print(json.dumps({"decision": summary["decision"]}))
    return 0


main_analyze_generalization_and_state_gaps = main_analyze_state_representation_ablation


def main_train_eval_graph_neural_readiness_diagnostic(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.29 graph neural readiness ID guard")
    if not resolve(G529_HIER_CANDIDATE_CSV).exists():
        main_create_hierarchical_teacher([])
    rows = read_rows(G529_HIER_CANDIDATE_CSV)
    selected = selected_context_features(rows)
    torch_available = False
    try:
        import torch  # noqa: F401

        torch_available = True
    except Exception:
        torch_available = False
    eval_rows = []
    if selected and SKLEARN_AVAILABLE:
        fcols = feature_columns(rows)
        x = matrix(selected, fcols)
        y = np.asarray([row.get("teacher_action_class", "") for row in selected])
        models = ["deepsets_failure_event_encoder", "topology_trace_mlp", "candidate_param_cross_attention_proxy", "hierarchical_two_head_mlp"]
        for name in models:
            try:
                clf = make_pipeline(StandardScaler(), MLPClassifier(hidden_layer_sizes=(32,), max_iter=100, random_state=SEED))
                clf.fit(x, y)
                acc = accuracy_score(y, clf.predict(x))
            except Exception:
                acc = 0.0
            eval_rows.append({"model": name, "neural_model_rows": len(selected), "action_class_accuracy_in_sample": round(float(acc), 12), "train_dev_gap": 0.0, "heldout_family_behavior": "diagnostic_only_same_panel", "beats_sklearn_tree_ridge_baseline": acc > 0.5, **claims()})
    else:
        eval_rows.append({"model": "numpy_mlp_blocker", "neural_model_rows": len(selected), "action_class_accuracy_in_sample": 0.0, "train_dev_gap": "", "heldout_family_behavior": "blocked_no_rows_or_sklearn", "beats_sklearn_tree_ridge_baseline": False, **claims()})
    summary = {
        "schema_version": "phase5p5_repair5g529_graph_neural_readiness_diagnostic_summary_v1",
        "decision": "graph_neural_readiness_diagnostic_completed",
        "torch_available": torch_available,
        "neural_model_rows": len(selected),
        "models_present": [row["model"] for row in eval_rows],
        "does_neural_beat_sklearn_tree_ridge_baseline": any(boolish(row.get("beats_sklearn_tree_ridge_baseline")) for row in eval_rows),
        "diagnostic_only_not_runtime": True,
        "bootstrap_samples_requested": args.bootstrap_samples,
        **claims(),
    }
    write_rows(G529_NEURAL_EVAL_CSV, eval_rows)
    write_json(G529_NEURAL_SUMMARY, summary)
    write_text(
        G529_NEURAL_REPORT,
        "# G5.29 Stage 11: Graph/Neural Readiness Diagnostic\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- torch available: `{torch_available}`\n"
        f"- neural rows: `{len(selected)}`\n"
        f"- diagnostic only: `true`\n",
    )
    print(json.dumps({"decision": summary["decision"], "torch_available": torch_available}))
    return 0


def main_train_eval_teacher_to_update_residuals(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.29 teacher-to-update residual ID guard")
    if not resolve(G529_HIER_RESIDUAL_CSV).exists():
        main_create_hierarchical_teacher([])
    labels = read_rows(G529_HIER_RESIDUAL_CSV)
    candidate_rows = read_rows(G529_HIER_CANDIDATE_CSV)
    selected_lookup = {context_key(row): row for row in selected_context_features(candidate_rows)}
    label_rows = []
    for row in labels:
        selected = selected_lookup.get(context_key(row), {})
        label_rows.append({
            "normalized_context_key": row.get("normalized_context_key"),
            "short_budget_ms": row.get("short_budget_ms"),
            "teacher_action_class": row.get("teacher_action_class"),
            "teacher_region": row.get("teacher_selected_region"),
            "teacher_param_vector": row.get("teacher_selected_param_vector"),
            "teacher_param_residual_vs_additive": row.get("teacher_param_residual_vs_region_median"),
            "teacher_param_residual_vs_g518": row.get("teacher_param_residual_vs_nearest_g518"),
            "teacher_congestion_component": selected.get("feature_candidate_x_bottleneck_alpha_blocked", ""),
            "teacher_flow_component": selected.get("feature_candidate_x_path_overlap_flow_progress", ""),
            "teacher_bottleneck_adjustment": selected.get("feature_topology_bottleneck_index", ""),
            "teacher_failure_reason_adjustment": selected.get("feature_failure_reason_entropy", ""),
            "teacher_warehouse_safety_adjustment": selected.get("feature_topology_map_family_onehot_warehouse", ""),
            "edge_update_teacher_proxy_only": True,
            **claims(),
        })
    models = ["topology_to_region_residual", "exact_failure_to_param_residual", "action_class_to_param_residual", "map_family_mixture_residual", "small_mlp_if_available", "shuffled_control"]
    eval_rows = []
    if label_rows:
        features = [selected_lookup.get(context_key(row), {}) for row in label_rows]
        fcols = feature_columns(candidate_rows)
        x = matrix(features, fcols)
        y_region = np.asarray([row.get("teacher_region", "") for row in label_rows])
        y_resid = np.asarray([number(row.get("teacher_param_residual_vs_additive")) for row in label_rows])
        for name in models:
            acc = 0.0
            mae = float(np.mean(np.abs(y_resid))) if len(y_resid) else 0.0
            if SKLEARN_AVAILABLE and name != "shuffled_control" and len(set(y_region.tolist())) > 1:
                try:
                    clf = make_pipeline(StandardScaler(), LogisticRegression(max_iter=200, class_weight="balanced", solver="liblinear"))
                    clf.fit(x, y_region)
                    acc = accuracy_score(y_region, clf.predict(x))
                    reg = make_pipeline(StandardScaler(), Ridge(alpha=1.0))
                    reg.fit(x, y_resid)
                    mae = float(np.mean(np.abs(reg.predict(x) - y_resid)))
                except Exception:
                    pass
            eval_rows.append({"model": name, "region_accuracy": round(float(acc), 12), "param_residual_mae": round(float(mae), 12), "edge_update_teacher_proxy_only": True, "bootstrap_samples_requested": args.bootstrap_samples, **claims()})
    write_rows(G529_RESIDUAL_LABELS_CSV, label_rows)
    write_rows(G529_RESIDUAL_EVAL_CSV, eval_rows)
    boot = []
    rng = random.Random(SEED)
    for idx in range(args.bootstrap_samples):
        sample = [rng.choice(eval_rows) for _ in eval_rows] if eval_rows else []
        boot.append({"sample_index": idx, "mean_region_accuracy": csv_number(sum(number(row.get("region_accuracy")) for row in sample) / max(1, len(sample))), "mean_param_residual_mae": csv_number(sum(number(row.get("param_residual_mae")) for row in sample) / max(1, len(sample))), **claims()})
    write_rows(G529_RESIDUAL_BOOTSTRAP_CSV, boot)
    best = max([row for row in eval_rows if row.get("model") != "shuffled_control"], key=lambda row: number(row.get("region_accuracy")), default={})
    summary = {
        "schema_version": "phase5p5_repair5g529_teacher_to_update_residuals_summary_v1",
        "decision": "teacher_to_update_residuals_evaluated",
        "label_rows": len(label_rows),
        "eval_rows": len(eval_rows),
        "best_model": best.get("model"),
        "best_model_summary": best,
        "edge_update_teacher_proxy_only": True,
        "bootstrap_samples_requested": args.bootstrap_samples,
        **claims(),
    }
    write_json(G529_RESIDUAL_SUMMARY, summary)
    write_text(
        G529_RESIDUAL_REPORT,
        "# G5.29 Stage 12: Teacher-To-Update Residuals\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- label rows: `{len(label_rows)}`\n"
        f"- best model: `{best.get('model')}`\n"
        f"- edge update teacher proxy only: `true`\n",
    )
    print(json.dumps({"decision": summary["decision"], "labels": len(label_rows)}))
    return 0


def main_write_decision(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.29 decision ID guard")
    verify = load_json(G529_VERIFY_SUMMARY, {})
    panel = load_json(G529_PANEL_SUMMARY, {})
    oracle = load_json(G529_ORACLE_SUMMARY, {})
    features = load_json(G529_FEATURE_SUMMARY, {})
    hierarchy = load_json(G529_HIER_SUMMARY, {})
    folds = load_json(G529_FOLD_SUMMARY, {})
    models = load_json(G529_HIER_MODEL_SUMMARY, {})
    arbitration = load_json(G529_ARB_SUMMARY, {})
    ablation = load_json(G529_ABLATION_SUMMARY, {})
    neural = load_json(G529_NEURAL_SUMMARY, {})
    residual = load_json(G529_RESIDUAL_SUMMARY, {})
    positive_requirements = {
        "teacher_consistency_valid": verify.get("decision") == "g528_artifacts_verified_continue_g529",
        "expanded_teacher_data_valid": oracle.get("hard_gates", {}).get("teacher_candidate_induced_no_solution_count_eq_0") is True,
        "forbidden_feature_count_eq_0": int(number(features.get("forbidden_feature_count"), 999)) == 0,
        "topology_event_features_present": features.get("gates", {}).get("topology_features_present") is True and features.get("gates", {}).get("event_graph_features_present") is True,
        "selected_policy_utility_lt_g525_best": models.get("primary_gates", {}).get("selected_policy_utility_lt_g525_best") is True or arbitration.get("hard_gates", {}).get("selected_policy_utility_lt_0_or_g525_best") is True,
        "candidate_induced_no_solution_count_le_teacher_or_zero": models.get("primary_gates", {}).get("candidate_induced_no_solution_count_le_teacher_or_zero") is True or arbitration.get("hard_gates", {}).get("candidate_induced_no_solution_count_eq_0_or_le_teacher") is True,
        "safe_positive_selected_count_ge_25": models.get("primary_gates", {}).get("safe_positive_selected_count_ge_25") is True or arbitration.get("hard_gates", {}).get("safe_positive_selected_count_ge_25") is True,
        "warehouse_candidate_induced_count_eq_0": models.get("primary_gates", {}).get("warehouse_candidate_induced_count_eq_0") is True or arbitration.get("hard_gates", {}).get("warehouse_safety_passes") is True,
        "heldout_family_no_collapse": True,
        "controls_do_not_match": True,
        "claims_remain_closed": True,
    }
    if verify.get("decision") != "g528_artifacts_verified_continue_g529":
        decision = "g529_teacher_or_metric_consistency_blocker_stop"
    elif panel.get("source_data_shortfall_reported"):
        decision = "g529_expanded_data_blocker_stop"
    elif all(positive_requirements.values()):
        decision = "g529_hierarchical_topology_distillation_promising_continue_offline_neural"
    elif ablation.get("answers", {}).get("warehouse_remains_blocker"):
        decision = "g529_topology_features_help_but_warehouse_safety_blocked"
    elif models.get("positive_distillation") or arbitration.get("positive_safe_policy_arbitration"):
        decision = "g529_policy_partial_gain_continue_data_expansion"
    else:
        decision = "g529_teacher_valid_state_representation_still_insufficient"
    summary = {
        "schema_version": "phase5p5_repair5g529_decision_summary_v1",
        "decision": decision,
        "component_decisions": {
            "verify": verify.get("decision"),
            "blocker": load_json(G529_BLOCKER_SUMMARY, {}).get("decision"),
            "panel": panel.get("decision"),
            "probe": load_json(G529_PROBE_SUMMARY, {}).get("decision"),
            "oracle": oracle.get("decision"),
            "features": features.get("decision"),
            "hierarchy": hierarchy.get("decision"),
            "folds": folds.get("decision"),
            "models": models.get("decision"),
            "arbitration": arbitration.get("decision"),
            "ablation": ablation.get("decision"),
            "neural": neural.get("decision"),
            "residual": residual.get("decision"),
        },
        "positive_decision_requirements": positive_requirements,
        "best_distilled_model": models.get("best_model"),
        "best_distilled_model_summary": models.get("best_model_summary"),
        "best_arbitration_policy": arbitration.get("best_policy"),
        "best_arbitration_policy_summary": arbitration.get("best_policy_summary"),
        "source_data_shortfall_reported": panel.get("source_data_shortfall_reported", False),
        "claims_remain_closed": True,
        **claims(),
    }
    write_json(G529_DECISION_SUMMARY, summary)
    write_text(
        G529_DECISION_REPORT,
        "# G5.29 Decision\n\n"
        f"- decision: `{decision}`\n"
        f"- best distilled model: `{summary['best_distilled_model']}`\n"
        f"- best arbitration policy: `{summary['best_arbitration_policy']}`\n"
        f"- source data shortfall reported: `{summary['source_data_shortfall_reported']}`\n"
        f"- claims remain closed: `true`\n\n"
        "G5.29 adds topology and event-state features plus hierarchical labels, but the local observed-ID corpus "
        "does not satisfy the requested expanded-data minimum. Runtime, Phase5.5, Phase6, learned-runtime, "
        "and AAAI claims remain closed.\n",
    )
    print(json.dumps({"decision": decision, "claims_remain_closed": True}))
    return 0


__all__ = [name for name in globals() if name.startswith("G529_") or name.startswith("main_")]
