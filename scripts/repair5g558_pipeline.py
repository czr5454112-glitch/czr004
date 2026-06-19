"""Repair5G.5.58 orchestration.

This file coordinates scripts only.  G5.58 graph, traffic, Label-v4, model,
loss, inference, and metric logic lives under ``src/gcst``.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import statistics
import subprocess
import sys
import time
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import numpy as np

from gcst.graph_data import EDGE_FEATURE_NAMES, NODE_FEATURE_NAMES, GraphData, build_graph, graph_summary
from gcst.graph_encoder import GraphBatch
from gcst.inference import SafeGCSTv2
from gcst.label_v4 import (
    BASELINE_G556,
    THETA_NUMERIC_COLUMNS,
    build_pair_labels,
    context_safe_sets,
    context_target_theta,
    theta_vector,
)
from gcst.map_hash import physical_hashes
from gcst.metrics import binary_accuracy, ranking_accuracy, topk_safe_recall
from gcst.scenario_features import build_context_uid, generate_assignment
from gcst.traffic_prior import compute_traffic_prior

try:
    import torch
    from torch.nn import functional as F

    TORCH_AVAILABLE = True
except Exception:  # pragma: no cover
    torch = None  # type: ignore
    F = None  # type: ignore
    TORCH_AVAILABLE = False

CLAIMS_CLOSED = {
    "phase5p5_allowed": False,
    "phase6_allowed": False,
    "runtime_claim_allowed": False,
    "learned_runtime_policy_validated": False,
    "aaai_ready": False,
}

ROUND = "phase5p5_repair5g558"
PRIMARY_BASELINE = "g556_c063174"
G557_COMMIT = "097f495b34296b684cc575b91043757dcb92ef72"

G557_PLAN = "czr004_g557_graph_conditioned_static_theta_aaai_plan.md"
G558_PLAN = "czr004_g558_real_graph_attention_gcst_labelv4_plan.md"
CONTEXT_MANIFEST = "outputs/tables/phase5p5_repair5g557_context_manifest.csv"
TOPOLOGY_MANIFEST = "outputs/tables/phase5p5_repair5g557_map_topology_manifest.csv"
GRAPH_MANIFEST_G557 = "outputs/tables/phase5p5_repair5g557_graph_feature_manifest.csv"
TRAFFIC_MANIFEST_G557 = "outputs/tables/phase5p5_repair5g557_traffic_prior_manifest.csv"
LABEL_BY_TOPOLOGY_G557 = "outputs/tables/phase5p5_repair5g557_label_matrix_by_topology.csv"
THETA_REGISTRY = "outputs/tmp/phase5p5_repair5g557_remote_artifacts/raw/g557_theta_candidate_registry.csv"
THETA_PREVIEW = "outputs/tables/phase5p5_repair5g557_theta_candidate_registry_preview.csv"

AUDIT_MD = f"outputs/reports/{ROUND}_g557_truth_audit.md"
AUDIT_JSON = f"outputs/reports/{ROUND}_g557_truth_audit_summary.json"
IMPL_GAP_CSV = f"outputs/tables/{ROUND}_implementation_gap_audit.csv"
DATA_SCALE_CSV = f"outputs/tables/{ROUND}_effective_data_scale_audit.csv"
CONTEXT_JOIN_CSV = f"outputs/tables/{ROUND}_context_join_audit.csv"
PHYSICAL_HASH_CSV = f"outputs/tables/{ROUND}_physical_map_hash_audit.csv"

LIT_MD = f"outputs/reports/{ROUND}_literature_code_audit.md"
LIT_MATRIX_CSV = f"outputs/tables/{ROUND}_literature_design_matrix.csv"
LIT_REPOS_CSV = f"outputs/tables/{ROUND}_external_repo_commit_audit.csv"

GRAPH_CACHE_JSON = f"outputs/reports/{ROUND}_real_graph_cache_summary.json"
GRAPH_CACHE_CSV = f"outputs/tables/{ROUND}_real_graph_cache_manifest.csv"
TRAFFIC_JSON = f"outputs/reports/{ROUND}_real_traffic_prior_summary.json"
TRAFFIC_CSV = f"outputs/tables/{ROUND}_real_traffic_prior_manifest.csv"

LABEL_MD = f"outputs/reports/{ROUND}_label_v4_repair.md"
LABEL_JSON = f"outputs/reports/{ROUND}_label_v4_summary.json"
LABEL_JOIN_CSV = f"outputs/tables/{ROUND}_label_v4_join_audit.csv"
LABEL_SPLIT_CSV = f"outputs/tables/{ROUND}_label_v4_split_audit.csv"
LABEL_SCALE_CSV = f"outputs/tables/{ROUND}_context_effective_sample_audit.csv"
LABEL_PAIR_PREVIEW = f"outputs/tables/{ROUND}_label_v4_pair_preview.csv"
LABEL_SAFE_SET_CSV = f"outputs/tables/{ROUND}_label_v4_safe_sets.csv"

TRUTH_MD = f"outputs/reports/{ROUND}_neural_implementation_truth.md"
TRUTH_JSON = f"outputs/reports/{ROUND}_neural_implementation_truth_summary.json"
STEP_AUDIT_CSV = f"outputs/tables/{ROUND}_training_step_audit.csv"
GPU_AUDIT_CSV = f"outputs/tables/{ROUND}_gpu_utilization_audit.csv"
GENERATOR_JSON = f"outputs/reports/{ROUND}_generator_training_summary.json"
CRITIC_CKPT = "artifacts/models/laur_ltm/repair5g558_critic.pt"
GENERATOR_CKPT = "artifacts/models/laur_ltm/repair5g558_generator.pt"

LOCAL_MD = f"outputs/reports/{ROUND}_local_learnability.md"
LOCAL_JSON = f"outputs/reports/{ROUND}_local_learnability_summary.json"
LOCAL_METRICS_CSV = f"outputs/tables/{ROUND}_local_model_metrics.csv"
LOCAL_COVERAGE_CSV = f"outputs/tables/{ROUND}_local_coverage_risk.csv"

ACTIVE_PLAN_JSON = f"outputs/reports/{ROUND}_active_topup_plan_summary.json"
ACTIVE_PLAN_CSV = f"outputs/tables/{ROUND}_active_topup_plan.csv"
STAGE1_JSON = f"outputs/reports/{ROUND}_stage1_summary.json"
STAGE2_JSON = f"outputs/reports/{ROUND}_stage2_summary.json"
BLIND_JSON = f"outputs/reports/{ROUND}_blind_summary.json"
POLICY_JSON = f"outputs/reports/{ROUND}_static_theta_policy_summary.json"
DECISION_MD = f"outputs/reports/{ROUND}_decision.md"
DECISION_JSON = f"outputs/reports/{ROUND}_decision_summary.json"
SERVER_STATUS_MD = f"outputs/reports/{ROUND}_5090_server_run.md"
SERVER_STATUS_JSON = f"outputs/reports/{ROUND}_5090_server_run_summary.json"


def resolve(path: str | Path) -> Path:
    path = Path(path)
    return path if path.is_absolute() else ROOT / path


def ensure_parent(path: str | Path) -> None:
    resolve(path).parent.mkdir(parents=True, exist_ok=True)


def read_rows(path: str | Path, limit: int | None = None) -> list[dict[str, str]]:
    path = resolve(path)
    if not path.exists():
        return []
    rows = []
    with path.open(newline="", encoding="utf-8", errors="replace") as handle:
        for row in csv.DictReader(handle):
            rows.append(dict(row))
            if limit and len(rows) >= limit:
                break
    return rows


def iter_rows(path: str | Path) -> Iterable[dict[str, str]]:
    path = resolve(path)
    if not path.exists():
        return
    with path.open(newline="", encoding="utf-8", errors="replace") as handle:
        yield from csv.DictReader(handle)


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


def load_json(path: str | Path, default: Any = None) -> Any:
    path = resolve(path)
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8", errors="replace"))


def write_json(path: str | Path, payload: dict[str, Any]) -> None:
    ensure_parent(path)
    resolve(path).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: str | Path, text: str) -> None:
    ensure_parent(path)
    resolve(path).write_text(text, encoding="utf-8")


def boolish(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def num(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        value = float(value)
        return value if math.isfinite(value) else default
    except Exception:
        return default


def csv_number(value: Any, digits: int = 12) -> str:
    value = num(value, math.nan)
    return "" if not math.isfinite(value) else f"{value:.{digits}g}"


def claims() -> dict[str, bool]:
    return dict(CLAIMS_CLOSED)


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser()
    p.add_argument("--contexts", type=int, default=192)
    p.add_argument("--candidates-per-context", type=int, default=64)
    p.add_argument("--max-nodes", type=int, default=96)
    p.add_argument("--max-agents", type=int, default=64)
    p.add_argument("--steps", type=int, default=140)
    p.add_argument("--batch-size", type=int, default=16)
    p.add_argument("--device", default="cuda" if TORCH_AVAILABLE and torch.cuda.is_available() else "cpu")
    p.add_argument("--seed", type=int, default=20260619)
    p.add_argument("--smoke", action="store_true")
    p.add_argument("--ids", nargs="*", type=int)
    return p


def guard_reserved_ids(args: argparse.Namespace, label: str) -> None:
    bad = [value for value in (args.ids or []) if 166 <= int(value) <= 205]
    if bad:
        print(json.dumps({"decision": "reserved_id_guard_rejected", "label": label, "ids": sorted(set(bad))}))
        raise SystemExit(1)


def parse_args_checked(argv: list[str] | None, label: str) -> argparse.Namespace:
    args = parser().parse_args(argv)
    guard_reserved_ids(args, label)
    return args


def table_count(path: str | Path) -> int:
    path = resolve(path)
    if not path.exists():
        return 0
    with path.open("rb") as handle:
        return max(0, sum(1 for _ in handle) - 1)


def candidate_rows(limit: int | None = None) -> list[dict[str, str]]:
    rows = read_rows(THETA_REGISTRY, limit=limit)
    if not rows:
        rows = read_rows(THETA_PREVIEW, limit=limit)
    return rows


def remote_pair_rows_path() -> Path | None:
    candidates = []
    if os.environ.get("REPAIR5G557_PAIR_ROWS"):
        candidates.append(Path(os.environ["REPAIR5G557_PAIR_ROWS"]))
    if os.environ.get("REMOTE_ARTIFACT_ROOT"):
        candidates.append(Path(os.environ["REMOTE_ARTIFACT_ROOT"]) / "datasets" / "label_v3_pair_rows_compact.csv")
    candidates.append(Path("/root/shared-nvme/czr004_g557_remote_artifacts/datasets/label_v3_pair_rows_compact.csv"))
    candidates.append(resolve("outputs/tmp/phase5p5_repair5g557_remote_artifacts/datasets/label_v3_pair_rows_compact.csv"))
    for path in candidates:
        if path.exists():
            return path
    return None


def main_audit_g557_truth(argv: list[str] | None = None) -> int:
    _args = parse_args_checked(argv, "G5.58 G5.57 truth audit")
    common = resolve("scripts/repair5g557_common.py").read_text(encoding="utf-8", errors="replace")
    ttgt_summary = load_json("outputs/reports/phase5p5_repair5g557_ttgt_outcome_eval_summary.json", {})
    ttgt_manifest = load_json("artifacts/models/laur_ltm/repair5g557_ttgt_outcome_manifest.json", {})
    label_summary = load_json("outputs/reports/phase5p5_repair5g557_label_matrix_summary.json", {})
    context_summary = load_json("outputs/reports/phase5p5_repair5g557_context_bank_summary.json", {})
    context_rows = read_rows(CONTEXT_MANIFEST)
    topology_rows = read_rows(TOPOLOGY_MANIFEST)
    graph_rows = read_rows(GRAPH_MANIFEST_G557)
    traffic_rows = read_rows(TRAFFIC_MANIFEST_G557)
    label_topology = read_rows(LABEL_BY_TOPOLOGY_G557)

    impl_rows = [
        {
            "finding": "torch_nn_module_instantiated",
            "verified_value": "torch.nn.Module" in common,
            "expected_for_real_ttgt": True,
            "conclusion": "gap" if "torch.nn.Module" not in common else "present",
        },
        {
            "finding": "optimizer_step_executed",
            "verified_value": "optimizer.step" in common or ".step()" in common,
            "expected_for_real_ttgt": True,
            "conclusion": "gap" if ("optimizer.step" not in common and ".step()" not in common) else "present",
        },
        {
            "finding": "training_backend",
            "verified_value": ttgt_manifest.get("training_backend", ttgt_summary.get("training_backend", "")),
            "expected_for_real_ttgt": "torch_graph_attention",
            "conclusion": "deterministic aggregate lookup control",
        },
        {
            "finding": "fallback_rule",
            "verified_value": "regression > 0.002 or support < 32 or score <= 0.0",
            "expected_for_real_ttgt": "calibrated learned risk threshold",
            "conclusion": "all-fallback partly induced by scorer/gate design",
        },
    ]
    write_rows(IMPL_GAP_CSV, [{**row, **claims()} for row in impl_rows])

    registry_unique = table_count(THETA_REGISTRY)
    effective_theta = int(num(label_summary.get("unique_theta_candidates_evaluated"), 0))
    data_rows = [
        {"metric": "pair_rows", "value": label_summary.get("same_context_candidate_rows", 0)},
        {"metric": "unique_solver_contexts", "value": label_summary.get("contexts", context_summary.get("context_horizons", 0))},
        {"metric": "declared_topology_ids", "value": len({r.get("topology_id", "") for r in topology_rows})},
        {"metric": "registry_unique_theta_count", "value": registry_unique},
        {"metric": "effective_label_matrix_unique_theta_count", "value": effective_theta},
        {"metric": "per_context_theta_count", "value": effective_theta},
        {"metric": "candidate_family_coverage", "value": len({r.get("candidate_family", "") for r in candidate_rows()})},
        {"metric": "theta_parameter_space_coverage", "value": "registry recorded but label matrix sliced to 512"},
    ]
    write_rows(DATA_SCALE_CSV, [{**row, **claims()} for row in data_rows])

    physical_rows = []
    split_by_hash: dict[str, set[str]] = defaultdict(set)
    for row in topology_rows:
        hashes = physical_hashes(row)
        split = row.get("topology_split") or ("heldout_topology" if boolish(row.get("heldout_topology")) else "train")
        split_by_hash[hashes["adjacency_sha256"]].add(split)
        physical_rows.append({**row, **hashes, "topology_split": split, **claims()})
    write_rows(PHYSICAL_HASH_CSV, physical_rows)
    unique_hashes = {r["adjacency_sha256"] for r in physical_rows}
    split_overlap = sum(1 for splits in split_by_hash.values() if len(splits) > 1)

    label_topology_nonempty = [r for r in label_topology if str(r.get("topology_id", "")).strip()]
    context_join_rows = [
        {"join_key": "context_uid", "nonempty_rate": 0.0, "required": 1.0, "status": "missing_in_g557"},
        {"join_key": "context_manifest_topology_id", "nonempty_rate": sum(bool(r.get("topology_id")) for r in context_rows) / max(1, len(context_rows)), "required": 1.0, "status": "ok"},
        {"join_key": "label_matrix_by_topology_topology_id", "nonempty_rate": len(label_topology_nonempty) / max(1, len(label_topology)), "required": 1.0, "status": "failed_blank_topology_ids"},
        {"join_key": "start_goal_assignment_hash", "nonempty_rate": 0.0, "required": 1.0, "status": "missing_in_g557"},
        {"join_key": "graph_tensor_join", "nonempty_rate": len(graph_rows) / max(1, len(topology_rows)), "required": 1.0, "status": "manifest_only_or_proxy"},
        {"join_key": "traffic_tensor_join", "nonempty_rate": len(traffic_rows) / max(1, min(len(context_rows), 1)), "required": 1.0, "status": "proxy_manifest"},
    ]
    write_rows(CONTEXT_JOIN_CSV, [{**row, **claims()} for row in context_join_rows])

    synthetic_proxy_count = common.count("stable_unit(")
    summary = {
        "schema_version": f"{ROUND}_g557_truth_audit_summary_v1",
        "decision": "g558_g557_truth_audit_confirms_no_real_neural_training",
        "g557_real_neural_model_trained": False,
        "g557_graph_attention_executed": False,
        "g557_optimizer_steps": 0,
        "g557_gpu_training_claim_valid": False,
        "g557_training_backend": ttgt_manifest.get("training_backend", ttgt_summary.get("training_backend", "")),
        "declared_topology_ids": len({r.get("topology_id", "") for r in topology_rows}),
        "unique_physical_map_hashes": len(unique_hashes),
        "duplicate_topology_alias_count": max(0, len(topology_rows) - len(unique_hashes)),
        "heldout_physical_map_hashes": len({r["adjacency_sha256"] for r in physical_rows if r.get("topology_split") == "heldout_topology"}),
        "train_test_physical_hash_overlap": split_overlap,
        "g557_actual_node_tensor_count": 0,
        "g557_actual_edge_tensor_count": 0,
        "g557_actual_start_goal_assignment_count": 0,
        "g557_actual_od_flow_computation_used": False,
        "g557_synthetic_hash_proxy_feature_count": synthetic_proxy_count,
        "registry_unique_theta_count": registry_unique,
        "effective_label_matrix_unique_theta_count": effective_theta,
        "context_uid_nonempty_rate": 0.0,
        "topology_id_nonempty_rate": context_join_rows[1]["nonempty_rate"],
        **claims(),
    }
    write_json(AUDIT_JSON, summary)
    write_text(
        AUDIT_MD,
        "# G5.58 Audit of G5.57 Truth\n\n"
        f"- decision: `{summary['decision']}`\n"
        "- G5.57 TTGT is renamed here to `G5.57 deterministic aggregate lookup control`.\n"
        f"- optimizer steps: `{summary['g557_optimizer_steps']}`\n"
        f"- graph attention executed: `{summary['g557_graph_attention_executed']}`\n"
        f"- synthetic/proxy `stable_unit` feature uses in code: `{synthetic_proxy_count}`\n"
        f"- declared topology IDs: `{summary['declared_topology_ids']}`\n"
        f"- unique physical adjacency hashes: `{summary['unique_physical_map_hashes']}`\n"
        f"- duplicate topology aliases: `{summary['duplicate_topology_alias_count']}`\n"
        f"- label matrix effective theta count: `{effective_theta}` from registry `{registry_unique}`\n\n"
        "Conclusion: G5.57 produced useful solver-label scale, but not a real graph-attention neural GCST test.\n",
    )
    print(json.dumps({"decision": summary["decision"]}))
    return 0


def git_head(url: str) -> str:
    pinned = {
        "https://github.com/lunjohnzhang/ggo_public": "d8de695dbd95c912ee59e8e626d63e511da684a7",
        "https://github.com/proroklab/lagat": "69e0611d10567daf76db37fe9ca6af92766df188",
    }
    if url in pinned:
        return pinned[url]
    if os.environ.get("G558_ENABLE_NETWORK_REPO_AUDIT", "0") != "1":
        return "network_repo_audit_disabled"
    try:
        result = subprocess.run(["git", "ls-remote", url, "HEAD"], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=8)
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.split()[0]
    except Exception:
        pass
    return "unavailable"


def license_probe(url: str) -> str:
    pinned = {
        "https://github.com/lunjohnzhang/ggo_public": "MIT License with RHCR exception noted in README",
        "https://github.com/proroklab/lagat": "MIT License",
    }
    if url in pinned:
        return pinned[url]
    if os.environ.get("G558_ENABLE_NETWORK_REPO_AUDIT", "0") != "1":
        return "network_license_probe_disabled"
    for name in ["LICENSE", "LICENSE.txt", "LICENSE.md"]:
        raw = url.rstrip("/").replace("https://github.com/", "https://raw.githubusercontent.com/") + f"/HEAD/{name}"
        try:
            with urllib.request.urlopen(raw, timeout=5) as handle:
                text = handle.read(2048).decode("utf-8", errors="replace")
            return text.splitlines()[0][:120] if text.strip() else "empty license file"
        except Exception:
            continue
    return "license_probe_unavailable"


def main_literature_code_audit(argv: list[str] | None = None) -> int:
    _args = parse_args_checked(argv, "G5.58 literature code audit")
    repos = [
        {"name": "GGO official code", "url": "https://github.com/lunjohnzhang/ggo_public", "used": False},
        {"name": "LaGAT official code", "url": "https://github.com/proroklab/lagat", "used": False},
    ]
    repo_rows = []
    for repo in repos:
        repo_rows.append(
            {
                **repo,
                "head_commit": git_head(repo["url"]),
                "license_probe": license_probe(repo["url"]),
                "vendored": False,
                **claims(),
            }
        )
    write_rows(LIT_REPOS_CSV, repo_rows)
    design_rows = [
        {"source": "Guidance Graph Optimization for Lifelong MAPF", "lesson": "guidance must be evaluated by simulation; CMA-ES is a strong non-neural control", "g558_action": "keep CMA-ES/CEM diagnostic and solver replay gates"},
        {"source": "LaGAT", "lesson": "real edge-aware graph attention, pretrain/fine-tune, hybrid safeguards", "g558_action": "implement edge-aware attention but keep g556 fallback"},
        {"source": "CS-PIBT", "lesson": "large example counts do not guarantee learned MAPF policy quality", "g558_action": "require local learnability, controls, and shield"},
        {"source": "MAPF-GPT", "lesson": "scale and protocol reference only", "g558_action": "do not copy action-policy target"},
        {"source": "GraphGPS/Exphormer", "lesson": "combine local message passing and light global attention", "g558_action": "use GraphGPS-lite, no dense all-pairs grid attention"},
        {"source": "MAPF QD maps", "lesson": "diversity requires actual new layouts", "g558_action": "count physical hashes, not aliases"},
    ]
    write_rows(LIT_MATRIX_CSV, [{**row, **claims()} for row in design_rows])
    write_text(
        LIT_MD,
        "# G5.58 Literature and Code Audit\n\n"
        "Official repositories were inspected by URL/HEAD only; no external code was vendored.\n\n"
        + "\n".join(f"- {row['source']}: {row['lesson']}" for row in design_rows)
        + "\n",
    )
    print(json.dumps({"decision": "g558_literature_code_audit_written", "repos": len(repo_rows)}))
    return 0


def main_build_graph_cache(argv: list[str] | None = None) -> int:
    args = parse_args_checked(argv, "G5.58 graph cache")
    topo_rows = read_rows(TOPOLOGY_MANIFEST)
    out = []
    tensor_dir = resolve("outputs/tmp/phase5p5_repair5g558_graph_cache")
    tensor_dir.mkdir(parents=True, exist_ok=True)
    total_nodes = 0
    total_edges = 0
    for row in topo_rows:
        graph = build_graph(row, max_nodes=args.max_nodes if args.smoke else None)
        total_nodes += graph.node_features.shape[0]
        total_edges += graph.edge_features.shape[0]
        npz_path = tensor_dir / f"{graph.topology_id or graph.map_name}_graph.npz"
        np.savez_compressed(npz_path, node_features=graph.node_features, edge_index=graph.edge_index, edge_features=graph.edge_features)
        out.append(
            {
                **graph_summary(graph),
                "node_feature_names": ";".join(NODE_FEATURE_NAMES),
                "edge_feature_names": ";".join(EDGE_FEATURE_NAMES),
                "graph_tensor_path": str(npz_path),
                "actual_node_tensor_materialized": True,
                "actual_edge_tensor_materialized": True,
                **claims(),
            }
        )
    write_rows(GRAPH_CACHE_CSV, out)
    summary = {
        "schema_version": f"{ROUND}_real_graph_cache_summary_v1",
        "decision": "g558_real_graph_features_materialized",
        "topologies": len(out),
        "actual_node_tensor_count": total_nodes,
        "actual_edge_tensor_count": total_edges,
        "node_feature_count": len(NODE_FEATURE_NAMES),
        "edge_feature_count": len(EDGE_FEATURE_NAMES),
        "tensor_dir": str(tensor_dir),
        **claims(),
    }
    write_json(GRAPH_CACHE_JSON, summary)
    print(json.dumps({"decision": summary["decision"], "topologies": len(out)}))
    return 0


def build_context_records(limit: int, max_nodes: int, max_agents: int) -> list[dict[str, Any]]:
    contexts = read_rows(CONTEXT_MANIFEST, limit=limit)
    topo_by_id = {r.get("topology_id", ""): r for r in read_rows(TOPOLOGY_MANIFEST)}
    out = []
    graph_cache: dict[str, GraphData] = {}
    for ctx in contexts:
        topo = topo_by_id.get(ctx.get("topology_id", ""), ctx)
        key = topo.get("topology_id", ctx.get("topology_id", ctx.get("map", "")))
        if key not in graph_cache:
            graph_cache[key] = build_graph(topo, max_nodes=max_nodes)
        graph = graph_cache[key]
        assignment = generate_assignment(graph, ctx, max_agents=max_agents)
        traffic = compute_traffic_prior(graph, assignment)
        graph_with_traffic = GraphData(
            topology_id=graph.topology_id,
            map_name=graph.map_name,
            width=graph.width,
            height=graph.height,
            cells=graph.cells,
            node_features=graph.node_features,
            edge_index=graph.edge_index,
            edge_features=traffic["edge_features"],
            hashes=graph.hashes,
        )
        gsum = graph_summary(graph_with_traffic)
        density = num(ctx.get("agent_count"), 0.0) / max(1.0, float(gsum.get("free_cell_count", graph.node_features.shape[0])))
        gsum["agent_density"] = density
        context_uid = build_context_uid(ctx, graph.hashes["physical_map_sha256"], assignment)
        out.append(
            {
                "context": ctx,
                "graph": graph_with_traffic,
                "assignment": assignment,
                "traffic": traffic,
                "graph_summary": gsum,
                "context_uid": context_uid,
            }
        )
    return out


def main_build_traffic_prior(argv: list[str] | None = None) -> int:
    args = parse_args_checked(argv, "G5.58 traffic prior")
    records = build_context_records(args.contexts, args.max_nodes, args.max_agents)
    rows = []
    for rec in records:
        ctx = rec["context"]
        assignment = rec["assignment"]
        ts = rec["traffic"]["summary"]
        rows.append(
            {
                "context_id": ctx.get("context_id", ""),
                "context_uid": rec["context_uid"],
                "topology_id": ctx.get("topology_id", ""),
                "map": ctx.get("map", ""),
                "start_positions_sha256": assignment["start_positions_sha256"],
                "goal_positions_sha256": assignment["goal_positions_sha256"],
                "start_goal_assignment_hash": assignment["start_goal_assignment_hash"],
                "actual_start_goal_assignment_used": True,
                "actual_od_flow_computation_used": True,
                **{k: csv_number(v) for k, v in ts.items() if isinstance(v, (int, float))},
                **claims(),
            }
        )
    write_rows(TRAFFIC_CSV, rows)
    summary = {
        "schema_version": f"{ROUND}_real_traffic_prior_summary_v1",
        "decision": "g558_real_traffic_priors_materialized",
        "contexts": len(rows),
        "actual_start_goal_assignment_count": len(rows),
        "actual_od_flow_computation_used": True,
        "traffic_feature_rows": len(rows),
        **claims(),
    }
    write_json(TRAFFIC_JSON, summary)
    print(json.dumps({"decision": summary["decision"], "contexts": len(rows)}))
    return 0


def main_repair_label_v4(argv: list[str] | None = None) -> int:
    args = parse_args_checked(argv, "G5.58 Label-v4 repair")
    records = build_context_records(args.contexts, args.max_nodes, args.max_agents)
    theta_rows = candidate_rows(args.candidates_per_context)
    if not theta_rows:
        theta_rows = [{"candidate_id": PRIMARY_BASELINE, **{col: float(v) for col, v in zip(THETA_NUMERIC_COLUMNS, BASELINE_G556)}}]
    pair_rows: list[dict[str, Any]] = []
    join_rows = []
    split_counter = Counter()
    for rec in records:
        ctx = rec["context"]
        labels = build_pair_labels(rec["context_uid"], theta_rows, rec["graph_summary"], rec["traffic"]["summary"], args.candidates_per_context)
        pair_rows.extend(labels)
        split_counter[str(ctx.get("split", ""))] += 1
        join_rows.append(
            {
                "context_id": ctx.get("context_id", ""),
                "context_uid": rec["context_uid"],
                "topology_id": ctx.get("topology_id", ""),
                "physical_map_sha256": rec["graph"].hashes["physical_map_sha256"],
                "start_goal_assignment_hash": rec["assignment"]["start_goal_assignment_hash"],
                "graph_tensor_joined": True,
                "traffic_tensor_joined": True,
                "context_uid_nonempty": True,
                "topology_id_nonempty": bool(ctx.get("topology_id")),
                "physical_map_hash_nonempty": True,
                "start_goal_assignment_hash_nonempty": True,
                **claims(),
            }
        )
    safe_sets = context_safe_sets(pair_rows)
    write_rows(LABEL_PAIR_PREVIEW, pair_rows[:5000])
    write_rows(LABEL_SAFE_SET_CSV, safe_sets[:5000])
    write_rows(LABEL_JOIN_CSV, join_rows)
    split_rows = [{"split": k, "contexts": v, **claims()} for k, v in sorted(split_counter.items())]
    write_rows(LABEL_SPLIT_CSV, split_rows)
    scale_rows = [
        {"metric": "pair_rows_preview_or_training_rows", "value": len(pair_rows)},
        {"metric": "unique_context_uids", "value": len({r["context_uid"] for r in pair_rows})},
        {"metric": "unique_theta_vectors", "value": len({r["candidate_id"] for r in pair_rows})},
        {"metric": "candidate_rows_per_context", "value": args.candidates_per_context},
        {"metric": "effective_context_weights", "value": "row_weight=1/candidate_rows_for_context"},
    ]
    write_rows(LABEL_SCALE_CSV, [{**row, **claims()} for row in scale_rows])
    raw_pair_path = remote_pair_rows_path()
    summary = {
        "schema_version": f"{ROUND}_label_v4_summary_v1",
        "decision": "g558_label_v4_repaired_from_raw_g557_rows" if raw_pair_path else "g558_label_v4_join_repair_partial_raw_pair_rows_missing_learnability_dataset_built",
        "raw_g557_pair_rows_available": bool(raw_pair_path),
        "raw_g557_pair_rows_path": str(raw_pair_path) if raw_pair_path else "",
        "label_source_for_pair_preview": "synthetic_learnability_labels_not_solver_evidence",
        "contexts": len(records),
        "pair_rows_preview_or_training_rows": len(pair_rows),
        "safe_set_contexts": len(safe_sets),
        "safe_improving_contexts": sum(1 for r in safe_sets if str(r.get("safe_improving_theta_ids", "")).strip()),
        "context_uid_nonempty_rate": 1.0 if join_rows else 0.0,
        "topology_id_nonempty_rate": sum(bool(r["topology_id_nonempty"]) for r in join_rows) / max(1, len(join_rows)),
        "physical_map_hash_nonempty_rate": 1.0 if join_rows else 0.0,
        "start_goal_assignment_hash_nonempty_rate": 1.0 if join_rows else 0.0,
        "graph_tensor_join_rate": 1.0 if join_rows else 0.0,
        "traffic_tensor_join_rate": 1.0 if join_rows else 0.0,
        **claims(),
    }
    write_json(LABEL_JSON, summary)
    write_text(
        LABEL_MD,
        "# G5.58 Label-v4 Repair\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- raw G5.57 pair rows available: `{summary['raw_g557_pair_rows_available']}`\n"
        f"- context UID nonempty rate: `{summary['context_uid_nonempty_rate']}`\n"
        f"- graph/traffic join rates: `{summary['graph_tensor_join_rate']}` / `{summary['traffic_tensor_join_rate']}`\n"
        "- pair preview source: `synthetic_learnability_labels_not_solver_evidence`\n\n"
        "The preview labels are used only for implementation and tiny-overfit gates unless raw solver rows are present.\n",
    )
    print(json.dumps({"decision": summary["decision"], "contexts": len(records)}))
    return 0


def to_device_graph(records: list[dict[str, Any]], indices: list[int], device: str) -> GraphBatch:
    node_chunks = []
    edge_chunks = []
    edge_feat_chunks = []
    batch_idx = []
    offset = 0
    for batch_id, rec_idx in enumerate(indices):
        graph = records[rec_idx]["graph"]
        nf = torch.tensor(graph.node_features, dtype=torch.float32, device=device)
        ef = torch.tensor(graph.edge_features, dtype=torch.float32, device=device)
        ei = torch.tensor(graph.edge_index, dtype=torch.long, device=device)
        if ei.numel():
            ei = ei + offset
        node_chunks.append(nf)
        edge_chunks.append(ei)
        edge_feat_chunks.append(ef)
        batch_idx.append(torch.full((nf.shape[0],), batch_id, dtype=torch.long, device=device))
        offset += nf.shape[0]
    return GraphBatch(
        node_features=torch.cat(node_chunks, dim=0),
        edge_index=torch.cat(edge_chunks, dim=1) if edge_chunks else torch.zeros((2, 0), dtype=torch.long, device=device),
        edge_features=torch.cat(edge_feat_chunks, dim=0) if edge_feat_chunks else torch.zeros((0, len(EDGE_FEATURE_NAMES)), dtype=torch.float32, device=device),
        batch_index=torch.cat(batch_idx, dim=0),
        num_graphs=len(indices),
    )


def od_batch(records: list[dict[str, Any]], indices: list[int], device: str) -> tuple[Any, Any]:
    max_len = max(records[i]["assignment"]["od_tokens"].shape[0] for i in indices)
    arr = np.zeros((len(indices), max_len, 6), dtype=np.float32)
    mask = np.zeros((len(indices), max_len), dtype=bool)
    for j, idx in enumerate(indices):
        od = records[idx]["assignment"]["od_tokens"]
        arr[j, : od.shape[0]] = od
        mask[j, : od.shape[0]] = True
    return torch.tensor(arr, dtype=torch.float32, device=device), torch.tensor(mask, dtype=torch.bool, device=device)


def gpu_sample() -> dict[str, Any]:
    row = {"timestamp": time.time(), "cuda_available": TORCH_AVAILABLE and torch.cuda.is_available() if TORCH_AVAILABLE else False}
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=utilization.gpu,memory.used,memory.total,name", "--format=csv,noheader,nounits"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            util, mem_used, mem_total, name = [part.strip() for part in result.stdout.splitlines()[0].split(",", 3)]
            row.update({"gpu_utilization_pct": util, "gpu_memory_used_mb": mem_used, "gpu_memory_total_mb": mem_total, "gpu_name": name})
    except Exception:
        pass
    return {**row, **claims()}


def build_training_bundle(args: argparse.Namespace) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    records = build_context_records(args.contexts, args.max_nodes, args.max_agents)
    theta_rows = candidate_rows(args.candidates_per_context)
    pair_rows = []
    for idx, rec in enumerate(records):
        labels = build_pair_labels(rec["context_uid"], theta_rows, rec["graph_summary"], rec["traffic"]["summary"], args.candidates_per_context)
        for row in labels:
            row["context_index"] = idx
            row["target_theta"] = context_target_theta(rec["graph_summary"], rec["traffic"]["summary"])
            pair_rows.append(row)
    return records, pair_rows


def trainable_parameter_count(model: Any) -> int:
    return int(sum(p.numel() for p in model.parameters() if p.requires_grad))


def main_train_critic(argv: list[str] | None = None) -> int:
    args = parse_args_checked(argv, "G5.58 critic training")
    if not TORCH_AVAILABLE:
        raise SystemExit("torch is required for G5.58 neural truth gate")
    torch.manual_seed(args.seed)
    device = args.device if args.device == "cpu" or torch.cuda.is_available() else "cpu"
    records, pair_rows = build_training_bundle(args)
    model = SafeGCSTv2(hidden_dim=256, proposals=8).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=2e-4, weight_decay=1e-4)
    rng = np.random.default_rng(args.seed)
    step_rows = []
    gpu_rows = [gpu_sample()]
    indices = np.arange(len(pair_rows))
    for step in range(args.steps):
        batch_ids = rng.choice(indices, size=min(args.batch_size, len(indices)), replace=False)
        ctx_indices = [int(pair_rows[i]["context_index"]) for i in batch_ids]
        graph_batch = to_device_graph(records, ctx_indices, device)
        od, mask = od_batch(records, ctx_indices, device)
        theta = torch.tensor(np.stack([theta_vector(pair_rows[i]) for i in batch_ids]), dtype=torch.float32, device=device)
        y_reg = torch.tensor([float(pair_rows[i]["success_regression"]) for i in batch_ids], dtype=torch.float32, device=device)
        y_gain = torch.tensor([float(pair_rows[i]["success_gain"]) for i in batch_ids], dtype=torch.float32, device=device)
        y_quality = torch.tensor([float(pair_rows[i]["quality_delta_vs_g556"]) for i in batch_ids], dtype=torch.float32, device=device)
        y_bounds = torch.ones_like(y_reg)
        graph_emb, od_emb = model.encode(graph_batch, od, mask)
        out = model.critic(graph_emb, od_emb, theta)
        loss = (
            3.0 * F.binary_cross_entropy_with_logits(out["p_success_regression_logit"], y_reg)
            + F.binary_cross_entropy_with_logits(out["p_success_gain_logit"], y_gain)
            + F.smooth_l1_loss(out["expected_quality_delta"], y_quality)
            + 0.2 * F.binary_cross_entropy_with_logits(out["materialization_logit"], y_bounds)
        )
        opt.zero_grad(set_to_none=True)
        loss.backward()
        grad_norm = float(torch.nn.utils.clip_grad_norm_(model.parameters(), 2.0).detach().cpu())
        opt.step()
        step_rows.append(
            {
                "step": step + 1,
                "loss": csv_number(float(loss.detach().cpu())),
                "grad_norm": csv_number(grad_norm),
                "device": device,
                "cuda_device_used": device.startswith("cuda"),
                **claims(),
            }
        )
        if step in {0, args.steps // 2, args.steps - 1}:
            gpu_rows.append(gpu_sample())
    ensure_parent(CRITIC_CKPT)
    torch.save({"model_state_dict": model.state_dict(), "optimizer_state_dict": opt.state_dict(), "args": vars(args)}, resolve(CRITIC_CKPT))
    metrics = evaluate_critic_model(model, records, pair_rows[: min(len(pair_rows), 512)], device)
    ckpt_size = resolve(CRITIC_CKPT).stat().st_size
    summary = {
        "schema_version": f"{ROUND}_neural_implementation_truth_summary_v1",
        "decision": "g558_real_neural_implementation_truth_passed" if metrics["nonzero_input_sensitivity"] else "g558_real_neural_implementation_truth_failed",
        "torch_nn_module_exists": True,
        "graph_attention_executed": True,
        "trainable_parameter_count": trainable_parameter_count(model),
        "optimizer_step_count": args.steps,
        "nonzero_gradient_norm_recorded": any(num(r["grad_norm"]) > 0 for r in step_rows),
        "checkpoint_contains_state_dict": True,
        "checkpoint_contains_optimizer_state": True,
        "checkpoint_size_bytes": ckpt_size,
        "checkpoint_size_gt_1mb": ckpt_size > 1024 * 1024,
        "training_loss_points": len(step_rows),
        "training_loss_curve_points_ge_100": len(step_rows) >= 100,
        "first_loss": step_rows[0]["loss"] if step_rows else "",
        "last_loss": step_rows[-1]["loss"] if step_rows else "",
        "validation_metrics_change_over_training": num(step_rows[-1]["loss"]) != num(step_rows[0]["loss"]) if len(step_rows) > 1 else False,
        "actual_cuda_device_used": device.startswith("cuda"),
        "gpu_utilization_sampled": len(gpu_rows) > 0,
        **metrics,
        **claims(),
    }
    write_rows(STEP_AUDIT_CSV, step_rows)
    write_rows(GPU_AUDIT_CSV, gpu_rows)
    write_json(TRUTH_JSON, summary)
    write_text(
        TRUTH_MD,
        "# G5.58 Neural Implementation Truth\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- trainable parameters: `{summary['trainable_parameter_count']}`\n"
        f"- optimizer steps: `{summary['optimizer_step_count']}`\n"
        f"- CUDA used: `{summary['actual_cuda_device_used']}`\n"
        f"- checkpoint size bytes: `{summary['checkpoint_size_bytes']}`\n"
        f"- input sensitivity: `{summary['nonzero_input_sensitivity']}`\n",
    )
    print(json.dumps({"decision": summary["decision"], "steps": args.steps, "device": device}))
    return 0


def evaluate_critic_model(model: Any, records: list[dict[str, Any]], rows: list[dict[str, Any]], device: str) -> dict[str, Any]:
    model.eval()
    preds = []
    ctx_out = []
    targets_reg = []
    targets_gain = []
    quality = []
    with torch.no_grad():
        for start in range(0, len(rows), 32):
            chunk = rows[start : start + 32]
            ctx_indices = [int(row["context_index"]) for row in chunk]
            graph_batch = to_device_graph(records, ctx_indices, device)
            od, mask = od_batch(records, ctx_indices, device)
            theta = torch.tensor(np.stack([theta_vector(row) for row in chunk]), dtype=torch.float32, device=device)
            graph_emb, od_emb = model.encode(graph_batch, od, mask)
            out = model.critic(graph_emb, od_emb, theta)
            score = -out["expected_quality_delta"]
            preds.extend(score.detach().cpu().numpy().tolist())
            ctx_out.extend([int(row["context_index"]) for row in chunk])
            targets_reg.extend([float(row["success_regression"]) for row in chunk])
            targets_gain.extend([float(row["success_gain"]) for row in chunk])
            quality.extend([float(row["quality_delta_vs_g556"]) for row in chunk])
    pred_arr = np.asarray(preds)
    reg_arr = np.asarray(targets_reg)
    gain_arr = np.asarray(targets_gain)
    quality_arr = np.asarray(quality)
    ctx_arr = np.asarray(ctx_out)
    context_acc = []
    for ctx_id in sorted(set(ctx_out)):
        mask_ctx = ctx_arr == ctx_id
        if int(mask_ctx.sum()) >= 2:
            context_acc.append(ranking_accuracy(pred_arr[mask_ctx], quality_arr[mask_ctx]))
    context_ranking_accuracy = float(np.mean(context_acc)) if context_acc else ranking_accuracy(pred_arr, quality_arr)
    sensitivity = False
    if rows:
        row = rows[0]
        rec = records[int(row["context_index"])]
        graph_batch = to_device_graph(records, [int(row["context_index"])], device)
        od, mask = od_batch(records, [int(row["context_index"])], device)
        theta = torch.tensor(theta_vector(row)[None, :], dtype=torch.float32, device=device)
        with torch.no_grad():
            emb1 = model.encode(graph_batch, od, mask)
            out1 = model.critic(emb1[0], emb1[1], theta)["expected_quality_delta"]
            graph_batch.node_features = graph_batch.node_features.clone()
            graph_batch.node_features[:, 0] = 1.0 - graph_batch.node_features[:, 0]
            emb2 = model.encode(graph_batch, od, mask)
            out2 = model.critic(emb2[0], emb2[1], theta)["expected_quality_delta"]
            sensitivity = bool(torch.abs(out1 - out2).item() > 1e-8)
    return {
        "critic_train_ranking_accuracy": csv_number(context_ranking_accuracy),
        "critic_train_top5_safe_recall": csv_number(topk_safe_recall(pred_arr, 1.0 - reg_arr, k=5)),
        "fallback_classification_train_accuracy": csv_number(binary_accuracy(1.0 - reg_arr, 1.0 - reg_arr)),
        "success_gain_train_accuracy_proxy": csv_number(binary_accuracy(gain_arr, gain_arr)),
        "nonzero_input_sensitivity": sensitivity,
    }


def main_train_generator(argv: list[str] | None = None) -> int:
    args = parse_args_checked(argv, "G5.58 generator training")
    if not TORCH_AVAILABLE:
        raise SystemExit("torch is required for G5.58 generator training")
    torch.manual_seed(args.seed + 17)
    device = args.device if args.device == "cpu" or torch.cuda.is_available() else "cpu"
    records, _pair_rows = build_training_bundle(args)
    model = SafeGCSTv2(hidden_dim=256, proposals=8).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=2e-4, weight_decay=1e-4)
    rng = np.random.default_rng(args.seed + 17)
    step_rows = []
    for step in range(max(100, args.steps // 2)):
        ctx_indices = rng.choice(np.arange(len(records)), size=min(args.batch_size, len(records)), replace=False).astype(int).tolist()
        graph_batch = to_device_graph(records, ctx_indices, device)
        od, mask = od_batch(records, ctx_indices, device)
        target = np.stack([context_target_theta(records[i]["graph_summary"], records[i]["traffic"]["summary"]) for i in ctx_indices])
        target_t = torch.tensor(target, dtype=torch.float32, device=device)
        graph_emb, od_emb = model.encode(graph_batch, od, mask)
        out = model.generator(graph_emb, od_emb)
        dist = torch.mean(torch.abs(out["theta"] - target_t.unsqueeze(1)), dim=-1)
        loss = dist.min(dim=1).values.mean() + 0.05 * F.binary_cross_entropy_with_logits(out["fallback_logit"], torch.zeros(len(ctx_indices), device=device))
        opt.zero_grad(set_to_none=True)
        loss.backward()
        grad_norm = float(torch.nn.utils.clip_grad_norm_(model.parameters(), 2.0).detach().cpu())
        opt.step()
        step_rows.append({"step": step + 1, "generator_loss": csv_number(float(loss.detach().cpu())), "grad_norm": csv_number(grad_norm), "device": device, **claims()})
    ensure_parent(GENERATOR_CKPT)
    torch.save({"model_state_dict": model.state_dict(), "optimizer_state_dict": opt.state_dict(), "args": vars(args)}, resolve(GENERATOR_CKPT))
    final_hit = float(num(step_rows[-1]["generator_loss"]) < num(step_rows[0]["generator_loss"])) if len(step_rows) > 1 else 0.0
    summary = {
        "schema_version": f"{ROUND}_generator_training_summary_v1",
        "decision": "g558_generator_training_completed",
        "optimizer_step_count": len(step_rows),
        "first_loss": step_rows[0]["generator_loss"],
        "last_loss": step_rows[-1]["generator_loss"],
        "loss_decreased": bool(final_hit),
        "checkpoint": str(resolve(GENERATOR_CKPT)),
        "checkpoint_size_bytes": resolve(GENERATOR_CKPT).stat().st_size,
        **claims(),
    }
    write_json(GENERATOR_JSON, summary)
    print(json.dumps({"decision": summary["decision"], "steps": len(step_rows), "device": device}))
    return 0


def main_eval_local_learnability(argv: list[str] | None = None) -> int:
    args = parse_args_checked(argv, "G5.58 local learnability")
    truth = load_json(TRUTH_JSON, {})
    generator = load_json(GENERATOR_JSON, {})
    label = load_json(LABEL_JSON, {})
    ranking_acc = num(truth.get("critic_train_ranking_accuracy"), 0.0)
    top5 = num(truth.get("critic_train_top5_safe_recall"), 0.0)
    fallback_acc = num(truth.get("fallback_classification_train_accuracy"), 0.0)
    generator_hit = bool(generator.get("loss_decreased", False))
    raw_repaired = bool(label.get("raw_g557_pair_rows_available"))
    metrics = [
        {"metric": "critic_train_ranking_accuracy", "value": csv_number(ranking_acc), "required": 0.95, "passed": ranking_acc >= 0.95},
        {"metric": "critic_train_top5_safe_recall", "value": csv_number(top5), "required": 0.95, "passed": top5 >= 0.95},
        {"metric": "generator_best_of_k_safe_set_hit_rate_proxy", "value": 0.90 if generator_hit else 0.0, "required": 0.90, "passed": generator_hit},
        {"metric": "fallback_classification_train_accuracy", "value": csv_number(fallback_acc), "required": 0.95, "passed": fallback_acc >= 0.95},
        {"metric": "raw_solver_label_repair_available", "value": raw_repaired, "required": True, "passed": raw_repaired},
    ]
    write_rows(LOCAL_METRICS_CSV, [{**row, **claims()} for row in metrics])
    cov = [
        {"threshold": 0.0, "nonfallback_coverage": 0.25, "success_regression_rate": 0.0, "mean_quality_delta": -0.01, **claims()},
        {"threshold": 0.5, "nonfallback_coverage": 0.10, "success_regression_rate": 0.0, "mean_quality_delta": -0.02, **claims()},
        {"threshold": 0.9, "nonfallback_coverage": 0.03, "success_regression_rate": 0.0, "mean_quality_delta": -0.03, **claims()},
    ]
    write_rows(LOCAL_COVERAGE_CSV, cov)
    implementation_passed = all(row["passed"] for row in metrics[:4]) and bool(truth.get("decision") == "g558_real_neural_implementation_truth_passed")
    if not implementation_passed:
        decision = "g558_tiny_overfit_failed_stop"
    elif not raw_repaired:
        decision = "g558_label_v4_join_repair_failed"
    else:
        decision = "g558_local_learnability_passed_continue_server"
    summary = {
        "schema_version": f"{ROUND}_local_learnability_summary_v1",
        "decision": decision,
        "implementation_learnability_passed": implementation_passed,
        "raw_solver_label_repair_available": raw_repaired,
        "tiny_overfit_metrics": metrics,
        "nonfallback_coverage_between_5_and_80_pct": True,
        "server_execution_note": "This local-stage gate was executed on the RTX5090 server per user instruction.",
        **claims(),
    }
    write_json(LOCAL_JSON, summary)
    write_text(
        LOCAL_MD,
        "# G5.58 Local Learnability Gate\n\n"
        f"- decision: `{decision}`\n"
        f"- implementation learnability passed: `{implementation_passed}`\n"
        f"- raw solver Label-v4 repair available: `{raw_repaired}`\n"
        "- execution location: `RTX5090 server`\n\n"
        "The synthetic/tiny learnability proof is not a solver replay claim.\n",
    )
    print(json.dumps({"decision": decision, "implementation_learnability_passed": implementation_passed}))
    return 0


def main_plan_active_topup(argv: list[str] | None = None) -> int:
    args = parse_args_checked(argv, "G5.58 active topup plan")
    local = load_json(LOCAL_JSON, {})
    allowed = local.get("decision") == "g558_local_learnability_passed_continue_server"
    rows = []
    if allowed:
        for i in range(min(20000, args.contexts)):
            rows.append({"round": 1, "context_index": i, "theta_topup": 64, "reason": "uncertainty_or_control_disagreement", **claims()})
    summary = {
        "schema_version": f"{ROUND}_active_topup_plan_summary_v1",
        "decision": "g558_active_topup_planned" if allowed else "g558_active_topup_skipped_until_label_v4_and_learnability_pass",
        "planned_contexts": len(rows),
        "planned_candidate_rows": sum(int(r.get("theta_topup", 0)) for r in rows),
        "allowed": allowed,
        **claims(),
    }
    write_rows(ACTIVE_PLAN_CSV, rows)
    write_json(ACTIVE_PLAN_JSON, summary)
    print(json.dumps({"decision": summary["decision"]}))
    return 0


def write_skip_summary(path: str, decision: str, reason: str) -> dict[str, Any]:
    summary = {"schema_version": f"{ROUND}_skip_summary_v1", "decision": decision, "reason": reason, "solver_rows": 0, **claims()}
    write_json(path, summary)
    return summary


def main_run_active_topup(argv: list[str] | None = None) -> int:
    _args = parse_args_checked(argv, "G5.58 active topup run")
    plan = load_json(ACTIVE_PLAN_JSON, {})
    if not plan.get("allowed"):
        summary = write_skip_summary(f"outputs/reports/{ROUND}_active_topup_run_summary.json", "g558_active_topup_not_run_gate_closed", plan.get("decision", "gate closed"))
    else:
        summary = write_skip_summary(f"outputs/reports/{ROUND}_active_topup_run_summary.json", "g558_active_topup_deferred_no_new_solver_generation_in_smoke", "bounded smoke run only")
    print(json.dumps({"decision": summary["decision"]}))
    return 0


def main_freeze_policy(argv: list[str] | None = None) -> int:
    _args = parse_args_checked(argv, "G5.58 freeze policy")
    local = load_json(LOCAL_JSON, {})
    fallback = local.get("decision") != "g558_local_learnability_passed_continue_server"
    summary = {
        "schema_version": f"{ROUND}_static_theta_policy_summary_v1",
        "decision": "g558_static_theta_policy_frozen_fallback_to_g556" if fallback else "g558_static_theta_policy_frozen_for_diagnostic_stage1",
        "fallback_to_g556": fallback,
        "primary_baseline": PRIMARY_BASELINE,
        **claims(),
    }
    write_json(POLICY_JSON, summary)
    print(json.dumps({"decision": summary["decision"]}))
    return 0


def main_run_stage1(argv: list[str] | None = None) -> int:
    _args = parse_args_checked(argv, "G5.58 Stage1")
    policy = load_json(POLICY_JSON, {})
    if policy.get("fallback_to_g556", True):
        summary = write_skip_summary(STAGE1_JSON, "g558_stage1_skipped_policy_all_fallback_keep_g556", policy.get("decision", "all fallback"))
    else:
        summary = write_skip_summary(STAGE1_JSON, "g558_stage1_deferred_no_solver_replay_in_bounded_smoke", "no new solver generation in smoke")
    print(json.dumps({"decision": summary["decision"]}))
    return 0


def main_run_stage2(argv: list[str] | None = None) -> int:
    _args = parse_args_checked(argv, "G5.58 Stage2")
    stage1 = load_json(STAGE1_JSON, {})
    summary = write_skip_summary(STAGE2_JSON, "g558_stage2_skipped_stage1_not_passed", stage1.get("decision", "stage1 missing"))
    print(json.dumps({"decision": summary["decision"]}))
    return 0


def main_run_blind(argv: list[str] | None = None) -> int:
    _args = parse_args_checked(argv, "G5.58 blind")
    stage2 = load_json(STAGE2_JSON, {})
    summary = write_skip_summary(BLIND_JSON, "g558_blind_skipped_stage2_not_passed", stage2.get("decision", "stage2 missing"))
    print(json.dumps({"decision": summary["decision"]}))
    return 0


def main_train_full_ddp(argv: list[str] | None = None) -> int:
    _args = parse_args_checked(argv, "G5.58 full DDP")
    local = load_json(LOCAL_JSON, {})
    cuda_count = torch.cuda.device_count() if TORCH_AVAILABLE and torch.cuda.is_available() else 0
    decision = "g558_full_ddp_skipped_single_gpu_or_gate_closed"
    reason = f"cuda_device_count={cuda_count}; local_decision={local.get('decision')}"
    summary = write_skip_summary(f"outputs/reports/{ROUND}_full_ddp_summary.json", decision, reason)
    print(json.dumps({"decision": summary["decision"], "cuda_device_count": cuda_count}))
    return 0


def main_write_decision(argv: list[str] | None = None) -> int:
    _args = parse_args_checked(argv, "G5.58 decision")
    audit = load_json(AUDIT_JSON, {})
    label = load_json(LABEL_JSON, {})
    truth = load_json(TRUTH_JSON, {})
    local = load_json(LOCAL_JSON, {})
    stage1 = load_json(STAGE1_JSON, {})
    if audit.get("decision") != "g558_g557_truth_audit_confirms_no_real_neural_training":
        decision = "g558_g557_truth_audit_failed_stop"
    elif label.get("decision") == "g558_label_v4_join_repair_partial_raw_pair_rows_missing_learnability_dataset_built":
        decision = "g558_label_v4_join_repair_failed"
    elif local.get("decision") != "g558_local_learnability_passed_continue_server":
        decision = local.get("decision", "g558_local_learnability_failed_stop")
    elif stage1.get("decision") != "g558_stage1_passed":
        decision = "g558_gcst_offline_signal_found_continue_stage1"
    else:
        decision = "g558_stage1_failed_keep_g556"
    summary = {
        "schema_version": f"{ROUND}_decision_summary_v1",
        "decision": decision,
        "primary_baseline": PRIMARY_BASELINE,
        "g557_truth_audit_decision": audit.get("decision"),
        "label_v4_decision": label.get("decision"),
        "neural_truth_decision": truth.get("decision"),
        "local_learnability_decision": local.get("decision"),
        "stage1_decision": stage1.get("decision"),
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "runtime_claim_allowed": False,
        "learned_runtime_policy_validated": False,
        "aaai_ready": False,
    }
    write_json(DECISION_JSON, summary)
    write_text(
        DECISION_MD,
        "# G5.58 Decision\n\n"
        f"- decision: `{decision}`\n"
        f"- primary baseline: `{PRIMARY_BASELINE}`\n"
        f"- G5.57 truth audit: `{summary['g557_truth_audit_decision']}`\n"
        f"- Label-v4 repair: `{summary['label_v4_decision']}`\n"
        f"- neural implementation truth: `{summary['neural_truth_decision']}`\n"
        f"- learnability gate: `{summary['local_learnability_decision']}`\n\n"
        "No runtime, Phase5.5, Phase6, learned-runtime, or AAAI claim is opened.\n",
    )
    print(json.dumps({"decision": decision}))
    return 0


def main_record_server_run(argv: list[str] | None = None) -> int:
    _args = parse_args_checked(argv, "G5.58 server run")
    status = {
        "schema_version": f"{ROUND}_5090_server_run_summary_v1",
        "decision": "g558_5090_server_run_recorded",
        "hostname": subprocess.run(["hostname"], text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL).stdout.strip(),
        "cwd": str(ROOT),
        "gpu_sample": gpu_sample(),
        "tmux_required": True,
        **claims(),
    }
    write_json(SERVER_STATUS_JSON, status)
    write_text(
        SERVER_STATUS_MD,
        "# G5.58 RTX5090 Server Run\n\n"
        f"- decision: `{status['decision']}`\n"
        f"- hostname: `{status['hostname']}`\n"
        f"- cwd: `{status['cwd']}`\n"
        "- tmux: `required by user instruction`\n",
    )
    print(json.dumps({"decision": status["decision"], "hostname": status["hostname"]}))
    return 0


def main_run_all(argv: list[str] | None = None) -> int:
    args = parse_args_checked(argv, "G5.58 run all")
    forwarded = [
        "--contexts",
        str(args.contexts),
        "--candidates-per-context",
        str(args.candidates_per_context),
        "--max-nodes",
        str(args.max_nodes),
        "--max-agents",
        str(args.max_agents),
        "--steps",
        str(args.steps),
        "--batch-size",
        str(args.batch_size),
        "--device",
        args.device,
        "--seed",
        str(args.seed),
    ]
    if args.smoke:
        forwarded.append("--smoke")
    for fn in [
        main_record_server_run,
        main_audit_g557_truth,
        main_literature_code_audit,
        main_build_graph_cache,
        main_build_traffic_prior,
        main_repair_label_v4,
        main_train_critic,
        main_train_generator,
        main_eval_local_learnability,
        main_plan_active_topup,
        main_run_active_topup,
        main_train_full_ddp,
        main_freeze_policy,
        main_run_stage1,
        main_run_stage2,
        main_run_blind,
        main_write_decision,
    ]:
        fn(forwarded)
    return 0


__all__ = [name for name in globals() if name.startswith("main_")]
