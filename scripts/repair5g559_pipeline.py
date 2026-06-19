"""Repair5G.5.59 orchestration.

G5.59 repairs the G5.58 evidence chain: topology-preserving graph features,
all-agent traffic priors, non-proxy metrics/losses, and real-solver Label-v5
plumbing.  Synthetic labels are used only for contract tests.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import random
import statistics
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import numpy as np

from gcst.artifact_registry import make_entry, write_registry
from gcst.graph_coarsening import audit_corridor_graph, build_corridor_graph
from gcst.graph_data import build_graph, graph_summary
from gcst.label_v4 import BASELINE_G556, THETA_HI, THETA_LO, THETA_NUMERIC_COLUMNS
from gcst.label_v5 import aggregate_replicates, evaluation_uid, instance_uid, pair_record, row_weight_by_instance, safe_sets
from gcst.map_hash import physical_hashes
from gcst.metrics import coverage_risk, fallback_accuracy, generator_safe_set_hit_rate, ranking_accuracy, safe_recall_at_k
from gcst.scenario_features import generate_assignment
from gcst.traffic_prior import compute_traffic_prior

try:
    import torch

    TORCH_AVAILABLE = True
except Exception:  # pragma: no cover
    torch = None  # type: ignore
    TORCH_AVAILABLE = False

try:
    import repair5g549_common as g549
    import repair5g553_common as g553

    SOLVER_HELPERS_AVAILABLE = True
except Exception:  # pragma: no cover
    g549 = None  # type: ignore
    g553 = None  # type: ignore
    SOLVER_HELPERS_AVAILABLE = False

ROUND = "phase5p5_repair5g559"
PRIMARY_BASELINE = "g556_c063174"
START_COMMIT = "6b0c5e807239b68f1c9c86018db3424c25739525"
REMOTE_ARTIFACT_ROOT = Path(os.environ.get("REMOTE_ARTIFACT_ROOT", "/root/shared-nvme/czr004_g559_remote_artifacts"))

CLAIMS_CLOSED = {
    "phase5p5_allowed": False,
    "phase6_allowed": False,
    "runtime_claim_allowed": False,
    "learned_runtime_policy_validated": False,
    "aaai_ready": False,
}

AUTOPSY_MD = f"outputs/reports/{ROUND}_g558_failure_autopsy.md"
AUTOPSY_JSON = f"outputs/reports/{ROUND}_g558_failure_autopsy_summary.json"
LOSS_METRIC_CSV = f"outputs/tables/{ROUND}_loss_metric_mismatch_audit.csv"
CONNECTIVITY_CSV = f"outputs/tables/{ROUND}_graph_connectivity_audit.csv"
BATCH_INV_CSV = f"outputs/tables/{ROUND}_batch_invariance_audit.csv"
TRAFFIC_NONZERO_CSV = f"outputs/tables/{ROUND}_traffic_nonzero_audit.csv"
AGENT_MASS_CSV = f"outputs/tables/{ROUND}_agent_mass_audit.csv"

LIT_MD = f"outputs/reports/{ROUND}_literature_code_audit.md"
LIT_MATRIX_CSV = f"outputs/tables/{ROUND}_literature_method_matrix.csv"
LIT_MANIFEST_CSV = f"outputs/tables/{ROUND}_official_repo_commit_manifest.csv"

CORRIDOR_JSON = f"outputs/reports/{ROUND}_corridor_graph_summary.json"
CORRIDOR_CSV = f"outputs/tables/{ROUND}_corridor_graph_manifest.csv"
INSTANCE_JSON = f"outputs/reports/{ROUND}_instance_generation_summary.json"
INSTANCE_CSV = f"outputs/tables/{ROUND}_instance_manifest.csv"
CODEBOOK_JSON = f"outputs/reports/{ROUND}_codebook_summary.json"
CODEBOOK_CSV = f"outputs/tables/{ROUND}_theta_codebook.csv"
PLAN_CSV = f"outputs/tables/{ROUND}_labelv5_pilot_plan.csv"
PILOT_JSON = f"outputs/reports/{ROUND}_labelv5_pilot_summary.json"
PILOT_PAIR_CSV = f"outputs/tables/{ROUND}_labelv5_pair_rows.csv"
PILOT_AGG_CSV = f"outputs/tables/{ROUND}_labelv5_replicate_aggregates.csv"
PILOT_SAFE_CSV = f"outputs/tables/{ROUND}_labelv5_safe_sets.csv"
SYNTHETIC_JSON = f"outputs/reports/{ROUND}_synthetic_contract_summary.json"
SYNTHETIC_METRICS_CSV = f"outputs/tables/{ROUND}_synthetic_contract_metrics.csv"
LEARNABILITY_JSON = f"outputs/reports/{ROUND}_real_learnability_summary.json"
LEARNABILITY_CSV = f"outputs/tables/{ROUND}_real_learnability_metrics.csv"
ACTIVE_JSON = f"outputs/reports/{ROUND}_active_round_plan_summary.json"
ACTIVE_CSV = f"outputs/tables/{ROUND}_active_round_plan.csv"
POLICY_JSON = f"outputs/reports/{ROUND}_policy_freeze_summary.json"
STAGE1_JSON = f"outputs/reports/{ROUND}_stage1_summary.json"
STAGE2_JSON = f"outputs/reports/{ROUND}_stage2_summary.json"
BLIND_JSON = f"outputs/reports/{ROUND}_blind_summary.json"
DECISION_MD = f"outputs/reports/{ROUND}_decision.md"
DECISION_JSON = f"outputs/reports/{ROUND}_decision_summary.json"
REGISTRY_JSON = f"outputs/reports/{ROUND}_artifact_registry.json"
SERVER_JSON = f"outputs/reports/{ROUND}_5090_server_run_summary.json"
SERVER_MD = f"outputs/reports/{ROUND}_5090_server_run.md"


def resolve(path: str | Path) -> Path:
    p = Path(path)
    return p if p.is_absolute() else ROOT / p


def ensure_parent(path: str | Path) -> None:
    resolve(path).parent.mkdir(parents=True, exist_ok=True)


def read_rows(path: str | Path, limit: int | None = None) -> list[dict[str, str]]:
    p = resolve(path)
    if not p.exists():
        return []
    rows: list[dict[str, str]] = []
    with p.open(newline="", encoding="utf-8", errors="replace") as handle:
        for row in csv.DictReader(handle):
            rows.append(dict(row))
            if limit and len(rows) >= limit:
                break
    return rows


def write_rows(path: str | Path, rows: Iterable[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    rows = [dict(row) for row in rows]
    ensure_parent(path)
    if fieldnames is None:
        fieldnames = []
        seen = set()
        for row in rows:
            for key in row:
                if key not in seen:
                    seen.add(key)
                    fieldnames.append(key)
    with resolve(path).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: str | Path, payload: dict[str, Any]) -> None:
    ensure_parent(path)
    resolve(path).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_json(path: str | Path, default: Any = None) -> Any:
    p = resolve(path)
    return json.loads(p.read_text(encoding="utf-8", errors="replace")) if p.exists() else default


def write_text(path: str | Path, text: str) -> None:
    ensure_parent(path)
    resolve(path).write_text(text, encoding="utf-8")


def num(value: Any, default: float = 0.0) -> float:
    try:
        out = float(value)
        return out if math.isfinite(out) else default
    except Exception:
        return default


def boolish(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def csv_number(value: Any, digits: int = 12) -> str:
    value = num(value, math.nan)
    return "" if not math.isfinite(value) else f"{value:.{digits}g}"


def git_head() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return ""


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser()
    p.add_argument("--contexts", type=int, default=96)
    p.add_argument("--pilot-instances", type=int, default=48)
    p.add_argument("--candidates-per-instance", type=int, default=8)
    p.add_argument("--codebook-size", type=int, default=256)
    p.add_argument("--row-limit", type=int, default=0)
    p.add_argument("--max-workers", type=int, default=1)
    p.add_argument("--seed", type=int, default=20260619)
    p.add_argument("--binary", type=Path, default=Path("build/phase1a-batch/phase1a_batch"))
    p.add_argument("--smoke", action="store_true")
    p.add_argument("--ids", nargs="*", type=int)
    return p


def parse_args_checked(argv: list[str] | None, label: str) -> argparse.Namespace:
    args = parser().parse_args(argv)
    bad = sorted({int(value) for value in (args.ids or []) if 166 <= int(value) <= 205})
    if bad:
        print(json.dumps({"decision": "reserved_id_guard_rejected", "label": label, "ids": bad}))
        raise SystemExit(1)
    return args


def default_topologies(limit: int = 24) -> list[dict[str, Any]]:
    names = [
        ("empty-8-8", "empty", 8, 8),
        ("empty-16-16", "empty", 16, 16),
        ("empty-32-32", "empty", 32, 32),
        ("random-8-8-20", "random", 8, 8),
        ("random-32-32-10", "random", 32, 32),
        ("random-32-32-20", "random", 32, 32),
        ("maze-32-32-2", "maze", 32, 32),
        ("maze-32-32-4", "maze", 32, 32),
        ("room-32-32-4", "room", 32, 32),
        ("room-64-64-8", "room", 64, 64),
        ("warehouse-10-20-10-2-1", "warehouse", 32, 32),
        ("warehouse-10-20-10-2-2", "warehouse", 32, 32),
        ("connector", "irregular_bottleneck", 32, 32),
        ("corners", "irregular_bottleneck", 32, 32),
        ("loop-chain", "irregular_bottleneck", 32, 32),
        ("tunnel", "irregular_bottleneck", 32, 32),
        ("string", "irregular_bottleneck", 32, 32),
        ("tree", "irregular_bottleneck", 32, 32),
        ("den312d", "game", 64, 64),
        ("brc202d", "game", 64, 64),
        ("Berlin_1_256", "city", 64, 64),
        ("Boston_0_256", "city", 64, 64),
        ("Paris_1_256", "city", 64, 64),
        ("lak303d", "game", 64, 64),
    ]
    return [
        {"topology_id": f"g559_topo_{idx:03d}", "map": name, "map_family": family, "width": width, "height": height}
        for idx, (name, family, width, height) in enumerate(names[:limit])
    ]


def main_record_server_run(argv: list[str] | None = None) -> int:
    _args = parse_args_checked(argv, "G5.59 server run")
    gpu = ""
    try:
        gpu = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=5,
        ).stdout.strip()
    except Exception:
        pass
    summary = {
        "schema_version": f"{ROUND}_5090_server_run_summary_v1",
        "decision": "g559_5090_server_run_recorded",
        "hostname": "redacted_rtx5090_server",
        "cwd": str(ROOT),
        "gpu_sample": gpu,
        "tmux_required": True,
        **CLAIMS_CLOSED,
    }
    write_json(SERVER_JSON, summary)
    write_text(SERVER_MD, f"# G5.59 RTX5090 Server Run\n\n- decision: `{summary['decision']}`\n- gpu: `{gpu}`\n- tmux: `required`\n")
    print(json.dumps({"decision": summary["decision"]}))
    return 0


def main_audit_g558_failure(argv: list[str] | None = None) -> int:
    _args = parse_args_checked(argv, "G5.59 G5.58 failure autopsy")
    g558_truth = load_json("outputs/reports/phase5p5_repair5g558_neural_implementation_truth_summary.json", {})
    g558_label = load_json("outputs/reports/phase5p5_repair5g558_label_v4_summary.json", {})
    g558_local = load_json("outputs/reports/phase5p5_repair5g558_local_learnability_summary.json", {})
    graph_rows = read_rows("outputs/tables/phase5p5_repair5g558_real_graph_cache_manifest.csv")
    traffic_rows = read_rows("outputs/tables/phase5p5_repair5g558_real_traffic_prior_manifest.csv")
    loss_rows = [
        {"finding": "critic_loss_no_explicit_pairwise_or_listwise_ranking", "g558_status": True, "g559_action": "added gcst.listwise_losses"},
        {"finding": "generator_target_single_synthetic_theta", "g558_status": True, "g559_action": "Label-v5 safe-set and set-matching APIs added"},
        {"finding": "fallback_accuracy_proxy_identity", "g558_status": True, "g559_action": "fallback_accuracy now consumes predictions"},
        {"finding": "success_gain_accuracy_proxy_identity", "g558_status": True, "g559_action": "metric removed from pass gate"},
        {"finding": "generator_safe_set_hit_rate_proxy", "g558_status": True, "g559_action": "generator_safe_set_hit_rate consumes generated ids"},
        {"finding": "narrow_ordered_slice_evaluation", "g558_status": True, "g559_action": "context-balanced Label-v5 evaluation plan"},
    ]
    write_rows(LOSS_METRIC_CSV, [{**row, **CLAIMS_CLOSED} for row in loss_rows])
    avg_nodes = statistics.fmean([num(r.get("node_count")) for r in graph_rows]) if graph_rows else 0.0
    avg_edges = statistics.fmean([num(r.get("directed_edge_count")) for r in graph_rows]) if graph_rows else 0.0
    conn_rows = []
    for topo in default_topologies(limit=24):
        audit = audit_corridor_graph(topo)
        conn_rows.append({**audit, **CLAIMS_CLOSED})
    write_rows(CONNECTIVITY_CSV, conn_rows)
    batch_rows = [
        {"invariant": "single_instance_vs_batched_prediction", "g558_violation": True, "g559_current_fix": "per_graph_global_attention", "required_test": "test_batch_composition_invariance", **CLAIMS_CLOSED},
        {"invariant": "batch_order_invariance", "g558_violation": True, "g559_current_fix": "per_graph_global_attention", "required_test": "test_batch_order_invariance", **CLAIMS_CLOSED},
    ]
    write_rows(BATCH_INV_CSV, batch_rows)
    zero_flow = sum(1 for r in traffic_rows if num(r.get("edge_use_total")) <= 0)
    write_rows(
        TRAFFIC_NONZERO_CSV,
        [
            {
                "metric": "g558_zero_edge_use_contexts",
                "value": zero_flow,
                "denominator": len(traffic_rows),
                "rate": csv_number(zero_flow / max(1, len(traffic_rows))),
                "g559_action": "traffic computed on full graph with path_found_rate and flow_mass_preservation",
                **CLAIMS_CLOSED,
            }
        ],
    )
    agent_rows = []
    for agents in [32, 64, 128, 256, 512, 1024]:
        agent_rows.append(
            {
                "requested_agent_count": agents,
                "g558_max_agents": 64,
                "g558_represented_agent_mass": min(agents, 64),
                "g558_mass_preserved": agents <= 64,
                "g559_required_represented_agent_mass": agents,
                **CLAIMS_CLOSED,
            }
        )
    write_rows(AGENT_MASS_CSV, agent_rows)
    summary = {
        "schema_version": f"{ROUND}_g558_failure_autopsy_summary_v1",
        "decision": "g559_g558_representation_bug_confirmed",
        "g558_real_neural_implementation": bool(g558_truth.get("decision") == "g558_real_neural_implementation_truth_passed"),
        "trainable_parameters": g558_truth.get("trainable_parameter_count", 0),
        "optimizer_steps": g558_truth.get("optimizer_step_count", 0),
        "cuda_used": g558_truth.get("actual_cuda_device_used", False),
        "raw_solver_pair_rows_available": bool(g558_label.get("raw_g557_pair_rows_available", False)),
        "training_label_source": "synthetic analytic learnability labels",
        "training_contexts": g558_label.get("contexts", 192),
        "candidate_rows": g558_label.get("candidate_pair_rows", 12288),
        "actual_solver_stage1_rows": 0,
        "actual_solver_stage2_rows": 0,
        "actual_solver_blind_rows": 0,
        "critic_train_ranking_accuracy": g558_truth.get("critic_train_ranking_accuracy", ""),
        "local_learnability_decision": g558_local.get("decision", ""),
        "g558_average_nodes_per_topology": avg_nodes,
        "g558_average_directed_edges_per_topology": avg_edges,
        "g558_zero_flow_contexts": zero_flow,
        **CLAIMS_CLOSED,
    }
    write_json(AUTOPSY_JSON, summary)
    write_text(
        AUTOPSY_MD,
        "# G5.59 Autopsy of G5.58\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- real neural implementation: `{summary['g558_real_neural_implementation']}`\n"
        f"- trainable parameters: `{summary['trainable_parameters']}`\n"
        f"- raw solver pair rows available: `{summary['raw_solver_pair_rows_available']}`\n"
        f"- training label source: `{summary['training_label_source']}`\n"
        f"- tiny ranking accuracy: `{summary['critic_train_ranking_accuracy']}`\n\n"
        "Conclusion: G5.58 was an implementation smoke, not a real solver-label test of GCST. "
        "G5.59 therefore repairs representation, metrics, and Label-v5 provenance before any claim can open.\n",
    )
    print(json.dumps({"decision": summary["decision"]}))
    return 0


def main_literature_code_audit(argv: list[str] | None = None) -> int:
    _args = parse_args_checked(argv, "G5.59 literature code audit")
    repos = [
        {
            "name": "GGO",
            "url": "https://github.com/lunjohnzhang/ggo_public",
            "head_commit": "d8de695dbd95c912ee59e8e626d63e511da684a7",
            "lesson": "CMA-ES/control optimizer, solver-facing simulation as truth, exact reloadable logs",
        },
        {
            "name": "LaGAT",
            "url": "https://github.com/proroklab/lagat",
            "head_commit": "69e0611d10567daf76db37fe9ca6af92766df188",
            "lesson": "edge-aware graph attention and learned/search safeguards",
        },
        {
            "name": "MAPF-GPT",
            "url": "https://github.com/CognitiveAISystems/MAPF-GPT",
            "head_commit": "d6307447ddc6bc2b7bf5da4f81d4e0707fbc8fa3",
            "lesson": "streaming datasets, train/validation separation, reproducible configs",
        },
        {
            "name": "ML-MAPF-with-Search",
            "url": "https://github.com/Rishi-V/ML-MAPF-with-Search",
            "head_commit": "ed9e273ac0d72f492d3fa5f799dc3a20f17a0364",
            "lesson": "learned guidance needs strong search shield/baseline",
        },
    ]
    write_rows(LIT_MANIFEST_CSV, [{**r, "vendored": False, "modified": False, **CLAIMS_CLOSED} for r in repos])
    matrix = [
        {"method_family": "GGO", "adopted_in_g559": "CMA-ES/CEM teacher/control, reloadable logs", "not_adopted": "guidance graph replacement"},
        {"method_family": "LaGAT", "adopted_in_g559": "edge-aware local layers plus per-graph global attention", "not_adopted": "MAPF action policy"},
        {"method_family": "MAPF-GPT", "adopted_in_g559": "dataset streaming and split rigor", "not_adopted": "trajectory/action imitation target"},
        {"method_family": "CS-PIBT/ML-MAPF-with-Search", "adopted_in_g559": "strong g556 fallback shield", "not_adopted": "search action learning"},
        {"method_family": "GraphGPS/Exphormer", "adopted_in_g559": "local real-edge aggregation with graph-local global attention", "not_adopted": "cross-instance attention"},
        {"method_family": "QD-MAPPER", "adopted_in_g559": "morphology-stratified maps and physical hash accounting", "not_adopted": "claiming aliases as new maps"},
    ]
    write_rows(LIT_MATRIX_CSV, [{**row, **CLAIMS_CLOSED} for row in matrix])
    write_text(
        LIT_MD,
        "# G5.59 Literature and Code Audit\n\n"
        "- Inspected official repositories for GGO, LaGAT, MAPF-GPT, and ML-MAPF-with-Search.\n"
        "- No external code is vendored or modified.\n"
        "- Adopted lessons are limited to representation, data engineering, controls, and reproducibility.\n",
    )
    print(json.dumps({"decision": "g559_literature_code_audit_written"}))
    return 0


def main_build_corridor_graphs(argv: list[str] | None = None) -> int:
    args = parse_args_checked(argv, "G5.59 corridor graphs")
    rows = []
    for topo in default_topologies(limit=24 if not args.smoke else 6):
        rows.append({**audit_corridor_graph(topo), **CLAIMS_CLOSED})
    unique_hashes = len({r["adjacency_sha256"] for r in rows})
    summary = {
        "schema_version": f"{ROUND}_corridor_graph_summary_v1",
        "decision": "g559_corridor_graphs_materialized",
        "topologies": len(rows),
        "unique_physical_map_hashes": unique_hashes,
        "all_cells_assigned": all(boolish(r.get("all_cells_assigned")) for r in rows),
        "component_count_unchanged": all(boolish(r.get("component_count_unchanged")) for r in rows),
        "max_shortest_path_distortion": max([num(r.get("shortest_path_distortion_max")) for r in rows], default=0.0),
        **CLAIMS_CLOSED,
    }
    write_rows(CORRIDOR_CSV, rows)
    write_json(CORRIDOR_JSON, summary)
    print(json.dumps({"decision": summary["decision"], "topologies": len(rows)}))
    return 0


def build_instances(count: int, seed: int) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    topologies = default_topologies(limit=24)
    regimes = ["uniform_random", "opposite_side_cross_flow", "room_to_room_door_bottleneck", "warehouse_aisle_to_aisle", "clustered_starts_to_dispersed_goals"]
    budgets = [500, 1000, 2000, 5000]
    rows: list[dict[str, Any]] = []
    for idx in range(count):
        topo = topologies[idx % len(topologies)]
        graph = build_corridor_graph(topo).graph
        agents = [16, 32, 64, 96, 128, 256][idx % 6]
        context = {
            **topo,
            "agent_count": agents,
            "agents": agents,
            "seed": 5000 + idx,
            "solver_seed": 7000 + idx,
            "nominal_budget_ms": budgets[idx % len(budgets)],
            "base_time_limit_sec": max(0.25, budgets[idx % len(budgets)] / 1000.0),
            "ltm_max_iterations": 2 + (idx % 3),
            "start_goal_regime": regimes[idx % len(regimes)],
        }
        assignment = generate_assignment(graph, context, max_agents=None)
        traffic = compute_traffic_prior(graph, assignment)
        hashes = physical_hashes(topo)
        uid = instance_uid(hashes["physical_map_sha256"], assignment["start_goal_assignment_hash"], agents, context["nominal_budget_ms"], context["ltm_max_iterations"])
        rows.append(
            {
                "instance_uid": uid,
                "evaluation_uid": evaluation_uid(uid, context["solver_seed"]),
                "context_id": f"g559_ctx_{idx:06d}",
                "map": topo["map"],
                "map_family": topo["map_family"],
                "topology_id": topo["topology_id"],
                "agents": agents,
                "agent_count": agents,
                "seed": context["solver_seed"],
                "budget_ms": context["nominal_budget_ms"],
                "nominal_budget_ms": context["nominal_budget_ms"],
                "horizon_id": f"g559_b{context['nominal_budget_ms']}_i{context['ltm_max_iterations']}",
                "base_time_limit_sec": context["base_time_limit_sec"],
                "ltm_max_iterations": context["ltm_max_iterations"],
                "physical_map_sha256": hashes["physical_map_sha256"],
                "adjacency_sha256": hashes["adjacency_sha256"],
                "start_goal_assignment_sha256": assignment["start_goal_assignment_hash"],
                "requested_agent_count": assignment["requested_agent_count"],
                "encoded_OD_token_count": assignment["encoded_agent_count"],
                "represented_agent_mass": assignment["represented_agent_mass"],
                "represented_flow_mass": traffic["summary"]["edge_use_total"],
                "path_found_rate": traffic["summary"]["path_found_rate"],
                "nonzero_flow": traffic["summary"]["nonzero_flow"],
                **CLAIMS_CLOSED,
            }
        )
    rng.shuffle(rows)
    return rows


def main_generate_real_instances(argv: list[str] | None = None) -> int:
    args = parse_args_checked(argv, "G5.59 instance generation")
    rows = build_instances(args.pilot_instances if args.smoke else max(args.pilot_instances, 96), args.seed)
    summary = {
        "schema_version": f"{ROUND}_instance_generation_summary_v1",
        "decision": "g559_instance_manifest_ready",
        "instances": len(rows),
        "unique_instance_uids": len({r["instance_uid"] for r in rows}),
        "unique_physical_map_hashes": len({r["adjacency_sha256"] for r in rows}),
        "map_families": len({r["map_family"] for r in rows}),
        "all_agent_mass_preserved": all(num(r["represented_agent_mass"]) == num(r["requested_agent_count"]) for r in rows),
        "path_found_rate_min": min([num(r["path_found_rate"]) for r in rows], default=0.0),
        **CLAIMS_CLOSED,
    }
    write_rows(INSTANCE_CSV, rows)
    write_json(INSTANCE_JSON, summary)
    print(json.dumps({"decision": summary["decision"], "instances": len(rows)}))
    return 0


def theta_columns() -> list[str]:
    return list(g553.THETA_COLUMNS) if SOLVER_HELPERS_AVAILABLE else [*THETA_NUMERIC_COLUMNS, "theta_goal_projection_mode_flow_shield", "theta_goal_projection_mode_agent_progress", "theta_goal_projection_mode_none"]


def numeric_bounds() -> tuple[np.ndarray, np.ndarray]:
    if SOLVER_HELPERS_AVAILABLE:
        lo = np.asarray([float(g553.THETA_BOUNDS[col][0]) for col in THETA_NUMERIC_COLUMNS], dtype=np.float32)
        hi = np.asarray([float(g553.THETA_BOUNDS[col][1]) for col in THETA_NUMERIC_COLUMNS], dtype=np.float32)
        return lo, hi
    return THETA_LO, THETA_HI


def baseline_theta_row() -> dict[str, Any]:
    numeric = {col: float(value) for col, value in zip(THETA_NUMERIC_COLUMNS, BASELINE_G556)}
    return {**numeric, "theta_goal_projection_mode_flow_shield": 1, "theta_goal_projection_mode_agent_progress": 0, "theta_goal_projection_mode_none": 0}


def main_build_codebook(argv: list[str] | None = None) -> int:
    args = parse_args_checked(argv, "G5.59 codebook")
    rng = np.random.default_rng(args.seed)
    baseline = baseline_theta_row()
    cols = theta_columns()
    rows = [{"candidate_id": PRIMARY_BASELINE, "candidate_source": "primary_baseline", "theta_id": PRIMARY_BASELINE, **baseline, **CLAIMS_CLOSED}]
    count = args.codebook_size if not args.smoke else min(args.codebook_size, 64)
    for idx in range(max(0, count - 1)):
        scale = 0.05 + 0.35 * ((idx % 17) / 16)
        lo, hi = numeric_bounds()
        vec = BASELINE_G556 + rng.normal(0.0, scale, size=BASELINE_G556.shape).astype(np.float32) * (hi - lo)
        vec = np.minimum(np.maximum(vec, lo), hi)
        row = {col: float(value) for col, value in zip(THETA_NUMERIC_COLUMNS, vec)}
        row.update({"theta_goal_projection_mode_flow_shield": 1, "theta_goal_projection_mode_agent_progress": 0, "theta_goal_projection_mode_none": 0})
        rows.append({"candidate_id": f"g559_c{idx:05d}", "theta_id": f"g559_c{idx:05d}", "candidate_source": "sobol_like_trust_region", **row, **CLAIMS_CLOSED})
    rows = [{k: row.get(k, "") for k in ["candidate_id", "theta_id", "candidate_source", *cols, *CLAIMS_CLOSED.keys()]} for row in rows]
    write_rows(CODEBOOK_CSV, rows)
    write_json(CODEBOOK_JSON, {"schema_version": f"{ROUND}_codebook_summary_v1", "decision": "g559_codebook_ready", "candidate_count": len(rows), "primary_baseline": PRIMARY_BASELINE, **CLAIMS_CLOSED})
    print(json.dumps({"decision": "g559_codebook_ready", "candidates": len(rows)}))
    return 0


def main_plan_labelv5_pilot(argv: list[str] | None = None) -> int:
    args = parse_args_checked(argv, "G5.59 Label-v5 pilot plan")
    if not resolve(INSTANCE_CSV).exists():
        main_generate_real_instances(["--pilot-instances", str(args.pilot_instances), "--seed", str(args.seed)] + (["--smoke"] if args.smoke else []))
    if not resolve(CODEBOOK_CSV).exists():
        main_build_codebook(["--codebook-size", str(args.codebook_size), "--seed", str(args.seed)] + (["--smoke"] if args.smoke else []))
    instances = read_rows(INSTANCE_CSV, limit=args.pilot_instances)
    candidates = [r for r in read_rows(CODEBOOK_CSV) if r.get("candidate_id") != PRIMARY_BASELINE]
    baseline = next((r for r in read_rows(CODEBOOK_CSV) if r.get("candidate_id") == PRIMARY_BASELINE), {**baseline_theta_row(), "candidate_id": PRIMARY_BASELINE})
    plan_rows = []
    for idx, inst in enumerate(instances):
        common = {
            **inst,
            "panel": "g559_labelv5_pilot",
            "route": "level0_short_budget",
            "short_budget_ms": min(1000, int(num(inst.get("nominal_budget_ms"), 1000))),
            "traffic_input_mode": "P",
        }
        plan_rows.append(
            {
                "plan_row_id": f"g559_pilot_{len(plan_rows):08d}",
                **common,
                "role": "static_flow_shield",
                "candidate_id": PRIMARY_BASELINE,
                "theta_id": PRIMARY_BASELINE,
                "materialized_method": PRIMARY_BASELINE,
                "sampling_policy": "paired_baseline",
                "theta_cluster": "primary_g556_baseline",
                **{k: baseline.get(k, "") for k in theta_columns()},
                **CLAIMS_CLOSED,
            }
        )
        offset = (idx * args.candidates_per_instance) % max(1, len(candidates))
        slate = [candidates[(offset + j) % len(candidates)] for j in range(min(args.candidates_per_instance, len(candidates)))]
        for cand in slate:
            plan_rows.append(
                {
                    "plan_row_id": f"g559_pilot_{len(plan_rows):08d}",
                    **common,
                    "role": f"generated_theta::{cand['candidate_id']}",
                    "candidate_id": cand["candidate_id"],
                    "theta_id": cand["candidate_id"],
                    "materialized_method": cand["candidate_id"],
                    "sampling_policy": "level0_rotating_codebook",
                    "theta_cluster": "g559_codebook",
                    **{k: cand.get(k, "") for k in theta_columns()},
                    **CLAIMS_CLOSED,
                }
            )
    write_rows(PLAN_CSV, plan_rows)
    print(json.dumps({"decision": "g559_labelv5_pilot_plan_ready", "planned_rows": len(plan_rows)}))
    return 0


def solver_binary(args: argparse.Namespace) -> Path:
    candidates = [args.binary, Path("build/phase1a-batch/phase1a_batch"), Path("build/phase1-ltm/phase1a_batch"), Path("build/phase1a-batch/phase1a_batch.exe")]
    for cand in candidates:
        p = resolve(cand)
        if p.exists():
            return p
    return resolve(args.binary)


def write_pilot_skip(decision: str, reason: str, planned_rows: int = 0) -> dict[str, Any]:
    summary = {
        "schema_version": f"{ROUND}_labelv5_pilot_summary_v1",
        "decision": decision,
        "reason": reason,
        "real_solver_rows": 0,
        "planned_solver_rows": planned_rows,
        "raw_solver_labelv5_available": False,
        **CLAIMS_CLOSED,
    }
    write_json(PILOT_JSON, summary)
    write_rows(PILOT_PAIR_CSV, [], fieldnames=["instance_uid", "evaluation_uid", "theta_id", "candidate_success", "baseline_success", "success_regression", "quality_delta_vs_g556", *CLAIMS_CLOSED.keys()])
    write_rows(PILOT_AGG_CSV, [], fieldnames=["instance_uid", "theta_id", "replicate_count", "success_regression_count", "quality_delta_mean", *CLAIMS_CLOSED.keys()])
    write_rows(PILOT_SAFE_CSV, [], fieldnames=["instance_uid", "safe_theta_ids", "safe_improving_theta_ids", "fallback_required", *CLAIMS_CLOSED.keys()])
    return summary


def main_run_labelv5_pilot(argv: list[str] | None = None) -> int:
    args = parse_args_checked(argv, "G5.59 Label-v5 pilot run")
    if not resolve(PLAN_CSV).exists():
        main_plan_labelv5_pilot(argv)
    plan = read_rows(PLAN_CSV)
    binary = solver_binary(args)
    if not SOLVER_HELPERS_AVAILABLE:
        summary = write_pilot_skip("g559_real_labelv5_pilot_underpowered", "solver helper imports unavailable", len(plan))
        print(json.dumps({"decision": summary["decision"], "rows": 0}))
        return 0
    if not binary.exists():
        summary = write_pilot_skip("g559_real_labelv5_pilot_underpowered", f"missing Linux solver binary {binary}", len(plan))
        print(json.dumps({"decision": summary["decision"], "rows": 0}))
        return 0
    result_csv = str(REMOTE_ARTIFACT_ROOT / "pair_rows" / "labelv5_pilot_results.csv")
    raw_csv = str(REMOTE_ARTIFACT_ROOT / "pair_rows" / "labelv5_pilot_results.raw.csv")
    log_dir = str(REMOTE_ARTIFACT_ROOT / "solver_logs" / "labelv5_pilot")
    try:
        g549.run_probe_plan(
            plan,
            binary=binary,
            overwrite=False,
            row_limit=args.row_limit,
            max_workers=args.max_workers,
            registry_path=str(resolve(CODEBOOK_CSV)),
            result_csv=result_csv,
            raw_csv=raw_csv,
            log_dir=log_dir,
            run_jsonl=str(REMOTE_ARTIFACT_ROOT / "solver_logs" / "runs.jsonl"),
            command_jsonl=str(REMOTE_ARTIFACT_ROOT / "solver_logs" / "commands.jsonl"),
            update_jsonl=str(REMOTE_ARTIFACT_ROOT / "solver_logs" / "updates.jsonl"),
            probe_jsonl=str(REMOTE_ARTIFACT_ROOT / "solver_logs" / "counterfactual_probes.jsonl"),
            checkpoint_jsonl=str(REMOTE_ARTIFACT_ROOT / "solver_logs" / "checkpoints.jsonl"),
            status_json=str(REMOTE_ARTIFACT_ROOT / "solver_logs" / "status.json"),
            scenario_dir=str(REMOTE_ARTIFACT_ROOT / "contexts" / "scenarios"),
            scenario_metadata=str(REMOTE_ARTIFACT_ROOT / "contexts" / "scenario_metadata.json"),
            manifest_prefix="g559_labelv5_pilot",
            row_prefix="g559_labelv5",
            execution_mode="new_g559_labelv5_real_solver_row",
        )
    except Exception as exc:
        summary = write_pilot_skip("g559_real_labelv5_pilot_underpowered", f"real solver pilot failed: {type(exc).__name__}: {exc}", len(plan))
        print(json.dumps({"decision": summary["decision"], "rows": 0}))
        return 0
    compact_rows = read_rows(result_csv)
    write_rows(PILOT_PAIR_CSV, compact_rows[:5000])
    summary = {
        "schema_version": f"{ROUND}_labelv5_pilot_summary_v1",
        "decision": "g559_labelv5_pilot_real_solver_rows_recorded" if compact_rows else "g559_real_labelv5_pilot_underpowered",
        "real_solver_rows": len(compact_rows),
        "planned_solver_rows": len(plan),
        "raw_solver_labelv5_available": bool(compact_rows),
        "remote_result_csv": result_csv,
        **CLAIMS_CLOSED,
    }
    write_json(PILOT_JSON, summary)
    print(json.dumps({"decision": summary["decision"], "rows": len(compact_rows)}))
    return 0


def main_analyze_labelv5_pilot(argv: list[str] | None = None) -> int:
    _args = parse_args_checked(argv, "G5.59 Label-v5 pilot analysis")
    pilot = load_json(PILOT_JSON, {})
    rows = read_rows(PILOT_PAIR_CSV)
    if not rows or not bool(pilot.get("raw_solver_labelv5_available")):
        summary = write_pilot_skip("g559_real_labelv5_pilot_underpowered", pilot.get("reason", "no real solver rows available"), int(pilot.get("planned_solver_rows", 0)))
        print(json.dumps({"decision": summary["decision"]}))
        return 0
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    baselines: dict[str, dict[str, Any]] = {}
    for row in rows:
        uid = str(row.get("instance_uid", row.get("context_horizon_key", "")))
        if row.get("candidate_id") == PRIMARY_BASELINE or row.get("role") == "static_flow_shield":
            baselines[uid] = row
        else:
            grouped[(uid, row.get("candidate_id", ""))] = row
    pair_rows = []
    for (uid, _tid), cand in grouped.items():
        base = baselines.get(uid)
        if not base:
            continue
        cand = {**cand, "instance_uid": uid, "evaluation_uid": cand.get("evaluation_uid", cand.get("seed", ""))}
        base = {**base, "instance_uid": uid, "evaluation_uid": base.get("evaluation_uid", base.get("seed", ""))}
        pair_rows.append(pair_record(cand, base))
    weights = row_weight_by_instance(pair_rows)
    for row, weight in zip(pair_rows, weights):
        row["row_weight"] = weight
        row.update(CLAIMS_CLOSED)
    agg = [{**row, **CLAIMS_CLOSED} for row in aggregate_replicates(pair_rows)]
    safe = [{**row, **CLAIMS_CLOSED} for row in safe_sets(agg)]
    write_rows(PILOT_PAIR_CSV, pair_rows)
    write_rows(PILOT_AGG_CSV, agg)
    write_rows(PILOT_SAFE_CSV, safe)
    summary = {**pilot, "decision": "g559_labelv5_pilot_analyzed", "pair_rows": len(pair_rows), "aggregate_rows": len(agg), "safe_set_rows": len(safe), **CLAIMS_CLOSED}
    write_json(PILOT_JSON, summary)
    print(json.dumps({"decision": summary["decision"], "pair_rows": len(pair_rows)}))
    return 0


def main_synthetic_contract(argv: list[str] | None = None) -> int:
    _args = parse_args_checked(argv, "G5.59 synthetic contract")
    rng = np.random.default_rng(559)
    n = 256
    quality = rng.normal(0, 1, size=n)
    scores = -quality + rng.normal(0, 0.001, size=n)
    safe = quality < 0.25
    fallback_required = ~safe
    fallback_prob = fallback_required.astype(float)
    generated = [[f"theta_{i}"] for i in range(n)]
    safe_ids = [{f"theta_{i}"} if safe[i] else set() for i in range(n)]
    metrics = [
        {"metric": "ranking_accuracy", "value": ranking_accuracy(scores, quality), "required": 0.98},
        {"metric": "safe_classification", "value": float(((scores > -0.25) == safe).mean()), "required": 0.99},
        {"metric": "fallback_accuracy", "value": fallback_accuracy(fallback_prob, fallback_required), "required": 0.99},
        {"metric": "best_of_k_safe_set_hit", "value": generator_safe_set_hit_rate(generated, safe_ids), "required": 0.98},
        {"metric": "safe_recall_at_16", "value": safe_recall_at_k(scores, safe, k=16), "required": 0.01},
    ]
    for row in metrics:
        row["passed"] = float(row["value"]) >= float(row["required"])
        row.update(CLAIMS_CLOSED)
    passed = all(row["passed"] for row in metrics[:4])
    write_rows(SYNTHETIC_METRICS_CSV, metrics)
    summary = {"schema_version": f"{ROUND}_synthetic_contract_summary_v1", "decision": "g559_synthetic_contract_passed" if passed else "g559_synthetic_contract_failed", "passed": passed, **CLAIMS_CLOSED}
    write_json(SYNTHETIC_JSON, summary)
    print(json.dumps({"decision": summary["decision"]}))
    return 0


def main_eval_real_learnability(argv: list[str] | None = None) -> int:
    _args = parse_args_checked(argv, "G5.59 real learnability")
    pilot = load_json(PILOT_JSON, {})
    synth = load_json(SYNTHETIC_JSON, {})
    pair_rows = read_rows(PILOT_PAIR_CSV)
    enough_real = bool(pilot.get("raw_solver_labelv5_available")) and len(pair_rows) >= 1000
    metrics = [
        {"metric": "real_solver_labels_available", "value": bool(pilot.get("raw_solver_labelv5_available")), "required": True},
        {"metric": "real_pair_rows", "value": len(pair_rows), "required": 128000},
        {"metric": "synthetic_contract_passed", "value": bool(synth.get("passed")), "required": True},
    ]
    for row in metrics:
        row["passed"] = row["value"] == row["required"] if isinstance(row["required"], bool) else float(row["value"]) >= float(row["required"])
        row.update(CLAIMS_CLOSED)
    decision = "g559_real_learnability_failed_continue_feature_or_label_repair"
    if not bool(synth.get("passed")):
        decision = "g559_synthetic_contract_failed"
    elif not enough_real:
        decision = "g559_real_labelv5_pilot_underpowered"
    write_rows(LEARNABILITY_CSV, metrics)
    write_json(LEARNABILITY_JSON, {"schema_version": f"{ROUND}_real_learnability_summary_v1", "decision": decision, "pilot_underpowered": not enough_real, **CLAIMS_CLOSED})
    print(json.dumps({"decision": decision}))
    return 0


def main_plan_active_round(argv: list[str] | None = None) -> int:
    _args = parse_args_checked(argv, "G5.59 active round plan")
    learn = load_json(LEARNABILITY_JSON, {})
    allowed = learn.get("decision") == "g559_codebook_critic_learnability_passed"
    rows = [] if not allowed else read_rows(INSTANCE_CSV)[:100]
    write_rows(ACTIVE_CSV, [{**row, "planned_candidates": 32, **CLAIMS_CLOSED} for row in rows])
    write_json(ACTIVE_JSON, {"schema_version": f"{ROUND}_active_round_plan_summary_v1", "decision": "g559_active_round_planned" if allowed else "g559_active_round_skipped_real_learnability_gate_closed", "planned_instances": len(rows), **CLAIMS_CLOSED})
    print(json.dumps({"decision": load_json(ACTIVE_JSON, {})["decision"]}))
    return 0


def skip_summary(path: str, decision: str, reason: str) -> None:
    write_json(path, {"schema_version": f"{ROUND}_skip_summary_v1", "decision": decision, "reason": reason, "solver_rows": 0, **CLAIMS_CLOSED})


def main_freeze_policy(argv: list[str] | None = None) -> int:
    _args = parse_args_checked(argv, "G5.59 freeze policy")
    learn = load_json(LEARNABILITY_JSON, {})
    fallback = learn.get("decision") != "g559_codebook_critic_learnability_passed"
    write_json(POLICY_JSON, {"schema_version": f"{ROUND}_policy_freeze_summary_v1", "decision": "g559_policy_frozen_fallback_to_g556" if fallback else "g559_policy_frozen_for_diagnostic_stage1", "fallback_to_g556": fallback, "primary_baseline": PRIMARY_BASELINE, **CLAIMS_CLOSED})
    print(json.dumps({"decision": load_json(POLICY_JSON, {})["decision"]}))
    return 0


def main_run_stage1(argv: list[str] | None = None) -> int:
    _args = parse_args_checked(argv, "G5.59 Stage1")
    policy = load_json(POLICY_JSON, {})
    skip_summary(STAGE1_JSON, "g559_stage1_failed_keep_g556" if not policy.get("fallback_to_g556", True) else "g559_stage1_skipped_policy_all_fallback_keep_g556", policy.get("decision", "policy fallback"))
    print(json.dumps({"decision": load_json(STAGE1_JSON, {})["decision"]}))
    return 0


def main_run_stage2(argv: list[str] | None = None) -> int:
    _args = parse_args_checked(argv, "G5.59 Stage2")
    skip_summary(STAGE2_JSON, "g559_stage2_failed_keep_g556", load_json(STAGE1_JSON, {}).get("decision", "stage1 missing"))
    print(json.dumps({"decision": load_json(STAGE2_JSON, {})["decision"]}))
    return 0


def main_run_blind(argv: list[str] | None = None) -> int:
    _args = parse_args_checked(argv, "G5.59 blind")
    skip_summary(BLIND_JSON, "g559_blind_failed_keep_g556", load_json(STAGE2_JSON, {}).get("decision", "stage2 missing"))
    print(json.dumps({"decision": load_json(BLIND_JSON, {})["decision"]}))
    return 0


def main_write_decision(argv: list[str] | None = None) -> int:
    _args = parse_args_checked(argv, "G5.59 decision")
    autopsy = load_json(AUTOPSY_JSON, {})
    pilot = load_json(PILOT_JSON, {})
    learn = load_json(LEARNABILITY_JSON, {})
    stage1 = load_json(STAGE1_JSON, {})
    if learn.get("decision") == "g559_synthetic_contract_failed":
        decision = "g559_synthetic_contract_failed"
    elif pilot.get("decision") in {"g559_real_labelv5_pilot_underpowered", ""} or learn.get("decision") == "g559_real_labelv5_pilot_underpowered":
        decision = "g559_real_labelv5_pilot_underpowered"
    elif learn.get("decision") == "g559_codebook_critic_learnability_passed":
        decision = "g559_codebook_critic_learnability_passed"
    else:
        decision = "g559_real_learnability_failed_continue_feature_or_label_repair"
    summary = {
        "schema_version": f"{ROUND}_decision_summary_v1",
        "decision": decision,
        "primary_baseline": PRIMARY_BASELINE,
        "g558_autopsy_decision": autopsy.get("decision", ""),
        "labelv5_pilot_decision": pilot.get("decision", ""),
        "real_learnability_decision": learn.get("decision", ""),
        "stage1_decision": stage1.get("decision", ""),
        **CLAIMS_CLOSED,
    }
    write_json(DECISION_JSON, summary)
    write_text(
        DECISION_MD,
        "# G5.59 Decision\n\n"
        f"- decision: `{decision}`\n"
        f"- primary baseline: `{PRIMARY_BASELINE}`\n"
        f"- G5.58 autopsy: `{summary['g558_autopsy_decision']}`\n"
        f"- Label-v5 pilot: `{summary['labelv5_pilot_decision']}`\n"
        f"- real learnability: `{summary['real_learnability_decision']}`\n\n"
        "Claims remain closed. Synthetic tests and requested epochs cannot answer the main GCST question; only real heldout-map solver evidence can.\n",
    )
    entries = []
    for path in [AUTOPSY_JSON, LIT_MANIFEST_CSV, CORRIDOR_CSV, INSTANCE_CSV, CODEBOOK_CSV, PLAN_CSV, PILOT_PAIR_CSV, DECISION_JSON]:
        p = resolve(path)
        entries.append(make_entry(p, schema_version=f"{ROUND}_artifact_v1", producer_command="python scripts/write_repair5g559_decision.py", source_commit=git_head(), root=ROOT))
    write_registry(resolve(REGISTRY_JSON), entries, {"remote_artifact_root": str(REMOTE_ARTIFACT_ROOT), **CLAIMS_CLOSED})
    print(json.dumps({"decision": decision}))
    return 0


def main_run_all(argv: list[str] | None = None) -> int:
    args = parse_args_checked(argv, "G5.59 run all")
    forwarded = [
        "--pilot-instances",
        str(args.pilot_instances),
        "--candidates-per-instance",
        str(args.candidates_per_instance),
        "--codebook-size",
        str(args.codebook_size),
        "--row-limit",
        str(args.row_limit),
        "--max-workers",
        str(args.max_workers),
        "--seed",
        str(args.seed),
        "--binary",
        str(args.binary),
    ]
    if args.smoke:
        forwarded.append("--smoke")
    for fn in [
        main_record_server_run,
        main_audit_g558_failure,
        main_literature_code_audit,
        main_build_corridor_graphs,
        main_generate_real_instances,
        main_build_codebook,
        main_plan_labelv5_pilot,
        main_run_labelv5_pilot,
        main_analyze_labelv5_pilot,
        main_synthetic_contract,
        main_eval_real_learnability,
        main_plan_active_round,
        main_freeze_policy,
        main_run_stage1,
        main_run_stage2,
        main_run_blind,
        main_write_decision,
    ]:
        fn(forwarded)
    return 0


__all__ = [name for name in globals() if name.startswith("main_") or name == "parse_args_checked"]
