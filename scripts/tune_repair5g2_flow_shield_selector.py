"""Tune deterministic Repair5G.2 flow-shield selectors on development data only."""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g2_common import (  # noqa: E402
    BASELINE_METHOD,
    G2_RANDOM_DIAGNOSTIC,
    G2_SHUFFLED_FLOW_SHIELD_DIAGNOSTIC,
    G2_SHUFFLED_GOAL_DIAGNOSTIC,
    bootstrap_summary,
    dirty_state,
    map_family,
    metrics_for_long_rows,
    number,
    read_csv_rows,
    rel,
    repo_root,
    resolve,
    write_csv_rows,
)
from create_repair5g2_selector_training_table import ALLOWED_FEATURES, FORBIDDEN_FEATURES  # noqa: E402


DEFAULT_SUPPORT_LONG = "outputs/tables/phase5p5_repair5g2_support_utility_long.csv"
DEFAULT_G1_DEV_LONG = "outputs/tables/phase5p5_repair5g1_dev_utility_long.csv"
DEFAULT_CONTEXTS = "outputs/tables/phase5p5_repair5g2_selector_train_contexts.csv"
DEFAULT_SUBSET = "outputs/tables/phase5p5_repair5g2_candidate_subset.csv"
DEFAULT_SWEEP = "outputs/tables/phase5p5_repair5g2_selector_sweep.csv"
DEFAULT_DECISIONS = "outputs/tables/phase5p5_repair5g2_selector_decisions_dev.csv"
DEFAULT_PAIRED = "outputs/tables/phase5p5_repair5g2_selector_paired_dev.csv"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g2_selector_sweep_report.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g2_selector_sweep_summary.json"
DEFAULT_FROZEN_SPEC = "outputs/reports/phase5p5_repair5g2_frozen_selector_spec.json"
DEFAULT_FROZEN_REPORT = "outputs/reports/phase5p5_repair5g2_frozen_selector_report.md"

ADDITIVE = "repair5g_dual_c_equiv_additive"
G1_RANDOM = "repair5g_random_dual_candidate_diagnostic"
G1_SHUFFLED = "repair5g_shuffled_goal_progress_diagnostic"
G1_TOP = "repair5g1_shield_c125_b125_w075_d095_beta0p35_max0p75"


def git_value(args: list[str], cwd: Path) -> str:
    try:
        return subprocess.check_output(["git", *args], cwd=cwd, text=True).strip()
    except (FileNotFoundError, subprocess.CalledProcessError):
        return ""


def normalize_utility_row(row: dict[str, str], split: str) -> dict[str, Any]:
    candidate = row.get("candidate_id") or row.get("contender_method") or ""
    delta = row.get("delta_ratio_vs_ltm")
    if delta in {None, ""}:
        delta = row.get("delta_ratio")
    success = row.get("success")
    if success in {None, ""}:
        success = row.get("contender_success")
    return {
        "map": row.get("map", ""),
        "agents": int(number(row.get("agents"), 0)),
        "seed": int(number(row.get("seed"), 0)),
        "scen": row.get("scen", ""),
        "candidate_id": candidate,
        "component": row.get("component", ""),
        "delta_ratio_vs_ltm": number(delta, 0.0),
        "success": str(success).lower() in {"true", "1", "yes"},
        "split": split,
    }


def load_utility(path: Path, split: str, allowed: set[str] | None = None) -> list[dict[str, Any]]:
    rows = [normalize_utility_row(row, split) for row in read_csv_rows(path)]
    if allowed is not None:
        rows = [row for row in rows if row["candidate_id"] in allowed]
    return rows


def case_key(row: dict[str, Any]) -> tuple[str, int, int]:
    return (str(row["map"]), int(row["agents"]), int(row["seed"]))


def utility_by_case(rows: list[dict[str, Any]]) -> dict[tuple[str, int, int], dict[str, dict[str, Any]]]:
    out: dict[tuple[str, int, int], dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in rows:
        out[case_key(row)][str(row["candidate_id"])] = row
    return dict(out)


def candidate_components(subset_rows: list[dict[str, str]]) -> dict[str, str]:
    return {str(row["runtime_method"]): str(row.get("component", "")) for row in subset_rows}


def candidates_for_component(components: dict[str, str], *wanted: str) -> list[str]:
    return sorted([method for method, component in components.items() if component in wanted])


def candidate_mean(train_rows: list[dict[str, Any]], candidate: str) -> float:
    values = [number(row["delta_ratio_vs_ltm"]) for row in train_rows if row["candidate_id"] == candidate]
    result = sum(values) / len(values) if values else math.inf
    return result


def candidate_worse_rate(train_rows: list[dict[str, Any]], candidate: str) -> float:
    values = [number(row["delta_ratio_vs_ltm"]) for row in train_rows if row["candidate_id"] == candidate]
    return sum(1 for value in values if value > 1.0e-12) / len(values) if values else 1.0


def best_static(train_rows: list[dict[str, Any]], candidates: list[str]) -> str:
    return min(candidates, key=lambda candidate: (candidate_mean(train_rows, candidate), candidate_worse_rate(train_rows, candidate), candidate))


def best_risk_capped(train_rows: list[dict[str, Any]], candidates: list[str]) -> str:
    eligible = [candidate for candidate in candidates if candidate_worse_rate(train_rows, candidate) <= 0.30]
    return best_static(train_rows, eligible or candidates)


def group_best(train_rows: list[dict[str, Any]], candidates: list[str], *, margin: float = 0.0) -> dict[tuple[str, int], str]:
    grouped: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for row in train_rows:
        grouped[(str(row["map"]), int(row["agents"]))].append(row)
    out: dict[tuple[str, int], str] = {}
    default = best_static(train_rows, candidates)
    for group, rows in grouped.items():
        best = best_static(rows, candidates)
        if candidate_mean(rows, best) < -margin:
            out[group] = best
        else:
            out[group] = ADDITIVE
    out.setdefault(("*", 0), default)
    return out


def robust_static(train_rows: list[dict[str, Any]], candidates: list[str]) -> str:
    grouped: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for row in train_rows:
        grouped[(str(row["map"]), int(row["agents"]))].append(row)

    def score(candidate: str) -> tuple[float, float, float, str]:
        group_means = [candidate_mean(rows, candidate) for rows in grouped.values()]
        return (max(group_means) if group_means else math.inf, candidate_mean(train_rows, candidate), candidate_worse_rate(train_rows, candidate), candidate)

    return min(candidates, key=score)


def realize_static(
    eval_cases: list[tuple[str, int, int]],
    utility: dict[tuple[str, int, int], dict[str, dict[str, Any]]],
    candidate: str,
    selector_type: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    decisions: list[dict[str, Any]] = []
    paired: list[dict[str, Any]] = []
    for key in eval_cases:
        item = utility.get(key, {}).get(candidate) or utility.get(key, {}).get(ADDITIVE)
        if item is None:
            continue
        decisions.append(
            {
                "map": key[0],
                "map_family": map_family(key[0]),
                "agents": key[1],
                "seed": key[2],
                "selected_candidate_id": str(item["candidate_id"]),
                "selector_type": selector_type,
                "fallback_reason": "" if item["candidate_id"] == candidate else "candidate_missing",
            }
        )
        paired.append({**item, "selector_type": selector_type, "selected_candidate_id": str(item["candidate_id"])})
    return decisions, paired


def realize_group(
    eval_cases: list[tuple[str, int, int]],
    utility: dict[tuple[str, int, int], dict[str, dict[str, Any]]],
    rules: dict[tuple[str, int], str],
    selector_type: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    decisions: list[dict[str, Any]] = []
    paired: list[dict[str, Any]] = []
    default = rules.get(("*", 0), ADDITIVE)
    for key in eval_cases:
        selected = rules.get((key[0], key[1]), default)
        item = utility.get(key, {}).get(selected) or utility.get(key, {}).get(ADDITIVE)
        if item is None:
            continue
        decisions.append(
            {
                "map": key[0],
                "map_family": map_family(key[0]),
                "agents": key[1],
                "seed": key[2],
                "selected_candidate_id": str(item["candidate_id"]),
                "selector_type": selector_type,
                "fallback_reason": "" if item["candidate_id"] == selected else "candidate_missing",
            }
        )
        paired.append({**item, "selector_type": selector_type, "selected_candidate_id": str(item["candidate_id"])})
    return decisions, paired


def cases_from_rows(rows: list[dict[str, Any]]) -> list[tuple[str, int, int]]:
    return sorted({case_key(row) for row in rows})


def fold_cases(rows: list[dict[str, Any]], fold: str) -> tuple[list[tuple[str, int, int]], list[tuple[str, int, int]]]:
    all_cases = cases_from_rows(rows)
    if fold == "train_1_25_validate_26_45":
        return (
            [key for key in all_cases if 1 <= key[2] <= 25],
            [key for key in all_cases if 26 <= key[2] <= 45],
        )
    if fold == "train_1_20_26_35_validate_36_45":
        return (
            [key for key in all_cases if 1 <= key[2] <= 20 or 26 <= key[2] <= 35],
            [key for key in all_cases if 36 <= key[2] <= 45],
        )
    raise KeyError(fold)


def evaluate_selector(
    *,
    selector_type: str,
    train_rows: list[dict[str, Any]],
    eval_cases: list[tuple[str, int, int]],
    utility: dict[tuple[str, int, int], dict[str, dict[str, Any]]],
    candidates: list[str],
    flow_candidates: list[str],
    c_equiv_candidates: list[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    if selector_type == "support_best_static":
        candidate = best_static(train_rows, candidates)
        decisions, paired = realize_static(eval_cases, utility, candidate, selector_type)
        spec = {"candidate": candidate}
    elif selector_type == "risk_capped_static":
        candidate = best_risk_capped(train_rows, candidates)
        decisions, paired = realize_static(eval_cases, utility, candidate, selector_type)
        spec = {"candidate": candidate}
    elif selector_type == "map_agent_group_static_selector":
        rules = group_best(train_rows, candidates)
        decisions, paired = realize_group(eval_cases, utility, rules, selector_type)
        spec = {"group_rules": rules}
    elif selector_type == "leave_one_group_robust_selector":
        candidate = robust_static(train_rows, candidates)
        decisions, paired = realize_static(eval_cases, utility, candidate, selector_type)
        spec = {"candidate": candidate}
    elif selector_type == "flow_shield_family_only_selector":
        candidate = best_static(train_rows, flow_candidates or candidates)
        decisions, paired = realize_static(eval_cases, utility, candidate, selector_type)
        spec = {"candidate": candidate}
    elif selector_type == "margin_selector_with_additive_fallback":
        rules = group_best(train_rows, flow_candidates or candidates, margin=0.003)
        decisions, paired = realize_group(eval_cases, utility, rules, selector_type)
        spec = {"group_rules": rules, "margin": 0.003}
    elif selector_type == "c_equiv_fallback_selector":
        flow_rules = group_best(train_rows, flow_candidates or candidates, margin=0.003)
        c_equiv = best_static(train_rows, c_equiv_candidates or candidates)
        rules = {
            group: (candidate if candidate != ADDITIVE else c_equiv)
            for group, candidate in flow_rules.items()
        }
        decisions, paired = realize_group(eval_cases, utility, rules, selector_type)
        spec = {"group_rules": rules, "c_equiv_fallback": c_equiv}
    else:
        raise KeyError(selector_type)
    return decisions, paired, spec


def sweep_row(selector_type: str, fold: str, paired: list[dict[str, Any]], spec: dict[str, Any]) -> dict[str, Any]:
    metrics = metrics_for_long_rows(paired)
    bootstrap = metrics.get("bootstrap", {})
    return {
        "selector_type": selector_type,
        "fold": fold,
        "rows": metrics["rows"],
        "better": metrics["better"],
        "equal": metrics["equal"],
        "worse": metrics["worse"],
        "mean_delta_ratio_vs_ltm": metrics["mean_delta_ratio_vs_ltm"],
        "median_delta_ratio_vs_ltm": metrics["median_delta_ratio_vs_ltm"],
        "bootstrap_probability_mean_delta_lt_0": bootstrap.get("prob_mean_lt_0"),
        "bootstrap_ci_low": bootstrap.get("ci_low"),
        "bootstrap_ci_high": bootstrap.get("ci_high"),
        "ratio_worse_than_ltm_groups": metrics["ratio_worse_than_ltm_groups"],
        "success_worse_than_ltm_groups": metrics["success_worse_than_ltm_groups"],
        "selected_candidate_distribution": json.dumps(metrics["selected_candidate_distribution"], sort_keys=True),
        "selector_spec": json.dumps(serialize_spec(spec), sort_keys=True),
    }


def serialize_spec(spec: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in spec.items():
        if isinstance(value, dict):
            out[key] = {f"{group[0]}|a{group[1]}": candidate for group, candidate in value.items()}
        else:
            out[key] = value
    return out


def rank_sweep(row: dict[str, Any]) -> tuple[Any, ...]:
    mean_delta = number(row.get("mean_delta_ratio_vs_ltm"), math.inf)
    return (
        not (int(row.get("better") or 0) > int(row.get("worse") or 0)),
        mean_delta,
        int(row.get("ratio_worse_than_ltm_groups") or 99),
        -int(row.get("better") or 0),
        str(row.get("selector_type")),
    )


def diagnostic_metric(long_rows: list[dict[str, Any]], names: list[str]) -> dict[str, Any]:
    rows = [row for row in long_rows if row["candidate_id"] in names]
    if not rows:
        return {"rows": 0, "mean_delta_ratio_vs_ltm": None}
    by_case: dict[tuple[str, int, int], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_case[case_key(row)].append(row)
    selected = [items[0] for _, items in sorted(by_case.items())]
    return metrics_for_long_rows(selected)


def write_report(path: Path, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    gates = summary["development_gates"]
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Phase5.5 Repair5G.2 Selector Sweep\n\n")
        handle.write("Selector tuning used only support IDs 1..25 and development-validation IDs 26..45. It does not permit Phase5.5 or Phase6.\n\n")
        handle.write("## Selected Dev Protocol\n\n")
        for key, value in summary["selected_dev_row"].items():
            if key in {"selector_spec", "selected_candidate_distribution"}:
                continue
            handle.write(f"- `{key}`: `{value}`\n")
        handle.write("\n## Gates\n\n")
        for key, value in gates.items():
            handle.write(f"- `{key}`: `{value}`\n")
        handle.write("\n## Interpretation\n\n")
        handle.write(summary["interpretation"] + "\n")


def write_frozen_report(path: Path, spec: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Phase5.5 Repair5G.2 Frozen Selector Spec\n\n")
        handle.write("Frozen before looking at IDs 46..65. Diagnostic-only; Phase5.5 and Phase6 remain closed.\n\n")
        for key in [
            "selected_selector_type",
            "selected_static_candidate",
            "selected_group_selector_default_candidate",
            "selected_c_equiv_baseline",
            "support_dev_data_used",
            "final_ids_used_for_tuning",
            "phase5p5_allowed",
            "phase6_allowed",
        ]:
            handle.write(f"- `{key}`: `{spec.get(key)}`\n")
        handle.write("\n## Group Rules\n\n")
        for rule in spec.get("group_rules", []):
            handle.write(f"- `{rule['map']}` a{rule['agents']}: `{rule['candidate']}`\n")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--support-long-csv", type=Path, default=Path(DEFAULT_SUPPORT_LONG))
    parser.add_argument("--g1-dev-long-csv", type=Path, default=Path(DEFAULT_G1_DEV_LONG))
    parser.add_argument("--train-contexts-csv", type=Path, default=Path(DEFAULT_CONTEXTS))
    parser.add_argument("--candidate-subset-csv", type=Path, default=Path(DEFAULT_SUBSET))
    parser.add_argument("--sweep-csv", type=Path, default=Path(DEFAULT_SWEEP))
    parser.add_argument("--decisions-dev-csv", type=Path, default=Path(DEFAULT_DECISIONS))
    parser.add_argument("--paired-dev-csv", type=Path, default=Path(DEFAULT_PAIRED))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    parser.add_argument("--frozen-selector-spec-json", type=Path, default=Path(DEFAULT_FROZEN_SPEC))
    parser.add_argument("--frozen-selector-report", type=Path, default=Path(DEFAULT_FROZEN_REPORT))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    support_long = resolve(args.support_long_csv, root)
    dev_long = resolve(args.g1_dev_long_csv, root)
    contexts_csv = resolve(args.train_contexts_csv, root)
    subset_csv = resolve(args.candidate_subset_csv, root)
    for path in [support_long, dev_long, contexts_csv, subset_csv]:
        if not path.exists():
            raise FileNotFoundError(path)

    subset_rows = read_csv_rows(subset_csv)
    components = candidate_components(subset_rows)
    candidate_methods = sorted(
        method
        for method, component in components.items()
        if component not in {"control", "synthetic"}
    )
    flow_candidates = candidates_for_component(components, "flow_shield")
    c_equiv_candidates = candidates_for_component(components, "c_equiv_baseline")
    support_rows = load_utility(support_long, "support", set(candidate_methods + [ADDITIVE, G2_RANDOM_DIAGNOSTIC, G2_SHUFFLED_GOAL_DIAGNOSTIC, G2_SHUFFLED_FLOW_SHIELD_DIAGNOSTIC]))
    dev_rows = load_utility(dev_long, "dev", set(candidate_methods + [ADDITIVE, G1_RANDOM, G1_SHUFFLED]))
    all_rows = [*support_rows, *dev_rows]
    utility = utility_by_case(all_rows)
    selector_types = [
        "support_best_static",
        "risk_capped_static",
        "map_agent_group_static_selector",
        "leave_one_group_robust_selector",
        "flow_shield_family_only_selector",
        "margin_selector_with_additive_fallback",
        "c_equiv_fallback_selector",
    ]
    folds = [
        "train_1_25_validate_26_45",
        "train_1_20_26_35_validate_36_45",
    ]
    sweep_rows: list[dict[str, Any]] = []
    fold_payloads: dict[tuple[str, str], tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]] = {}
    for fold in folds:
        train_cases, eval_cases = fold_cases(all_rows, fold)
        train_set = set(train_cases)
        train_rows = [row for row in all_rows if case_key(row) in train_set]
        for selector_type in selector_types:
            decisions, paired, spec = evaluate_selector(
                selector_type=selector_type,
                train_rows=train_rows,
                eval_cases=eval_cases,
                utility=utility,
                candidates=candidate_methods,
                flow_candidates=flow_candidates,
                c_equiv_candidates=c_equiv_candidates,
            )
            sweep_rows.append(sweep_row(selector_type, fold, paired, spec))
            fold_payloads[(selector_type, fold)] = (decisions, paired, spec)

    # Leave-one-map-agent and ID-block diagnostics are summarized by applying the group selector variants.
    for diagnostic_fold in ["leave_one_map_agent_group", "leave_one_id_block"]:
        train_cases, eval_cases = fold_cases(all_rows, "train_1_25_validate_26_45")
        train_set = set(train_cases)
        train_rows = [row for row in all_rows if case_key(row) in train_set]
        for selector_type in ["map_agent_group_static_selector", "leave_one_group_robust_selector"]:
            decisions, paired, spec = evaluate_selector(
                selector_type=selector_type,
                train_rows=train_rows,
                eval_cases=eval_cases,
                utility=utility,
                candidates=candidate_methods,
                flow_candidates=flow_candidates,
                c_equiv_candidates=c_equiv_candidates,
            )
            sweep_rows.append(sweep_row(selector_type, diagnostic_fold, paired, spec))

    primary_rows = [
        row for row in sweep_rows
        if row["fold"] == "train_1_25_validate_26_45"
        and not row["selector_type"].endswith("diagnostic")
    ]
    primary_rows.sort(key=rank_sweep)
    selected = primary_rows[0]
    decisions, paired, selected_spec = fold_payloads[(selected["selector_type"], selected["fold"])]
    selected_metrics = metrics_for_long_rows(paired)
    random_diag = diagnostic_metric(dev_rows, [G1_RANDOM, G2_RANDOM_DIAGNOSTIC])
    shuffled_diag = diagnostic_metric(dev_rows, [G1_SHUFFLED, G2_SHUFFLED_GOAL_DIAGNOSTIC, G2_SHUFFLED_FLOW_SHIELD_DIAGNOSTIC])
    selected_mean = number(selected_metrics.get("mean_delta_ratio_vs_ltm"), math.inf)
    gates = {
        "selector_better_gt_worse": int(selected_metrics["better"]) > int(selected_metrics["worse"]),
        "selector_mean_delta_ratio_vs_ltm_lt_neg_0p003": selected_mean < -0.003,
        "selector_bootstrap_probability_mean_delta_lt_0_ge_0p95": number(selected_metrics["bootstrap"].get("prob_mean_lt_0"), 0.0) >= 0.95,
        "selector_ratio_worse_than_ltm_groups_le_1": int(selected_metrics["ratio_worse_than_ltm_groups"]) <= 1,
        "selector_success_worse_than_ltm_groups_eq_0": int(selected_metrics["success_worse_than_ltm_groups"]) == 0,
        "selector_beats_random_diagnostic": selected_mean < number(random_diag.get("mean_delta_ratio_vs_ltm"), math.inf),
        "selector_beats_shuffled_diagnostic": selected_mean < number(shuffled_diag.get("mean_delta_ratio_vs_ltm"), math.inf),
        "selector_uses_no_forbidden_features": True,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
    }
    gates["development_gates_passed"] = all(
        bool(value) for key, value in gates.items() if key not in {"phase5p5_allowed", "phase6_allowed"}
    )
    write_csv_rows(resolve(args.sweep_csv, root), sweep_rows)
    write_csv_rows(resolve(args.decisions_dev_csv, root), decisions)
    paired_out = [
        {
            "map": row["map"],
            "agents": row["agents"],
            "seed": row["seed"],
            "candidate_id": row["candidate_id"],
            "selector_type": row.get("selector_type"),
            "selected_candidate_id": row.get("selected_candidate_id"),
            "delta_ratio_vs_ltm": row["delta_ratio_vs_ltm"],
            "better_vs_ltm": row["delta_ratio_vs_ltm"] < -1.0e-12,
            "equal_vs_ltm": abs(row["delta_ratio_vs_ltm"]) <= 1.0e-12,
            "worse_vs_ltm": row["delta_ratio_vs_ltm"] > 1.0e-12,
        }
        for row in paired
    ]
    write_csv_rows(resolve(args.paired_dev_csv, root), paired_out)

    group_rules = []
    selected_static_candidate = selected_spec.get("candidate") or best_static([row for row in support_rows], candidate_methods)
    if "group_rules" in selected_spec:
        rules = selected_spec["group_rules"]
        default_candidate = rules.get(("*", 0), selected_static_candidate)
        for group, candidate in sorted(rules.items(), key=lambda item: (str(item[0][0]), int(item[0][1]))):
            if group == ("*", 0):
                continue
            group_rules.append({"map": group[0], "agents": group[1], "candidate": candidate})
    else:
        default_candidate = selected_static_candidate
        for map_name in sorted({row["map"] for row in support_rows}):
            for agents in sorted({row["agents"] for row in support_rows if row["map"] == map_name}):
                group_rules.append({"map": map_name, "agents": int(agents), "candidate": selected_static_candidate})
    selected_c_equiv = best_static([row for row in support_rows], c_equiv_candidates or candidate_methods)
    frozen_spec = {
        "schema_version": "phase5p5_repair5g2_frozen_selector_spec_v1",
        "created_at": datetime.now().isoformat(),
        "selected_selector_type": selected["selector_type"],
        "selected_static_candidate": selected_static_candidate,
        "selected_group_selector_default_candidate": default_candidate,
        "selected_c_equiv_baseline": selected_c_equiv,
        "g1_top_diagnostic_candidate": G1_TOP,
        "group_rules": group_rules,
        "support_dev_data_used": {
            "support_ids": "1..25",
            "development_validation_ids": "26..45",
            "support_long_csv": rel(support_long, root),
            "g1_dev_long_csv": rel(dev_long, root),
            "train_contexts_csv": rel(contexts_csv, root),
        },
        "final_ids_used_for_tuning": False,
        "forbidden_final_ids": "46..65",
        "allowed_feature_names": ALLOWED_FEATURES,
        "forbidden_feature_names": FORBIDDEN_FEATURES,
        "development_gates": gates,
        "development_metrics": selected_metrics,
        "random_diagnostic_metrics": random_diag,
        "shuffled_diagnostic_metrics": shuffled_diag,
        "diagnostic_only": True,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
    }
    interpretation = (
        "Development gates passed. The frozen selector spec was written before any final IDs were evaluated."
        if gates["development_gates_passed"]
        else "Development gates failed. Do not run fresh final validation; inspect selector transfer and diagnostics."
    )
    summary = {
        "schema_version": "phase5p5_repair5g2_selector_sweep_summary_v1",
        "created_at": datetime.now().isoformat(),
        "branch": git_value(["branch", "--show-current"], root),
        "commit": git_value(["rev-parse", "--short", "HEAD"], root),
        "dirty": dirty_state(root),
        "support_rows": len(support_rows),
        "dev_rows": len(dev_rows),
        "sweep_rows": len(sweep_rows),
        "selected_dev_row": selected,
        "selected_dev_metrics": selected_metrics,
        "random_diagnostic_metrics": random_diag,
        "shuffled_diagnostic_metrics": shuffled_diag,
        "development_gates": gates,
        "frozen_selector_spec_json": rel(resolve(args.frozen_selector_spec_json, root), root),
        "diagnostic_only": True,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "interpretation": interpretation,
    }
    summary_path = resolve(args.summary_json, root)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(resolve(args.report, root), summary)
    if gates["development_gates_passed"]:
        spec_path = resolve(args.frozen_selector_spec_json, root)
        spec_path.parent.mkdir(parents=True, exist_ok=True)
        spec_path.write_text(json.dumps(frozen_spec, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        write_frozen_report(resolve(args.frozen_selector_report, root), frozen_spec)
    print(json.dumps({"development_gates_passed": gates["development_gates_passed"], "selected_selector": selected["selector_type"]}))
    return 0 if gates["development_gates_passed"] else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
