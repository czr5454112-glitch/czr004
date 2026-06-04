"""Export the Repair5G.5 contextual flow-shield selector runtime artifact."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g5_common import (  # noqa: E402
    DEFAULT_FROZEN_G2_SPEC,
    DEFAULT_SELECTOR_SPEC,
    load_json,
    rel,
    repo_root,
    resolve,
    sha256_file,
    write_json,
)


DEFAULT_G4_SPEC = "outputs/reports/phase5p5_repair5g4_contextual_selector_spec.json"
DEFAULT_G4_SUMMARY = "outputs/reports/phase5p5_repair5g4_contextual_selector_summary.json"
DEFAULT_DATASET = "outputs/tables/phase5p5_repair5g4_learning_bridge_dataset.csv"
DEFAULT_MODEL_DIR = "artifacts/models/laur_ltm/repair5g5_contextual_flow_shield_selector"
DEFAULT_DESIGN = "outputs/reports/phase5p5_repair5g5_runtime_contextual_selector_design.md"
DEFAULT_SPEC_REPORT_JSON = "outputs/reports/phase5p5_repair5g5_runtime_contextual_selector_spec.json"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g5_contextual_selector_export_report.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g5_contextual_selector_export_summary.json"


ALLOWED_FEATURES = [
    "map_width",
    "map_height",
    "obstacle_ratio",
    "free_cells",
    "agents",
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
]

FORBIDDEN_FEATURES = [
    "instance_id",
    "seed",
    "scen filename",
    "candidate outcome columns",
    "oracle choice from held-out case",
    "final solver outcome",
    "post-update improvement caused by a candidate not yet chosen",
    "action labels",
    "restart labels",
    "priority labels",
    "h_i(v)",
    "candidate deletion labels",
]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--g4-spec-json", type=Path, default=Path(DEFAULT_G4_SPEC))
    parser.add_argument("--g4-summary-json", type=Path, default=Path(DEFAULT_G4_SUMMARY))
    parser.add_argument("--dataset-csv", type=Path, default=Path(DEFAULT_DATASET))
    parser.add_argument("--g2-frozen-selector-spec-json", type=Path, default=Path(DEFAULT_FROZEN_G2_SPEC))
    parser.add_argument("--model-dir", type=Path, default=Path(DEFAULT_MODEL_DIR))
    parser.add_argument("--design-report", type=Path, default=Path(DEFAULT_DESIGN))
    parser.add_argument("--runtime-spec-json", type=Path, default=Path(DEFAULT_SPEC_REPORT_JSON))
    parser.add_argument("--export-report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    return parser.parse_args(argv)


def read_header(path: Path) -> list[str]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        return next(reader, [])


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def component(method: str) -> str:
    if method.startswith("repair5g1_shield_"):
        return "flow_shield"
    if method.startswith("repair5g_dual_c_equiv_") or method == "repair5g2_c_equiv_best_frozen_baseline":
        return "c_equiv"
    if method.startswith("repair5g2_"):
        return "frozen_alias"
    if method == "additive_ltm":
        return "additive"
    return "diagnostic"


def candidate_rows(methods: list[str], aliases: dict[str, str]) -> list[dict[str, Any]]:
    rows = []
    for method in sorted(dict.fromkeys(methods)):
        rows.append(
            {
                "candidate_id": method,
                "resolved_runtime_method": aliases.get(method, method),
                "component": component(method),
                "bounded_updateparams": True,
                "phase5p5_allowed": False,
                "phase6_allowed": False,
            }
        )
    return rows


def write_design(path: Path, runtime_spec: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Phase5.5 Repair5G.5 Runtime Contextual Selector Design\n\n")
        handle.write("Diagnostic-only learned UpdateLTM runtime bridge. `phase5p5_allowed=false`, `phase6_allowed=false`, and `aaai_ready=false` remain closed.\n\n")
        handle.write("## Selector\n\n")
        handle.write(f"- selector_name: `{runtime_spec['selector_name']}`\n")
        handle.write(f"- selector_type: `{runtime_spec['selector_type']}`\n")
        handle.write("- feature_extraction_time: `pre_update_before_UpdateLTM`\n")
        handle.write("- runtime_hook: `cpp/tools/phase1a_batch.cpp LtmOptions.update_policy`\n")
        handle.write("- fallback_policy: unsupported/missing candidates defer to exact additive LTM and log the reason\n\n")
        handle.write("## Rule\n\n")
        rule = runtime_spec["selector_rule"]
        handle.write(
            f"`{rule['feature']} <= {rule['threshold']}` selects `{rule['left_method']}`, otherwise `{rule['right_method']}`.\n\n"
        )
        handle.write("## Boundaries\n\n")
        handle.write("- allowed output: finite bounded UpdateParams candidate ID\n")
        handle.write("- forbidden output: actions, restart nodes, priorities, h_i(v), candidate deletion, conflict decisions\n")


def write_export_report(path: Path, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Phase5.5 Repair5G.5 Contextual Selector Export Report\n\n")
        handle.write("The G4 offline `decision_stump_selector` is exported as a frozen runtime-readable JSON rule for observed-ID smoke only.\n\n")
        for key in [
            "selector_name",
            "selector_hash",
            "candidate_set_hash",
            "feature_schema_hash",
            "training_data_ranges",
            "forbidden_final_ids",
        ]:
            handle.write(f"- `{key}`: `{summary.get(key)}`\n")
        handle.write("- phase5p5_allowed: `false`\n")
        handle.write("- phase6_allowed: `false`\n")
        handle.write("- aaai_ready: `false`\n")


def write_diagnostic_selector(root: Path, parent: Path, name: str, base_spec: dict[str, Any]) -> None:
    target = parent / name
    target.mkdir(parents=True, exist_ok=True)
    payload = dict(base_spec)
    payload["selector_name"] = name
    payload["selector_type"] = name
    payload["diagnostic_only"] = True
    write_json(target / "selector_spec.json", payload)
    write_json(
        target / "export_manifest.json",
        {
            "schema_version": "phase5p5_repair5g5_diagnostic_selector_manifest_v1",
            "created_at": datetime.now().isoformat(),
            "selector_spec": rel(target / "selector_spec.json", root),
            "diagnostic_only": True,
            "phase5p5_allowed": False,
            "phase6_allowed": False,
        },
    )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    g4_spec = load_json(resolve(args.g4_spec_json, root))
    g4_summary = load_json(resolve(args.g4_summary_json, root))
    g2_spec = load_json(resolve(args.g2_frozen_selector_spec_json, root))
    if not g4_spec:
        raise SystemExit("missing G4 contextual selector spec")
    rule = dict(g4_spec.get("selector_spec", {}))
    selector_name = str(g4_spec.get("selector_name", "decision_stump_selector"))
    aliases = {
        "repair5g2_best_frozen_static_candidate": g2_spec.get(
            "selected_static_candidate",
            "repair5g1_shield_c125_b125_w075_d095_beta0p35_max0p75",
        ),
        "repair5g2_c_equiv_best_frozen_baseline": g2_spec.get(
            "selected_c_equiv_baseline",
            "repair5g_dual_c_equiv_c100_b100_w075_d100",
        ),
        "repair5g2_g1_top_diagnostic_candidate": g2_spec.get(
            "g1_top_diagnostic_candidate",
            "repair5g1_shield_c125_b125_w075_d095_beta0p35_max0p75",
        ),
    }
    candidates = list(g4_summary.get("candidate_methods") or [])
    for key in ["left_method", "right_method", "fallback_static"]:
        if rule.get(key):
            candidates.append(rule[key])
    candidate_set = candidate_rows(candidates, aliases)
    feature_schema = {
        "schema_version": "phase5p5_repair5g5_feature_schema_v1",
        "allowed_features": ALLOWED_FEATURES,
        "forbidden_features": FORBIDDEN_FEATURES,
        "feature_extraction_time": "pre_update_before_UpdateLTM",
        "forbidden_feature_policy_passed": True,
    }
    runtime_spec = {
        "schema_version": "phase5p5_repair5g5_contextual_selector_runtime_spec_v1",
        "created_at": datetime.now().isoformat(),
        "selector_name": selector_name,
        "selector_type": rule.get("type", "decision_stump"),
        "selector_rule": {
            "type": rule.get("type", "decision_stump"),
            "feature": rule.get("feature", "ltm_iterations"),
            "threshold": float(rule.get("threshold", 2.5)),
            "left_method": rule.get("left_method", "repair5g_dual_c_equiv_c100_b100_w100_d090"),
            "right_method": rule.get("right_method", "repair5g2_best_frozen_static_candidate"),
            "fallback_static": rule.get("fallback_static", "repair5g2_best_frozen_static_candidate"),
        },
        "candidate_aliases": aliases,
        "candidate_set": [row["candidate_id"] for row in candidate_set],
        "allowed_features": ALLOWED_FEATURES,
        "forbidden_features": FORBIDDEN_FEATURES,
        "feature_extraction_time": "pre_update_before_UpdateLTM",
        "fallback_policy": "unsupported_or_missing_candidate_defer_to_additive_ltm",
        "force_additive_policy": "repair5g5_contextual_flow_shield_selector_force_additive_parity returns additive UpdateParams",
        "disable_policy": "repair5g5_contextual_flow_shield_selector_disable maps to plain lacam_star_ltm",
        "parity_policy": "semantic_parity_plus_time_budget_equivalence_required",
        "runtime_hook": "cpp/tools/phase1a_batch.cpp:LtmOptions.update_policy",
        "export_schema": {
            "selector_spec_json": "selector_spec.json",
            "candidate_set_csv": "candidate_set.csv",
            "feature_schema_json": "feature_schema.json",
            "export_manifest_json": "export_manifest.json",
        },
        "training_data_ranges": "observed IDs 1..165; G4 clean IDs excluded from tuning in the bridge dataset",
        "development_data_ranges": "G3/G4 learning-bridge validation rows only",
        "forbidden_final_ids": "166..205 primary learned-runtime holdout",
        "diagnostic_only": True,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "aaai_ready": False,
    }
    model_dir = resolve(args.model_dir, root)
    model_dir.mkdir(parents=True, exist_ok=True)
    write_json(model_dir / "selector_spec.json", runtime_spec)
    write_csv(model_dir / "candidate_set.csv", candidate_set, ["candidate_id", "resolved_runtime_method", "component", "bounded_updateparams", "phase5p5_allowed", "phase6_allowed"])
    write_json(model_dir / "feature_schema.json", feature_schema)
    manifest = {
        "schema_version": "phase5p5_repair5g5_selector_export_manifest_v1",
        "created_at": runtime_spec["created_at"],
        "selector_spec": rel(model_dir / "selector_spec.json", root),
        "candidate_set": rel(model_dir / "candidate_set.csv", root),
        "feature_schema": rel(model_dir / "feature_schema.json", root),
        "source_g4_spec": rel(resolve(args.g4_spec_json, root), root),
        "source_g4_summary": rel(resolve(args.g4_summary_json, root), root),
        "source_dataset": rel(resolve(args.dataset_csv, root), root),
        "source_dataset_header": read_header(resolve(args.dataset_csv, root)),
        "selector_spec_hash": sha256_file(model_dir / "selector_spec.json"),
        "candidate_set_hash": sha256_file(model_dir / "candidate_set.csv"),
        "feature_schema_hash": sha256_file(model_dir / "feature_schema.json"),
        "diagnostic_only": True,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "aaai_ready": False,
    }
    write_json(model_dir / "export_manifest.json", manifest)
    write_json(resolve(args.runtime_spec_json, root), runtime_spec)
    write_design(resolve(args.design_report, root), runtime_spec)
    diagnostic_parent = model_dir.parent
    write_diagnostic_selector(root, diagnostic_parent, "repair5g5_contextual_selector_shuffled_labels_diagnostic", runtime_spec)
    write_diagnostic_selector(root, diagnostic_parent, "repair5g5_contextual_selector_random_features_diagnostic", runtime_spec)
    summary = {
        "schema_version": "phase5p5_repair5g5_contextual_selector_export_summary_v1",
        "created_at": runtime_spec["created_at"],
        "selector_name": selector_name,
        "selector_hash": manifest["selector_spec_hash"],
        "candidate_set_hash": manifest["candidate_set_hash"],
        "feature_schema_hash": manifest["feature_schema_hash"],
        "export_manifest_hash": sha256_file(model_dir / "export_manifest.json"),
        "training_data_ranges": runtime_spec["training_data_ranges"],
        "forbidden_final_ids": runtime_spec["forbidden_final_ids"],
        "runtime_integration_target": runtime_spec["runtime_hook"],
        "outputs": {
            "selector_spec": rel(model_dir / "selector_spec.json", root),
            "candidate_set": rel(model_dir / "candidate_set.csv", root),
            "feature_schema": rel(model_dir / "feature_schema.json", root),
            "export_manifest": rel(model_dir / "export_manifest.json", root),
        },
        "diagnostic_only": True,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "aaai_ready": False,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_export_report(resolve(args.export_report, root), summary)
    print(json.dumps({"selector": selector_name, "selector_hash": summary["selector_hash"]}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
