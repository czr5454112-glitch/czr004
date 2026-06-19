"""Real Label-v5.1 codebook critic training and evaluation for G5.60."""

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

from .identity_recovery import JOIN_AUDIT_CSV, TRAINING_ROWS_CSV, resolve
from .label_v4 import BASELINE_G556, THETA_HI, THETA_LO, THETA_NUMERIC_COLUMNS
from .schemas_v51 import PRIMARY_BASELINE, ROUND, bool_text, parse_bool

ROOT = Path(__file__).resolve().parents[2]

MODEL_DIR = Path("artifacts/models/gcst")
TRAINING_SUMMARY_JSON = Path(f"outputs/reports/{ROUND}_codebook_critic_training_summary.json")
EVAL_MD = Path(f"outputs/reports/{ROUND}_codebook_critic_evaluation.md")
EVAL_JSON = Path(f"outputs/reports/{ROUND}_codebook_critic_evaluation_summary.json")
EPOCH_METRICS_CSV = Path(f"outputs/tables/{ROUND}_codebook_critic_epoch_metrics.csv")
FOLD_METRICS_CSV = Path(f"outputs/tables/{ROUND}_codebook_critic_fold_metrics.csv")
SELECTOR_EVAL_CSV = Path(f"outputs/tables/{ROUND}_selector_eval.csv")
ORACLE_MD = Path(f"outputs/reports/{ROUND}_oracle_opportunity.md")
ORACLE_JSON = Path(f"outputs/reports/{ROUND}_oracle_opportunity_summary.json")
CANDIDATE_AUDIT_CSV = Path(f"outputs/tables/{ROUND}_candidate_space_audit.csv")
FAILURE_ATTRIBUTION_CSV = Path(f"outputs/tables/{ROUND}_failure_attribution.csv")
FAILURE_ATTRIBUTION_MD = Path(f"outputs/reports/{ROUND}_failure_attribution.md")
DECISION_MD = Path(f"outputs/reports/{ROUND}_decision.md")
DECISION_JSON = Path(f"outputs/reports/{ROUND}_decision_summary.json")

INSTANCE_FEATURES = [
    "agent_count",
    "nominal_budget_ms",
    "requested_agent_count",
    "physical_free_cell_count",
    "agent_density",
    "encoded_OD_token_count",
    "represented_agent_mass",
    "represented_flow_mass",
    "path_found_rate",
    "base_time_limit_sec",
    "ltm_max_iterations",
]
BOOL_FEATURES = ["nonzero_flow"]
FEATURE_SCHEMA = INSTANCE_FEATURES + BOOL_FEATURES + THETA_NUMERIC_COLUMNS + [f"delta_{col}" for col in THETA_NUMERIC_COLUMNS]


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


def featurize(row: dict[str, Any]) -> np.ndarray:
    values: list[float] = []
    for col in INSTANCE_FEATURES:
        values.append(_float(row, col))
    for col in BOOL_FEATURES:
        values.append(float(parse_bool(row.get(col))))
    for col in THETA_NUMERIC_COLUMNS:
        values.append(_float(row, col, float(BASELINE_G556[THETA_NUMERIC_COLUMNS.index(col)])))
    for idx, col in enumerate(THETA_NUMERIC_COLUMNS):
        values.append(_float(row, col, float(BASELINE_G556[idx])) - float(BASELINE_G556[idx]))
    return np.asarray(values, dtype=np.float32)


@dataclass
class Dataset:
    rows: list[dict[str, str]]
    x: np.ndarray
    y: np.ndarray
    safe: np.ndarray
    gain: np.ndarray
    regression: np.ndarray
    comparable: np.ndarray
    quality_delta: np.ndarray
    group_keys: np.ndarray
    physical_hashes: np.ndarray


def load_dataset(root: Path = ROOT, training_rows_path: Path = TRAINING_ROWS_CSV) -> Dataset:
    rows = _read_rows(training_rows_path, root)
    rows = [r for r in rows if r.get("row_kind") in {"candidate_pair", "baseline_pseudo_candidate"}]
    if not rows:
        raise FileNotFoundError(f"No Label-v5.1 training rows found at {resolve(training_rows_path, root)}")
    x = np.stack([featurize(r) for r in rows]).astype(np.float32)
    y = np.asarray([_float(r, "labelv51_target_utility") for r in rows], dtype=np.float32)
    safe = np.asarray([float(parse_bool(r.get("labelv51_development_safe"))) for r in rows], dtype=np.float32)
    gain = np.asarray([float(parse_bool(r.get("labelv51_success_gain"))) for r in rows], dtype=np.float32)
    regression = np.asarray([float(parse_bool(r.get("labelv51_success_regression"))) for r in rows], dtype=np.float32)
    comparable = np.asarray([float(parse_bool(r.get("labelv51_comparable_quality"))) for r in rows], dtype=np.float32)
    qd = np.asarray([_float(r, "quality_delta_vs_g556", 0.0) for r in rows], dtype=np.float32)
    group_keys = np.asarray([r.get("g560_evaluation_uid", "") for r in rows], dtype=object)
    physical_hashes = np.asarray([r.get("g560_physical_map_sha256", "") for r in rows], dtype=object)
    return Dataset(rows, x, y, safe, gain, regression, comparable, qd, group_keys, physical_hashes)


def fit_scaler(x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    mean = x.mean(axis=0)
    std = x.std(axis=0)
    std[std < 1.0e-6] = 1.0
    return mean.astype(np.float32), std.astype(np.float32)


def apply_scaler(x: np.ndarray, mean: np.ndarray, std: np.ndarray) -> np.ndarray:
    return ((x - mean) / std).astype(np.float32)


def make_physical_folds(dataset: Dataset, n_folds: int = 5) -> list[set[str]]:
    hashes = sorted({str(h) for h in dataset.physical_hashes if str(h)})
    if not hashes:
        return [set()]
    folds = [set() for _ in range(max(1, min(n_folds, len(hashes))))]
    # Round-robin by map hash keeps folds deterministic and leakage-free.
    for idx, h in enumerate(hashes):
        folds[idx % len(folds)].add(h)
    return folds


def grouped_indices(group_keys: np.ndarray, mask: np.ndarray) -> dict[str, np.ndarray]:
    groups: dict[str, list[int]] = defaultdict(list)
    for idx, keep in enumerate(mask):
        if keep:
            groups[str(group_keys[idx])].append(idx)
    return {k: np.asarray(v, dtype=np.int64) for k, v in groups.items()}


def listnet_targets(y: np.ndarray, group_indices: dict[str, np.ndarray]) -> np.ndarray:
    out = np.zeros(len(y), dtype=np.float32)
    for idxs in group_indices.values():
        values = y[idxs]
        values = values - values.max()
        probs = np.exp(values)
        probs = probs / max(float(probs.sum()), 1.0e-12)
        out[idxs] = probs
    return out


def evaluate_scores(dataset: Dataset, scores: np.ndarray, mask: np.ndarray, selector_name: str, seed: int = 0) -> dict[str, Any]:
    groups = grouped_indices(dataset.group_keys, mask)
    safe_recalls = []
    improving_recalls = []
    pairwise = []
    selected_utils = []
    selected_safe = []
    selected_gain = []
    selected_regression = []
    selected_delta = []
    oracle_gaps = []
    nonfallback = 0
    rng = random.Random(seed)
    worst_group = ("", 0.0)
    for group, idxs in groups.items():
        group_scores = scores[idxs]
        order = np.argsort(-group_scores)
        selected = idxs[int(order[0])]
        true_safe = dataset.safe[idxs] > 0.5
        true_improving = (dataset.gain[idxs] > 0.5) | ((dataset.safe[idxs] > 0.5) & (dataset.quality_delta[idxs] < 0.0))
        safe_recalls.append(float(true_safe[order[: min(8, len(order))]].sum() / max(1, true_safe.sum())))
        improving_recalls.append(float(true_improving[order[: min(8, len(order))]].sum() / max(1, true_improving.sum())) if true_improving.sum() else 1.0)
        if len(idxs) > 1:
            pairs = [(int(i), int(j)) for i in range(len(idxs)) for j in range(i + 1, len(idxs))]
            if len(pairs) > 512:
                pairs = rng.sample(pairs, 512)
            good = 0
            total = 0
            for i, j in pairs:
                yi = float(dataset.y[idxs[i]])
                yj = float(dataset.y[idxs[j]])
                if abs(yi - yj) < 1.0e-6:
                    continue
                total += 1
                good += int((group_scores[i] > group_scores[j]) == (yi > yj))
            if total:
                pairwise.append(good / total)
        selected_utils.append(float(dataset.y[selected]))
        selected_safe.append(float(dataset.safe[selected]))
        selected_gain.append(float(dataset.gain[selected]))
        selected_regression.append(float(dataset.regression[selected]))
        selected_delta.append(float(dataset.quality_delta[selected]))
        selected_theta = dataset.rows[selected].get("theta_id", "")
        nonfallback += int(selected_theta != PRIMARY_BASELINE)
        oracle = float(dataset.y[idxs].max())
        gap = oracle - float(dataset.y[selected])
        oracle_gaps.append(gap)
        if gap > worst_group[1]:
            worst_group = (group, gap)
    finite_delta = [v for v in selected_delta if math.isfinite(v)]
    return {
        "selector": selector_name,
        "seed": seed,
        "groups": len(groups),
        "rows": int(mask.sum()),
        "top8_safe_recall": float(np.mean(safe_recalls)) if safe_recalls else 0.0,
        "top8_safe_improving_recall": float(np.mean(improving_recalls)) if improving_recalls else 0.0,
        "pairwise_ranking_accuracy": float(np.mean(pairwise)) if pairwise else 0.0,
        "selected_safe_rate": float(np.mean(selected_safe)) if selected_safe else 0.0,
        "selected_gain_rate": float(np.mean(selected_gain)) if selected_gain else 0.0,
        "selected_regression_rate": float(np.mean(selected_regression)) if selected_regression else 0.0,
        "selected_mean_quality_delta": float(np.mean(finite_delta)) if finite_delta else 0.0,
        "selected_mean_utility": float(np.mean(selected_utils)) if selected_utils else 0.0,
        "oracle_regret_mean": float(np.mean(oracle_gaps)) if oracle_gaps else 0.0,
        "nonfallback_coverage": nonfallback / max(1, len(groups)),
        "worst_group": worst_group[0],
        "worst_group_oracle_regret": worst_group[1],
    }


def always_g556_scores(dataset: Dataset) -> np.ndarray:
    scores = np.full(len(dataset.rows), -1.0, dtype=np.float32)
    for idx, row in enumerate(dataset.rows):
        if row.get("theta_id") == PRIMARY_BASELINE:
            scores[idx] = 1.0
    return scores


def density_lookup_scores(dataset: Dataset) -> np.ndarray:
    scores = np.zeros(len(dataset.rows), dtype=np.float32)
    lambda_idx = THETA_NUMERIC_COLUMNS.index("theta_lambda_cong")
    flow_idx = THETA_NUMERIC_COLUMNS.index("theta_lambda_flow")
    max_edge_idx = THETA_NUMERIC_COLUMNS.index("theta_max_edge_cost")
    for idx, row in enumerate(dataset.rows):
        density = _float(row, "agent_density")
        theta = [float(dataset.x[idx, len(INSTANCE_FEATURES) + len(BOOL_FEATURES) + j]) for j in range(len(THETA_NUMERIC_COLUMNS))]
        target_cong = min(2.0, 0.4 + 2.5 * density)
        target_flow = min(2.0, 0.3 + 1.6 * density)
        target_edge = min(12.0, 5.0 + 12.0 * density)
        scores[idx] = -(
            abs(theta[lambda_idx] - target_cong) / 2.0
            + abs(theta[flow_idx] - target_flow) / 2.0
            + abs(theta[max_edge_idx] - target_edge) / 12.0
        )
        if row.get("theta_id") == PRIMARY_BASELINE:
            scores[idx] += 0.02
    return scores


def train_gbdt_scores(train_x: np.ndarray, train_y: np.ndarray, test_x: np.ndarray) -> tuple[np.ndarray, str]:
    try:
        from sklearn.ensemble import HistGradientBoostingRegressor

        model = HistGradientBoostingRegressor(max_iter=160, learning_rate=0.05, l2_regularization=0.01, random_state=560)
        model.fit(train_x, train_y)
        return model.predict(test_x).astype(np.float32), "sklearn_hist_gradient_boosting"
    except Exception as exc:
        # Ridge fallback keeps the control prediction-derived if sklearn GBDT is unavailable.
        try:
            from sklearn.linear_model import Ridge

            model = Ridge(alpha=1.0)
            model.fit(train_x, train_y)
            return model.predict(test_x).astype(np.float32), f"ridge_fallback_after_gbdt_error:{type(exc).__name__}"
        except Exception:
            coef = np.linalg.pinv(train_x.T @ train_x + np.eye(train_x.shape[1], dtype=np.float32) * 1.0) @ train_x.T @ train_y
            return (test_x @ coef).astype(np.float32), f"numpy_ridge_fallback_after_gbdt_error:{type(exc).__name__}"


class CodebookCritic:
    def __init__(self, input_dim: int, hidden_dim: int, depth: int = 3) -> None:
        import torch

        layers: list[Any] = []
        dim = input_dim
        for _ in range(depth):
            layers.append(torch.nn.Linear(dim, hidden_dim))
            layers.append(torch.nn.LayerNorm(hidden_dim))
            layers.append(torch.nn.SiLU())
            layers.append(torch.nn.Dropout(0.05))
            dim = hidden_dim
        layers.append(torch.nn.Linear(dim, 1))
        self.module = torch.nn.Sequential(*layers)


def _torch_train(
    dataset: Dataset,
    train_mask: np.ndarray,
    eval_mask: np.ndarray,
    hidden_dim: int,
    steps: int,
    batch_groups: int,
    seed: int,
    device_name: str,
    selector_name: str,
) -> tuple[np.ndarray, dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    import torch
    from torch.nn import functional as F

    torch.manual_seed(seed)
    np.random.seed(seed)
    random.seed(seed)
    train_x_raw = dataset.x[train_mask]
    mean, std = fit_scaler(train_x_raw)
    x_scaled = apply_scaler(dataset.x, mean, std)
    x = torch.tensor(x_scaled, dtype=torch.float32)
    y = torch.tensor(dataset.y, dtype=torch.float32)
    safe = torch.tensor(dataset.safe, dtype=torch.float32)
    gain = torch.tensor(dataset.gain, dtype=torch.float32)
    reg = torch.tensor(dataset.regression, dtype=torch.float32)
    comparable = torch.tensor(dataset.comparable, dtype=torch.float32)
    train_groups = grouped_indices(dataset.group_keys, train_mask)
    target_probs = torch.tensor(listnet_targets(dataset.y, train_groups), dtype=torch.float32)
    device = torch.device(device_name if device_name != "auto" else ("cuda" if torch.cuda.is_available() else "cpu"))
    critic = CodebookCritic(x.shape[1], hidden_dim=hidden_dim, depth=3).module.to(device)
    opt = torch.optim.AdamW(critic.parameters(), lr=2.0e-4, weight_decay=1.0e-4)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=max(1, steps))
    group_items = list(train_groups.items())
    epoch_rows: list[dict[str, Any]] = []
    best_metric = -1.0e9
    best_state: dict[str, Any] | None = None
    scaler_enabled = device.type == "cuda"
    amp_dtype = torch.bfloat16 if device.type == "cuda" else torch.float32
    for step in range(1, steps + 1):
        batch = random.sample(group_items, min(batch_groups, len(group_items)))
        idxs_np = np.concatenate([idxs for _group, idxs in batch])
        idxs = torch.tensor(idxs_np, dtype=torch.long, device=device)
        xb = x[idxs].to(device)
        yb = y[idxs].to(device)
        safeb = safe[idxs].to(device)
        gainb = gain[idxs].to(device)
        regb = reg[idxs].to(device)
        comparableb = comparable[idxs].to(device)
        targetb = target_probs[idxs].to(device)
        group_map = {group: local for local, (group, _idx) in enumerate(batch)}
        group_idx_np = []
        for group, group_idxs in batch:
            group_idx_np.extend([group_map[group]] * len(group_idxs))
        group_idx = torch.tensor(group_idx_np, dtype=torch.long, device=device)
        opt.zero_grad(set_to_none=True)
        with torch.autocast(device_type=device.type, dtype=amp_dtype, enabled=scaler_enabled):
            scores = critic(xb).flatten()
            mse = ((scores - yb) ** 2).mean()
            regression_bce = F.binary_cross_entropy_with_logits(-scores, regb)
            gain_bce = F.binary_cross_entropy_with_logits(scores, gainb)
            safe_bce = F.binary_cross_entropy_with_logits(scores, safeb)
            quality_loss = (((scores - yb) ** 2) * comparableb).sum() / comparableb.sum().clamp_min(1.0)
            list_losses = []
            for group_id in torch.unique(group_idx):
                m = group_idx == group_id
                logits = scores[m]
                target = targetb[m]
                target = target / target.sum().clamp_min(1.0e-12)
                list_losses.append(F.kl_div(F.log_softmax(logits, dim=0), target, reduction="sum"))
            listwise = torch.stack(list_losses).mean() if list_losses else scores.sum() * 0.0
            hard_negative = F.relu(scores[regb > 0.5] - 0.0).mean() if bool((regb > 0.5).any()) else scores.sum() * 0.0
            loss = mse + 0.5 * regression_bce + 0.35 * gain_bce + 0.25 * safe_bce + 0.5 * quality_loss + listwise + 0.5 * hard_negative
        loss.backward()
        torch.nn.utils.clip_grad_norm_(critic.parameters(), 2.0)
        opt.step()
        sched.step()
        if step == 1 or step % max(1, steps // 20) == 0 or step == steps:
            critic.eval()
            with torch.no_grad():
                eval_scores = critic(x.to(device)).flatten().detach().float().cpu().numpy()
            metric = evaluate_scores(dataset, eval_scores, eval_mask, selector_name, seed=seed)
            metric.update(
                {
                    "step": step,
                    "loss": float(loss.detach().float().cpu()),
                    "mse_loss": float(mse.detach().float().cpu()),
                    "regression_bce": float(regression_bce.detach().float().cpu()),
                    "gain_bce": float(gain_bce.detach().float().cpu()),
                    "safe_bce": float(safe_bce.detach().float().cpu()),
                    "quality_loss": float(quality_loss.detach().float().cpu()),
                    "listwise_loss": float(listwise.detach().float().cpu()),
                    "hard_negative_loss": float(hard_negative.detach().float().cpu()),
                    "device": str(device),
                }
            )
            epoch_rows.append(metric)
            select_metric = metric["selected_mean_utility"] - metric["selected_regression_rate"] - 0.1 * metric["oracle_regret_mean"]
            if select_metric > best_metric:
                best_metric = float(select_metric)
                best_state = {
                    "model_state_dict": {k: v.detach().cpu() for k, v in critic.state_dict().items()},
                    "optimizer_state_dict": opt.state_dict(),
                    "scheduler_state_dict": sched.state_dict(),
                    "step": step,
                    "best_validation_metric": best_metric,
                }
            critic.train()
    critic.eval()
    if best_state is not None:
        critic.load_state_dict(best_state["model_state_dict"])
    with torch.no_grad():
        all_scores = critic(x.to(device)).flatten().detach().float().cpu().numpy()
    ckpt = {
        "model_state_dict": critic.state_dict(),
        "optimizer_state_dict": opt.state_dict(),
        "scheduler_state_dict": sched.state_dict(),
        "step": steps,
        "best_validation_metric": best_metric,
        "feature_schema": FEATURE_SCHEMA,
        "feature_mean": mean,
        "feature_std": std,
        "hidden_dim": hidden_dim,
        "seed": seed,
        "selector_name": selector_name,
        "input_dim": int(x.shape[1]),
    }
    final_metric = evaluate_scores(dataset, all_scores, eval_mask, selector_name, seed=seed)
    final_metric["best_validation_metric"] = best_metric
    return all_scores, final_metric, epoch_rows, ckpt


def write_oracle_and_candidate_audit(root: Path = ROOT) -> dict[str, Any]:
    rows = _read_rows(JOIN_AUDIT_CSV, root)
    groups: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        groups[row.get("g560_evaluation_uid", "")].append(row)
    oracle_rows = []
    safe_improvement_groups = 0
    oracle_quality_gains = []
    for group, rs in groups.items():
        safe = [r for r in rs if parse_bool(r.get("labelv51_development_safe"))]
        improving = [
            r
            for r in safe
            if parse_bool(r.get("labelv51_success_gain")) or (_float(r, "quality_delta_vs_g556", 0.0) < 0.0 and parse_bool(r.get("labelv51_comparable_quality")))
        ]
        finite_safe = [r for r in safe if parse_bool(r.get("labelv51_comparable_quality"))]
        best_delta = min((_float(r, "quality_delta_vs_g556", 0.0) for r in finite_safe), default=0.0)
        if improving:
            safe_improvement_groups += 1
            oracle_quality_gains.append(best_delta)
        first = rs[0]
        oracle_rows.append(
            {
                "g560_evaluation_uid": group,
                "g560_physical_map_sha256": first.get("g560_physical_map_sha256", ""),
                "map_family": first.get("map_family", ""),
                "agent_density": first.get("agent_density", ""),
                "nominal_budget_ms": first.get("nominal_budget_ms", ""),
                "candidate_count": len(rs),
                "safe_count": len(safe),
                "safe_improving_count": len(improving),
                "oracle_best_quality_delta": best_delta,
            }
        )
    by_family: Counter = Counter()
    by_family_improving: Counter = Counter()
    for row in oracle_rows:
        fam = row["map_family"]
        by_family[fam] += 1
        by_family_improving[fam] += int(int(row["safe_improving_count"]) > 0)

    candidate_rows = []
    theta_values: dict[str, list[float]] = defaultdict(list)
    saturation_counts: Counter = Counter()
    regression_count = 0
    improvement_count = 0
    distances = []
    for row in rows:
        vec = np.asarray([_float(row, col, float(BASELINE_G556[i])) for i, col in enumerate(THETA_NUMERIC_COLUMNS)], dtype=np.float32)
        span = np.maximum(THETA_HI - THETA_LO, 1.0e-6)
        distances.append(float(np.mean(np.abs((vec - BASELINE_G556) / span))))
        regression_count += int(parse_bool(row.get("labelv51_success_regression")))
        improvement_count += int(parse_bool(row.get("labelv51_success_gain")) or (_float(row, "quality_delta_vs_g556", 0.0) < 0.0 and parse_bool(row.get("labelv51_development_safe"))))
        for i, col in enumerate(THETA_NUMERIC_COLUMNS):
            value = float(vec[i])
            theta_values[col].append(value)
            saturation_counts[col] += int(abs(value - float(THETA_LO[i])) < 1.0e-6 or abs(value - float(THETA_HI[i])) < 1.0e-6)
    total = max(1, len(rows))
    for i, col in enumerate(THETA_NUMERIC_COLUMNS):
        vals = theta_values[col]
        candidate_rows.append(
            {
                "theta_field": col,
                "value_mean": float(np.mean(vals)) if vals else 0.0,
                "value_std": float(np.std(vals)) if vals else 0.0,
                "value_min": float(np.min(vals)) if vals else 0.0,
                "value_max": float(np.max(vals)) if vals else 0.0,
                "lower_bound": float(THETA_LO[i]),
                "upper_bound": float(THETA_HI[i]),
                "field_bound_saturation_rate": saturation_counts[col] / total,
            }
        )
    _write_rows(CANDIDATE_AUDIT_CSV, candidate_rows, root)
    summary = {
        "round": ROUND,
        "groups": len(groups),
        "candidate_rows": len(rows),
        "fraction_with_safe_improvement": safe_improvement_groups / max(1, len(groups)),
        "mean_oracle_quality_gain": float(np.mean(oracle_quality_gains)) if oracle_quality_gains else 0.0,
        "oracle_success_gain_groups": safe_improvement_groups,
        "candidate_regression_rate": regression_count / total,
        "candidate_improvement_rate": improvement_count / total,
        "normalized_distance_from_g556_mean": float(np.mean(distances)) if distances else 0.0,
        "oracle_by_map_family": {fam: by_family_improving[fam] / max(1, by_family[fam]) for fam in sorted(by_family)},
        "candidate_slate_blocker": safe_improvement_groups / max(1, len(groups)) < 0.05,
    }
    _write_json(ORACLE_JSON, summary, root)
    md = [
        "# Repair5G.5.60 Oracle Opportunity",
        "",
        f"- Evaluation groups: {summary['groups']}",
        f"- Candidate rows: {summary['candidate_rows']}",
        f"- Fraction with safe improvement: {summary['fraction_with_safe_improvement']:.6f}",
        f"- Mean oracle quality gain: {summary['mean_oracle_quality_gain']:.6f}",
        f"- Candidate regression rate: {summary['candidate_regression_rate']:.6f}",
        f"- Candidate improvement rate: {summary['candidate_improvement_rate']:.6f}",
        f"- Candidate slate blocker: `{summary['candidate_slate_blocker']}`",
    ]
    p = resolve(ORACLE_MD, root)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join(md) + "\n", encoding="utf-8")
    return summary


def train_and_evaluate(
    root: Path = ROOT,
    seed: int = 560,
    hidden_dim: int = 128,
    steps: int = 20000,
    fold_steps: int = 4000,
    n_folds: int = 5,
    batch_groups: int = 12,
    device: str = "auto",
) -> dict[str, Any]:
    dataset = load_dataset(root)
    folds = make_physical_folds(dataset, n_folds)
    selector_rows: list[dict[str, Any]] = []
    fold_rows: list[dict[str, Any]] = []
    epoch_rows: list[dict[str, Any]] = []
    model_dir = resolve(MODEL_DIR, root)
    model_dir.mkdir(parents=True, exist_ok=True)
    all_fold_metrics: dict[str, list[float]] = defaultdict(list)
    for fold_idx, heldout_hashes in enumerate(folds):
        eval_mask = np.asarray([str(h) in heldout_hashes for h in dataset.physical_hashes], dtype=bool)
        train_mask = ~eval_mask
        if not eval_mask.any() or not train_mask.any():
            continue
        train_x_raw = dataset.x[train_mask]
        mean, std = fit_scaler(train_x_raw)
        x_scaled = apply_scaler(dataset.x, mean, std)

        control_scores = always_g556_scores(dataset)
        m = evaluate_scores(dataset, control_scores, eval_mask, "always_g556", seed=seed)
        m.update({"fold": fold_idx, "heldout_physical_hashes": ";".join(sorted(heldout_hashes)), "control_backend": "deterministic"})
        selector_rows.append(m)
        fold_rows.append(m)

        density_scores = density_lookup_scores(dataset)
        m = evaluate_scores(dataset, density_scores, eval_mask, "agent_density_lookup", seed=seed)
        m.update({"fold": fold_idx, "heldout_physical_hashes": ";".join(sorted(heldout_hashes)), "control_backend": "deterministic"})
        selector_rows.append(m)
        fold_rows.append(m)

        gbdt_eval_scores, backend = train_gbdt_scores(x_scaled[train_mask], dataset.y[train_mask], x_scaled[eval_mask])
        gbdt_scores = np.zeros(len(dataset.rows), dtype=np.float32)
        gbdt_scores[eval_mask] = gbdt_eval_scores
        m = evaluate_scores(dataset, gbdt_scores, eval_mask, "gbdt_or_ridge_tabular", seed=seed)
        m.update({"fold": fold_idx, "heldout_physical_hashes": ";".join(sorted(heldout_hashes)), "control_backend": backend})
        selector_rows.append(m)
        fold_rows.append(m)

        mlp_scores, mlp_metric, mlp_epochs, _mlp_ckpt = _torch_train(
            dataset, train_mask, eval_mask, hidden_dim=96, steps=max(1, min(fold_steps, steps)), batch_groups=batch_groups, seed=seed + fold_idx, device_name=device, selector_name="tabular_mlp_control"
        )
        mlp_metric.update({"fold": fold_idx, "heldout_physical_hashes": ";".join(sorted(heldout_hashes)), "control_backend": "torch_mlp"})
        selector_rows.append(mlp_metric)
        fold_rows.append(mlp_metric)
        epoch_rows.extend({**row, "fold": fold_idx, "selector": "tabular_mlp_control"} for row in mlp_epochs)

        gcst_scores, gcst_metric, gcst_epochs, _gcst_ckpt = _torch_train(
            dataset, train_mask, eval_mask, hidden_dim=hidden_dim, steps=max(1, fold_steps), batch_groups=batch_groups, seed=seed + 100 + fold_idx, device_name=device, selector_name="gcst_codebook_critic"
        )
        gcst_metric.update({"fold": fold_idx, "heldout_physical_hashes": ";".join(sorted(heldout_hashes)), "control_backend": "torch_grouped_listwise"})
        selector_rows.append(gcst_metric)
        fold_rows.append(gcst_metric)
        epoch_rows.extend({**row, "fold": fold_idx, "selector": "gcst_codebook_critic"} for row in gcst_epochs)
        for key, value in gcst_metric.items():
            if isinstance(value, (int, float)):
                all_fold_metrics[key].append(float(value))

    final_eval_hashes = set()
    for row in dataset.rows:
        if row.get("split") == "heldout":
            final_eval_hashes.add(row.get("g560_physical_map_sha256", ""))
    if not final_eval_hashes and folds:
        final_eval_hashes = folds[-1]
    final_eval_mask = np.asarray([str(h) in final_eval_hashes for h in dataset.physical_hashes], dtype=bool)
    final_train_mask = ~final_eval_mask
    final_scores, final_metric, final_epochs, final_ckpt = _torch_train(
        dataset,
        final_train_mask,
        final_eval_mask,
        hidden_dim=hidden_dim,
        steps=steps,
        batch_groups=batch_groups,
        seed=seed,
        device_name=device,
        selector_name="gcst_codebook_critic_final",
    )
    final_metric.update({"fold": "final_heldout_panel", "heldout_physical_hashes": ";".join(sorted(final_eval_hashes)), "control_backend": "torch_grouped_listwise"})
    selector_rows.append(final_metric)
    epoch_rows.extend({**row, "fold": "final_heldout_panel", "selector": "gcst_codebook_critic_final"} for row in final_epochs)

    import torch

    model_path = model_dir / f"g560_codebook_critic_{seed}.pt"
    final_ckpt.update(
        {
            "source_dataset": str(TRAINING_ROWS_CSV),
            "split_hashes": sorted(final_eval_hashes),
            "feature_schema": FEATURE_SCHEMA,
            "training_rows": len(dataset.rows),
            "physical_hash_count": len({str(h) for h in dataset.physical_hashes}),
        }
    )
    torch.save(final_ckpt, model_path)

    _write_rows(SELECTOR_EVAL_CSV, selector_rows, root)
    _write_rows(FOLD_METRICS_CSV, fold_rows, root)
    _write_rows(EPOCH_METRICS_CSV, epoch_rows, root)

    selector_by_name: dict[str, dict[str, float]] = {}
    for name in sorted({r["selector"] for r in selector_rows if isinstance(r.get("selector"), str)}):
        rs = [r for r in selector_rows if r["selector"] == name and isinstance(r.get("selected_mean_utility"), (int, float))]
        if not rs:
            continue
        selector_by_name[name] = {
            "selected_mean_utility_mean": float(np.mean([float(r["selected_mean_utility"]) for r in rs])),
            "selected_mean_quality_delta_mean": float(np.mean([float(r["selected_mean_quality_delta"]) for r in rs])),
            "selected_regression_rate_mean": float(np.mean([float(r["selected_regression_rate"]) for r in rs])),
            "nonfallback_coverage_mean": float(np.mean([float(r["nonfallback_coverage"]) for r in rs])),
            "top8_safe_recall_mean": float(np.mean([float(r["top8_safe_recall"]) for r in rs])),
        }
    main = selector_by_name.get("gcst_codebook_critic", {})
    density = selector_by_name.get("agent_density_lookup", {})
    gbdt = selector_by_name.get("gbdt_or_ridge_tabular", {})
    mlp = selector_by_name.get("tabular_mlp_control", {})
    critic_gate_passed = bool(
        main
        and main.get("selected_mean_utility_mean", -999.0) > density.get("selected_mean_utility_mean", 999.0)
        and main.get("selected_mean_utility_mean", -999.0) > gbdt.get("selected_mean_utility_mean", 999.0)
        and main.get("selected_mean_utility_mean", -999.0) > mlp.get("selected_mean_utility_mean", 999.0)
        and main.get("nonfallback_coverage_mean", 0.0) >= 0.05
        and main.get("selected_mean_quality_delta_mean", 1.0) < 0.0
    )
    failure_rows = [
        {
            "branch": "A_label_diagnosis",
            "status": "closed" if final_metric.get("groups", 0) > 0 else "open",
            "evidence": f"final heldout groups={final_metric.get('groups', 0)}",
        },
        {
            "branch": "B_feature_diagnosis",
            "status": "open" if main and density and main.get("selected_mean_utility_mean", -999) <= density.get("selected_mean_utility_mean", 999) else "closed",
            "evidence": f"gcst_vs_density={main.get('selected_mean_utility_mean', 0.0) - density.get('selected_mean_utility_mean', 0.0) if main and density else 0.0:.6f}",
        },
        {
            "branch": "C_model_loss_diagnosis",
            "status": "open" if main and mlp and main.get("selected_mean_utility_mean", -999) <= mlp.get("selected_mean_utility_mean", 999) else "closed",
            "evidence": f"gcst_vs_mlp={main.get('selected_mean_utility_mean', 0.0) - mlp.get('selected_mean_utility_mean', 0.0) if main and mlp else 0.0:.6f}",
        },
        {
            "branch": "D_candidate_space_diagnosis",
            "status": "open",
            "evidence": "see oracle opportunity and candidate-space audit",
        },
    ]
    _write_rows(FAILURE_ATTRIBUTION_CSV, failure_rows, root)
    failure_md = ["# Repair5G.5.60 Failure Attribution", ""]
    failure_md.extend(f"- {r['branch']}: {r['status']} ({r['evidence']})" for r in failure_rows)
    p = resolve(FAILURE_ATTRIBUTION_MD, root)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join(failure_md) + "\n", encoding="utf-8")

    summary = {
        "round": ROUND,
        "seed": seed,
        "model_path": str(model_path),
        "training_rows": len(dataset.rows),
        "feature_schema": FEATURE_SCHEMA,
        "fold_count": len(folds),
        "final_checkpoint_step": int(final_ckpt["step"]),
        "best_validation_metric": float(final_ckpt["best_validation_metric"]),
        "selector_summary": selector_by_name,
        "final_heldout_metric": final_metric,
        "critic_learnability_gate_passed": critic_gate_passed,
        "phase5p5_allowed": bool(critic_gate_passed),
        "phase6_allowed": False,
        "runtime_claim_allowed": False,
        "learned_runtime_policy_validated": False,
        "aaai_ready": False,
    }
    _write_json(TRAINING_SUMMARY_JSON, summary, root)
    _write_json(EVAL_JSON, summary, root)
    eval_md = [
        "# Repair5G.5.60 Codebook Critic Evaluation",
        "",
        f"- Model checkpoint: `{model_path}`",
        f"- Final checkpoint step: {final_ckpt['step']}",
        f"- Folds: {len(folds)}",
        f"- Critic learnability gate passed: `{critic_gate_passed}`",
        "",
        "## Selector Means",
        "",
    ]
    for name, vals in selector_by_name.items():
        eval_md.append(
            f"- {name}: utility={vals['selected_mean_utility_mean']:.6f}, delta={vals['selected_mean_quality_delta_mean']:.6f}, regression={vals['selected_regression_rate_mean']:.6f}, nonfallback={vals['nonfallback_coverage_mean']:.6f}"
        )
    p = resolve(EVAL_MD, root)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join(eval_md) + "\n", encoding="utf-8")

    decision = {
        "round": ROUND,
        "decision": "g560_critic_learnability_passed_continue_to_targeted_topup" if critic_gate_passed else "g560_critic_learnability_failed_complete_diagnosis_before_topup",
        "critic_learnability_gate_passed": critic_gate_passed,
        "model_path": str(model_path),
        "phase5p5_allowed": bool(critic_gate_passed),
        "phase6_allowed": False,
        "runtime_claim_allowed": False,
        "learned_runtime_policy_validated": False,
        "aaai_ready": False,
    }
    _write_json(DECISION_JSON, decision, root)
    decision_md = [
        "# Repair5G.5.60 Decision",
        "",
        f"Decision: `{decision['decision']}`",
        "",
        f"Critic learnability gate passed: `{critic_gate_passed}`.",
    ]
    p = resolve(DECISION_MD, root)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join(decision_md) + "\n", encoding="utf-8")
    return summary
