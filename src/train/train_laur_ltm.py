"""Train the Phase4F LAU-LTM checkpoint-level update model."""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(ROOT / "src"))

from czr004_teacher.update_sequences import validate_update_dataset_row  # noqa: E402
from models.laur_ltm import LaurMlpV1, write_laur_mlp_exports  # noqa: E402
from train.losses_laur import LaurLossWeights, laur_ltm_loss  # noqa: E402

try:
    import torch
except ImportError as exc:  # pragma: no cover - training is run in czr004 env
    raise RuntimeError(
        "PyTorch is required for Phase4F training. Use the czr004 conda environment."
    ) from exc


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _resolve(path: str | Path | None, root: Path) -> Path | None:
    if path is None:
        return None
    value = Path(path)
    return value if value.is_absolute() else root / value


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            if not line.strip():
                continue
            row = json.loads(line)
            if not isinstance(row, dict):
                raise ValueError(f"{path}:{line_no}: JSONL row must be an object")
            rows.append(row)
    return rows


def _read_probe_jsonl(path: Path | None) -> list[dict[str, Any]]:
    return _read_jsonl(path) if path is not None else []


def _load_config(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}
    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError("PyYAML is required to read Phase4 LAUR config") from exc
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    return data or {}


def _validate_rows(rows: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    for index, row in enumerate(rows, 1):
        errors.extend(f"row {index}: {error}" for error in validate_update_dataset_row(row))
    if not rows:
        errors.append("dataset is empty")
    return errors


def _feature_names(rows: list[dict[str, Any]]) -> list[str]:
    names = list(rows[0]["feature_names"])
    for index, row in enumerate(rows, 1):
        if list(row["feature_names"]) != names:
            raise ValueError(f"row {index}: feature_names differ from row 1")
    return names


def _parse_drop_features(value: Any) -> set[str]:
    if value is None:
        return set()
    if isinstance(value, str):
        return {item.strip() for item in value.split(",") if item.strip()}
    if isinstance(value, list):
        return {str(item).strip() for item in value if str(item).strip()}
    raise TypeError("drop_features must be a comma-separated string or list")


def _selected_feature_names(rows: list[dict[str, Any]], drop_features: set[str]) -> list[str]:
    names = [name for name in _feature_names(rows) if name not in drop_features]
    if not names:
        raise ValueError("feature selection removed every feature")
    missing = sorted(drop_features - set(_feature_names(rows)))
    if missing:
        raise ValueError(f"drop_features not present in dataset: {missing}")
    return names


def _rule_vocab(rows: list[dict[str, Any]]) -> list[str]:
    rules = list(rows[0]["target"]["rule_vocab"])
    for index, row in enumerate(rows, 1):
        if list(row["target"]["rule_vocab"]) != rules:
            raise ValueError(f"row {index}: target.rule_vocab differs from row 1")
    return rules


def _feature_matrix(rows: list[dict[str, Any]], names: list[str]) -> list[list[float]]:
    matrix: list[list[float]] = []
    for row in rows:
        features = row.get("features")
        if isinstance(features, dict) and all(name in features for name in names):
            matrix.append([float(features[name]) for name in names])
            continue
        row_names = list(row["feature_names"])
        row_values = list(row["feature_vector"])
        lookup = {name: float(row_values[index]) for index, name in enumerate(row_names)}
        matrix.append([lookup[name] for name in names])
    return matrix


def _targets(rows: list[dict[str, Any]], rules: list[str]) -> tuple[list[int], list[float], list[float], list[float]]:
    rule_ids = [str(row["target"]["rule_class"]) for row in rows]
    rule_target = [rules.index(rule_id) for rule_id in rule_ids]
    harmful = [1.0 if row["target"]["harmful_update"] else 0.0 for row in rows]
    delta = [float(row["target"]["delta_ratio_best"]) for row in rows]
    neutral = [1.0 if row["target"]["neutral"] else 0.0 for row in rows]
    return rule_target, harmful, delta, neutral


def _probe_rows_by_checkpoint(probe_rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in probe_rows:
        grouped[str(row["checkpoint_id"])].append(row)
    return grouped


def _soft_rule_targets(
    rows: list[dict[str, Any]],
    rules: list[str],
    probe_rows_by_checkpoint: dict[str, list[dict[str, Any]]],
    *,
    neutral_threshold: float,
    temperature: float,
    hard_mix: float,
) -> list[list[float]]:
    if temperature <= 0.0:
        raise ValueError("soft-label temperature must be positive")
    if hard_mix < 0.0 or hard_mix > 1.0:
        raise ValueError("soft-label hard mix must be in [0, 1]")
    targets: list[list[float]] = []
    for row in rows:
        scores = [float("-inf")] * len(rules)
        for probe_row in probe_rows_by_checkpoint.get(str(row["checkpoint_id"]), []):
            rule_id = str(probe_row["rule_id"])
            if rule_id in rules:
                scores[rules.index(rule_id)] = float(probe_row["delta_ratio_vs_additive"])
        if "neutral_additive" in rules:
            scores[rules.index("neutral_additive")] = float(neutral_threshold)
        finite_scores = [score for score in scores if math.isfinite(score)]
        hard = [0.0] * len(rules)
        hard[int(row["target"]["rule_class_index"])] = 1.0
        if not finite_scores:
            targets.append(hard)
            continue
        pivot = max(finite_scores)
        weights = [
            math.exp((score - pivot) / temperature) if math.isfinite(score) else 0.0
            for score in scores
        ]
        total = sum(weights)
        soft = [weight / total if total else 0.0 for weight in weights]
        targets.append(
            [
                float(hard_mix) * hard_value + (1.0 - float(hard_mix)) * soft_value
                for hard_value, soft_value in zip(hard, soft)
            ]
        )
    return targets


def _feature_stats(matrix: list[list[float]]) -> tuple[list[float], list[float]]:
    if not matrix:
        return [], []
    dim = len(matrix[0])
    mean = [sum(row[col] for row in matrix) / len(matrix) for col in range(dim)]
    std: list[float] = []
    for col in range(dim):
        variance = sum((row[col] - mean[col]) ** 2 for row in matrix) / len(matrix)
        value = math.sqrt(max(variance, 0.0))
        std.append(value if value > 1e-12 else 1.0)
    return mean, std


def _standardize(matrix: list[list[float]], mean: list[float], std: list[float]) -> list[list[float]]:
    return [
        [(float(value) - mean[col]) / std[col] for col, value in enumerate(row)]
        for row in matrix
    ]


def _split_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    train = [row for row in rows if row["split"] == "train"] or list(rows)
    validation = [row for row in rows if row["split"] == "validation"]
    test = [row for row in rows if row["split"] == "test"]
    validation_source = "validation"
    if not validation:
        validation = list(rows)
        validation_source = "all_rows_smoke_reuse"
    return {
        "train": train,
        "validation": validation,
        "test": test,
        "validation_source": validation_source,
    }


def _topk_indices(values: list[float], k: int) -> list[int]:
    return sorted(range(len(values)), key=lambda index: values[index], reverse=True)[:k]


def _binary_metrics(labels: list[int], predictions: list[int]) -> dict[str, float]:
    tp = sum(1 for label, pred in zip(labels, predictions) if label == 1 and pred == 1)
    fp = sum(1 for label, pred in zip(labels, predictions) if label == 0 and pred == 1)
    fn = sum(1 for label, pred in zip(labels, predictions) if label == 1 and pred == 0)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2.0 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"precision": precision, "recall": recall, "f1": f1}


def _binary_auroc(labels: list[int], scores: list[float]) -> float | None:
    positives = [score for label, score in zip(labels, scores) if label == 1]
    negatives = [score for label, score in zip(labels, scores) if label == 0]
    if not positives or not negatives:
        return None
    wins = 0.0
    for pos in positives:
        for neg in negatives:
            if pos > neg:
                wins += 1.0
            elif pos == neg:
                wins += 0.5
    return wins / (len(positives) * len(negatives))


def _evaluate_model(
    model: LaurMlpV1,
    rows: list[dict[str, Any]],
    *,
    rules: list[str],
    feature_names: list[str],
    feature_mean: list[float],
    feature_std: list[float],
    device: torch.device,
    harmful_threshold: float,
) -> dict[str, Any]:
    matrix = _standardize(_feature_matrix(rows, feature_names), feature_mean, feature_std)
    x = torch.tensor(matrix, dtype=torch.float32, device=device)
    target_indices, harmful, delta, neutral = _targets(rows, rules)
    with torch.no_grad():
        outputs = model(x)
        probs = torch.softmax(outputs["rule_logits"], dim=-1).cpu().tolist()
        harmful_prob = torch.sigmoid(outputs["safety_logit"]).cpu().tolist()
        delta_pred = outputs["delta_pred"].cpu().tolist()

    predictions = [int(max(range(len(row)), key=lambda index: row[index])) for row in probs]
    top3 = [_topk_indices(row, min(3, len(row))) for row in probs]
    top1_correct = [int(pred == target) for pred, target in zip(predictions, target_indices)]
    top3_correct = [int(target in candidates) for target, candidates in zip(target_indices, top3)]
    non_neutral_mask = [not bool(row["target"]["neutral"]) for row in rows]
    harmful_labels = [int(value) for value in harmful]
    harmful_predictions = [int(score >= harmful_threshold) for score in harmful_prob]
    safety = _binary_metrics(harmful_labels, harmful_predictions)
    matched_best_delta = [
        float(row["target"]["delta_ratio_best"]) if pred == target else 0.0
        for row, pred, target in zip(rows, predictions, target_indices)
    ]
    neutral_additive_rate = sum(
        1
        for pred in predictions
        if rules[pred] in {"additive_ltm", "neutral_additive"}
    ) / len(rows)

    return {
        "sample_count": len(rows),
        "rule_top1_accuracy": sum(top1_correct) / len(top1_correct),
        "rule_top3_accuracy": sum(top3_correct) / len(top3_correct),
        "non_neutral_rule_top1_accuracy": (
            sum(correct for correct, keep in zip(top1_correct, non_neutral_mask) if keep)
            / sum(non_neutral_mask)
            if any(non_neutral_mask)
            else None
        ),
        "harmful_update_precision": safety["precision"],
        "harmful_update_recall": safety["recall"],
        "harmful_update_f1": safety["f1"],
        "safety_auroc": _binary_auroc(harmful_labels, harmful_prob),
        "predicted_best_rule_mean_delta_ratio_proxy": sum(matched_best_delta)
        / len(matched_best_delta),
        "neutral_additive_rate": neutral_additive_rate,
        "delta_pred_smooth_l1_proxy": sum(abs(float(a) - float(b)) for a, b in zip(delta_pred, delta))
        / len(rows),
        "label_distribution": dict(sorted(Counter(row["target"]["rule_class"] for row in rows).items())),
        "predicted_rule_distribution": dict(sorted(Counter(rules[pred] for pred in predictions).items())),
    }


def _git_value(args: list[str], cwd: Path) -> str:
    try:
        return subprocess.check_output(["git", *args], cwd=cwd, text=True).strip()
    except (FileNotFoundError, subprocess.CalledProcessError):
        return ""


def _dirty_state(cwd: Path) -> str:
    tracked = _git_value(["status", "--porcelain", "--untracked-files=no"], cwd)
    untracked = _git_value(["status", "--porcelain", "--untracked-files=normal"], cwd)
    if tracked:
        return "tracked-dirty"
    if any(line.startswith("??") for line in untracked.splitlines()):
        return "tracked-clean_untracked-present"
    return "clean"


def _display(path: str | Path, root: Path) -> str:
    value = Path(path)
    try:
        return str(value.relative_to(root))
    except ValueError:
        return str(value)


def _write_report(
    path: Path,
    *,
    root: Path,
    dataset_path: Path,
    output_dir: Path,
    weights_path: Path,
    feature_stats_path: Path,
    rules_path: Path,
    train_metrics: dict[str, Any],
    validation_metrics: dict[str, Any],
    test_metrics: dict[str, Any] | None,
    summary: dict[str, Any],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    branch = _git_value(["branch", "--show-current"], root)
    commit = _git_value(["rev-parse", "--short", "HEAD"], root)
    dirty = _dirty_state(root)
    smoke_passed = bool(summary["gate"]["passed"])
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Phase4F LAU-LTM Train Report\n\n")
        handle.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S %z')}\n")
        handle.write(f"Status: {'passed' if smoke_passed else 'failed'}\n\n")
        handle.write("## Code State\n\n")
        handle.write(f"- branch: `{branch}`\n")
        handle.write(f"- commit: `{commit}`\n")
        handle.write(f"- dirty: `{dirty}`\n\n")
        handle.write("## Inputs\n\n")
        handle.write(f"- dataset: `{_display(dataset_path, root)}`\n")
        handle.write(f"- samples: {summary['sample_count']}\n")
        handle.write(f"- feature_count: {summary['feature_count']}\n")
        handle.write(f"- rules: `{summary['rules']}`\n")
        handle.write(f"- validation_source: `{summary['validation_source']}`\n\n")
        handle.write("## Outputs\n\n")
        handle.write(f"- output_dir: `{_display(output_dir, root)}`\n")
        handle.write(f"- weights: `{_display(weights_path, root)}`\n")
        handle.write(f"- feature_stats: `{_display(feature_stats_path, root)}`\n")
        handle.write(f"- rules_json: `{_display(rules_path, root)}`\n\n")
        handle.write("## Training\n\n")
        handle.write(f"- epochs: {summary['epochs']}\n")
        handle.write(f"- hidden_dim: {summary['hidden_dim']}\n")
        handle.write(f"- drop_features: `{summary.get('drop_features', [])}`\n")
        handle.write(f"- soft_label_temperature: `{summary.get('soft_label_temperature')}`\n")
        handle.write(f"- soft_label_hard_mix: `{summary.get('soft_label_hard_mix')}`\n")
        handle.write(f"- final_loss: {summary['final_loss']:.6f}\n\n")
        handle.write("## Metrics\n\n")
        for prefix, metrics in (
            ("train", train_metrics),
            ("validation", validation_metrics),
        ):
            handle.write(f"### {prefix}\n\n")
            for key in (
                "sample_count",
                "rule_top1_accuracy",
                "rule_top3_accuracy",
                "non_neutral_rule_top1_accuracy",
                "harmful_update_precision",
                "harmful_update_recall",
                "harmful_update_f1",
                "safety_auroc",
                "predicted_best_rule_mean_delta_ratio_proxy",
                "neutral_additive_rate",
            ):
                handle.write(f"- {key}: `{metrics.get(key)}`\n")
            handle.write("\n")
        if test_metrics is not None:
            handle.write("### test\n\n")
            for key, value in test_metrics.items():
                handle.write(f"- {key}: `{value}`\n")
            handle.write("\n")
        else:
            handle.write("### test\n\n- map-holdout test performance: `not_available`\n\n")
        handle.write("## Gate\n\n")
        for key, value in summary["gate"].items():
            handle.write(f"- {key}: `{value}`\n")
        handle.write("\n")
        handle.write("## Caveat\n\n")
        if summary["validation_source"] == "validation":
            handle.write(
                "This report evaluates checkpoint-level update-rule prediction "
                "on collected probe labels. It is offline evidence only; runtime "
                "benefit still requires paired solver comparisons before making "
                "a learned-update performance claim.\n"
            )
        else:
            handle.write(
                "This smoke run proves the Phase4F training/export path only. "
                "Validation reused the available rows because no held-out split "
                "was present, so it must not be used as a learned-update "
                "performance claim.\n"
            )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--summary-json", type=Path)
    parser.add_argument("--epochs", type=int)
    parser.add_argument("--hidden-dim", type=int)
    parser.add_argument("--learning-rate", type=float)
    parser.add_argument("--weight-decay", type=float)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--device", default="cpu", choices=["cpu", "cuda", "auto"])
    parser.add_argument("--harmful-threshold", type=float, default=0.5)
    parser.add_argument("--drop-features")
    parser.add_argument("--probe-jsonl", type=Path)
    parser.add_argument("--soft-label-temperature", type=float)
    parser.add_argument("--soft-label-hard-mix", type=float)
    parser.add_argument("--soft-label-neutral-threshold", type=float)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = _repo_root()
    config_path = _resolve(args.config, root)
    config = _load_config(config_path)
    train_config = config.get("training", {}) if isinstance(config.get("training", {}), dict) else {}

    dataset_path = _resolve(args.dataset, root)
    output_dir = _resolve(args.output_dir, root)
    report_path = _resolve(args.report, root)
    summary_json_path = _resolve(args.summary_json, root) if args.summary_json else output_dir / "laur_mlp_v1_train_summary.json"
    probe_path = _resolve(args.probe_jsonl, root)
    if probe_path is None and config.get("probe_output_jsonl"):
        probe_path = _resolve(Path(str(config["probe_output_jsonl"])), root)
    if dataset_path is None or output_dir is None or report_path is None:
        raise ValueError("--dataset, --output-dir, and --report are required")

    rows = _read_jsonl(dataset_path)
    schema_errors = _validate_rows(rows)
    if schema_errors:
        raise ValueError("Phase4F dataset schema errors:\n" + "\n".join(schema_errors[:20]))

    cli_drop_features = _parse_drop_features(args.drop_features)
    config_drop_features = _parse_drop_features(train_config.get("drop_features"))
    drop_features = cli_drop_features or config_drop_features
    feature_names = _selected_feature_names(rows, drop_features)
    rules = _rule_vocab(rows)
    splits = _split_rows(rows)
    train_rows = splits["train"]
    validation_rows = splits["validation"]
    test_rows = splits["test"]
    train_matrix = _feature_matrix(train_rows, feature_names)
    feature_mean, feature_std = _feature_stats(train_matrix)

    epochs = int(args.epochs if args.epochs is not None else train_config.get("epochs", 300))
    hidden_dim = int(args.hidden_dim if args.hidden_dim is not None else train_config.get("hidden_dim", 64))
    learning_rate = float(args.learning_rate if args.learning_rate is not None else train_config.get("learning_rate", 1e-2))
    weight_decay = float(args.weight_decay if args.weight_decay is not None else train_config.get("weight_decay", 1e-4))
    seed = int(args.seed if args.seed is not None else train_config.get("seed", 7))
    soft_temperature = args.soft_label_temperature
    if soft_temperature is None and train_config.get("soft_label_temperature") is not None:
        soft_temperature = float(train_config["soft_label_temperature"])
    soft_hard_mix = args.soft_label_hard_mix
    if soft_hard_mix is None and train_config.get("soft_label_hard_mix") is not None:
        soft_hard_mix = float(train_config["soft_label_hard_mix"])
    soft_neutral_threshold = float(
        args.soft_label_neutral_threshold
        if args.soft_label_neutral_threshold is not None
        else train_config.get("soft_label_neutral_threshold", 0.005)
    )

    torch.manual_seed(seed)
    if args.device == "auto":
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    else:
        device = torch.device(args.device)

    model = LaurMlpV1(len(feature_names), len(rules), hidden_dim=hidden_dim).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=learning_rate, weight_decay=weight_decay)

    x_train = torch.tensor(_standardize(train_matrix, feature_mean, feature_std), dtype=torch.float32, device=device)
    rule_target, harmful, delta, neutral = _targets(train_rows, rules)
    y_rule = torch.tensor(rule_target, dtype=torch.long, device=device)
    y_harmful = torch.tensor(harmful, dtype=torch.float32, device=device)
    y_delta = torch.tensor(delta, dtype=torch.float32, device=device)
    y_neutral = torch.tensor(neutral, dtype=torch.float32, device=device)
    y_rule_soft = None
    if soft_temperature is not None:
        probe_rows = _read_probe_jsonl(probe_path)
        if not probe_rows:
            raise ValueError("--soft-label-temperature requires --probe-jsonl or config.probe_output_jsonl")
        soft_targets = _soft_rule_targets(
            train_rows,
            rules,
            _probe_rows_by_checkpoint(probe_rows),
            neutral_threshold=soft_neutral_threshold,
            temperature=float(soft_temperature),
            hard_mix=float(soft_hard_mix if soft_hard_mix is not None else 0.5),
        )
        y_rule_soft = torch.tensor(soft_targets, dtype=torch.float32, device=device)
    additive_index = rules.index("additive_ltm") if "additive_ltm" in rules else 0
    neutral_index = rules.index("neutral_additive") if "neutral_additive" in rules else None
    loss_weights = LaurLossWeights()

    final_loss = 0.0
    final_components: dict[str, float] = {}
    model.train()
    for _epoch in range(epochs):
        optimizer.zero_grad(set_to_none=True)
        outputs = model(x_train)
        losses = laur_ltm_loss(
            outputs,
            rule_target=y_rule,
            rule_target_probs=y_rule_soft,
            harmful_target=y_harmful,
            delta_target=y_delta,
            neutral_target=y_neutral,
            additive_index=additive_index,
            neutral_index=neutral_index,
            weights=loss_weights,
        )
        losses["total"].backward()
        optimizer.step()
        final_loss = float(losses["total"].detach().cpu())
        final_components = {
            key: float(value.detach().cpu()) for key, value in losses.items() if key != "total"
        }

    model.eval()
    train_metrics = _evaluate_model(
        model,
        train_rows,
        rules=rules,
        feature_names=feature_names,
        feature_mean=feature_mean,
        feature_std=feature_std,
        device=device,
        harmful_threshold=float(args.harmful_threshold),
    )
    validation_metrics = _evaluate_model(
        model,
        validation_rows,
        rules=rules,
        feature_names=feature_names,
        feature_mean=feature_mean,
        feature_std=feature_std,
        device=device,
        harmful_threshold=float(args.harmful_threshold),
    )
    test_metrics = (
        _evaluate_model(
            model,
            test_rows,
            rules=rules,
            feature_names=feature_names,
            feature_mean=feature_mean,
            feature_std=feature_std,
            device=device,
            harmful_threshold=float(args.harmful_threshold),
        )
        if test_rows
        else None
    )

    metadata = {
        "created_at": datetime.now().isoformat(),
        "dataset": str(dataset_path),
        "config": str(config_path) if config_path else None,
        "seed": seed,
        "epochs": epochs,
        "hidden_dim": hidden_dim,
        "learning_rate": learning_rate,
        "weight_decay": weight_decay,
        "feature_set": rows[0]["feature_set"],
        "drop_features": sorted(drop_features),
        "input_features": feature_names,
        "probe_jsonl": str(probe_path) if probe_path else None,
        "soft_label_temperature": soft_temperature,
        "soft_label_hard_mix": soft_hard_mix,
        "soft_label_neutral_threshold": soft_neutral_threshold if soft_temperature is not None else None,
    }
    paths = write_laur_mlp_exports(
        model,
        output_dir=output_dir,
        input_features=feature_names,
        feature_mean=feature_mean,
        feature_std=feature_std,
        rules=rules,
        metadata=metadata,
    )

    gate = {
        "train_script_runs_end_to_end": True,
        "schema_validation_passes": True,
        "model_export_file_exists": paths["weights"].exists(),
        "validation_metrics_computed": bool(validation_metrics),
        "phase4f_smoke_passed": paths["weights"].exists() and bool(validation_metrics),
    }
    gate["passed"] = all(bool(value) for value in gate.values())
    summary = {
        "schema_version": "phase4_laur_train_summary_v1",
        "sample_count": len(rows),
        "feature_count": len(feature_names),
        "rules": rules,
        "train_sample_count": len(train_rows),
        "validation_sample_count": len(validation_rows),
        "test_sample_count": len(test_rows),
        "validation_source": splits["validation_source"],
        "epochs": epochs,
        "hidden_dim": hidden_dim,
        "drop_features": sorted(drop_features),
        "soft_label_temperature": soft_temperature,
        "soft_label_hard_mix": soft_hard_mix,
        "soft_label_neutral_threshold": soft_neutral_threshold if soft_temperature is not None else None,
        "final_loss": final_loss,
        "loss_components": final_components,
        "train_metrics": train_metrics,
        "validation_metrics": validation_metrics,
        "test_metrics": test_metrics,
        "weights_path": str(paths["weights"]),
        "feature_stats_path": str(paths["feature_stats"]),
        "rules_path": str(paths["rules"]),
        "gate": gate,
    }
    summary_json_path.parent.mkdir(parents=True, exist_ok=True)
    summary_json_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    _write_report(
        report_path,
        root=root,
        dataset_path=dataset_path,
        output_dir=output_dir,
        weights_path=paths["weights"],
        feature_stats_path=paths["feature_stats"],
        rules_path=paths["rules"],
        train_metrics=train_metrics,
        validation_metrics=validation_metrics,
        test_metrics=test_metrics,
        summary=summary,
    )
    print(json.dumps({"report": str(report_path), "weights": str(paths["weights"]), "passed": gate["passed"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
