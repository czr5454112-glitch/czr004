"""Lossless G5.59 to Label-v5.1 identity recovery for Repair5G.5.60."""

from __future__ import annotations

import ast
import csv
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

from .label_v4 import BASELINE_G556, THETA_NUMERIC_COLUMNS
from .schemas_v51 import PRIMARY_BASELINE, ROUND, SCHEMA_VERSION, SOURCE_ROUND, bool_text, identity_digest, legacy_context_key, parse_bool

ROOT = Path(__file__).resolve().parents[2]

G559_INSTANCE_CSV = Path("outputs/tables/phase5p5_repair5g559_instance_manifest.csv")
G559_PLAN_CSV = Path("outputs/tables/phase5p5_repair5g559_labelv5_pilot_plan.csv")
G559_PAIR_CSV = Path("outputs/tables/phase5p5_repair5g559_labelv5_pair_rows.csv")
G559_SPLIT_CSV = Path("outputs/tables/phase5p5_repair5g559_real_learnability_split_manifest.csv")

TRUTH_MD = Path(f"outputs/reports/{ROUND}_g559_truth_audit.md")
TRUTH_JSON = Path(f"outputs/reports/{ROUND}_g559_truth_audit_summary.json")
STAGE_AUDIT_CSV = Path(f"outputs/tables/{ROUND}_stage_implementation_audit.csv")
IDENTITY_FAILURE_CSV = Path(f"outputs/tables/{ROUND}_identity_failure_audit.csv")
SCENARIO_PRE_AUDIT_CSV = Path(f"outputs/tables/{ROUND}_scenario_validity_pre_audit.csv")
TRAINING_ENTRYPOINT_AUDIT_CSV = Path(f"outputs/tables/{ROUND}_training_entrypoint_audit.csv")

RECOVERY_MD = Path(f"outputs/reports/{ROUND}_labelv51_recovery.md")
RECOVERY_JSON = Path(f"outputs/reports/{ROUND}_labelv51_recovery_summary.json")
CROSSWALK_CSV = Path(f"outputs/tables/{ROUND}_identity_crosswalk.csv")
JOIN_AUDIT_CSV = Path(f"outputs/tables/{ROUND}_labelv51_join_audit.csv")
QUARANTINE_CSV = Path(f"outputs/tables/{ROUND}_labelv51_quarantine.csv")
TRAINING_ROWS_CSV = Path(f"outputs/tables/{ROUND}_labelv51_training_rows.csv")
SAFE_SETS_CSV = Path(f"outputs/tables/{ROUND}_labelv51_safe_sets.csv")


def resolve(path: str | Path, root: Path = ROOT) -> Path:
    p = Path(path)
    return p if p.is_absolute() else root / p


def ensure_parent(path: str | Path, root: Path = ROOT) -> None:
    resolve(path, root).parent.mkdir(parents=True, exist_ok=True)


def read_rows(path: str | Path, root: Path = ROOT, limit: int | None = None) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    p = resolve(path, root)
    if not p.exists():
        return rows
    with p.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader):
            rows.append(dict(row))
            if limit is not None and idx + 1 >= limit:
                break
    return rows


def row_count(path: str | Path, root: Path = ROOT) -> int:
    p = resolve(path, root)
    if not p.exists():
        return 0
    with p.open(newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        try:
            next(reader)
        except StopIteration:
            return 0
        return sum(1 for _ in reader)


def write_rows(path: str | Path, rows: Iterable[dict[str, Any]], fieldnames: list[str] | None = None, root: Path = ROOT) -> int:
    ensure_parent(path, root)
    rows_iter = iter(rows)
    first: dict[str, Any] | None = None
    if fieldnames is None:
        try:
            first = next(rows_iter)
        except StopIteration:
            fieldnames = []
        else:
            fieldnames = list(first.keys())
    count = 0
    with resolve(path, root).open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames or [], extrasaction="ignore")
        writer.writeheader()
        if first is not None:
            writer.writerow(first)
            count += 1
        for row in rows_iter:
            writer.writerow(row)
            count += 1
    return count


def write_json(path: str | Path, data: dict[str, Any], root: Path = ROOT) -> None:
    ensure_parent(path, root)
    resolve(path, root).write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def _script_imports(path: Path) -> list[str]:
    if not path.exists():
        return []
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError:
        return []
    out: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            for alias in node.names:
                out.append(f"{mod}.{alias.name}" if mod else alias.name)
        elif isinstance(node, ast.Import):
            out.extend(alias.name for alias in node.names)
    return sorted(out)


def _script_calls(path: Path) -> list[str]:
    if not path.exists():
        return []
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError:
        return []
    out: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            fn = node.func
            if isinstance(fn, ast.Name):
                out.append(fn.id)
            elif isinstance(fn, ast.Attribute):
                out.append(fn.attr)
    return sorted(set(out))


def _first_csv_columns(path: Path) -> list[str]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f).fieldnames or [])


def write_truth_audit(root: Path = ROOT) -> dict[str, Any]:
    root = Path(root)
    instance_rows = read_rows(G559_INSTANCE_CSV, root)
    pair_rows = read_rows(G559_PAIR_CSV, root)
    split_rows = read_rows(G559_SPLIT_CSV, root)
    instance_uids = [r.get("instance_uid", "") for r in instance_rows]
    pair_uids = [r.get("instance_uid", "") for r in pair_rows]
    split_by_uid = {r.get("instance_uid", ""): r.get("split", "") for r in split_rows}
    heldout_manifest_uids = {uid for uid, split in split_by_uid.items() if split == "heldout"}
    joined_pair_rows = sum(1 for uid in pair_uids if uid in split_by_uid)
    heldout_pair_rows = sum(1 for uid in pair_uids if uid in heldout_manifest_uids)
    path_found = []
    for row in instance_rows:
        try:
            path_found.append(float(row.get("path_found_rate", "nan")))
        except Exception:
            pass

    stage_specs = [
        ("train_codebook_critic", "scripts/train_repair5g559_codebook_critic.py", "main_eval_real_learnability"),
        ("train_continuous_generator", "scripts/train_repair5g559_continuous_generator.py", "main_eval_real_learnability"),
        ("pretrain_instance_encoder", "scripts/pretrain_repair5g559_instance_encoder.py", "main_synthetic_contract"),
        ("active_round", "scripts/run_repair5g559_active_round.py", "main_plan_active_round"),
    ]
    stage_rows = []
    entry_rows = []
    for stage, rel, problematic in stage_specs:
        path = root / rel
        imports = _script_imports(path)
        calls = _script_calls(path)
        problem = any(item.endswith(problematic) or item == problematic for item in imports + calls)
        stage_rows.append(
            {
                "round": SOURCE_ROUND,
                "stage": stage,
                "script": rel,
                "script_exists": bool_text(path.exists()),
                "problematic_symbol": problematic,
                "problematic_symbol_detected": bool_text(problem),
                "real_training_executed": "False",
                "audit_result": "failed_training_entrypoint" if problem else "needs_manual_review",
            }
        )
        entry_rows.append(
            {
                "script": rel,
                "imports": ";".join(imports),
                "calls": ";".join(calls),
                "calls_real_training": bool_text("train" in " ".join(calls).lower() and not problem),
                "audit_result": "not_real_training" if problem else "needs_manual_review",
            }
        )

    identity_rows = [
        {
            "check": "instance_manifest_rows",
            "observed": len(instance_rows),
            "expected": 2000,
            "passed": bool_text(len(instance_rows) == 2000),
        },
        {
            "check": "unique_sha_instance_uids",
            "observed": len(set(instance_uids)),
            "expected": 2000,
            "passed": bool_text(len(set(instance_uids)) == 2000),
        },
        {
            "check": "pair_rows",
            "observed": len(pair_rows),
            "expected": 128000,
            "passed": bool_text(len(pair_rows) == 128000),
        },
        {
            "check": "pair_uid_join_to_split_manifest",
            "observed": joined_pair_rows,
            "expected": len(pair_rows),
            "passed": bool_text(joined_pair_rows == len(pair_rows) and len(pair_rows) > 0),
        },
        {
            "check": "heldout_pair_rows_after_original_join",
            "observed": heldout_pair_rows,
            "expected": ">0",
            "passed": bool_text(heldout_pair_rows > 0),
        },
        {
            "check": "path_found_rate_min",
            "observed": min(path_found) if path_found else "",
            "expected": ">=0.95",
            "passed": bool_text(bool(path_found) and min(path_found) >= 0.95),
        },
    ]
    scenario_rows = []
    for row in instance_rows:
        scenario_rows.append(
            {
                "instance_uid": row.get("instance_uid", ""),
                "evaluation_uid": row.get("evaluation_uid", ""),
                "map": row.get("map", ""),
                "agent_count": row.get("agent_count", row.get("agents", "")),
                "solver_scenario_path": row.get("solver_scenario_path", ""),
                "solver_scenario_sha256": row.get("solver_scenario_sha256", ""),
                "actual_solver_scenario_from_instance_assignment": row.get("actual_solver_scenario_from_instance_assignment", ""),
                "pre_audit_result": "requires_actual_file_parse",
            }
        )

    write_rows(STAGE_AUDIT_CSV, stage_rows, root=root)
    write_rows(TRAINING_ENTRYPOINT_AUDIT_CSV, entry_rows, root=root)
    write_rows(IDENTITY_FAILURE_CSV, identity_rows, root=root)
    write_rows(SCENARIO_PRE_AUDIT_CSV, scenario_rows, root=root)

    summary = {
        "round": ROUND,
        "source_round": SOURCE_ROUND,
        "start_commit": "6c9de29909535df138e7b7dd0a6a4fce29024689",
        "real_solver_materialization_succeeded": True,
        "real_pair_outcomes_exist": len(pair_rows) == 128000,
        "real_gcst_codebook_critic_trained": False,
        "real_continuous_theta_generator_trained": False,
        "self_supervised_instance_pretraining_executed": False,
        "active_label_v5_acquisition_executed": False,
        "stage1_solver_policy_replay_executed": False,
        "stage2_solver_replay_executed": False,
        "blind_replay_executed": False,
        "instance_manifest_rows": len(instance_rows),
        "unique_sha_instance_uids": len(set(instance_uids)),
        "pair_rows": len(pair_rows),
        "pair_uid_join_to_split_manifest": joined_pair_rows,
        "heldout_pair_rows_after_original_join": heldout_pair_rows,
        "path_found_rate_min": min(path_found) if path_found else None,
        "decision": "g559_failed_identity_and_training_entrypoints_not_gcst_learnability",
    }
    write_json(TRUTH_JSON, summary, root=root)
    md = [
        "# Repair5G.5.60 G5.59 Truth Audit",
        "",
        "G5.59 produced real solver rows and real candidate-vs-g556 pair outcomes, but the learnability experiment did not train a real GCST critic.",
        "",
        "## Main Findings",
        "",
        f"- Pair rows: {len(pair_rows)}.",
        f"- Instance manifest rows: {len(instance_rows)}; unique SHA instance_uids: {len(set(instance_uids))}.",
        f"- Original pair-row uid join to split manifest: {joined_pair_rows}/{len(pair_rows)}.",
        f"- Original heldout examples after that join: {heldout_pair_rows}.",
        "- The legacy runner overwrote `instance_uid` with context-horizon keys, so heldout-map splits were present but unreachable.",
        "- G5.59 training wrapper scripts route to evaluator/synthetic planning functions rather than real training functions.",
        "",
        "## Decision",
        "",
        "`g559_failed_identity_and_training_entrypoints_not_gcst_learnability`",
    ]
    ensure_parent(TRUTH_MD, root)
    resolve(TRUTH_MD, root).write_text("\n".join(md) + "\n", encoding="utf-8")
    return summary


def _safe_float_text(value: Any) -> float | None:
    try:
        out = float(value)
    except Exception:
        return None
    return out if math.isfinite(out) else None


def labelv51_target(row: dict[str, Any]) -> dict[str, Any]:
    cand_success = parse_bool(row.get("candidate_success"))
    base_success = parse_bool(row.get("baseline_success"))
    regression = bool(base_success and not cand_success) or parse_bool(row.get("success_regression"))
    gain = bool(cand_success and not base_success) or parse_bool(row.get("success_gain"))
    both_success = bool(cand_success and base_success) or parse_bool(row.get("both_success"))
    both_fail = bool((not cand_success) and (not base_success)) or parse_bool(row.get("both_fail"))
    finite = _safe_float_text(row.get("quality_delta_vs_g556"))
    comparable = both_success and finite is not None
    if regression:
        utility = -2.0
    elif gain:
        utility = 1.0
    elif comparable:
        utility = max(-1.0, min(1.0, -float(finite)))
    elif both_fail:
        utility = -0.5
    else:
        utility = -1.0
    return {
        "labelv51_candidate_success": bool_text(cand_success),
        "labelv51_baseline_success": bool_text(base_success),
        "labelv51_success_regression": bool_text(regression),
        "labelv51_success_gain": bool_text(gain),
        "labelv51_both_success": bool_text(both_success),
        "labelv51_both_fail": bool_text(both_fail),
        "labelv51_comparable_quality": bool_text(comparable),
        "labelv51_development_safe": bool_text((not regression) and parse_bool(row.get("theta_in_bounds", "True"))),
        "labelv51_target_utility": utility,
    }


def _plan_identity(row: dict[str, Any]) -> dict[str, str]:
    candidate_id = str(row.get("candidate_id") or row.get("theta_id") or row.get("role") or "")
    theta_id = str(row.get("theta_id") or candidate_id)
    return {
        "g560_plan_row_uid": str(row.get("plan_row_id", "")),
        "g560_instance_uid": str(row.get("instance_uid", "")),
        "g560_evaluation_uid": str(row.get("evaluation_uid", "")),
        "g560_physical_map_sha256": str(row.get("physical_map_sha256", "")),
        "g560_start_goal_assignment_sha256": str(row.get("start_goal_assignment_sha256", "")),
        "g560_solver_scenario_sha256": str(row.get("solver_scenario_sha256", "")),
        "g560_theta_id": theta_id,
        "g560_candidate_id": candidate_id,
        "legacy_context_key": legacy_context_key(row),
        "legacy_solver_seed": str(row.get("seed", row.get("solver_seed", ""))),
    }


def build_plan_indices(root: Path = ROOT) -> tuple[dict[tuple[str, str], dict[str, str]], dict[str, dict[str, str]], Counter]:
    plan_path = resolve(G559_PLAN_CSV, root)
    by_candidate: dict[tuple[str, str], dict[str, str]] = {}
    baseline_by_key: dict[str, dict[str, str]] = {}
    duplicate_counter: Counter = Counter()
    with plan_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            ident = _plan_identity(row)
            ident["map"] = str(row.get("map", ""))
            ident["map_family"] = str(row.get("map_family", ""))
            ident["agent_count"] = str(row.get("agent_count", row.get("agents", "")))
            ident["nominal_budget_ms"] = str(row.get("nominal_budget_ms", row.get("budget_ms", "")))
            ident["horizon_id"] = str(row.get("horizon_id", ""))
            ident["solver_scenario_path"] = str(row.get("solver_scenario_path", ""))
            ident["requested_agent_count"] = str(row.get("requested_agent_count", row.get("agent_count", "")))
            ident["physical_free_cell_count"] = str(row.get("physical_free_cell_count", ""))
            ident["agent_density"] = str(row.get("agent_density", ""))
            ident["encoded_OD_token_count"] = str(row.get("encoded_OD_token_count", ""))
            ident["represented_agent_mass"] = str(row.get("represented_agent_mass", ""))
            ident["represented_flow_mass"] = str(row.get("represented_flow_mass", ""))
            ident["path_found_rate"] = str(row.get("path_found_rate", ""))
            ident["nonzero_flow"] = str(row.get("nonzero_flow", ""))
            ident["base_time_limit_sec"] = str(row.get("base_time_limit_sec", ""))
            ident["ltm_max_iterations"] = str(row.get("ltm_max_iterations", ""))
            for col in THETA_NUMERIC_COLUMNS:
                ident[col] = str(row.get(col, ""))
            key = (ident["legacy_context_key"], ident["g560_theta_id"])
            if key in by_candidate and by_candidate[key] != ident:
                duplicate_counter[key] += 1
            by_candidate.setdefault(key, ident)
            if ident["g560_candidate_id"] == PRIMARY_BASELINE or ident["g560_theta_id"] == PRIMARY_BASELINE:
                baseline_by_key.setdefault(ident["legacy_context_key"], ident)
    return by_candidate, baseline_by_key, duplicate_counter


def _crosswalk_rows(by_candidate: dict[tuple[str, str], dict[str, str]], baseline_by_key: dict[str, dict[str, str]], duplicate_counter: Counter) -> Iterable[dict[str, Any]]:
    for (legacy_key, theta_id), ident in sorted(by_candidate.items()):
        base = baseline_by_key.get(legacy_key, {})
        digest = identity_digest(ident)
        yield {
            **ident,
            "g560_identity_digest": digest,
            "baseline_g560_plan_row_uid": base.get("g560_plan_row_uid", ""),
            "baseline_g560_evaluation_uid": base.get("g560_evaluation_uid", ""),
            "baseline_g560_solver_scenario_sha256": base.get("g560_solver_scenario_sha256", ""),
            "baseline_pair_same_evaluation": bool_text(bool(base) and base.get("g560_evaluation_uid") == ident.get("g560_evaluation_uid")),
            "baseline_pair_same_scenario": bool_text(bool(base) and base.get("g560_solver_scenario_sha256") == ident.get("g560_solver_scenario_sha256")),
            "ambiguous_legacy_key_theta": bool_text(duplicate_counter.get((legacy_key, theta_id), 0) > 0),
        }


def _baseline_training_row(base: dict[str, str], split: str) -> dict[str, Any]:
    row: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "source_round": SOURCE_ROUND,
        "row_kind": "baseline_pseudo_candidate",
        "legacy_instance_uid": base.get("legacy_context_key", ""),
        "legacy_evaluation_uid": base.get("legacy_solver_seed", ""),
        **base,
        "g560_identity_digest": identity_digest(base),
        "split": split,
        "theta_id": PRIMARY_BASELINE,
        "candidate_id": PRIMARY_BASELINE,
        "labelv51_candidate_success": "True",
        "labelv51_baseline_success": "True",
        "labelv51_success_regression": "False",
        "labelv51_success_gain": "False",
        "labelv51_both_success": "True",
        "labelv51_both_fail": "False",
        "labelv51_comparable_quality": "True",
        "labelv51_development_safe": "True",
        "labelv51_target_utility": 0.0,
        "quality_delta_vs_g556": 0.0,
    }
    for col, value in zip(THETA_NUMERIC_COLUMNS, BASELINE_G556):
        row[col] = float(value)
    return row


def recover_labelv51(root: Path = ROOT) -> dict[str, Any]:
    root = Path(root)
    by_candidate, baseline_by_key, duplicate_counter = build_plan_indices(root)
    split_rows = read_rows(G559_SPLIT_CSV, root)
    split_by_uid = {r.get("instance_uid", ""): r.get("split", "") for r in split_rows}

    crosswalk_fields = [
        "g560_plan_row_uid",
        "g560_instance_uid",
        "g560_evaluation_uid",
        "g560_physical_map_sha256",
        "g560_start_goal_assignment_sha256",
        "g560_solver_scenario_sha256",
        "g560_theta_id",
        "g560_candidate_id",
        "legacy_context_key",
        "legacy_solver_seed",
        "map",
        "map_family",
        "agent_count",
        "nominal_budget_ms",
        "horizon_id",
        "solver_scenario_path",
        "requested_agent_count",
        "physical_free_cell_count",
        "agent_density",
        "encoded_OD_token_count",
        "represented_agent_mass",
        "represented_flow_mass",
        "path_found_rate",
        "nonzero_flow",
        "base_time_limit_sec",
        "ltm_max_iterations",
        *THETA_NUMERIC_COLUMNS,
        "g560_identity_digest",
        "baseline_g560_plan_row_uid",
        "baseline_g560_evaluation_uid",
        "baseline_g560_solver_scenario_sha256",
        "baseline_pair_same_evaluation",
        "baseline_pair_same_scenario",
        "ambiguous_legacy_key_theta",
    ]
    crosswalk_count = write_rows(CROSSWALK_CSV, _crosswalk_rows(by_candidate, baseline_by_key, duplicate_counter), crosswalk_fields, root)

    join_fields = [
        "schema_version",
        "source_round",
        "row_kind",
        "legacy_instance_uid",
        "legacy_evaluation_uid",
        "legacy_context_key",
        "theta_id",
        "candidate_id",
        "split",
        "g560_plan_row_uid",
        "g560_instance_uid",
        "g560_evaluation_uid",
        "g560_physical_map_sha256",
        "g560_start_goal_assignment_sha256",
        "g560_solver_scenario_sha256",
        "g560_theta_id",
        "g560_candidate_id",
        "g560_identity_digest",
        "identity_digest_recomputed",
        "identity_digest_match",
        "map",
        "map_family",
        "agent_count",
        "nominal_budget_ms",
        "horizon_id",
        "solver_scenario_path",
        "requested_agent_count",
        "physical_free_cell_count",
        "agent_density",
        "encoded_OD_token_count",
        "represented_agent_mass",
        "represented_flow_mass",
        "path_found_rate",
        "nonzero_flow",
        "base_time_limit_sec",
        "ltm_max_iterations",
        "baseline_g560_plan_row_uid",
        "baseline_g560_evaluation_uid",
        "baseline_g560_solver_scenario_sha256",
        "baseline_pair_same_evaluation",
        "baseline_pair_same_scenario",
        "plan_join_ok",
        "baseline_join_ok",
        "physical_map_join_ok",
        "scenario_join_ok",
        "theta_join_ok",
        "evaluation_uid_nonempty_ok",
        "candidate_success",
        "baseline_success",
        "success_regression",
        "success_gain",
        "both_success",
        "both_fail",
        "quality_delta_vs_g556",
        "candidate_recognized",
        "fingerprint_match",
        "cost_finite",
        "theta_in_bounds",
        "runtime",
        "labelv51_candidate_success",
        "labelv51_baseline_success",
        "labelv51_success_regression",
        "labelv51_success_gain",
        "labelv51_both_success",
        "labelv51_both_fail",
        "labelv51_comparable_quality",
        "labelv51_development_safe",
        "labelv51_target_utility",
        "row_weight",
        *THETA_NUMERIC_COLUMNS,
        "phase5p5_allowed",
        "phase6_allowed",
        "runtime_claim_allowed",
        "learned_runtime_policy_validated",
        "aaai_ready",
    ]
    quarantine_fields = [
        "legacy_instance_uid",
        "legacy_evaluation_uid",
        "theta_id",
        "reason",
        "legacy_context_key",
        "plan_join_ok",
        "baseline_join_ok",
        "physical_map_join_ok",
        "scenario_join_ok",
        "theta_join_ok",
        "evaluation_uid_nonempty_ok",
    ]
    pair_before = 0
    pair_after = 0
    quarantine_count = 0
    baseline_pairs_same_eval = 0
    identity_digest_matches = 0
    physical_join = 0
    scenario_join = 0
    theta_join = 0
    eval_nonempty = 0
    split_counts: Counter = Counter()
    baseline_written: set[str] = set()

    ensure_parent(JOIN_AUDIT_CSV, root)
    ensure_parent(QUARANTINE_CSV, root)
    ensure_parent(TRAINING_ROWS_CSV, root)
    with resolve(G559_PAIR_CSV, root).open(newline="", encoding="utf-8") as in_f, resolve(JOIN_AUDIT_CSV, root).open("w", newline="", encoding="utf-8") as join_f, resolve(
        QUARANTINE_CSV, root
    ).open("w", newline="", encoding="utf-8") as q_f, resolve(TRAINING_ROWS_CSV, root).open("w", newline="", encoding="utf-8") as train_f:
        reader = csv.DictReader(in_f)
        join_writer = csv.DictWriter(join_f, fieldnames=join_fields, extrasaction="ignore")
        q_writer = csv.DictWriter(q_f, fieldnames=quarantine_fields, extrasaction="ignore")
        train_writer = csv.DictWriter(train_f, fieldnames=join_fields, extrasaction="ignore")
        join_writer.writeheader()
        q_writer.writeheader()
        train_writer.writeheader()
        for pair in reader:
            pair_before += 1
            legacy_uid = str(pair.get("instance_uid", ""))
            theta = str(pair.get("theta_id", ""))
            ident = by_candidate.get((legacy_uid, theta))
            base = baseline_by_key.get(legacy_uid)
            checks = {
                "plan_join_ok": bool(ident),
                "baseline_join_ok": bool(base),
                "physical_map_join_ok": bool(ident and ident.get("g560_physical_map_sha256")),
                "scenario_join_ok": bool(ident and ident.get("g560_solver_scenario_sha256")),
                "theta_join_ok": bool(ident and ident.get("g560_theta_id") == theta),
                "evaluation_uid_nonempty_ok": bool(ident and ident.get("g560_evaluation_uid")),
            }
            if not all(checks.values()):
                quarantine_count += 1
                q_writer.writerow(
                    {
                        "legacy_instance_uid": legacy_uid,
                        "legacy_evaluation_uid": pair.get("evaluation_uid", ""),
                        "theta_id": theta,
                        "reason": ";".join(name for name, ok in checks.items() if not ok),
                        "legacy_context_key": legacy_uid,
                        **{k: bool_text(v) for k, v in checks.items()},
                    }
                )
                continue
            assert ident is not None and base is not None
            digest = identity_digest(ident)
            recomputed = identity_digest({**ident, "g560_identity_digest": digest})
            split = split_by_uid.get(ident.get("g560_instance_uid", ""), "unassigned")
            target = labelv51_target(pair)
            base_same_eval = base.get("g560_evaluation_uid") == ident.get("g560_evaluation_uid")
            base_same_scenario = base.get("g560_solver_scenario_sha256") == ident.get("g560_solver_scenario_sha256")
            recovered = {
                "schema_version": SCHEMA_VERSION,
                "source_round": SOURCE_ROUND,
                "row_kind": "candidate_pair",
                "legacy_instance_uid": legacy_uid,
                "legacy_evaluation_uid": pair.get("evaluation_uid", ""),
                **ident,
                "theta_id": theta,
                "candidate_id": ident.get("g560_candidate_id", theta),
                "split": split,
                "g560_identity_digest": digest,
                "identity_digest_recomputed": recomputed,
                "identity_digest_match": bool_text(digest == recomputed),
                "baseline_g560_plan_row_uid": base.get("g560_plan_row_uid", ""),
                "baseline_g560_evaluation_uid": base.get("g560_evaluation_uid", ""),
                "baseline_g560_solver_scenario_sha256": base.get("g560_solver_scenario_sha256", ""),
                "baseline_pair_same_evaluation": bool_text(base_same_eval),
                "baseline_pair_same_scenario": bool_text(base_same_scenario),
                **{k: bool_text(v) for k, v in checks.items()},
                **pair,
                **target,
                "phase5p5_allowed": "False",
                "phase6_allowed": "False",
                "runtime_claim_allowed": "False",
                "learned_runtime_policy_validated": "False",
                "aaai_ready": "False",
            }
            join_writer.writerow(recovered)
            train_writer.writerow(recovered)
            pair_after += 1
            physical_join += 1
            scenario_join += 1
            theta_join += 1
            eval_nonempty += 1
            baseline_pairs_same_eval += int(base_same_eval and base_same_scenario)
            identity_digest_matches += int(digest == recomputed)
            split_counts[split] += 1
            if ident["legacy_context_key"] not in baseline_written:
                train_writer.writerow(_baseline_training_row(base, split))
                baseline_written.add(ident["legacy_context_key"])

    safe_rows = []
    by_eval: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in read_rows(JOIN_AUDIT_CSV, root):
        by_eval[row.get("g560_evaluation_uid", "")].append(row)
    for eval_uid, rows in sorted(by_eval.items()):
        safe = [r for r in rows if parse_bool(r.get("labelv51_development_safe"))]
        improving = [r for r in safe if parse_bool(r.get("labelv51_success_gain")) or _safe_float_text(r.get("quality_delta_vs_g556")) is not None and float(r.get("quality_delta_vs_g556")) < 0.0]
        ranked = sorted(safe, key=lambda r: float(r.get("labelv51_target_utility", -999.0)), reverse=True)
        first = rows[0]
        safe_rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "g560_evaluation_uid": eval_uid,
                "g560_instance_uid": first.get("g560_instance_uid", ""),
                "legacy_context_key": first.get("legacy_context_key", ""),
                "split": first.get("split", ""),
                "candidate_count": len(rows),
                "safe_count": len(safe),
                "safe_improving_count": len(improving),
                "safe_theta_ids": ";".join(r.get("theta_id", "") for r in safe),
                "safe_improving_theta_ids": ";".join(r.get("theta_id", "") for r in improving),
                "top_k_safe_theta_ids": ";".join(r.get("theta_id", "") for r in ranked[:8]),
                "fallback_required": bool_text(len(improving) == 0),
                "phase5p5_allowed": "False",
                "phase6_allowed": "False",
                "runtime_claim_allowed": "False",
                "learned_runtime_policy_validated": "False",
                "aaai_ready": "False",
            }
        )
    write_rows(SAFE_SETS_CSV, safe_rows, root=root)

    rates = {
        "identity_join_rate": pair_after / max(1, pair_before),
        "physical_map_join_rate": physical_join / max(1, pair_before),
        "scenario_join_rate": scenario_join / max(1, pair_before),
        "theta_join_rate": theta_join / max(1, pair_before),
        "evaluation_uid_nonempty_rate": eval_nonempty / max(1, pair_before),
        "baseline_pair_same_evaluation_rate": baseline_pairs_same_eval / max(1, pair_after),
        "identity_digest_match_rate": identity_digest_matches / max(1, pair_after),
    }
    summary = {
        "round": ROUND,
        "schema_version": SCHEMA_VERSION,
        "source_round": SOURCE_ROUND,
        "pair_row_count_before": pair_before,
        "pair_row_count_after": pair_after,
        "quarantined_rows": quarantine_count,
        "identity_crosswalk_rows": crosswalk_count,
        "ambiguous_legacy_key_count": sum(1 for v in duplicate_counter.values() if v > 0),
        "baseline_pseudo_candidate_rows": len(baseline_written),
        "split_counts": dict(split_counts),
        "safe_set_rows": len(safe_rows),
        **rates,
        "recovery_gate_passed": bool(
            pair_before == 128000
            and pair_after == 128000
            and quarantine_count == 0
            and all(abs(v - 1.0) < 1.0e-12 for v in rates.values())
            and sum(1 for v in duplicate_counter.values() if v > 0) == 0
        ),
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "runtime_claim_allowed": False,
        "learned_runtime_policy_validated": False,
        "aaai_ready": False,
    }
    write_json(RECOVERY_JSON, summary, root=root)
    md = [
        "# Repair5G.5.60 Label-v5.1 Recovery",
        "",
        f"- Pair rows before recovery: {pair_before}",
        f"- Pair rows retained after recovery: {pair_after}",
        f"- Quarantined rows: {quarantine_count}",
        f"- Identity join rate: {rates['identity_join_rate']:.6f}",
        f"- Physical map join rate: {rates['physical_map_join_rate']:.6f}",
        f"- Scenario join rate: {rates['scenario_join_rate']:.6f}",
        f"- Theta join rate: {rates['theta_join_rate']:.6f}",
        f"- Baseline same-evaluation/same-scenario rate: {rates['baseline_pair_same_evaluation_rate']:.6f}",
        f"- Identity digest match rate: {rates['identity_digest_match_rate']:.6f}",
        f"- Ambiguous legacy key count: {summary['ambiguous_legacy_key_count']}",
        "",
        f"Recovery gate passed: `{summary['recovery_gate_passed']}`.",
    ]
    ensure_parent(RECOVERY_MD, root)
    resolve(RECOVERY_MD, root).write_text("\n".join(md) + "\n", encoding="utf-8")
    return summary
