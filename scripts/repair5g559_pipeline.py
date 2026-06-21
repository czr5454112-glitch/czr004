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
import zipfile
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
from gcst.map_hash import load_grid, physical_hashes
from gcst.metrics import coverage_risk, fallback_accuracy, generator_safe_set_hit_rate, ranking_accuracy, safe_recall_at_k
from gcst.scenario_features import generate_assignment
from gcst.traffic_prior import compute_traffic_prior
from generate_phase1a_scenarios import scenario_text

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

PILOT_MIN_INSTANCE_UIDS = 2000
PILOT_MIN_CANDIDATES_PER_INSTANCE = 64
PILOT_MIN_PAIR_ROWS = PILOT_MIN_INSTANCE_UIDS * PILOT_MIN_CANDIDATES_PER_INSTANCE
PILOT_MIN_PHYSICAL_HASHES = 24
PILOT_MIN_MAP_FAMILIES = 6

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
PLAN_JSON = f"outputs/reports/{ROUND}_labelv5_pilot_plan_summary.json"
PLAN_CSV = f"outputs/tables/{ROUND}_labelv5_pilot_plan.csv"
PILOT_JSON = f"outputs/reports/{ROUND}_labelv5_pilot_summary.json"
PILOT_PAIR_CSV = f"outputs/tables/{ROUND}_labelv5_pair_rows.csv"
PILOT_AGG_CSV = f"outputs/tables/{ROUND}_labelv5_replicate_aggregates.csv"
PILOT_SAFE_CSV = f"outputs/tables/{ROUND}_labelv5_safe_sets.csv"
SYNTHETIC_JSON = f"outputs/reports/{ROUND}_synthetic_contract_summary.json"
SYNTHETIC_METRICS_CSV = f"outputs/tables/{ROUND}_synthetic_contract_metrics.csv"
LEARNABILITY_JSON = f"outputs/reports/{ROUND}_real_learnability_summary.json"
LEARNABILITY_CSV = f"outputs/tables/{ROUND}_real_learnability_metrics.csv"
LEARNABILITY_SPLIT_CSV = f"outputs/tables/{ROUND}_real_learnability_split_manifest.csv"
LEARNABILITY_SELECTOR_CSV = f"outputs/tables/{ROUND}_real_learnability_selector_eval.csv"
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
RAW_TRANSFER_MANIFEST_CSV = f"outputs/tables/{ROUND}_raw_data_transfer_manifest.csv"
CHECKSUMS_SHA256 = f"outputs/tables/{ROUND}_checksums.sha256"
RESUME_SH = f"outputs/reports/{ROUND}_resume.sh"
VERIFY_CHECKSUMS_SH = f"outputs/reports/{ROUND}_verify_checksums.sh"
COMPACT_BUNDLE_ZIP = f"outputs/reports/{ROUND}_compact_bundle.zip"
SOLVER_MAP_MANIFEST_CSV = f"outputs/tables/{ROUND}_solver_map_manifest.csv"
SOLVER_SCENARIO_MANIFEST_CSV = f"outputs/tables/{ROUND}_solver_scenario_manifest.csv"


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
    override = os.environ.get("G559_SOURCE_COMMIT", "").strip()
    if override:
        return override
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return ""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def movingai_map_text(width: int, height: int, grid: list[str]) -> str:
    return "type octile\nheight {height}\nwidth {width}\nmap\n{grid}\n".format(
        height=int(height),
        width=int(width),
        grid="\n".join(grid),
    )


def solver_map_dir() -> Path:
    return REMOTE_ARTIFACT_ROOT / "contexts" / "maps"


def solver_scenario_dir() -> Path:
    return REMOTE_ARTIFACT_ROOT / "contexts" / "scenarios"


def solver_scenario_path(map_name: str, solver_seed: int) -> Path:
    return solver_scenario_dir() / f"{map_name}-random-{int(solver_seed)}.scen"


def register_solver_maps(topologies: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Materialize G5.59 maps as MovingAI files and register them for legacy solver helpers."""

    solver_map_dir().mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    map_paths: dict[str, str] = {}
    for topo in topologies:
        width, height, grid, source = load_grid(topo)
        text = movingai_map_text(width, height, grid)
        out = solver_map_dir() / f"{topo['map']}.map"
        out.write_text(text, encoding="utf-8", newline="\n")
        hashes = physical_hashes({**topo, "width": width, "height": height})
        map_path = str(out)
        map_paths[str(topo["map"])] = map_path
        rows.append(
            {
                "map": topo["map"],
                "map_family": topo["map_family"],
                "width": width,
                "height": height,
                "solver_map_path": map_path,
                "solver_map_sha256": sha256_bytes(text.encode("utf-8")),
                "grid_source": source,
                "physical_map_sha256": hashes["physical_map_sha256"],
                "adjacency_sha256": hashes["adjacency_sha256"],
                "actual_solver_map_registered": True,
                **CLAIMS_CLOSED,
            }
        )
    try:
        import run_repair5f4_static_updateparams_validation as f4maps
        import repair5g5_common as g5common

        for map_name, map_path in map_paths.items():
            f4maps.MAPS[map_name] = map_path
            g5common.MAP_PATHS[map_name] = map_path
    except Exception:
        pass
    write_rows(SOLVER_MAP_MANIFEST_CSV, rows)
    return rows


def materialize_solver_scenario(
    topo: dict[str, Any],
    graph: Any,
    assignment: dict[str, Any],
    solver_seed: int,
) -> dict[str, Any]:
    solver_scenario_dir().mkdir(parents=True, exist_ok=True)
    path = solver_scenario_path(str(topo["map"]), solver_seed)
    text = scenario_text(str(topo["map"]), graph.width, graph.height, assignment["starts"], assignment["goals"])
    path.write_text(text, encoding="utf-8", newline="\n")
    return {
        "map": topo["map"],
        "map_family": topo["map_family"],
        "solver_seed": int(solver_seed),
        "solver_scenario_path": str(path),
        "solver_scenario_sha256": sha256_bytes(text.encode("utf-8")),
        "solver_scenario_pair_count": len(assignment["starts"]),
        "start_goal_assignment_sha256": assignment["start_goal_assignment_hash"],
        "actual_solver_scenario_from_instance_assignment": True,
        **CLAIMS_CLOSED,
    }


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser()
    p.add_argument("--contexts", type=int, default=96)
    p.add_argument("--pilot-instances", type=int, default=PILOT_MIN_INSTANCE_UIDS)
    p.add_argument("--candidates-per-instance", type=int, default=PILOT_MIN_CANDIDATES_PER_INSTANCE)
    p.add_argument("--codebook-size", type=int, default=1024)
    p.add_argument("--row-limit", type=int, default=0)
    p.add_argument("--max-workers", type=int, default=1)
    p.add_argument("--seed", type=int, default=20260619)
    p.add_argument("--topology-count", type=int, default=24)
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


def effective_pilot_instances(args: argparse.Namespace) -> int:
    return int(args.pilot_instances if args.smoke else max(args.pilot_instances, PILOT_MIN_INSTANCE_UIDS))


def effective_candidates_per_instance(args: argparse.Namespace) -> int:
    return int(args.candidates_per_instance if args.smoke else max(args.candidates_per_instance, PILOT_MIN_CANDIDATES_PER_INSTANCE))


def effective_codebook_size(args: argparse.Namespace) -> int:
    required = effective_candidates_per_instance(args) + 1
    return int(min(args.codebook_size, 64) if args.smoke else max(args.codebook_size, required))


def default_topologies(limit: int = 24) -> list[dict[str, Any]]:
    names = [
        ("empty-8-8", "empty", 8, 8),
        ("empty-16-16", "empty", 16, 16),
        ("empty-32-32", "empty", 32, 32),
        ("random-8-8-20", "random", 8, 8),
        ("random-32-32-10", "random", 32, 32),
        ("random-32-32-20", "random", 32, 32),
        ("maze-32-32-2", "maze", 32, 32),
        ("maze-36-32-4", "maze", 36, 32),
        ("room-32-32-4", "room", 32, 32),
        ("room-40-32-8", "room", 40, 32),
        ("g559-synth-warehouse-a-32", "warehouse", 32, 32),
        ("g559-synth-warehouse-b-36", "warehouse", 36, 32),
        ("g559-synth-connector-32", "irregular_bottleneck", 32, 32),
        ("g559-synth-corners-34", "irregular_bottleneck", 34, 32),
        ("g559-synth-loop-chain-36", "irregular_bottleneck", 36, 32),
        ("g559-synth-tunnel-38", "irregular_bottleneck", 38, 32),
        ("g559-synth-string-40", "irregular_bottleneck", 40, 32),
        ("g559-synth-tree-42", "irregular_bottleneck", 42, 32),
        ("g559-synth-game-den-32", "game", 32, 32),
        ("g559-synth-game-brc-32", "game", 32, 32),
        ("g559-synth-city-berlin-32", "city", 32, 32),
        ("g559-synth-city-boston-32", "city", 32, 32),
        ("g559-synth-city-paris-32", "city", 32, 32),
        ("g559-synth-game-lak-32", "game", 32, 32),
        ("g565-synth-open-cross-40", "open_cross", 40, 40),
        ("g565-synth-open-halls-44", "open_cross", 44, 40),
        ("g565-synth-ring-a-40", "ring", 40, 40),
        ("g565-synth-ring-b-48", "ring", 48, 40),
        ("g565-synth-islands-a-40", "islands", 40, 40),
        ("g565-synth-islands-b-48", "islands", 48, 40),
        ("g565-synth-bridge-a-40", "narrow_bridge", 40, 40),
        ("g565-synth-bridge-b-48", "narrow_bridge", 48, 40),
        ("g565-synth-labyrinth-a-40", "labyrinth", 40, 40),
        ("g565-synth-labyrinth-b-48", "labyrinth", 48, 40),
        ("g565-synth-checker-a-40", "checker", 40, 40),
        ("g565-synth-checker-b-48", "checker", 48, 40),
        ("g565-synth-corridor-grid-a-44", "corridor_grid", 44, 44),
        ("g565-synth-corridor-grid-b-52", "corridor_grid", 52, 44),
        ("g565-synth-hub-spoke-a-44", "hub_spoke", 44, 44),
        ("g565-synth-hub-spoke-b-52", "hub_spoke", 52, 44),
    ]
    return [
        {"topology_id": f"g559_topo_{idx:03d}", "map": name, "map_family": family, "width": width, "height": height}
        for idx, (name, family, width, height) in enumerate(names[:limit])
    ]


def largest_component_size(graph) -> int:
    if not graph.cells:
        return 0
    adj: dict[int, list[int]] = {idx: [] for idx in range(len(graph.cells))}
    if graph.edge_index.size:
        for src, dst in graph.edge_index.T:
            adj[int(src)].append(int(dst))
    seen: set[int] = set()
    largest = 0
    for start in range(len(graph.cells)):
        if start in seen:
            continue
        stack = [start]
        seen.add(start)
        size = 0
        while stack:
            cur = stack.pop()
            size += 1
            for nxt in adj.get(cur, []):
                if nxt not in seen:
                    seen.add(nxt)
                    stack.append(nxt)
        largest = max(largest, size)
    return largest


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
    topologies = default_topologies(limit=max(24, int(args.topology_count)) if not args.smoke else min(6, int(args.topology_count)))
    register_solver_maps(topologies)
    for topo in topologies:
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


def build_instances(count: int, seed: int, topology_count: int = 24) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    topologies = default_topologies(limit=max(24, int(topology_count)))
    register_solver_maps(topologies)
    regimes = ["uniform_random", "opposite_side_cross_flow", "room_to_room_door_bottleneck", "warehouse_aisle_to_aisle", "clustered_starts_to_dispersed_goals"]
    budgets = [500, 1000, 2000, 5000]
    rows: list[dict[str, Any]] = []
    scenario_rows: list[dict[str, Any]] = []
    topology_cache: dict[tuple[str, int, int], dict[str, Any]] = {}
    for idx in range(count):
        topo = topologies[idx % len(topologies)]
        topo_key = (str(topo["map"]), int(topo["width"]), int(topo["height"]))
        if topo_key not in topology_cache:
            graph = build_corridor_graph(topo).graph
            topology_cache[topo_key] = {
                "graph": graph,
                "capacity": largest_component_size(graph),
                "hashes": physical_hashes(topo),
            }
        cached = topology_cache[topo_key]
        graph = cached["graph"]
        requested_agents = [16, 32, 64, 96, 128, 256][idx % 6]
        capacity = int(cached["capacity"])
        feasible_agent_counts = [value for value in [16, 32, 64, 96, 128, 256] if value <= capacity]
        agents = feasible_agent_counts[-1] if requested_agents > capacity and feasible_agent_counts else requested_agents
        if agents > capacity:
            agents = max(1, capacity)
        context = {
            **topo,
            "agent_count": agents,
            "agents": agents,
            "requested_pilot_agent_count": requested_agents,
            "solver_largest_component_size": capacity,
            "seed": 5000 + idx,
            "solver_seed": 7000 + idx,
            "nominal_budget_ms": budgets[idx % len(budgets)],
            "base_time_limit_sec": max(0.25, budgets[idx % len(budgets)] / 1000.0),
            "ltm_max_iterations": 2 + (idx % 3),
            "start_goal_regime": regimes[idx % len(regimes)],
        }
        assignment = generate_assignment(graph, context, max_agents=None)
        traffic = compute_traffic_prior(graph, assignment)
        hashes = cached["hashes"]
        scenario = materialize_solver_scenario(topo, graph, assignment, context["solver_seed"])
        scenario_rows.append({"instance_index": idx, **scenario})
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
                "requested_pilot_agent_count": requested_agents,
                "solver_largest_component_size": capacity,
                "seed": context["solver_seed"],
                "budget_ms": context["nominal_budget_ms"],
                "nominal_budget_ms": context["nominal_budget_ms"],
                "horizon_id": f"g559_b{context['nominal_budget_ms']}_i{context['ltm_max_iterations']}",
                "base_time_limit_sec": context["base_time_limit_sec"],
                "ltm_max_iterations": context["ltm_max_iterations"],
                "physical_map_sha256": hashes["physical_map_sha256"],
                "adjacency_sha256": hashes["adjacency_sha256"],
                "start_goal_assignment_sha256": assignment["start_goal_assignment_hash"],
                "solver_scenario_path": scenario["solver_scenario_path"],
                "solver_scenario_sha256": scenario["solver_scenario_sha256"],
                "actual_solver_scenario_from_instance_assignment": True,
                "requested_agent_count": assignment["requested_agent_count"],
                "physical_free_cell_count": graph.physical_free_cell_count,
                "agent_density": agents / max(1, graph.physical_free_cell_count),
                "encoded_OD_token_count": assignment["encoded_agent_count"],
                "represented_agent_mass": assignment["represented_agent_mass"],
                "represented_flow_mass": traffic["summary"]["edge_use_total"],
                "path_found_rate": traffic["summary"]["path_found_rate"],
                "nonzero_flow": traffic["summary"]["nonzero_flow"],
                **CLAIMS_CLOSED,
            }
        )
    write_rows(SOLVER_SCENARIO_MANIFEST_CSV, scenario_rows)
    rng.shuffle(rows)
    return rows


def main_generate_real_instances(argv: list[str] | None = None) -> int:
    args = parse_args_checked(argv, "G5.59 instance generation")
    rows = build_instances(effective_pilot_instances(args), args.seed, args.topology_count)
    summary = {
        "schema_version": f"{ROUND}_instance_generation_summary_v1",
        "decision": "g559_instance_manifest_ready",
        "instances": len(rows),
        "unique_instance_uids": len({r["instance_uid"] for r in rows}),
        "unique_physical_map_hashes": len({r["adjacency_sha256"] for r in rows}),
        "map_families": len({r["map_family"] for r in rows}),
        "requested_topology_count": args.topology_count,
        "materialized_topologies": len({r["map"] for r in rows}),
        "pilot_min_instance_uids": PILOT_MIN_INSTANCE_UIDS,
        "pilot_min_physical_hashes": PILOT_MIN_PHYSICAL_HASHES,
        "pilot_min_map_families": PILOT_MIN_MAP_FAMILIES,
        "meets_pilot_instance_minimum": len({r["instance_uid"] for r in rows}) >= (1 if args.smoke else PILOT_MIN_INSTANCE_UIDS),
        "meets_pilot_physical_hash_minimum": len({r["adjacency_sha256"] for r in rows}) >= (1 if args.smoke else PILOT_MIN_PHYSICAL_HASHES),
        "meets_pilot_map_family_minimum": len({r["map_family"] for r in rows}) >= (1 if args.smoke else PILOT_MIN_MAP_FAMILIES),
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
    count = effective_codebook_size(args)
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
    write_json(
        CODEBOOK_JSON,
        {
            "schema_version": f"{ROUND}_codebook_summary_v1",
            "decision": "g559_codebook_ready",
            "candidate_count": len(rows),
            "nonbaseline_candidate_count": max(0, len(rows) - 1),
            "pilot_min_candidates_per_instance": PILOT_MIN_CANDIDATES_PER_INSTANCE,
            "primary_baseline": PRIMARY_BASELINE,
            **CLAIMS_CLOSED,
        },
    )
    print(json.dumps({"decision": "g559_codebook_ready", "candidates": len(rows)}))
    return 0


def main_plan_labelv5_pilot(argv: list[str] | None = None) -> int:
    args = parse_args_checked(argv, "G5.59 Label-v5 pilot plan")
    effective_instances = effective_pilot_instances(args)
    effective_candidates = effective_candidates_per_instance(args)
    if not resolve(INSTANCE_CSV).exists():
        main_generate_real_instances(["--pilot-instances", str(effective_instances), "--seed", str(args.seed), "--topology-count", str(args.topology_count)] + (["--smoke"] if args.smoke else []))
    if not resolve(CODEBOOK_CSV).exists():
        main_build_codebook(["--codebook-size", str(effective_codebook_size(args)), "--seed", str(args.seed)] + (["--smoke"] if args.smoke else []))
    instances = read_rows(INSTANCE_CSV, limit=effective_instances)
    if len(instances) < effective_instances:
        main_generate_real_instances(["--pilot-instances", str(effective_instances), "--seed", str(args.seed), "--topology-count", str(args.topology_count)] + (["--smoke"] if args.smoke else []))
        instances = read_rows(INSTANCE_CSV, limit=effective_instances)
    candidates = [r for r in read_rows(CODEBOOK_CSV) if r.get("candidate_id") != PRIMARY_BASELINE]
    if len(candidates) < effective_candidates:
        main_build_codebook(["--codebook-size", str(effective_codebook_size(args)), "--seed", str(args.seed)] + (["--smoke"] if args.smoke else []))
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
        offset = (idx * effective_candidates) % max(1, len(candidates))
        slate = [candidates[(offset + j) % len(candidates)] for j in range(min(effective_candidates, len(candidates)))]
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
    candidate_rows = sum(1 for row in plan_rows if row.get("candidate_id") != PRIMARY_BASELINE)
    summary = {
        "schema_version": f"{ROUND}_labelv5_pilot_plan_summary_v1",
        "decision": "g559_labelv5_pilot_plan_ready",
        "planned_rows": len(plan_rows),
        "planned_candidate_rows": candidate_rows,
        "planned_baseline_rows": len(plan_rows) - candidate_rows,
        "unique_instance_uids": len({r.get("instance_uid", "") for r in plan_rows}),
        "unique_physical_map_hashes": len({r.get("physical_map_sha256", "") for r in plan_rows}),
        "map_families": len({r.get("map_family", "") for r in plan_rows}),
        "pilot_min_pair_rows": PILOT_MIN_PAIR_ROWS,
        "pilot_min_instance_uids": PILOT_MIN_INSTANCE_UIDS,
        "pilot_min_candidates_per_instance": PILOT_MIN_CANDIDATES_PER_INSTANCE,
        "meets_pilot_candidate_row_minimum": candidate_rows >= (1 if args.smoke else PILOT_MIN_PAIR_ROWS),
        **CLAIMS_CLOSED,
    }
    write_json(PLAN_JSON, summary)
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
    write_rows(PILOT_PAIR_CSV, compact_rows)
    candidate_rows = [row for row in compact_rows if row.get("candidate_id") != PRIMARY_BASELINE and row.get("materialized_method") != PRIMARY_BASELINE]
    summary = {
        "schema_version": f"{ROUND}_labelv5_pilot_summary_v1",
        "decision": "g559_labelv5_pilot_real_solver_rows_recorded" if compact_rows else "g559_real_labelv5_pilot_underpowered",
        "real_solver_rows": len(compact_rows),
        "real_solver_candidate_rows": len(candidate_rows),
        "planned_solver_rows": len(plan),
        "pilot_min_candidate_rows": PILOT_MIN_PAIR_ROWS,
        "meets_pilot_candidate_row_minimum": len(candidate_rows) >= (1 if args.smoke else PILOT_MIN_PAIR_ROWS),
        "raw_solver_labelv5_available": bool(compact_rows),
        "remote_result_csv": result_csv,
        "remote_raw_csv": raw_csv,
        "remote_log_dir": log_dir,
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


def _row_bool(row: dict[str, Any], key: str) -> bool:
    return str(row.get(key, "")).strip().lower() in {"1", "true", "yes", "y"}


def _quality_target(row: dict[str, Any]) -> float:
    if _row_bool(row, "success_regression"):
        return 10.0
    if _row_bool(row, "success_gain"):
        return -10.0
    value = num(row.get("quality_delta_vs_g556"), math.nan)
    if math.isfinite(value):
        return value
    if _row_bool(row, "both_fail"):
        return 2.0
    return 0.0


def _density_bin(value: Any) -> str:
    density = num(value, 0.0)
    if density < 0.10:
        return "d00_very_low"
    if density < 0.25:
        return "d01_low"
    if density < 0.50:
        return "d02_mid"
    if density < 1.00:
        return "d03_high"
    return "d04_extreme"


def _feature_vector(pair: dict[str, Any], inst: dict[str, Any]) -> list[float]:
    base = [
        num(inst.get("agent_count")),
        num(inst.get("nominal_budget_ms")),
        num(inst.get("ltm_max_iterations")),
        num(inst.get("agent_density")),
        num(inst.get("physical_free_cell_count")),
        num(inst.get("represented_flow_mass")),
        num(inst.get("path_found_rate")),
    ]
    theta = [num(pair.get(col), num(baseline_theta_row().get(col), 0.0)) for col in THETA_NUMERIC_COLUMNS]
    return [*base, *theta]


def _split_physical_hashes(instance_rows: list[dict[str, Any]]) -> dict[str, str]:
    hashes = sorted({str(row.get("physical_map_sha256") or row.get("adjacency_sha256") or "") for row in instance_rows if row.get("physical_map_sha256") or row.get("adjacency_sha256")})
    out: dict[str, str] = {}
    for h in hashes:
        bucket = int(hashlib.sha256(h.encode("utf-8")).hexdigest()[:8], 16) % 10
        if bucket < 7:
            split = "train"
        elif bucket < 9:
            split = "validation"
        else:
            split = "heldout"
        out[h] = split
    if hashes and "heldout" not in set(out.values()):
        out[hashes[-1]] = "heldout"
    if len(hashes) > 1 and "validation" not in set(out.values()):
        out[hashes[-2]] = "validation"
    return out


def _joined_label_examples(pair_rows: list[dict[str, Any]], instance_rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    instances = {str(row.get("instance_uid", "")): row for row in instance_rows}
    split_by_hash = _split_physical_hashes(instance_rows)
    split_rows = []
    for uid, inst in instances.items():
        physical = str(inst.get("physical_map_sha256") or inst.get("adjacency_sha256") or "")
        split = split_by_hash.get(physical, "train")
        split_rows.append(
            {
                "instance_uid": uid,
                "physical_map_sha256": physical,
                "map": inst.get("map", ""),
                "map_family": inst.get("map_family", ""),
                "split": split,
                **CLAIMS_CLOSED,
            }
        )
    examples = []
    for idx, row in enumerate(pair_rows):
        uid = str(row.get("instance_uid", ""))
        inst = instances.get(uid)
        if not inst:
            continue
        physical = str(inst.get("physical_map_sha256") or inst.get("adjacency_sha256") or "")
        target = _quality_target(row)
        examples.append(
            {
                "example_id": idx,
                "instance_uid": uid,
                "theta_id": str(row.get("theta_id") or row.get("candidate_id") or ""),
                "split": split_by_hash.get(physical, "train"),
                "density_bin": _density_bin(inst.get("agent_density")),
                "target": target,
                "quality_delta_vs_g556": num(row.get("quality_delta_vs_g556"), math.nan),
                "success_regression": _row_bool(row, "success_regression"),
                "success_gain": _row_bool(row, "success_gain"),
                "features": _feature_vector(row, inst),
                "row": row,
            }
        )
    return examples, split_rows


def _selector_metrics(name: str, selected: list[dict[str, Any]], *, available: bool = True, reason: str = "") -> dict[str, Any]:
    finite = [num(ex["quality_delta_vs_g556"], math.nan) for ex in selected]
    finite = [v for v in finite if math.isfinite(v)]
    regressions = sum(1 for ex in selected if bool(ex.get("success_regression")))
    improving = sum(1 for v in finite if v < 0.0)
    worse = sum(1 for v in finite if v > 0.0)
    return {
        "selector": name,
        "available": available,
        "reason": reason,
        "selected_instances": len({str(ex.get("instance_uid", "")) for ex in selected}),
        "selected_rows": len(selected),
        "nonfallback_coverage": 1.0 if selected else 0.0,
        "false_safe_rate": regressions / max(1, len(selected)),
        "success_regressions": regressions,
        "quality_delta_mean": statistics.fmean(finite) if finite else math.nan,
        "quality_delta_count": len(finite),
        "better": improving,
        "worse": worse,
        **CLAIMS_CLOSED,
    }


def _select_by_scores(examples: list[dict[str, Any]], scores: dict[int, float]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for ex in examples:
        grouped[str(ex["instance_uid"])].append(ex)
    selected = []
    for rows in grouped.values():
        selected.append(min(rows, key=lambda ex: scores.get(int(ex["example_id"]), float("inf"))))
    return selected


def _density_lookup_scores(train: list[dict[str, Any]], test: list[dict[str, Any]]) -> dict[int, float]:
    buckets: dict[tuple[str, str], list[float]] = defaultdict(list)
    global_theta: dict[str, list[float]] = defaultdict(list)
    for ex in train:
        buckets[(str(ex["density_bin"]), str(ex["theta_id"]))].append(float(ex["target"]))
        global_theta[str(ex["theta_id"])].append(float(ex["target"]))
    global_default = statistics.fmean([float(ex["target"]) for ex in train]) if train else 0.0
    return {
        int(ex["example_id"]): statistics.fmean(buckets.get((str(ex["density_bin"]), str(ex["theta_id"])), global_theta.get(str(ex["theta_id"]), [global_default])))
        for ex in test
    }


def _fit_boosted_stumps(train_x: np.ndarray, train_y: np.ndarray, rounds: int = 16) -> tuple[float, list[tuple[int, float, float, float]]]:
    if train_x.size == 0:
        return 0.0, []
    rng = np.random.default_rng(559)
    keep = np.arange(len(train_y))
    if len(keep) > 30000:
        keep = rng.choice(keep, size=30000, replace=False)
    x = train_x[keep]
    y = train_y[keep]
    base = float(np.mean(y))
    pred = np.full(len(y), base, dtype=np.float64)
    stumps: list[tuple[int, float, float, float]] = []
    lr = 0.12
    for _ in range(rounds):
        residual = y - pred
        best: tuple[float, int, float, float, float] | None = None
        for feat in range(x.shape[1]):
            thresholds = np.unique(np.quantile(x[:, feat], np.linspace(0.15, 0.85, 7)))
            for threshold in thresholds:
                left = x[:, feat] <= threshold
                if left.sum() < 16 or (~left).sum() < 16:
                    continue
                left_value = float(np.mean(residual[left]))
                right_value = float(np.mean(residual[~left]))
                update = np.where(left, left_value, right_value)
                loss = float(np.mean((residual - update) ** 2))
                if best is None or loss < best[0]:
                    best = (loss, feat, float(threshold), left_value, right_value)
        if best is None:
            break
        _loss, feat, threshold, left_value, right_value = best
        update = np.where(x[:, feat] <= threshold, left_value, right_value)
        pred += lr * update
        stumps.append((feat, threshold, lr * left_value, lr * right_value))
    return base, stumps


def _predict_boosted_stumps(x: np.ndarray, model: tuple[float, list[tuple[int, float, float, float]]]) -> np.ndarray:
    base, stumps = model
    pred = np.full(x.shape[0], base, dtype=np.float64)
    for feat, threshold, left, right in stumps:
        pred += np.where(x[:, feat] <= threshold, left, right)
    return pred


def _mlp_scores(train_x: np.ndarray, train_y: np.ndarray, test_x: np.ndarray) -> tuple[dict[int, float], str]:
    if not TORCH_AVAILABLE or torch is None:
        return {}, "torch unavailable"
    if train_x.size == 0 or test_x.size == 0:
        return {}, "empty train/test matrix"
    try:
        rng = np.random.default_rng(560)
        keep = np.arange(len(train_y))
        if len(keep) > 50000:
            keep = rng.choice(keep, size=50000, replace=False)
        x = train_x[keep].astype(np.float32)
        y = train_y[keep].astype(np.float32)
        mean = x.mean(axis=0, keepdims=True)
        std = x.std(axis=0, keepdims=True) + 1.0e-6
        x = (x - mean) / std
        xt = ((test_x.astype(np.float32) - mean) / std)
        device = "cuda" if torch.cuda.is_available() else "cpu"
        model = torch.nn.Sequential(torch.nn.Linear(x.shape[1], 64), torch.nn.GELU(), torch.nn.Linear(64, 32), torch.nn.GELU(), torch.nn.Linear(32, 1)).to(device)
        opt = torch.optim.AdamW(model.parameters(), lr=2.0e-3)
        tx = torch.tensor(x, device=device)
        ty = torch.tensor(y, device=device)
        for _ in range(8):
            order = torch.randperm(tx.shape[0], device=device)
            for start in range(0, tx.shape[0], 2048):
                batch = order[start : start + 2048]
                loss = torch.nn.functional.smooth_l1_loss(model(tx[batch]).squeeze(-1), ty[batch])
                opt.zero_grad()
                loss.backward()
                opt.step()
        with torch.no_grad():
            pred = model(torch.tensor(xt, device=device)).squeeze(-1).detach().cpu().numpy()
        return {i: float(v) for i, v in enumerate(pred)}, f"torch_device={device}"
    except Exception as exc:
        return {}, f"torch MLP failed: {type(exc).__name__}: {exc}"


def main_eval_real_learnability(argv: list[str] | None = None) -> int:
    args = parse_args_checked(argv, "G5.59 real learnability")
    pilot = load_json(PILOT_JSON, {})
    synth = load_json(SYNTHETIC_JSON, {})
    pair_rows = read_rows(PILOT_PAIR_CSV)
    instance_rows = read_rows(INSTANCE_CSV)
    instance_uids = {row.get("instance_uid", "") for row in pair_rows if row.get("instance_uid", "")}
    expected_pair_rows = 1 if args.smoke else PILOT_MIN_PAIR_ROWS
    expected_instances = 1 if args.smoke else PILOT_MIN_INSTANCE_UIDS
    enough_real = bool(pilot.get("raw_solver_labelv5_available")) and len(pair_rows) >= expected_pair_rows and len(instance_uids) >= expected_instances
    examples, split_rows = _joined_label_examples(pair_rows, instance_rows)
    train = [ex for ex in examples if ex["split"] == "train"]
    heldout = [ex for ex in examples if ex["split"] == "heldout"]
    if not heldout:
        heldout = [ex for ex in examples if ex["split"] in {"validation", "heldout"}]
    write_rows(LEARNABILITY_SPLIT_CSV, split_rows)

    selector_rows: list[dict[str, Any]] = []
    if heldout:
        oracle_scores = {int(ex["example_id"]): float(ex["target"]) for ex in heldout}
        selector_rows.append(_selector_metrics("oracle_candidate_slate", _select_by_scores(heldout, oracle_scores), available=True))
    else:
        selector_rows.append(_selector_metrics("oracle_candidate_slate", [], available=False, reason="no heldout physical-map examples"))

    if train and heldout:
        density_scores = _density_lookup_scores(train, heldout)
        selector_rows.append(_selector_metrics("agent_density_lookup", _select_by_scores(heldout, density_scores), available=True))
        train_x = np.asarray([ex["features"] for ex in train], dtype=np.float64)
        train_y = np.asarray([float(ex["target"]) for ex in train], dtype=np.float64)
        heldout_x = np.asarray([ex["features"] for ex in heldout], dtype=np.float64)

        stump_model = _fit_boosted_stumps(train_x, train_y)
        stump_pred = _predict_boosted_stumps(heldout_x, stump_model)
        stump_scores = {int(ex["example_id"]): float(pred) for ex, pred in zip(heldout, stump_pred)}
        selector_rows.append(_selector_metrics("gbdt_like_boosted_stumps", _select_by_scores(heldout, stump_scores), available=True, reason=f"stumps={len(stump_model[1])}"))

        mlp_index_scores, mlp_reason = _mlp_scores(train_x, train_y, heldout_x)
        if mlp_index_scores:
            mlp_scores = {int(ex["example_id"]): mlp_index_scores[idx] for idx, ex in enumerate(heldout)}
            selector_rows.append(_selector_metrics("tabular_mlp", _select_by_scores(heldout, mlp_scores), available=True, reason=mlp_reason))
        else:
            selector_rows.append(_selector_metrics("tabular_mlp", [], available=False, reason=mlp_reason))
    else:
        selector_rows.append(_selector_metrics("agent_density_lookup", [], available=False, reason="train or heldout split empty"))
        selector_rows.append(_selector_metrics("gbdt_like_boosted_stumps", [], available=False, reason="train or heldout split empty"))
        selector_rows.append(_selector_metrics("tabular_mlp", [], available=False, reason="train or heldout split empty"))

    gcst_checkpoint = ROOT / "artifacts" / "models" / "gcst" / "g559_codebook_critic.pt"
    selector_rows.append(
        _selector_metrics(
            "dualtraffic_hgt_gcst_codebook_critic",
            [],
            available=gcst_checkpoint.exists(),
            reason=("checkpoint present but evaluation hook not finalized" if gcst_checkpoint.exists() else "missing real trained GCST codebook critic checkpoint"),
        )
    )
    write_rows(LEARNABILITY_SELECTOR_CSV, selector_rows)

    selector_by_name = {str(row["selector"]): row for row in selector_rows}
    main_row = selector_by_name.get("dualtraffic_hgt_gcst_codebook_critic", {})
    density_row = selector_by_name.get("agent_density_lookup", {})
    gbdt_row = selector_by_name.get("gbdt_like_boosted_stumps", {})
    mlp_row = selector_by_name.get("tabular_mlp", {})
    main_available = bool(main_row.get("available"))
    main_quality = num(main_row.get("quality_delta_mean"), math.inf)
    beats_controls = (
        main_available
        and main_quality < num(density_row.get("quality_delta_mean"), math.inf)
        and main_quality < num(gbdt_row.get("quality_delta_mean"), math.inf)
        and main_quality < num(mlp_row.get("quality_delta_mean"), math.inf)
    )
    main_coverage_ok = num(main_row.get("nonfallback_coverage"), 0.0) >= 0.05
    main_quality_ok = math.isfinite(main_quality) and main_quality < 0.0
    false_safe_usable = main_available and num(main_row.get("false_safe_rate"), 1.0) <= 0.02
    metrics = [
        {"metric": "real_solver_labels_available", "value": bool(pilot.get("raw_solver_labelv5_available")), "required": True},
        {"metric": "real_pair_rows", "value": len(pair_rows), "required": expected_pair_rows},
        {"metric": "unique_instance_uids", "value": len(instance_uids), "required": expected_instances},
        {"metric": "heldout_physical_map_examples", "value": len(heldout), "required": 1},
        {"metric": "synthetic_contract_passed", "value": bool(synth.get("passed")), "required": True},
        {"metric": "main_gcst_model_available", "value": main_available, "required": True},
        {"metric": "density_gbdt_mlp_beaten_by_main_model", "value": beats_controls, "required": True},
        {"metric": "main_nonfallback_coverage", "value": num(main_row.get("nonfallback_coverage"), 0.0), "required": 0.05},
        {"metric": "main_heldout_quality_delta_negative", "value": main_quality_ok, "required": True},
        {"metric": "usable_false_safe_operating_point", "value": false_safe_usable, "required": True},
    ]
    for row in metrics:
        row["passed"] = row["value"] == row["required"] if isinstance(row["required"], bool) else float(row["value"]) >= float(row["required"])
        row.update(CLAIMS_CLOSED)
    decision = "g559_real_learnability_failed_continue_feature_or_label_repair"
    if not bool(synth.get("passed")):
        decision = "g559_synthetic_contract_failed"
    elif not enough_real:
        decision = "g559_real_labelv5_pilot_underpowered"
    elif all(bool(row["passed"]) for row in metrics):
        decision = "g559_codebook_critic_learnability_passed"
    write_rows(LEARNABILITY_CSV, metrics)
    write_json(
        LEARNABILITY_JSON,
        {
            "schema_version": f"{ROUND}_real_learnability_summary_v1",
            "decision": decision,
            "pilot_underpowered": not enough_real,
            "real_pair_rows": len(pair_rows),
            "unique_instance_uids": len(instance_uids),
            "pilot_min_pair_rows": expected_pair_rows,
            "heldout_examples": len(heldout),
            "selector_eval_csv": LEARNABILITY_SELECTOR_CSV,
            "split_manifest_csv": LEARNABILITY_SPLIT_CSV,
            **CLAIMS_CLOSED,
        },
    )
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


def _g559_output_files() -> list[Path]:
    roots = [ROOT / "outputs" / "reports", ROOT / "outputs" / "tables", ROOT / "outputs" / "logs"]
    files: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob(f"*{ROUND}*"):
            if path.is_file() and path.name != Path(COMPACT_BUNDLE_ZIP).name:
                files.append(path)
    return sorted(set(files))


def _remote_artifact_files() -> list[Path]:
    if not REMOTE_ARTIFACT_ROOT.exists():
        return []
    return sorted(path for path in REMOTE_ARTIFACT_ROOT.rglob("*") if path.is_file())


def main_write_artifact_bundle(argv: list[str] | None = None) -> int:
    args = parse_args_checked(argv, "G5.59 artifact durability")
    source_commit = git_head()
    remote_files = _remote_artifact_files()
    remote_entries = [
        make_entry(path, schema_version=f"{ROUND}_remote_raw_artifact_v1", producer_command="python scripts/run_repair5g559_5090.py", source_commit=source_commit, root=REMOTE_ARTIFACT_ROOT)
        for path in remote_files
    ]
    write_rows(RAW_TRANSFER_MANIFEST_CSV, [entry.__dict__ for entry in remote_entries])

    output_files = _g559_output_files()
    checksum_lines = []
    for path in output_files + remote_files:
        digest = hashlib.sha256()
        try:
            with path.open("rb") as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(chunk)
            try:
                rel = path.resolve().relative_to(ROOT.resolve())
            except Exception:
                rel = path
            checksum_lines.append(f"{digest.hexdigest()}  {str(rel).replace(os.sep, '/')}")
        except Exception:
            continue
    write_text(CHECKSUMS_SHA256, "\n".join(checksum_lines) + ("\n" if checksum_lines else ""))

    resume_command = (
        "python scripts/run_repair5g559_5090.py "
        f"--pilot-instances {effective_pilot_instances(args)} "
        f"--candidates-per-instance {effective_candidates_per_instance(args)} "
        f"--codebook-size {effective_codebook_size(args)} "
        f"--row-limit {args.row_limit} "
        f"--max-workers {args.max_workers} "
        f"--seed {args.seed} "
        f"--topology-count {args.topology_count} "
        f"--binary {args.binary}"
    )
    if args.smoke:
        resume_command += " --smoke"
    write_text(
        RESUME_SH,
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        "cd \"${CZR004_ROOT:-/root/czr004}\"\n"
        "export PYTHONPATH=\"$PWD/src:$PWD/scripts:${PYTHONPATH:-}\"\n"
        "export REMOTE_ARTIFACT_ROOT=\"${REMOTE_ARTIFACT_ROOT:-/root/shared-nvme/czr004_g559_remote_artifacts}\"\n"
        f"{resume_command}\n",
    )
    write_text(
        VERIFY_CHECKSUMS_SH,
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        "cd \"${CZR004_ROOT:-/root/czr004}\"\n"
        f"sha256sum -c {CHECKSUMS_SHA256}\n",
    )
    for script in [resolve(RESUME_SH), resolve(VERIFY_CHECKSUMS_SH)]:
        try:
            script.chmod(script.stat().st_mode | 0o755)
        except Exception:
            pass

    bundle = resolve(COMPACT_BUNDLE_ZIP)
    ensure_parent(bundle)
    with zipfile.ZipFile(bundle, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in _g559_output_files():
            try:
                zf.write(path, arcname=str(path.resolve().relative_to(ROOT.resolve())).replace(os.sep, "/"))
            except Exception:
                continue

    local_entries = [
        make_entry(path, schema_version=f"{ROUND}_artifact_v1", producer_command="python scripts/run_repair5g559_5090.py", source_commit=source_commit, root=ROOT)
        for path in [*output_files, resolve(RAW_TRANSFER_MANIFEST_CSV), resolve(CHECKSUMS_SHA256), resolve(RESUME_SH), resolve(VERIFY_CHECKSUMS_SH), bundle]
    ]
    write_registry(
        resolve(REGISTRY_JSON),
        [*local_entries, *remote_entries],
        {
            "remote_artifact_root": str(REMOTE_ARTIFACT_ROOT),
            "compact_bundle": COMPACT_BUNDLE_ZIP,
            "raw_transfer_manifest": RAW_TRANSFER_MANIFEST_CSV,
            "resume_script": RESUME_SH,
            "checksum_script": VERIFY_CHECKSUMS_SH,
            **CLAIMS_CLOSED,
        },
    )
    print(json.dumps({"decision": "g559_artifact_durability_bundle_written", "remote_files": len(remote_files), "bundle": COMPACT_BUNDLE_ZIP}))
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
        "--topology-count",
        str(args.topology_count),
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
        main_write_artifact_bundle,
    ]:
        fn(forwarded)
    return 0


__all__ = [name for name in globals() if name.startswith("main_") or name == "parse_args_checked"]
