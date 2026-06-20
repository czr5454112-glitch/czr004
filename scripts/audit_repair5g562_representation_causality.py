from __future__ import annotations

import argparse
import csv
import json
import random
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from gcst.dual_stream_graph_actor import DualStreamGoalAwareActor  # noqa: E402
from gcst.goal_aware_actor import make_graph_batch, pad_od_tokens, scalar_features  # noqa: E402
from gcst.graph_data import GraphData  # noqa: E402
from gcst.graph_encoder import GraphBatch  # noqa: E402
from gcst.theta_schema import THETA_HI, THETA_LO  # noqa: E402
from train_repair5g562_real_label_actors import load_examples  # noqa: E402


ROUND = "phase5p5_repair5g562"
TABLE = ROOT / f"outputs/tables/{ROUND}_causal_representation_audit.csv"
SUMMARY = ROOT / f"outputs/reports/{ROUND}_causal_representation_summary.json"
ARCH = ROOT / f"outputs/tables/{ROUND}_architecture_matrix.csv"


def claims() -> dict[str, bool]:
    return {
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "runtime_claim_allowed": False,
        "learned_runtime_policy_validated": False,
        "aaai_ready": False,
    }


def read_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def number(value: Any, default: float = 999.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def boolish(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def write_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def graph_with_edges(graph: GraphData, edge_features: np.ndarray) -> GraphData:
    return GraphData(
        topology_id=graph.topology_id,
        map_name=graph.map_name,
        width=graph.width,
        height=graph.height,
        cells=graph.cells,
        node_features=graph.node_features,
        edge_index=graph.edge_index,
        edge_features=edge_features,
        hashes=graph.hashes,
        component_count=graph.component_count,
        physical_free_cell_count=graph.physical_free_cell_count,
    )


def zero_c0(graph: GraphData) -> GraphData:
    edge = graph.edge_features.copy()
    if edge.shape[1] >= 9:
        edge[:, 6:9] = 0.0
    return graph_with_edges(graph, edge)


def zero_f0(graph: GraphData) -> GraphData:
    edge = graph.edge_features.copy()
    if edge.shape[1] >= 6:
        edge[:, 5] = 0.0
    return graph_with_edges(graph, edge)


def permute_nodes(graph: GraphData, rng: random.Random) -> GraphData:
    n = len(graph.cells)
    perm = list(range(n))
    rng.shuffle(perm)
    inv = np.zeros((n,), dtype=np.int64)
    for new_idx, old_idx in enumerate(perm):
        inv[old_idx] = new_idx
    edge_index = inv[graph.edge_index] if graph.edge_index.size else graph.edge_index
    return GraphData(
        topology_id=graph.topology_id,
        map_name=graph.map_name,
        width=graph.width,
        height=graph.height,
        cells=[graph.cells[i] for i in perm],
        node_features=graph.node_features[perm],
        edge_index=edge_index,
        edge_features=graph.edge_features,
        hashes=graph.hashes,
        component_count=graph.component_count,
        physical_free_cell_count=graph.physical_free_cell_count,
    )


def shuffle_od(assignment: dict[str, Any], rng: random.Random) -> dict[str, Any]:
    out = dict(assignment)
    od = np.asarray(assignment.get("od_tokens"), dtype=np.float32).copy()
    if len(od) > 1:
        perm = list(range(len(od)))
        rng.shuffle(perm)
        od[:, 2:4] = od[perm, 2:4]
        od[:, 4] = np.abs(od[:, 0] - od[:, 2]) + np.abs(od[:, 1] - od[:, 3])
    out["od_tokens"] = od
    return out


def move_graph_batch(batch: GraphBatch, device: str) -> GraphBatch:
    return GraphBatch(batch.node_features.to(device), batch.edge_index.to(device), batch.edge_features.to(device), batch.batch_index.to(device), batch.num_graphs)


def selected_actor() -> dict[str, str]:
    rows = [row for row in read_rows(ARCH) if row.get("model_path") and str(row.get("rich_attention_actor", "")).lower() == "true"]
    if not rows:
        rows = [row for row in read_rows(ARCH) if row.get("model_path")]
    if not rows:
        raise SystemExit("no G5.62 actor checkpoint available")
    rows.sort(key=lambda row: (number(row.get("validation_real_label_normalized_l1")), str(row.get("variant_id")), str(row.get("seed"))))
    return rows[0]


def hidden_dim_from_checkpoint(checkpoint: dict[str, Any]) -> int:
    if checkpoint.get("hidden_dim"):
        return int(checkpoint["hidden_dim"])
    state = checkpoint.get("actor_state_dict", {})
    weight = state.get("scalar_encoder.0.weight")
    return int(weight.shape[0]) if weight is not None else 96


def predict(model: Any, examples: list[Any], graphs: list[GraphData], assignments: list[dict[str, Any]], device: str):
    import torch

    graph_batch = move_graph_batch(make_graph_batch(graphs), device)
    od_tokens, od_mask = pad_od_tokens(assignments)
    scalar_x = torch.tensor(np.stack([scalar_features(ex.context) for ex in examples]), dtype=torch.float32, device=device)
    with torch.no_grad():
        return model(graph_batch, od_tokens.to(device), od_mask.to(device), scalar_x).detach().cpu().numpy()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit G5.62 actor causal representation interventions.")
    parser.add_argument("--max-contexts", type=int, default=32)
    parser.add_argument("--device", default="auto")
    args = parser.parse_args(argv)

    import torch

    device = args.device if args.device != "auto" else ("cuda" if torch.cuda.is_available() else "cpu")
    actor_row = selected_actor()
    checkpoint = torch.load(ROOT / actor_row["model_path"], map_location=device, weights_only=False)
    model = DualStreamGoalAwareActor(
        hidden_dim=hidden_dim_from_checkpoint(checkpoint),
        scalar_only_control=boolish(checkpoint.get("scalar_only_control")),
        use_cross_attention=boolish(checkpoint.get("use_cross_attention")),
        safe_subspace=boolish(checkpoint.get("safe_subspace")),
        field_group_trust=boolish(checkpoint.get("field_group_trust")),
    ).module().to(device)
    model.load_state_dict(checkpoint["actor_state_dict"])
    model.eval()
    examples = load_examples(args.max_contexts)
    rng = random.Random(562)
    base_graphs = [ex.graph for ex in examples]
    base_assignments = [ex.assignment for ex in examples]
    base = predict(model, examples, base_graphs, base_assignments, device)
    repeat = predict(model, examples, base_graphs, base_assignments, device)
    interventions = {
        "repeat_noise_floor": (base_graphs, base_assignments, repeat),
        "paired_goal_shuffle": (base_graphs, [shuffle_od(ex.assignment, rng) for ex in examples], None),
        "zero_c0": ([zero_c0(ex.graph) for ex in examples], base_assignments, None),
        "zero_f0": ([zero_f0(ex.graph) for ex in examples], base_assignments, None),
        "node_order_permutation": ([permute_nodes(ex.graph, rng) for ex in examples], base_assignments, None),
    }
    span = np.maximum(np.asarray(THETA_HI - THETA_LO, dtype=np.float32), 1.0e-6)
    rows = []
    noise = float(np.mean(np.abs((base - repeat) / span)))
    for name, (graphs, assignments, precomputed) in interventions.items():
        pred = precomputed if precomputed is not None else predict(model, examples, graphs, assignments, device)
        delta = np.mean(np.abs((base - pred) / span), axis=1)
        rows.append(
            {
                "intervention": name,
                "contexts": len(examples),
                "normalized_theta_l1_mean": float(delta.mean()),
                "normalized_theta_l1_max": float(delta.max()),
                "noise_floor_multiple": float(delta.mean() / max(noise, 1.0e-9)),
                "exceeds_noise_floor_10x": float(delta.mean()) > max(noise * 10.0, 1.0e-8),
                "selected_variant_id": actor_row.get("variant_id", ""),
                "selected_seed": actor_row.get("seed", ""),
                **claims(),
            }
        )
    write_rows(TABLE, rows)
    changed = {row["intervention"]: boolish(row["exceeds_noise_floor_10x"]) for row in rows}
    summary = {
        "schema_version": f"{ROUND}_causal_representation_summary_v1",
        "decision": "g562_causal_representation_audit_completed",
        "selected_variant_id": actor_row.get("variant_id", ""),
        "selected_seed": actor_row.get("seed", ""),
        "contexts": len(examples),
        "noise_floor": noise,
        "paired_goal_shuffle_exceeds_noise_floor": changed.get("paired_goal_shuffle", False),
        "c0_intervention_exceeds_noise_floor": changed.get("zero_c0", False),
        "f0_intervention_exceeds_noise_floor": changed.get("zero_f0", False),
        "node_order_permutation_invariance_ok": not changed.get("node_order_permutation", False),
        **claims(),
    }
    SUMMARY.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
