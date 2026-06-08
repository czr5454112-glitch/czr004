"""Propose bounded G5.18 lattice candidates with an evidence-weighted surrogate."""

from __future__ import annotations

import argparse
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g518_common import (  # noqa: E402
    CandidateParams,
    DEFAULT_G516_PROBE_PLAN,
    DEFAULT_MARGIN,
    G517_ORACLE_CONTEXT_TABLE,
    G517_TARGETED_RESULTS,
    G518_CLOSED_CLAIMS,
    G518_POOL_CSV,
    G518_PROPOSAL_REPORT,
    G518_PROPOSAL_SUMMARY,
    G518_SELECTED_CSV,
    candidate_params,
    family_for_candidate,
    finite_number,
    g518_candidate_id,
    map_family,
    mean,
    old14_candidate_ids,
    param_distance,
    parse_g518_candidate_id,
    plan_rows,
    read_csv_dicts,
    repair_candidate_ids,
    repo_root,
    resolve,
    score_from_probe,
    write_csv,
    write_json_file,
    write_text_file,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--g511-results-csv", type=Path, default=Path("outputs/tables/phase5p5_repair5g511_full_lattice_counterfactual_results.csv"))
    parser.add_argument("--g517-results-csv", type=Path, default=Path(G517_TARGETED_RESULTS))
    parser.add_argument("--g514-matrix-csv", type=Path, default=Path("outputs/tables/phase5p5_repair5g514_candidate_feature_matrix_v4.csv"))
    parser.add_argument("--g515-matrix-csv", type=Path, default=Path("outputs/tables/phase5p5_repair5g515_candidate_feature_matrix_v5.csv"))
    parser.add_argument("--g516-matrix-csv", type=Path, default=Path("outputs/tables/phase5p5_repair5g516_candidate_feature_matrix_v6.csv"))
    parser.add_argument("--g517-context-oracle-csv", type=Path, default=Path(G517_ORACLE_CONTEXT_TABLE))
    parser.add_argument("--probe-plan-csv", type=Path, default=Path(DEFAULT_G516_PROBE_PLAN))
    parser.add_argument("--pool-csv", type=Path, default=Path(G518_POOL_CSV))
    parser.add_argument("--selected-csv", type=Path, default=Path(G518_SELECTED_CSV))
    parser.add_argument("--summary-json", type=Path, default=Path(G518_PROPOSAL_SUMMARY))
    parser.add_argument("--report", type=Path, default=Path(G518_PROPOSAL_REPORT))
    return parser.parse_args(argv)


def clamp(value: float, lower: float, upper: float) -> float:
    return min(upper, max(lower, value))


def rounded_params(params: CandidateParams) -> CandidateParams:
    return CandidateParams(
        round(clamp(params.alpha_cong_committed, 0.0, 2.0), 2),
        round(clamp(params.alpha_cong_blocked, 0.0, 2.0), 2),
        round(clamp(params.alpha_flow_progress, 0.0, 2.0), 2),
        round(clamp(params.alpha_flow_wait_or_nonprogress, 0.0, 2.0), 2),
        round(clamp(params.rho_cong, 0.80, 1.02), 2),
        round(clamp(params.rho_flow, 0.80, 1.02), 2),
        round(clamp(params.flow_shield_beta, 0.0, 0.80), 2),
        round(clamp(params.max_flow_shield, 0.0, 1.50), 2),
        params.c_only,
    )


def training_examples_from_matrix(rows: list[dict[str, Any]], source: str) -> list[dict[str, Any]]:
    examples = []
    for row in rows:
        candidate = str(row.get("candidate_id", ""))
        params = candidate_params(candidate)
        if params is None:
            params = CandidateParams(
                finite_number(row.get("feature_candidate_alpha_cong_committed"), math.nan),
                finite_number(row.get("feature_candidate_alpha_cong_blocked"), math.nan),
                finite_number(row.get("feature_candidate_alpha_flow_progress"), math.nan),
                finite_number(row.get("feature_candidate_alpha_flow_wait_or_nonprogress"), math.nan),
                finite_number(row.get("feature_candidate_rho_cong"), math.nan),
                finite_number(row.get("feature_candidate_rho_flow"), math.nan),
                finite_number(row.get("feature_candidate_flow_shield_beta"), math.nan),
                finite_number(row.get("feature_candidate_max_flow_shield"), math.nan),
                str(row.get("feature_candidate_is_c_only_f_disabled", "0")).strip() in {"1", "1.0", "true", "True"},
            )
        if any(not math.isfinite(value) for value in params.as_tuple()[:-1]):
            continue
        target = finite_number(row.get("mean_delta_vs_static_primary"), math.nan)
        if not math.isfinite(target):
            continue
        examples.append(
            {
                "source": source,
                "candidate_id": candidate,
                "params": params,
                "map_family": map_family(str(row.get("map", ""))),
                "agents": finite_number(row.get("agents"), 0.0),
                "trace_events_per_agent": finite_number(row.get("feature_map_trace_events_per_agent"), 0.0),
                "target_delta_vs_static": target,
                "rank": finite_number(row.get("rank_primary"), math.nan),
                "harmful": target > DEFAULT_MARGIN,
                "helpful": target < -DEFAULT_MARGIN,
            }
        )
    return examples


def static_scores(rows: list[dict[str, Any]]) -> dict[tuple[str, int], float]:
    out: dict[tuple[str, int], float] = {}
    for row in rows:
        if str(row.get("candidate_id", "")) not in {"repair5g59_static_flow_shield", "repair5g59_static_abstain_candidate"}:
            continue
        key = (str(row.get("normalized_context_key", "")), int(finite_number(row.get("short_budget_ms"), 0.0)))
        score = score_from_probe(row)
        if math.isfinite(score):
            out[key] = score
    return out


def training_examples_from_probe(rows: list[dict[str, Any]], source: str) -> list[dict[str, Any]]:
    static_by_context_budget = static_scores(rows)
    examples = []
    for row in rows:
        candidate = str(row.get("candidate_id", ""))
        params = candidate_params(candidate)
        if params is None:
            continue
        key = (str(row.get("normalized_context_key", "")), int(finite_number(row.get("short_budget_ms"), 0.0)))
        static_score = static_by_context_budget.get(key, math.inf)
        score = score_from_probe(row)
        if not math.isfinite(score) or not math.isfinite(static_score):
            continue
        delta = score - static_score
        examples.append(
            {
                "source": source,
                "candidate_id": candidate,
                "params": params,
                "map_family": map_family(str(row.get("map", ""))),
                "agents": finite_number(row.get("agents"), 0.0),
                "trace_events_per_agent": finite_number(row.get("trace_event_count"), 0.0) / max(1.0, finite_number(row.get("agents"), 1.0)),
                "target_delta_vs_static": delta,
                "rank": math.nan,
                "harmful": delta > DEFAULT_MARGIN,
                "helpful": delta < -DEFAULT_MARGIN,
            }
        )
    return examples


def target_contexts(plan: list[dict[str, Any]], context_oracle_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    plan_by_key: dict[str, dict[str, Any]] = {}
    for row in plan:
        key = str(row.get("normalized_context_key", ""))
        if key and key not in plan_by_key:
            plan_by_key[key] = row
    out = []
    for row in context_oracle_rows:
        key = str(row.get("normalized_context_key", ""))
        plan_row = plan_by_key.get(key, {})
        static_score = finite_number(row.get("static_score"), math.inf)
        old_score = finite_number(row.get("old14_oracle_score"), math.inf)
        if not math.isfinite(static_score) or not math.isfinite(old_score):
            continue
        out.append(
            {
                "normalized_context_key": key,
                "short_budget_ms": int(finite_number(row.get("short_budget_ms"), 0.0)),
                "map_family": map_family(key.split("|", 1)[0]),
                "agents": finite_number(plan_row.get("agents"), 0.0),
                "old_oracle_gap_vs_static": old_score - static_score,
                "old14_oracle_candidate": str(row.get("old14_oracle_candidate", "")),
                "error_category": str(plan_row.get("error_category", "")),
            }
        )
    return out


def surrogate_predict(params: CandidateParams, context: dict[str, Any], examples: list[dict[str, Any]]) -> tuple[float, float]:
    weighted: list[tuple[float, float, bool]] = []
    for example in examples:
        dist = param_distance(params, example["params"])
        if not math.isfinite(dist):
            continue
        context_penalty = 0.0
        if example["map_family"] != context["map_family"]:
            context_penalty += 0.35
        context_penalty += min(0.40, abs(float(example["agents"]) - float(context["agents"])) / 250.0)
        source_boost = 0.65 if example["source"] == "g517_targeted" else 1.0
        denom = 0.04 + dist + context_penalty
        weight = source_boost / max(denom * denom, 1.0e-6)
        weighted.append((weight, float(example["target_delta_vs_static"]), bool(example["harmful"])))
    weighted.sort(key=lambda item: -item[0])
    top = weighted[:64]
    total = sum(item[0] for item in top)
    if total <= 0.0:
        return 0.0, 0.5
    predicted = sum(weight * target for weight, target, _harmful in top) / total
    harmful_risk = sum(weight for weight, _target, harmful in top if harmful) / total
    return predicted, harmful_risk


def compressed_examples(examples: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for example in examples:
        params = example["params"]
        key = (
            example["source"],
            example["candidate_id"],
            example["map_family"],
            int(float(example["agents"]) // 25),
            params.as_tuple(),
        )
        grouped[key].append(example)
    out = []
    for (_source, _candidate, _family, _bucket, _params), group in grouped.items():
        first = group[0]
        target = mean(float(row["target_delta_vs_static"]) for row in group)
        harmful_rate = mean(1.0 if row["harmful"] else 0.0 for row in group)
        helpful_rate = mean(1.0 if row["helpful"] else 0.0 for row in group)
        out.append(
            {
                **first,
                "target_delta_vs_static": target,
                "harmful": harmful_rate >= 0.5,
                "helpful": helpful_rate >= 0.5,
                "compressed_count": len(group),
            }
        )
    return out


def add_candidate(pool: dict[str, dict[str, Any]], family: str, params: CandidateParams, *, seed: str) -> None:
    actual = rounded_params(params)
    candidate_id = g518_candidate_id(actual)
    pool.setdefault(
        candidate_id,
        {
            "candidate_id": candidate_id,
            "candidate_family": family,
            "proposal_seed": seed,
            **actual.as_feature_dict(),
        },
    )


def generate_candidate_pool() -> dict[str, dict[str, Any]]:
    pool: dict[str, dict[str, Any]] = {}
    # Block-heavy, wait, high-beta, low-beta-high-cap, flow-decay, static-boundary,
    # and hybrid families are intentionally represented. Values stay within the
    # C++ adapter bounds and avoid the low-cap-only G5.16 pattern.
    for c in [0.90, 1.00, 1.10, 1.25]:
        for b in [1.40, 1.50, 1.65, 1.80]:
            for w in [0.45, 0.55, 0.65]:
                for beta in [0.35, 0.45, 0.55]:
                    for cap in [0.75, 1.00]:
                        add_candidate(pool, "block_heavy", CandidateParams(c, b, 1.0, w, 0.95, 1.00, beta, cap, False), seed="block_heavy_grid")
    for w in [0.35, 0.45, 0.50, 0.60, 0.90, 1.00, 1.15, 1.30]:
        for beta in [0.30, 0.35, 0.50, 0.60]:
            for cap in [0.75, 1.00, 1.25]:
                family = "wait_aggressive" if w >= 0.90 else "wait_conservative"
                add_candidate(pool, family, CandidateParams(1.25, 1.25, 1.0, w, 0.95, 1.00, beta, cap, False), seed="wait_grid")
    for beta in [0.55, 0.60, 0.70, 0.80]:
        for cap in [0.75, 1.00, 1.25, 1.50]:
            for b in [1.15, 1.35, 1.55]:
                add_candidate(pool, "high_beta", CandidateParams(1.20, b, 1.0, 0.70, 0.95, 1.00, beta, cap, False), seed="high_beta_grid")
    for beta in [0.10, 0.15, 0.20, 0.25, 0.30]:
        for cap in [1.00, 1.25, 1.50]:
            for w in [0.60, 0.75, 0.95]:
                add_candidate(pool, "low_beta_high_cap", CandidateParams(1.25, 1.25, 1.0, w, 0.95, 1.00, beta, cap, False), seed="low_beta_high_cap_grid")
    for dc in [0.88, 0.90, 0.92, 0.95, 0.98]:
        for df in [0.88, 0.92, 0.95, 0.98]:
            for cap in [0.75, 1.00, 1.25]:
                add_candidate(pool, "flow_decay", CandidateParams(1.25, 1.25, 1.0, 0.75, dc, df, 0.35, cap, False), seed="decay_grid")
    for c in [0.95, 1.05, 1.20, 1.35]:
        for b in [0.95, 1.15, 1.35]:
            for cap in [0.60, 0.75, 0.90]:
                add_candidate(pool, "static_boundary", CandidateParams(c, b, 1.0, 0.80, 0.95, 1.00, 0.25, cap, False), seed="static_boundary_grid")
    for c in [1.00, 1.15, 1.30, 1.50]:
        for b in [1.00, 1.25, 1.50]:
            add_candidate(pool, "static_boundary_c_only", CandidateParams(c, b, 1.0, 0.75, 0.95, 1.00, 0.0, 0.0, True), seed="c_only_grid")
    for b in [1.35, 1.55, 1.75]:
        for w in [0.90, 1.10, 1.30]:
            for beta in [0.45, 0.60]:
                add_candidate(pool, "hybrid_block_wait_flow", CandidateParams(1.10, b, 1.0, w, 0.95, 0.98, beta, 1.00, False), seed="hybrid_grid")
    return pool


def bounded_pool(pool: dict[str, dict[str, Any]], limit: int = 300) -> dict[str, dict[str, Any]]:
    by_family: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in sorted(pool.values(), key=lambda item: str(item["candidate_id"])):
        by_family[str(row["candidate_family"])].append(row)
    out: dict[str, dict[str, Any]] = {}
    families = sorted(by_family)
    while len(out) < limit and any(by_family.values()):
        for family in families:
            if by_family[family] and len(out) < limit:
                row = by_family[family].pop(0)
                out[str(row["candidate_id"])] = row
    return out


def score_pool(pool: dict[str, dict[str, Any]], target_rows: list[dict[str, Any]], examples: list[dict[str, Any]]) -> list[dict[str, Any]]:
    failed_params = [candidate_params(candidate) for candidate in repair_candidate_ids()]
    old_params = [candidate_params(candidate) for candidate in old14_candidate_ids()]
    scored = []
    for row in pool.values():
        params = parse_g518_candidate_id(str(row["candidate_id"]))
        predicted_gaps = []
        harmful_risks = []
        improvement_count = 0
        for context in target_rows:
            predicted_delta, harmful_risk = surrogate_predict(params, context, examples)
            harmful_risks.append(harmful_risk)
            gap = predicted_delta - float(context["old_oracle_gap_vs_static"])
            predicted_gaps.append(gap)
            if gap < -DEFAULT_MARGIN:
                improvement_count += 1
        mean_gap = mean(predicted_gaps)
        mean_risk = mean(harmful_risks)
        nearest_failed = min(param_distance(params, failed) for failed in failed_params if failed is not None)
        nearest_old = min(param_distance(params, old) for old in old_params if old is not None)
        too_close_failed = nearest_failed < 0.035
        scored_row = dict(row)
        scored_row.update(
            {
                "predicted_context_budget_pairs": len(target_rows),
                "predicted_improvement_context_budget_pairs": improvement_count,
                "mean_predicted_new_gap_vs_old_oracle": round(mean_gap, 12),
                "predicted_harmful_risk": round(mean_risk, 12),
                "nearest_g517_failed_param_distance": round(nearest_failed, 12),
                "nearest_old14_param_distance": round(nearest_old, 12),
                "too_close_to_g517_failed_candidate": too_close_failed,
                "surrogate_selection_score": round(mean_gap + 0.015 * mean_risk + (0.015 if too_close_failed else 0.0), 12),
            }
        )
        scored.append(scored_row)
    return sorted(scored, key=lambda item: (float(item["surrogate_selection_score"]), -int(item["predicted_improvement_context_budget_pairs"]), item["candidate_id"]))


def select_diverse(
    scored: list[dict[str, Any]],
    *,
    count: int,
    families: set[str] | None,
    used: set[str],
    family_cap: int,
    min_distance: float,
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    by_family: Counter[str] = Counter()
    for row in scored:
        candidate = str(row["candidate_id"])
        family = str(row["candidate_family"])
        if candidate in used:
            continue
        if families is not None and family not in families:
            continue
        if str(row.get("too_close_to_g517_failed_candidate", "")).lower() == "true":
            continue
        if by_family[family] >= family_cap:
            continue
        params = parse_g518_candidate_id(candidate)
        if any(param_distance(params, parse_g518_candidate_id(str(prev["candidate_id"]))) < min_distance for prev in selected):
            continue
        selected.append(row)
        used.add(candidate)
        by_family[family] += 1
        if len(selected) >= count:
            return selected
    for row in scored:
        candidate = str(row["candidate_id"])
        family = str(row["candidate_family"])
        if candidate in used:
            continue
        if families is not None and family not in families:
            continue
        selected.append(row)
        used.add(candidate)
        if len(selected) >= count:
            return selected
    return selected


def selected_output_rows(batches: dict[str, list[dict[str, Any]]], old_controls: list[str]) -> list[dict[str, Any]]:
    rows = []
    for batch, new_rows in batches.items():
        for index, candidate in enumerate(old_controls):
            params = candidate_params(candidate)
            row = {
                "batch": batch,
                "row_type": "old14_control",
                "candidate_id": candidate,
                "candidate_family": family_for_candidate(candidate, params),
                "batch_candidate_index": index,
                "old14_control": True,
                "new_candidate": False,
            }
            if params is not None:
                row.update(params.as_feature_dict())
            rows.append(row)
        offset = len(old_controls)
        for index, item in enumerate(new_rows):
            candidate = str(item["candidate_id"])
            params = parse_g518_candidate_id(candidate)
            row = {
                "batch": batch,
                "row_type": "new_candidate",
                "candidate_id": candidate,
                "candidate_family": item["candidate_family"],
                "batch_candidate_index": offset + index,
                "old14_control": False,
                "new_candidate": True,
                "surrogate_selection_score": item["surrogate_selection_score"],
                "mean_predicted_new_gap_vs_old_oracle": item["mean_predicted_new_gap_vs_old_oracle"],
                "predicted_harmful_risk": item["predicted_harmful_risk"],
                "predicted_improvement_context_budget_pairs": item["predicted_improvement_context_budget_pairs"],
                "nearest_g517_failed_param_distance": item["nearest_g517_failed_param_distance"],
                "nearest_old14_param_distance": item["nearest_old14_param_distance"],
            }
            row.update(params.as_feature_dict())
            rows.append(row)
    return rows


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    g511_rows = read_csv_dicts(resolve(args.g511_results_csv, root))
    g517_rows = read_csv_dicts(resolve(args.g517_results_csv, root))
    g514_rows = read_csv_dicts(resolve(args.g514_matrix_csv, root))
    g515_rows = read_csv_dicts(resolve(args.g515_matrix_csv, root))
    g516_rows = read_csv_dicts(resolve(args.g516_matrix_csv, root))
    plan = plan_rows(resolve(args.probe_plan_csv, root))
    target_rows = target_contexts(plan, read_csv_dicts(resolve(args.g517_context_oracle_csv, root)))
    examples = []
    examples.extend(training_examples_from_matrix(g514_rows, "g514_v4_matrix"))
    examples.extend(training_examples_from_matrix(g515_rows, "g515_v5_matrix"))
    examples.extend(training_examples_from_matrix(g516_rows, "g516_v6_matrix"))
    examples.extend(training_examples_from_probe(g511_rows, "g511_full_lattice"))
    examples.extend(training_examples_from_probe(g517_rows, "g517_targeted"))
    raw_training_example_count = len(examples)
    examples = compressed_examples(examples)
    pool = bounded_pool(generate_candidate_pool(), limit=300)
    scored = score_pool(pool, target_rows, examples)
    used: set[str] = set()
    batches = {
        "A": select_diverse(scored, count=12, families=None, used=used, family_cap=3, min_distance=0.06),
        "B": select_diverse(
            scored,
            count=10,
            families={"block_heavy", "wait_conservative", "wait_aggressive", "high_beta", "low_beta_high_cap", "flow_decay", "hybrid_block_wait_flow"},
            used=used,
            family_cap=3,
            min_distance=0.05,
        ),
        "C": select_diverse(
            scored,
            count=8,
            families={"static_boundary", "static_boundary_c_only", "high_beta", "low_beta_high_cap"},
            used=used,
            family_cap=3,
            min_distance=0.04,
        ),
    }
    pool_rows = []
    selected_by_candidate = {str(row["candidate_id"]): batch for batch, rows in batches.items() for row in rows}
    for row in scored:
        actual = dict(row)
        actual["selected_batch"] = selected_by_candidate.get(str(row["candidate_id"]), "")
        pool_rows.append(actual)
    old_controls = old14_candidate_ids(root)
    selected = selected_output_rows(batches, old_controls)
    write_csv(args.pool_csv, pool_rows)
    write_csv(args.selected_csv, selected)
    batch_counts = {batch: len(rows) for batch, rows in batches.items()}
    family_counts = {
        batch: dict(sorted(Counter(str(row["candidate_family"]) for row in rows).items()))
        for batch, rows in batches.items()
    }
    summary = {
        "schema_version": "phase5p5_repair5g518_surrogate_lattice_proposal_summary_v1",
        "decision": "surrogate_candidate_batches_selected_continue_adapter_verification",
        "surrogate_model": "evidence_weighted_param_context_knn",
        "raw_training_example_count": raw_training_example_count,
        "training_example_count": len(examples),
        "training_sources": dict(sorted(Counter(str(row["source"]) for row in examples).items())),
        "target_context_budget_pairs": len(target_rows),
        "candidate_pool_count": len(pool_rows),
        "selected_new_candidate_count": sum(batch_counts.values()),
        "old14_control_count": len(old_controls),
        "batch_new_candidate_counts": batch_counts,
        "batch_total_candidate_counts": {batch: len(old_controls) + count for batch, count in batch_counts.items()},
        "batch_family_counts": family_counts,
        "pool_csv": str(resolve(args.pool_csv, root)),
        "selected_csv": str(resolve(args.selected_csv, root)),
        **G518_CLOSED_CLAIMS,
    }
    write_json_file(args.summary_json, summary)
    batch_lines = "\n".join(
        f"- Batch `{batch}`: new candidates `{len(rows)}`, total candidates `{len(old_controls) + len(rows)}`, families `{family_counts[batch]}`"
        for batch, rows in batches.items()
    )
    best_lines = "\n".join(
        f"- `{row['candidate_id']}` ({row['candidate_family']}): mean predicted gap `{row['mean_predicted_new_gap_vs_old_oracle']}`, risk `{row['predicted_harmful_risk']}`"
        for row in scored[:10]
    )
    write_text_file(
        args.report,
        "# Phase5.5 Repair5G.5.18 Surrogate Lattice Proposal\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- surrogate_model: `{summary['surrogate_model']}`\n"
        f"- training_example_count: `{len(examples)}`\n"
        f"- candidate_pool_count: `{len(pool_rows)}`\n"
        f"- selected_new_candidate_count: `{summary['selected_new_candidate_count']}`\n"
        f"- old14_control_count: `{len(old_controls)}`\n\n"
        "## Selected Batches\n\n"
        f"{batch_lines}\n\n"
        "## Best Surrogate Rows\n\n"
        f"{best_lines}\n\n"
        "The surrogate is used only to propose executable bounded UpdateParams candidates. Final claims remain tied to local counterfactual probe evidence, not this proposal score.\n",
    )
    print({"decision": summary["decision"], "candidate_pool_count": len(pool_rows), "selected_new_candidate_count": summary["selected_new_candidate_count"]})
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
