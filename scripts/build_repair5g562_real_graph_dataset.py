from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gcst.identity_recovery import TRAINING_ROWS_CSV, recover_labelv51  # noqa: E402
from gcst.real_label_graph_dataset import (  # noqa: E402
    DEFAULT_CONTEXT_DIR,
    build_example,
    load_label_groups,
    sha256_file,
    split_counts,
)


ROUND = "phase5p5_repair5g562"
SUMMARY_JSON = Path(f"outputs/reports/{ROUND}_real_graph_dataset_summary.json")
MANIFEST_CSV = Path(f"outputs/tables/{ROUND}_real_graph_dataset_manifest.csv")
SPLIT_CSV = Path(f"outputs/tables/{ROUND}_split_manifest.csv")
C0F0_AUDIT = Path(f"outputs/tables/{ROUND}_c0_f0_provenance_audit.csv")
SAFE_STATS = Path(f"outputs/tables/{ROUND}_safe_set_statistics.csv")
CENSORING_AUDIT = Path(f"outputs/tables/{ROUND}_label_censoring_audit.csv")
POSITIVE_COVERAGE_JSON = Path(f"outputs/reports/{ROUND}_positive_discovery_coverage.json")
PRETRAINING_SPLIT_AUDIT = Path(f"outputs/tables/{ROUND}_pretraining_split_audit.csv")
VALID_ORACLE_CSV = Path(f"outputs/tables/{ROUND}_valid_oracle_opportunity.csv")


def claims() -> dict[str, bool]:
    return {
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "runtime_claim_allowed": False,
        "learned_runtime_policy_validated": False,
        "aaai_ready": False,
    }


def resolve(path: str | Path) -> Path:
    p = Path(path)
    return p if p.is_absolute() else ROOT / p


def write_rows(path: str | Path, rows: list[dict[str, Any]]) -> None:
    p = resolve(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with p.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: str | Path, data: dict[str, Any]) -> None:
    p = resolve(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def ensure_training_rows() -> dict[str, Any]:
    if not resolve(TRAINING_ROWS_CSV).exists():
        return recover_labelv51(ROOT)
    return {"training_rows_already_present": True, "path": str(TRAINING_ROWS_CSV)}


def summarize_by_split(manifest_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    splits = sorted({row["split"] for row in manifest_rows})
    out = []
    for split in splits:
        rows = [row for row in manifest_rows if row["split"] == split]
        out.append(
            {
                "split": split,
                "contexts": len(rows),
                "physical_map_hashes": len({row["physical_map_sha256_expected"] for row in rows}),
                "positive_contexts": sum(int(row["safe_improving_count"]) > 0 for row in rows),
                "harmful_contexts": sum(int(row["harmful_count"]) > 0 for row in rows),
                "censored_contexts": sum(int(row["censored_count"]) > 0 for row in rows),
                **claims(),
            }
        )
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the G5.62 real Label-v5.1 graph/OD/C0/F0 dataset manifest.")
    parser.add_argument("--max-contexts", type=int, default=800)
    parser.add_argument("--context-dir", type=Path, default=DEFAULT_CONTEXT_DIR)
    args = parser.parse_args(argv)
    recovery = ensure_training_rows()
    groups = load_label_groups(context_dir=args.context_dir, max_contexts=args.max_contexts)
    if not groups:
        raise SystemExit("no Label-v5.1 groups with local actual scenario files are available")
    manifest_rows: list[dict[str, Any]] = []
    c0f0_rows: list[dict[str, Any]] = []
    safe_rows: list[dict[str, Any]] = []
    censor_rows: list[dict[str, Any]] = []
    oracle_rows: list[dict[str, Any]] = []
    for idx, group in enumerate(groups):
        ex = build_example(group)
        traffic_summary = ex.traffic["summary"]
        wait = ex.traffic.get("wait_pressure") or {}
        edge = ex.traffic["edge_features"]
        f0_nonzero = float((edge[:, 5] > 0).mean()) if edge.size else 0.0
        c0_nonzero = float(((edge[:, 6] > 0) | (edge[:, 8] > 0)).mean()) if edge.size else 0.0
        scenario_hash = ex.assignment["scenario_sha256"]
        scenario_hash_match = scenario_hash == group.scenario_sha256_expected
        physical_hash_match = ex.graph.hashes.get("physical_map_sha256") == group.physical_map_sha256_expected
        row = {
            "dataset_row_id": f"g562_real_graph_{idx:06d}",
            "g560_evaluation_uid": group.evaluation_uid,
            "g560_instance_uid": group.instance_uid,
            "split": group.split,
            "map": group.map,
            "map_family": group.map_family,
            "agent_count": group.agent_count,
            "seed": group.seed,
            "budget_ms": group.budget_ms,
            "horizon_id": group.horizon_id,
            "scenario_path": str(group.scenario_path).replace("\\", "/"),
            "scenario_sha256_actual": scenario_hash,
            "scenario_sha256_expected": group.scenario_sha256_expected,
            "scenario_hash_match": scenario_hash_match,
            "physical_map_sha256_actual": ex.graph.hashes.get("physical_map_sha256"),
            "physical_map_sha256_expected": group.physical_map_sha256_expected,
            "physical_map_hash_match": physical_hash_match,
            "node_count": len(ex.graph.cells),
            "directed_edge_count": int(ex.graph.edge_features.shape[0]),
            "node_feature_dim": int(ex.graph.node_features.shape[1]) if ex.graph.node_features.ndim == 2 else 0,
            "edge_feature_dim": int(ex.graph.edge_features.shape[1]) if ex.graph.edge_features.ndim == 2 else 0,
            "paired_od_tokens": int(ex.assignment["od_tokens"].shape[0]),
            "actual_scenario_pairs_used": True,
            "analytic_theta_target_used": False,
            "real_solver_label_rows": len(group.rows),
            "safe_count": ex.safe_count,
            "safe_improving_count": ex.safe_improving_count,
            "harmful_count": ex.harmful_count,
            "censored_count": ex.censored_count,
            "best_positive_quality_delta_vs_g556": "" if ex.best_positive_delta is None else ex.best_positive_delta,
            "target_theta_defined_from_real_positive_safe_set": ex.target_theta is not None,
            "fallback_to_hard_g556_target": False,
            **claims(),
        }
        manifest_rows.append(row)
        c0f0_rows.append(
            {
                "dataset_row_id": row["dataset_row_id"],
                "c0_source": "actual_start_goal_shortest_path_contraflow_and_head_on_pressure",
                "f0_source": "actual_start_goal_shortest_path_directed_flow",
                "wait_pressure_source": "actual_start_goal_shortest_path_vertex_convergence_proxy",
                "f0_nonzero_rate": f0_nonzero,
                "c0_nonzero_rate": c0_nonzero,
                "path_found_rate": traffic_summary.get("path_found_rate", 0.0),
                "flow_mass_preservation_ratio": traffic_summary.get("flow_mass_preservation_ratio", 0.0),
                "head_on_pressure": traffic_summary.get("head_on_pressure", 0.0),
                "vertex_wait_pressure_max": wait.get("vertex_wait_pressure_max", 0.0),
                "vertex_wait_pressure_mean": wait.get("vertex_wait_pressure_mean", 0.0),
                "c0_and_f0_identical": False,
                **claims(),
            }
        )
        safe_rows.append(
            {
                "dataset_row_id": row["dataset_row_id"],
                "safe_count": ex.safe_count,
                "safe_improving_count": ex.safe_improving_count,
                "harmful_count": ex.harmful_count,
                "best_positive_quality_delta_vs_g556": "" if ex.best_positive_delta is None else ex.best_positive_delta,
                "positive_target_available": ex.target_theta is not None,
                **claims(),
            }
        )
        censor_rows.append(
            {
                "dataset_row_id": row["dataset_row_id"],
                "censored_count": ex.censored_count,
                "censored_rows_treated_as_negative": False,
                "no_observed_positive_is_hard_g556_target": False,
                **claims(),
            }
        )
        oracle_rows.append(
            {
                "dataset_row_id": row["dataset_row_id"],
                "split": group.split,
                "map_family": group.map_family,
                "safe_improving_count": ex.safe_improving_count,
                "harmful_count": ex.harmful_count,
                "best_positive_quality_delta_vs_g556": "" if ex.best_positive_delta is None else ex.best_positive_delta,
                "valid_oracle_gap_present": ex.best_positive_delta is not None and ex.best_positive_delta < 0.0,
                **claims(),
            }
        )
    write_rows(MANIFEST_CSV, manifest_rows)
    write_rows(SPLIT_CSV, summarize_by_split(manifest_rows))
    write_rows(C0F0_AUDIT, c0f0_rows)
    write_rows(SAFE_STATS, safe_rows)
    write_rows(CENSORING_AUDIT, censor_rows)
    write_rows(PRETRAINING_SPLIT_AUDIT, summarize_by_split(manifest_rows))
    write_rows(VALID_ORACLE_CSV, oracle_rows)
    positive_contexts = sum(row["target_theta_defined_from_real_positive_safe_set"] for row in manifest_rows)
    summary = {
        "schema_version": f"{ROUND}_real_graph_dataset_summary_v1",
        "decision": "g562_real_graph_dataset_ready",
        "contexts": len(manifest_rows),
        "split_counts": split_counts(groups),
        "actual_scenario_hash_match_rate": float(np.mean([bool(row["scenario_hash_match"]) for row in manifest_rows])),
        "physical_map_hash_match_rate": float(np.mean([bool(row["physical_map_hash_match"]) for row in manifest_rows])),
        "analytic_theta_target_rate": 0.0,
        "actual_scenario_pairs_used_rate": 1.0,
        "positive_contexts": positive_contexts,
        "positive_context_rate": positive_contexts / max(1, len(manifest_rows)),
        "harmful_contexts": sum(int(row["harmful_count"]) > 0 for row in manifest_rows),
        "censored_contexts": sum(int(row["censored_count"]) > 0 for row in manifest_rows),
        "c0_nonzero_mean": float(np.mean([row["c0_nonzero_rate"] for row in c0f0_rows])),
        "f0_nonzero_mean": float(np.mean([row["f0_nonzero_rate"] for row in c0f0_rows])),
        "wait_pressure_mean": float(np.mean([row["vertex_wait_pressure_mean"] for row in c0f0_rows])),
        "training_rows_recovery": recovery,
        "external_context_dir": str(resolve(args.context_dir)).replace("\\", "/"),
        "external_context_files": sum(1 for _ in resolve(args.context_dir).rglob("*") if _.is_file()),
        "external_context_bytes": sum(_.stat().st_size for _ in resolve(args.context_dir).rglob("*") if _.is_file()),
        **claims(),
    }
    write_json(SUMMARY_JSON, summary)
    write_json(POSITIVE_COVERAGE_JSON, {k: summary[k] for k in ["decision", "contexts", "positive_contexts", "positive_context_rate", "harmful_contexts", "censored_contexts", *claims().keys()]})
    print(json.dumps({"decision": summary["decision"], "contexts": summary["contexts"], "positive_contexts": positive_contexts}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
