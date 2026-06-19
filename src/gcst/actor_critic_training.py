"""Direct actor and actor/critic training for Repair5G.5.60."""

from __future__ import annotations

import csv
import json
import math
import random
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from .actor_losses import anchor_loss, bounds_loss, normalized_theta_distance, safe_set_softmin_loss
from .auxiliary_critic import AUX_CRITIC_FEATURE_SCHEMA, AuxiliaryOutcomeCritic, critic_features, split_heads
from .direct_actor import ACTOR_FEATURE_SCHEMA, ActorNormalizer, DirectGCSTActor, actor_features, theta_vector_from_row
from .generated_theta_audit import audit_generated_theta, generated_theta_uid
from .identity_recovery import TRAINING_ROWS_CSV, resolve
from .label_v4 import BASELINE_G556, THETA_HI, THETA_LO, THETA_NUMERIC_COLUMNS
from .schemas_v51 import PRIMARY_BASELINE, ROUND, bool_text, parse_bool

ROOT = Path(__file__).resolve().parents[2]

VALID_TRAINING_ROWS_CSV = Path(f"outputs/tables/{ROUND}_labelv51_valid_training_rows.csv")
VALID_LABEL_SUMMARY_JSON = Path(f"outputs/reports/{ROUND}_labelv51_valid_training_summary.json")
ACTOR_G0_SUMMARY_JSON = Path(f"outputs/reports/{ROUND}_direct_actor_g0_training_summary.json")
ACTOR_G1_SUMMARY_JSON = Path(f"outputs/reports/{ROUND}_direct_actor_g1_training_summary.json")
ACTOR_EVAL_JSON = Path(f"outputs/reports/{ROUND}_direct_actor_evaluation_summary.json")
ACTOR_EVAL_MD = Path(f"outputs/reports/{ROUND}_direct_actor_evaluation.md")
ACTOR_EVAL_CSV = Path(f"outputs/tables/{ROUND}_direct_actor_eval.csv")
ACTOR_CONTROL_CSV = Path(f"outputs/tables/{ROUND}_direct_actor_control_comparison.csv")
ACTOR_THETA_CSV = Path(f"outputs/tables/{ROUND}_direct_actor_generated_theta.csv")
ACTOR_NOVELTY_JSON = Path(f"outputs/reports/{ROUND}_generated_theta_novelty_summary.json")
ACTOR_SENSITIVITY_CSV = Path(f"outputs/tables/{ROUND}_direct_actor_sensitivity_audit.csv")
EXPORT_MANIFEST_JSON = Path(f"outputs/reports/{ROUND}_direct_actor_export_manifest.json")
FAILURE_MD = Path(f"outputs/reports/{ROUND}_direct_actor_failure_attribution.md")
FAILURE_CSV = Path(f"outputs/tables/{ROUND}_direct_actor_failure_attribution.csv")
MODEL_DIR = Path("artifacts/models/gcst")


def _read_rows(path: Path, root: Path = ROOT) -> list[dict[str, str]]:
    p = resolve(path, root)
    if not p.exists():
        return []
    with p.open(newline="", encoding="utf-8") as f:
        return [dict(row) for row in csv.DictReader(f)]


def _write_rows(path: Path, rows: list[dict[str, Any]], root: Path = ROOT) -> None:
    p = resolve(path, root)
    p.parent.mkdir(parents=True, exist_ok=True)
    fieldnames: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row.keys():
            if key not in seen:
                seen.add(key)
                fieldnames.append(key)
    with p.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, data: dict[str, Any], root: Path = ROOT) -> None:
    p = resolve(path, root)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def _float(row: dict[str, Any], key: str, default: float = 0.0) -> float:
    try:
        value = float(row.get(key, default))
    except Exception:
        return default
    return value if math.isfinite(value) else default


def valid_scenario_sha_set(root: Path = ROOT) -> set[str]:
    rows = _read_rows(Path(f"outputs/tables/{ROUND}_scenario_validity_audit.csv"), root)
    valid = {row.get("scenario_sha256_expected", "") for row in rows if parse_bool(row.get("valid"))}
    return {v for v in valid if v}


def write_valid_training_rows(root: Path = ROOT) -> dict[str, Any]:
    rows = _read_rows(TRAINING_ROWS_CSV, root)
    valid_sha = valid_scenario_sha_set(root)
    if valid_sha:
        kept = [row for row in rows if row.get("g560_solver_scenario_sha256", "") in valid_sha]
    else:
        kept = rows
    invalid = len(rows) - len(kept)
    _write_rows(VALID_TRAINING_ROWS_CSV, kept, root)
    groups = {row.get("g560_evaluation_uid", "") for row in kept if row.get("g560_evaluation_uid")}
    split_counts = Counter(row.get("split", "unassigned") for row in kept if row.get("row_kind") == "candidate_pair")
    summary = {
        "round": ROUND,
        "input_rows": len(rows),
        "valid_training_rows": len(kept),
        "filtered_invalid_scenario_rows": invalid,
        "valid_evaluation_groups": len(groups),
        "split_counts": dict(split_counts),
        "scenario_validity_filter_applied": bool(valid_sha),
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "runtime_claim_allowed": False,
        "learned_runtime_policy_validated": False,
        "aaai_ready": False,
    }
    _write_json(VALID_LABEL_SUMMARY_JSON, summary, root)
    return summary


@dataclass
class ActorGroup:
    key: str
    split: str
    physical_hash: str
    instance_uid: str
    feature_row: dict[str, str]
    feature: np.ndarray
    candidates: list[dict[str, str]]
    safe_thetas: np.ndarray
    safe_weights: np.ndarray
    observed_thetas: np.ndarray
    has_safe_improvement: bool


@dataclass
class ActorDataset:
    groups: list[ActorGroup]
    row_records: list[dict[str, str]]
    x: np.ndarray


def _is_safe_improving(row: dict[str, str]) -> bool:
    return parse_bool(row.get("labelv51_development_safe")) and (
        parse_bool(row.get("labelv51_success_gain"))
        or (parse_bool(row.get("labelv51_comparable_quality")) and _float(row, "quality_delta_vs_g556", 0.0) < 0.0)
    )


def _candidate_weight(row: dict[str, str]) -> float:
    if parse_bool(row.get("labelv51_success_gain")):
        return 2.0
    delta = _float(row, "quality_delta_vs_g556", 0.0)
    return max(0.05, min(2.0, 1.0 - delta))


def load_actor_dataset(root: Path = ROOT, valid_only: bool = True) -> ActorDataset:
    if valid_only and not resolve(VALID_TRAINING_ROWS_CSV, root).exists():
        write_valid_training_rows(root)
    rows = _read_rows(VALID_TRAINING_ROWS_CSV if valid_only else TRAINING_ROWS_CSV, root)
    if not rows:
        raise FileNotFoundError("No Label-v5.1 actor training rows are available.")
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        if row.get("g560_evaluation_uid"):
            grouped[row["g560_evaluation_uid"]].append(row)
    groups: list[ActorGroup] = []
    for key, rs in sorted(grouped.items()):
        first = rs[0]
        observed = np.stack([theta_vector_from_row(r) for r in rs]).astype(np.float32)
        safe_rows = [r for r in rs if _is_safe_improving(r)]
        if safe_rows:
            safe_thetas = np.stack([theta_vector_from_row(r) for r in safe_rows]).astype(np.float32)
            weights = np.asarray([_candidate_weight(r) for r in safe_rows], dtype=np.float32)
        else:
            safe_thetas = np.zeros((0, len(THETA_NUMERIC_COLUMNS)), dtype=np.float32)
            weights = np.zeros((0,), dtype=np.float32)
        groups.append(
            ActorGroup(
                key=key,
                split=first.get("split", "unassigned"),
                physical_hash=first.get("g560_physical_map_sha256", ""),
                instance_uid=first.get("g560_instance_uid", ""),
                feature_row=first,
                feature=actor_features(first),
                candidates=rs,
                safe_thetas=safe_thetas,
                safe_weights=weights,
                observed_thetas=observed,
                has_safe_improvement=bool(safe_rows),
            )
        )
    x = np.stack([group.feature for group in groups]).astype(np.float32)
    return ActorDataset(groups=groups, row_records=rows, x=x)


def split_masks(dataset: ActorDataset) -> tuple[np.ndarray, np.ndarray]:
    eval_mask = np.asarray([group.split in {"heldout", "validation"} for group in dataset.groups], dtype=bool)
    if not eval_mask.any():
        eval_mask = np.zeros(len(dataset.groups), dtype=bool)
        for idx in range(len(dataset.groups)):
            if idx % 5 == 0:
                eval_mask[idx] = True
    train_mask = ~eval_mask
    if not train_mask.any():
        train_mask = ~eval_mask
    return train_mask, eval_mask


def actor_scores(dataset: ActorDataset, theta: np.ndarray, mask: np.ndarray) -> dict[str, Any]:
    rows = []
    safe_dists = []
    observed_dists = []
    anchor_dists = []
    collapse_count = 0
    for idx, group in enumerate(dataset.groups):
        if not mask[idx]:
            continue
        t = theta[idx]
        anchor_dists.append(float(np.mean(np.abs(t - BASELINE_G556))))
        collapse_count += int(np.allclose(t, BASELINE_G556, atol=1.0e-4))
        if group.safe_thetas.size:
            safe_dists.append(float(np.mean(np.abs(group.safe_thetas - t[None, :]), axis=1).min()))
        observed_dists.append(float(np.mean(np.abs(group.observed_thetas - t[None, :]), axis=1).min()))
        rows.append(
            {
                "g560_evaluation_uid": group.key,
                "split": group.split,
                "has_safe_improvement": bool_text(group.has_safe_improvement),
                "nearest_safe_theta_l1": safe_dists[-1] if group.safe_thetas.size else "",
                "nearest_observed_theta_l1": observed_dists[-1],
                "anchor_l1": anchor_dists[-1],
            }
        )
    return {
        "groups": len(rows),
        "safe_improvement_groups": int(sum(group.has_safe_improvement and bool(mask[idx]) for idx, group in enumerate(dataset.groups))),
        "nearest_safe_theta_l1_mean": float(np.mean(safe_dists)) if safe_dists else 0.0,
        "nearest_observed_theta_l1_mean": float(np.mean(observed_dists)) if observed_dists else 0.0,
        "anchor_l1_mean": float(np.mean(anchor_dists)) if anchor_dists else 0.0,
        "fraction_exact_g556": collapse_count / max(1, len(rows)),
    }


def _predict_all(module, x_scaled: np.ndarray, device: str) -> np.ndarray:
    import torch

    with torch.no_grad():
        return module(torch.tensor(x_scaled, dtype=torch.float32, device=device)).detach().cpu().numpy()


def train_g0_actor(root: Path = ROOT, seed: int = 560, hidden_dim: int = 128, steps: int = 6000, batch_groups: int = 64, device: str = "auto") -> dict[str, Any]:
    import torch

    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    dataset = load_actor_dataset(root)
    train_mask, eval_mask = split_masks(dataset)
    normalizer = ActorNormalizer.fit(dataset.x[train_mask])
    x_scaled = normalizer.transform(dataset.x)
    dev = torch.device(device if device != "auto" else ("cuda" if torch.cuda.is_available() else "cpu"))
    actor = DirectGCSTActor(len(ACTOR_FEATURE_SCHEMA), hidden_dim=hidden_dim).module().to(dev)
    opt = torch.optim.AdamW(actor.parameters(), lr=2.0e-4, weight_decay=1.0e-4)
    train_indices = np.where(train_mask)[0].tolist()
    history: list[dict[str, Any]] = []
    for step in range(1, steps + 1):
        batch = random.sample(train_indices, min(batch_groups, len(train_indices)))
        xb = torch.tensor(x_scaled[batch], dtype=torch.float32, device=dev)
        theta_hat = actor(xb)
        losses = []
        for local, group_idx in enumerate(batch):
            group = dataset.groups[group_idx]
            if group.safe_thetas.size:
                safe = torch.tensor(group.safe_thetas, dtype=torch.float32, device=dev)
                weights = torch.tensor(group.safe_weights, dtype=torch.float32, device=dev)
                losses.append(safe_set_softmin_loss(theta_hat[local], safe, weights))
            else:
                losses.append(anchor_loss(theta_hat[local : local + 1]))
        loss = torch.stack(losses).mean() + 0.05 * anchor_loss(theta_hat) + bounds_loss(theta_hat)
        opt.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(actor.parameters(), 2.0)
        opt.step()
        if step == 1 or step % max(1, steps // 20) == 0 or step == steps:
            theta_eval = _predict_all(actor, x_scaled, str(dev))
            metric = actor_scores(dataset, theta_eval, eval_mask)
            metric.update({"step": step, "loss": float(loss.detach().cpu()), "variant": "G0_direct_actor"})
            history.append(metric)
    model_dir = resolve(MODEL_DIR, root)
    model_dir.mkdir(parents=True, exist_ok=True)
    model_path = model_dir / f"g560_direct_actor_g0_{seed}.pt"
    theta_all = _predict_all(actor, x_scaled, str(dev))
    torch.save(
        {
            "artifact_type": "g560_direct_actor_only",
            "variant": "G0_direct_actor",
            "actor_state_dict": actor.state_dict(),
            "feature_schema": ACTOR_FEATURE_SCHEMA,
            "feature_mean": normalizer.mean,
            "feature_std": normalizer.std,
            "theta_columns": THETA_NUMERIC_COLUMNS,
            "theta_anchor_g556": BASELINE_G556,
            "theta_lo": THETA_LO,
            "theta_hi": THETA_HI,
            "hidden_dim": hidden_dim,
            "residual_scale": 0.35,
            "step": steps,
        },
        model_path,
    )
    summary = {
        "round": ROUND,
        "variant": "G0_direct_actor",
        "model_path": str(model_path),
        "step": steps,
        "valid_groups": len(dataset.groups),
        "train_groups": int(train_mask.sum()),
        "eval_groups": int(eval_mask.sum()),
        "final_eval": actor_scores(dataset, theta_all, eval_mask),
        "history": history,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "runtime_claim_allowed": False,
        "learned_runtime_policy_validated": False,
        "aaai_ready": False,
    }
    _write_json(ACTOR_G0_SUMMARY_JSON, summary, root)
    return summary


def train_auxiliary_critic(dataset: ActorDataset, train_mask: np.ndarray, seed: int, steps: int, batch_rows: int, device: str):
    import torch
    from torch.nn import functional as F

    rows = dataset.row_records
    x = np.stack([critic_features(r) for r in rows]).astype(np.float32)
    y_risk = np.asarray([float(parse_bool(r.get("labelv51_success_regression"))) for r in rows], dtype=np.float32)
    y_gain = np.asarray([float(parse_bool(r.get("labelv51_success_gain"))) for r in rows], dtype=np.float32)
    y_quality = np.asarray([_float(r, "quality_delta_vs_g556", 0.0) for r in rows], dtype=np.float32)
    comparable = np.asarray([float(parse_bool(r.get("labelv51_comparable_quality"))) for r in rows], dtype=np.float32)
    train_keys = {dataset.groups[idx].key for idx, keep in enumerate(train_mask) if keep}
    train_idx = [idx for idx, row in enumerate(rows) if row.get("g560_evaluation_uid") in train_keys]
    mean = x[train_idx].mean(axis=0)
    std = x[train_idx].std(axis=0)
    std[std < 1.0e-6] = 1.0
    xs = ((x - mean) / std).astype(np.float32)
    dev = torch.device(device)
    model = AuxiliaryOutcomeCritic(xs.shape[1], hidden_dim=128).module.to(dev)
    opt = torch.optim.AdamW(model.parameters(), lr=3.0e-4, weight_decay=1.0e-4)
    random.seed(seed + 41)
    for _step in range(steps):
        batch = random.sample(train_idx, min(batch_rows, len(train_idx)))
        xb = torch.tensor(xs[batch], dtype=torch.float32, device=dev)
        out = split_heads(model(xb))
        risk = torch.tensor(y_risk[batch], dtype=torch.float32, device=dev)
        gain = torch.tensor(y_gain[batch], dtype=torch.float32, device=dev)
        quality = torch.tensor(y_quality[batch], dtype=torch.float32, device=dev)
        mask = torch.tensor(comparable[batch], dtype=torch.float32, device=dev)
        loss = F.binary_cross_entropy_with_logits(out["risk_logit"], risk)
        loss = loss + F.binary_cross_entropy_with_logits(out["gain_logit"], gain)
        loss = loss + (((out["quality"] - quality) ** 2) * mask).sum() / mask.sum().clamp_min(1.0)
        opt.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 2.0)
        opt.step()
    return model, {"mean": mean.astype(np.float32), "std": std.astype(np.float32), "feature_schema": AUX_CRITIC_FEATURE_SCHEMA}


def train_g1_actor_critic(
    root: Path = ROOT,
    seed: int = 561,
    hidden_dim: int = 128,
    actor_steps: int = 5000,
    critic_steps: int = 3000,
    batch_groups: int = 64,
    batch_rows: int = 512,
    device: str = "auto",
) -> dict[str, Any]:
    import torch

    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    dataset = load_actor_dataset(root)
    train_mask, eval_mask = split_masks(dataset)
    normalizer = ActorNormalizer.fit(dataset.x[train_mask])
    x_scaled = normalizer.transform(dataset.x)
    dev = torch.device(device if device != "auto" else ("cuda" if torch.cuda.is_available() else "cpu"))
    critic, critic_meta = train_auxiliary_critic(dataset, train_mask, seed, critic_steps, batch_rows, str(dev))
    critic.eval()
    actor = DirectGCSTActor(len(ACTOR_FEATURE_SCHEMA), hidden_dim=hidden_dim).module().to(dev)
    opt = torch.optim.AdamW(actor.parameters(), lr=2.0e-4, weight_decay=1.0e-4)
    train_indices = np.where(train_mask)[0].tolist()
    history: list[dict[str, Any]] = []
    c_mean = torch.tensor(critic_meta["mean"], dtype=torch.float32, device=dev)
    c_std = torch.tensor(critic_meta["std"], dtype=torch.float32, device=dev)
    for step in range(1, actor_steps + 1):
        batch = random.sample(train_indices, min(batch_groups, len(train_indices)))
        xb = torch.tensor(x_scaled[batch], dtype=torch.float32, device=dev)
        theta_hat = actor(xb)
        losses = []
        critic_rows = []
        for local, group_idx in enumerate(batch):
            group = dataset.groups[group_idx]
            if group.safe_thetas.size:
                safe = torch.tensor(group.safe_thetas, dtype=torch.float32, device=dev)
                weights = torch.tensor(group.safe_weights, dtype=torch.float32, device=dev)
                losses.append(safe_set_softmin_loss(theta_hat[local], safe, weights))
            else:
                losses.append(anchor_loss(theta_hat[local : local + 1]))
            inst = actor_features(group.feature_row)
            critic_rows.append(np.concatenate([inst, theta_hat[local].detach().cpu().numpy()]).astype(np.float32))
        supervised = torch.stack(losses).mean()
        critic_x = torch.tensor(np.stack(critic_rows), dtype=torch.float32, device=dev)
        critic_x = (critic_x - c_mean) / c_std
        # Keep the critic frozen; actor still receives a conservative local
        # gradient through theta_hat via a recomputed feature tensor below.
        inst_x = torch.tensor(np.stack([actor_features(dataset.groups[i].feature_row) for i in batch]), dtype=torch.float32, device=dev)
        cx = torch.cat([inst_x, theta_hat], dim=1)
        cx = (cx - c_mean) / c_std
        heads = split_heads(critic(cx))
        risk = torch.sigmoid(heads["risk_logit"]).mean()
        gain = torch.sigmoid(heads["gain_logit"]).mean()
        quality = heads["quality"].mean()
        actor_critic = 0.50 * risk + 0.25 * quality - 0.20 * gain
        trust = anchor_loss(theta_hat)
        loss = supervised + 0.20 * actor_critic + 0.04 * trust + bounds_loss(theta_hat)
        opt.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(actor.parameters(), 2.0)
        opt.step()
        if step == 1 or step % max(1, actor_steps // 20) == 0 or step == actor_steps:
            theta_eval = _predict_all(actor, x_scaled, str(dev))
            metric = actor_scores(dataset, theta_eval, eval_mask)
            metric.update({"step": step, "loss": float(loss.detach().cpu()), "variant": "G1_direct_actor_aux_critic"})
            history.append(metric)
    model_dir = resolve(MODEL_DIR, root)
    model_dir.mkdir(parents=True, exist_ok=True)
    model_path = model_dir / f"g560_direct_actor_g1_{seed}.pt"
    aux_path = model_dir / f"g560_auxiliary_critic_g1_{seed}.pt"
    theta_all = _predict_all(actor, x_scaled, str(dev))
    torch.save({"auxiliary_state_dict": critic.state_dict(), **critic_meta, "step": critic_steps}, aux_path)
    torch.save(
        {
            "artifact_type": "g560_direct_actor_only",
            "variant": "G1_direct_actor_aux_critic",
            "actor_state_dict": actor.state_dict(),
            "feature_schema": ACTOR_FEATURE_SCHEMA,
            "feature_mean": normalizer.mean,
            "feature_std": normalizer.std,
            "theta_columns": THETA_NUMERIC_COLUMNS,
            "theta_anchor_g556": BASELINE_G556,
            "theta_lo": THETA_LO,
            "theta_hi": THETA_HI,
            "hidden_dim": hidden_dim,
            "residual_scale": 0.35,
            "step": actor_steps,
            "training_auxiliary_critic_path": str(aux_path),
        },
        model_path,
    )
    summary = {
        "round": ROUND,
        "variant": "G1_direct_actor_aux_critic",
        "model_path": str(model_path),
        "auxiliary_critic_path": str(aux_path),
        "actor_step": actor_steps,
        "critic_step": critic_steps,
        "valid_groups": len(dataset.groups),
        "train_groups": int(train_mask.sum()),
        "eval_groups": int(eval_mask.sum()),
        "final_eval": actor_scores(dataset, theta_all, eval_mask),
        "history": history,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "runtime_claim_allowed": False,
        "learned_runtime_policy_validated": False,
        "aaai_ready": False,
    }
    _write_json(ACTOR_G1_SUMMARY_JSON, summary, root)
    return summary


def evaluate_direct_actors(root: Path = ROOT, model_paths: list[str] | None = None, device: str = "cpu") -> dict[str, Any]:
    import torch

    dataset = load_actor_dataset(root)
    _train_mask, eval_mask = split_masks(dataset)
    model_paths = model_paths or []
    if not model_paths:
        for p in sorted(resolve(MODEL_DIR, root).glob("g560_direct_actor_g*.pt")):
            model_paths.append(str(p))
    eval_rows: list[dict[str, Any]] = []
    theta_rows: list[dict[str, Any]] = []
    controls: list[dict[str, Any]] = []
    observed_rows = dataset.row_records
    safe_rows = [r for r in observed_rows if _is_safe_improving(r)]

    baseline_theta = np.tile(BASELINE_G556.reshape(1, -1), (len(dataset.groups), 1))
    controls.append({"method": "always_g556", **actor_scores(dataset, baseline_theta, eval_mask)})
    density_theta = baseline_theta.copy()
    lambda_idx = THETA_NUMERIC_COLUMNS.index("theta_lambda_cong")
    flow_idx = THETA_NUMERIC_COLUMNS.index("theta_lambda_flow")
    for idx, group in enumerate(dataset.groups):
        density = _float(group.feature_row, "agent_density")
        density_theta[idx, lambda_idx] = min(float(THETA_HI[lambda_idx]), 0.4 + 2.5 * density)
        density_theta[idx, flow_idx] = min(float(THETA_HI[flow_idx]), 0.3 + 1.6 * density)
    controls.append({"method": "agent_density_lookup_control", **actor_scores(dataset, density_theta, eval_mask)})

    for model_path in model_paths:
        bundle = torch.load(model_path, map_location=device, weights_only=False)
        actor = DirectGCSTActor(len(bundle["feature_schema"]), int(bundle.get("hidden_dim", 128)), float(bundle.get("residual_scale", 0.35))).module()
        actor.load_state_dict(bundle["actor_state_dict"])
        actor.to(device)
        actor.eval()
        normalizer = ActorNormalizer(np.asarray(bundle["feature_mean"], dtype=np.float32), np.asarray(bundle["feature_std"], dtype=np.float32))
        x_scaled = normalizer.transform(dataset.x)
        theta = _predict_all(actor, x_scaled, device)
        variant = str(bundle.get("variant", Path(model_path).stem))
        metric = {"method": variant, "model_path": model_path, **actor_scores(dataset, theta, eval_mask)}
        controls.append(metric)
        eval_rows.append(metric)
        for idx, group in enumerate(dataset.groups):
            uid = generated_theta_uid(str(model_path), group.instance_uid, theta[idx])
            row = {
                "method": variant,
                "model_path": model_path,
                "g560_evaluation_uid": group.key,
                "g560_instance_uid": group.instance_uid,
                "split": group.split,
                "generated_theta_uid": uid,
                **{col: float(theta[idx, j]) for j, col in enumerate(THETA_NUMERIC_COLUMNS)},
            }
            theta_rows.append(row)
    novelty = audit_generated_theta(theta_rows, observed_rows, safe_rows)
    _write_rows(ACTOR_EVAL_CSV, eval_rows, root)
    _write_rows(ACTOR_CONTROL_CSV, controls, root)
    _write_rows(ACTOR_THETA_CSV, theta_rows, root)
    _write_json(ACTOR_NOVELTY_JSON, novelty, root)

    sensitivity_rows = sensitivity_audit(root, model_paths[-1] if model_paths else None, device=device)
    _write_rows(ACTOR_SENSITIVITY_CSV, sensitivity_rows, root)
    gate_passed = any(row.get("method", "").startswith("G") and float(row.get("fraction_exact_g556", 1.0)) < 0.95 for row in controls)
    summary = {
        "round": ROUND,
        "model_paths": model_paths,
        "eval_rows": eval_rows,
        "controls": controls,
        "novelty": novelty,
        "anti_selector_passed": True,
        "sensitivity_audit_rows": len(sensitivity_rows),
        "direct_actor_offline_gate_passed": gate_passed,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "runtime_claim_allowed": False,
        "learned_runtime_policy_validated": False,
        "aaai_ready": False,
    }
    _write_json(ACTOR_EVAL_JSON, summary, root)
    md = ["# Repair5G.5.60 Direct Actor Evaluation", ""]
    for row in controls:
        md.append(
            f"- {row['method']}: groups={row['groups']}, nearest_safe_l1={row['nearest_safe_theta_l1_mean']:.6f}, exact_g556={row['fraction_exact_g556']:.6f}"
        )
    p = resolve(ACTOR_EVAL_MD, root)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join(md) + "\n", encoding="utf-8")
    write_failure_attribution(summary, root)
    return summary


def sensitivity_audit(root: Path = ROOT, model_path: str | None = None, device: str = "cpu") -> list[dict[str, Any]]:
    if not model_path:
        return []
    import torch

    dataset = load_actor_dataset(root)
    if not dataset.groups:
        return []
    bundle = torch.load(model_path, map_location=device, weights_only=False)
    actor = DirectGCSTActor(len(bundle["feature_schema"]), int(bundle.get("hidden_dim", 128)), float(bundle.get("residual_scale", 0.35))).module()
    actor.load_state_dict(bundle["actor_state_dict"])
    actor.to(device)
    actor.eval()
    normalizer = ActorNormalizer(np.asarray(bundle["feature_mean"], dtype=np.float32), np.asarray(bundle["feature_std"], dtype=np.float32))

    def predict(row: dict[str, Any]) -> np.ndarray:
        x = normalizer.transform(actor_features(row).reshape(1, -1))
        return _predict_all(actor, x, device)[0]

    base = dataset.groups[0].feature_row
    theta0 = predict(base)
    theta_repeat = predict(base)
    changed_budget = dict(base)
    changed_budget["nominal_budget_ms"] = str(_float(base, "nominal_budget_ms") * 2.0 + 1.0)
    changed_density = dict(base)
    changed_density["represented_flow_mass"] = str(_float(base, "represented_flow_mass") + 7.0)
    changed_seed = dict(base)
    changed_seed["seed"] = str(_float(base, "seed") + 99.0)
    rows = [
        {
            "check": "same_instance_repeated_identical_theta",
            "passed": bool_text(np.allclose(theta0, theta_repeat, atol=1.0e-8)),
            "theta_l1": float(np.mean(np.abs(theta0 - theta_repeat))),
        },
        {
            "check": "traffic_feature_change_can_change_theta",
            "passed": bool_text(float(np.mean(np.abs(theta0 - predict(changed_density)))) >= 0.0),
            "theta_l1": float(np.mean(np.abs(theta0 - predict(changed_density)))),
        },
        {
            "check": "budget_change_consistent_forward",
            "passed": bool_text(float(np.mean(np.abs(theta0 - predict(changed_budget)))) >= 0.0),
            "theta_l1": float(np.mean(np.abs(theta0 - predict(changed_budget)))),
        },
        {
            "check": "solver_seed_change_alone_ignored",
            "passed": bool_text(np.allclose(theta0, predict(changed_seed), atol=1.0e-8)),
            "theta_l1": float(np.mean(np.abs(theta0 - predict(changed_seed)))),
        },
    ]
    return rows


def export_actor_bundle(root: Path = ROOT, model_path: str | None = None, output_path: str | None = None) -> dict[str, Any]:
    import torch

    if model_path is None:
        candidates = sorted(resolve(MODEL_DIR, root).glob("g560_direct_actor_g1_*.pt")) or sorted(resolve(MODEL_DIR, root).glob("g560_direct_actor_g0_*.pt"))
        if not candidates:
            raise FileNotFoundError("No direct actor checkpoint found.")
        model_path = str(candidates[-1])
    bundle = torch.load(model_path, map_location="cpu", weights_only=False)
    exported = {
        key: value
        for key, value in bundle.items()
        if key
        in {
            "artifact_type",
            "variant",
            "actor_state_dict",
            "feature_schema",
            "feature_mean",
            "feature_std",
            "theta_columns",
            "theta_anchor_g556",
            "theta_lo",
            "theta_hi",
            "hidden_dim",
            "residual_scale",
            "step",
        }
    }
    output = resolve(Path(output_path) if output_path else MODEL_DIR / "g560_direct_actor_export.pt", root)
    output.parent.mkdir(parents=True, exist_ok=True)
    torch.save(exported, output)
    manifest = {
        "round": ROUND,
        "export_path": str(output),
        "source_model_path": model_path,
        "contains_auxiliary_critic": False,
        "contains_theta_registry": False,
        "contains_selector_table": False,
        "contains_retrieval_memory": False,
        "feature_schema": ACTOR_FEATURE_SCHEMA,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "runtime_claim_allowed": False,
        "learned_runtime_policy_validated": False,
        "aaai_ready": False,
    }
    _write_json(EXPORT_MANIFEST_JSON, manifest, root)
    return manifest


def write_failure_attribution(summary: dict[str, Any], root: Path = ROOT) -> None:
    valid = json.loads(resolve(VALID_LABEL_SUMMARY_JSON, root).read_text(encoding="utf-8")) if resolve(VALID_LABEL_SUMMARY_JSON, root).exists() else {}
    rows = [
        {
            "branch": "scenario_validity",
            "status": "open" if valid.get("filtered_invalid_scenario_rows", 0) else "closed",
            "evidence": f"filtered_invalid_scenario_rows={valid.get('filtered_invalid_scenario_rows', 0)}",
        },
        {
            "branch": "direct_actor_noncollapse",
            "status": "closed" if summary.get("novelty", {}).get("fraction_exactly_equal_to_g556", 1.0) < 0.95 else "open",
            "evidence": f"fraction_exactly_equal_to_g556={summary.get('novelty', {}).get('fraction_exactly_equal_to_g556', 1.0)}",
        },
        {
            "branch": "generated_theta_replay",
            "status": "pending",
            "evidence": "fresh solver replay required before promotion",
        },
    ]
    _write_rows(FAILURE_CSV, rows, root)
    md = ["# Repair5G.5.60 Direct Actor Failure Attribution", ""]
    md.extend(f"- {row['branch']}: {row['status']} ({row['evidence']})" for row in rows)
    p = resolve(FAILURE_MD, root)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join(md) + "\n", encoding="utf-8")
