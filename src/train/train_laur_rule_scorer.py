"""Train an experimental rule-aware Phase4F LAUR scorer.

This is a P4 repair experiment for the failed Phase4F gate. Instead of mapping
one checkpoint directly to one hard update-rule class, the scorer sees
`(checkpoint_features, rule_features)` pairs and predicts the short-probe delta
for each candidate rule. At evaluation time it ranks all candidate rules and
uses the existing `neutral_additive` threshold as an explicit fallback class.
"""

from __future__ import annotations

import argparse
import csv
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

try:
    import torch
    from torch import nn
    import torch.nn.functional as F
except ImportError as exc:  # pragma: no cover - training is run in czr004 env
    raise RuntimeError("PyTorch is required for Phase4F rule-aware training") from exc


RULE_PARAM_NAMES = [
    "alpha_commit",
    "alpha_block",
    "alpha_wait",
    "rho_decay",
    "saturation_scale",
    "contraflow_penalty",
    "force_additive",
]


class RuleScorer(nn.Module):
    def __init__(self, input_dim: int, hidden_dim: int):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
        )
        self.delta_head = nn.Linear(hidden_dim, 1)
        self.harmful_head = nn.Linear(hidden_dim, 1)

    def forward(self, x: torch.Tensor) -> dict[str, torch.Tensor]:
        h = self.net(x)
        return {
            "delta": self.delta_head(h).squeeze(-1),
            "harmful_logit": self.harmful_head(h).squeeze(-1),
        }


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def resolve_path(path: str | Path | None, root: Path) -> Path | None:
    if path is None:
        return None
    value = Path(path)
    return value if value.is_absolute() else root / value


def read_jsonl(path: Path) -> list[dict[str, Any]]:
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


def validate_dataset(rows: list[dict[str, Any]]) -> None:
    errors: list[str] = []
    for index, row in enumerate(rows, 1):
        errors.extend(f"row {index}: {error}" for error in validate_update_dataset_row(row))
    if errors:
        raise ValueError("Phase4F dataset schema errors:\n" + "\n".join(errors[:20]))


def group_probe_rows(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["checkpoint_id"])].append(row)
    return grouped


def feature_names(rows: list[dict[str, Any]]) -> list[str]:
    names = list(rows[0]["feature_names"])
    for index, row in enumerate(rows, 1):
        if list(row["feature_names"]) != names:
            raise ValueError(f"row {index}: feature_names differ from row 1")
    return names


def rule_vocab(rows: list[dict[str, Any]]) -> list[str]:
    rules = list(rows[0]["target"]["rule_vocab"])
    for index, row in enumerate(rows, 1):
        if list(row["target"]["rule_vocab"]) != rules:
            raise ValueError(f"row {index}: target.rule_vocab differs from row 1")
    return rules


def probe_rule_vocab(probe_rows: list[dict[str, Any]]) -> list[str]:
    seen: list[str] = []
    for row in probe_rows:
        rule_id = str(row["rule_id"])
        if rule_id not in seen:
            seen.append(rule_id)
    return seen


def checkpoint_vector(row: dict[str, Any]) -> list[float]:
    return [float(value) for value in row["feature_vector"]]


def rule_feature_vector(rule_id: str, rule_params: dict[str, Any], probe_rules: list[str]) -> list[float]:
    one_hot = [1.0 if rule_id == candidate else 0.0 for candidate in probe_rules]
    params = []
    for name in RULE_PARAM_NAMES:
        value = rule_params.get(name, 0.0)
        params.append(1.0 if value is True else 0.0 if value is False else float(value))
    return one_hot + params


def pair_vector(
    dataset_row: dict[str, Any],
    probe_row: dict[str, Any],
    probe_rules: list[str],
) -> list[float]:
    return checkpoint_vector(dataset_row) + rule_feature_vector(
        str(probe_row["rule_id"]),
        probe_row.get("rule_params", {}),
        probe_rules,
    )


def split_rows(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["split"])].append(row)
    return grouped


def build_pair_samples(
    rows: list[dict[str, Any]],
    probe_by_checkpoint: dict[str, list[dict[str, Any]]],
    probe_rules: list[str],
) -> tuple[list[list[float]], list[float], list[float]]:
    x: list[list[float]] = []
    delta: list[float] = []
    harmful: list[float] = []
    for row in rows:
        for probe_row in probe_by_checkpoint.get(str(row["checkpoint_id"]), []):
            x.append(pair_vector(row, probe_row, probe_rules))
            delta.append(float(probe_row["delta_ratio_vs_additive"]))
            harmful.append(1.0 if probe_row.get("harmful") else 0.0)
    return x, delta, harmful


def feature_stats(matrix: list[list[float]]) -> tuple[list[float], list[float]]:
    dim = len(matrix[0])
    means = [sum(row[index] for row in matrix) / len(matrix) for index in range(dim)]
    stds: list[float] = []
    for index in range(dim):
        variance = sum((row[index] - means[index]) ** 2 for row in matrix) / len(matrix)
        std = math.sqrt(max(variance, 0.0))
        stds.append(std if std > 1e-12 else 1.0)
    return means, stds


def standardize(matrix: list[list[float]], means: list[float], stds: list[float]) -> list[list[float]]:
    return [[(value - means[index]) / stds[index] for index, value in enumerate(row)] for row in matrix]


def topk_indices(values: list[float], k: int) -> list[int]:
    return sorted(range(len(values)), key=lambda index: values[index], reverse=True)[:k]


def binary_metrics(labels: list[int], predictions: list[int]) -> dict[str, float]:
    tp = sum(1 for label, pred in zip(labels, predictions) if label == 1 and pred == 1)
    fp = sum(1 for label, pred in zip(labels, predictions) if label == 0 and pred == 1)
    fn = sum(1 for label, pred in zip(labels, predictions) if label == 1 and pred == 0)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2.0 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"precision": precision, "recall": recall, "f1": f1}


def binary_auroc(labels: list[int], scores: list[float]) -> float | None:
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


def predict_checkpoint(
    model: RuleScorer,
    row: dict[str, Any],
    probe_rows: list[dict[str, Any]],
    *,
    means: list[float],
    stds: list[float],
    probe_rules: list[str],
    full_rules: list[str],
    neutral_threshold: float,
    device: torch.device,
) -> dict[str, Any]:
    vectors = [pair_vector(row, probe_row, probe_rules) for probe_row in probe_rows]
    x = torch.tensor(standardize(vectors, means, stds), dtype=torch.float32, device=device)
    with torch.no_grad():
        outputs = model(x)
        delta_scores = [float(value) for value in outputs["delta"].cpu().tolist()]
        harmful_scores = [float(value) for value in torch.sigmoid(outputs["harmful_logit"]).cpu().tolist()]

    rule_to_score = {str(probe_row["rule_id"]): score for probe_row, score in zip(probe_rows, delta_scores)}
    class_scores: list[float] = []
    for rule_id in full_rules:
        if rule_id == "neutral_additive":
            class_scores.append(float(neutral_threshold))
        else:
            class_scores.append(float(rule_to_score.get(rule_id, -1e9)))
    top3 = topk_indices(class_scores, min(3, len(class_scores)))
    pred_index = top3[0]
    pred_rule = full_rules[pred_index]
    return {
        "predicted_rule": pred_rule,
        "predicted_rule_index": pred_index,
        "top3_indices": top3,
        "harmful_update_probability": max(harmful_scores) if harmful_scores else 0.0,
        "predicted_delta_score": class_scores[pred_index],
    }


def probe_delta_lookup(probe_rows: list[dict[str, Any]]) -> dict[tuple[str, str], float]:
    return {
        (str(row["checkpoint_id"]), str(row["rule_id"])): float(row["delta_ratio_vs_additive"])
        for row in probe_rows
    }


def evaluate(
    model: RuleScorer,
    rows: list[dict[str, Any]],
    *,
    probe_by_checkpoint: dict[str, list[dict[str, Any]]],
    probe_deltas: dict[tuple[str, str], float],
    means: list[float],
    stds: list[float],
    probe_rules: list[str],
    full_rules: list[str],
    neutral_threshold: float,
    harmful_threshold: float,
    device: torch.device,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    records: list[dict[str, Any]] = []
    for row in rows:
        checkpoint_id = str(row["checkpoint_id"])
        target_rule = str(row["target"]["rule_class"])
        target_index = full_rules.index(target_rule)
        prediction = predict_checkpoint(
            model,
            row,
            probe_by_checkpoint[checkpoint_id],
            means=means,
            stds=stds,
            probe_rules=probe_rules,
            full_rules=full_rules,
            neutral_threshold=neutral_threshold,
            device=device,
        )
        pred_rule = prediction["predicted_rule"]
        predicted_delta = 0.0 if pred_rule in {"additive_ltm", "neutral_additive"} else probe_deltas.get((checkpoint_id, pred_rule), 0.0)
        records.append(
            {
                "split": row["split"],
                "run_id": row["run_id"],
                "checkpoint_id": checkpoint_id,
                "map_name": row["map_name"],
                "agents": row["agents"],
                "seed": row["seed"],
                "iteration": row["iteration"],
                "target_rule": target_rule,
                "predicted_rule": pred_rule,
                "top1_correct": int(pred_rule == target_rule),
                "top3_correct": int(target_index in prediction["top3_indices"]),
                "harmful_update": int(bool(row["target"]["harmful_update"])),
                "harmful_update_probability": prediction["harmful_update_probability"],
                "harmful_prediction": int(prediction["harmful_update_probability"] >= harmful_threshold),
                "delta_ratio_best": float(row["target"]["delta_ratio_best"]),
                "predicted_rule_delta_ratio_vs_additive": predicted_delta,
                "neutral": int(bool(row["target"]["neutral"])),
                "predicted_delta_score": prediction["predicted_delta_score"],
            }
        )

    if not records:
        return {"sample_count": 0}, records
    top1 = [int(row["top1_correct"]) for row in records]
    top3 = [int(row["top3_correct"]) for row in records]
    non_neutral = [row for row in records if not int(row["neutral"])]
    harmful_labels = [int(row["harmful_update"]) for row in records]
    harmful_predictions = [int(row["harmful_prediction"]) for row in records]
    harmful_scores = [float(row["harmful_update_probability"]) for row in records]
    safety = binary_metrics(harmful_labels, harmful_predictions)
    metrics = {
        "sample_count": len(records),
        "rule_top1_accuracy": sum(top1) / len(top1),
        "rule_top3_accuracy": sum(top3) / len(top3),
        "non_neutral_rule_top1_accuracy": (
            sum(int(row["top1_correct"]) for row in non_neutral) / len(non_neutral)
            if non_neutral
            else None
        ),
        "harmful_update_precision": safety["precision"],
        "harmful_update_recall": safety["recall"],
        "harmful_update_f1": safety["f1"],
        "safety_auroc": binary_auroc(harmful_labels, harmful_scores),
        "predicted_rule_validation_mean_delta_ratio": sum(
            float(row["predicted_rule_delta_ratio_vs_additive"]) for row in records
        )
        / len(records),
        "neutral_additive_rate": sum(
            1 for row in records if row["predicted_rule"] in {"additive_ltm", "neutral_additive"}
        )
        / len(records),
        "label_distribution": dict(sorted(Counter(row["target_rule"] for row in records).items())),
        "predicted_rule_distribution": dict(sorted(Counter(row["predicted_rule"] for row in records).items())),
    }
    return metrics, records


def write_csv(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "split",
        "run_id",
        "checkpoint_id",
        "map_name",
        "agents",
        "seed",
        "iteration",
        "target_rule",
        "predicted_rule",
        "top1_correct",
        "top3_correct",
        "harmful_update",
        "harmful_update_probability",
        "harmful_prediction",
        "delta_ratio_best",
        "predicted_rule_delta_ratio_vs_additive",
        "neutral",
        "predicted_delta_score",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in records:
            writer.writerow({key: row[key] for key in fieldnames})


def git_value(args: list[str], cwd: Path) -> str:
    try:
        return subprocess.check_output(["git", *args], cwd=cwd, text=True).strip()
    except (FileNotFoundError, subprocess.CalledProcessError):
        return ""


def dirty_state(cwd: Path) -> str:
    tracked = git_value(["status", "--porcelain", "--untracked-files=no"], cwd)
    untracked = git_value(["status", "--porcelain", "--untracked-files=normal"], cwd)
    if tracked:
        return "tracked-dirty"
    if any(line.startswith("??") for line in untracked.splitlines()):
        return "tracked-clean_untracked-present"
    return "clean"


def write_report(
    path: Path,
    *,
    root: Path,
    summary: dict[str, Any],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    branch = git_value(["branch", "--show-current"], root)
    commit = git_value(["rev-parse", "--short", "HEAD"], root)
    dirty = dirty_state(root)
    validation = summary["metrics_by_split"].get("validation", {})
    train = summary["metrics_by_split"].get("train", {})
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Phase4F Rule-Aware Scorer Experiment\n\n")
        handle.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S %z')}\n\n")
        handle.write("## Code State\n\n")
        handle.write(f"- branch: `{branch}`\n")
        handle.write(f"- commit: `{commit}`\n")
        handle.write(f"- dirty: `{dirty}`\n\n")
        handle.write("## Inputs\n\n")
        handle.write(f"- dataset: `{summary['dataset']}`\n")
        handle.write(f"- probes: `{summary['probes']}`\n")
        handle.write(f"- train pair rows: `{summary['train_pair_count']}`\n")
        handle.write(f"- validation checkpoints: `{validation.get('sample_count')}`\n")
        handle.write(f"- neutral_threshold: `{summary['neutral_threshold']}`\n")
        handle.write(f"- harmful_threshold: `{summary['harmful_threshold']}`\n\n")
        handle.write("## Metrics\n\n")
        handle.write("| split | samples | top1 | top3 | harmful recall | harmful precision | mean predicted delta | neutral rate |\n")
        handle.write("|---|---:|---:|---:|---:|---:|---:|---:|\n")
        for name, metrics in (("train", train), ("validation", validation)):
            handle.write(
                f"| {name} | {metrics.get('sample_count')} | "
                f"{metrics.get('rule_top1_accuracy')} | {metrics.get('rule_top3_accuracy')} | "
                f"{metrics.get('harmful_update_recall')} | {metrics.get('harmful_update_precision')} | "
                f"{metrics.get('predicted_rule_validation_mean_delta_ratio')} | "
                f"{metrics.get('neutral_additive_rate')} |\n"
            )
        handle.write("\n## Interpretation\n\n")
        handle.write(
            "This is an offline P4 repair experiment. It tests whether rule-aware "
            "candidate scoring is a better direction than direct hard-class "
            "checkpoint classification. It is not a Phase5 runtime integration.\n"
        )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--probes", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--summary-json", type=Path, required=True)
    parser.add_argument("--summary-csv", type=Path, required=True)
    parser.add_argument("--epochs", type=int, default=700)
    parser.add_argument("--hidden-dim", type=int, default=96)
    parser.add_argument("--learning-rate", type=float, default=0.003)
    parser.add_argument("--weight-decay", type=float, default=0.001)
    parser.add_argument("--delta-scale", type=float, default=25.0)
    parser.add_argument("--safety-loss-weight", type=float, default=0.2)
    parser.add_argument("--neutral-threshold", type=float, default=0.005)
    parser.add_argument("--harmful-threshold", type=float, default=0.1)
    parser.add_argument("--seed", type=int, default=23)
    parser.add_argument("--device", choices=["cpu", "cuda", "auto"], default="cpu")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    dataset_path = resolve_path(args.dataset, root)
    probes_path = resolve_path(args.probes, root)
    output_dir = resolve_path(args.output_dir, root)
    report_path = resolve_path(args.report, root)
    summary_json_path = resolve_path(args.summary_json, root)
    summary_csv_path = resolve_path(args.summary_csv, root)
    if None in (dataset_path, probes_path, output_dir, report_path, summary_json_path, summary_csv_path):
        raise ValueError("all input/output paths are required")
    assert dataset_path and probes_path and output_dir and report_path and summary_json_path and summary_csv_path

    rows = read_jsonl(dataset_path)
    validate_dataset(rows)
    probes = read_jsonl(probes_path)
    by_checkpoint = group_probe_rows(probes)
    full_rules = rule_vocab(rows)
    candidate_rules = probe_rule_vocab(probes)
    splits = split_rows(rows)
    train_rows = splits.get("train", rows)
    validation_rows = splits.get("validation", rows)
    train_x, train_delta, train_harmful = build_pair_samples(train_rows, by_checkpoint, candidate_rules)
    means, stds = feature_stats(train_x)

    torch.manual_seed(int(args.seed))
    if args.device == "auto":
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    else:
        device = torch.device(args.device)
    model = RuleScorer(len(train_x[0]), int(args.hidden_dim)).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=float(args.learning_rate), weight_decay=float(args.weight_decay))

    x_tensor = torch.tensor(standardize(train_x, means, stds), dtype=torch.float32, device=device)
    delta_tensor = torch.tensor([value * float(args.delta_scale) for value in train_delta], dtype=torch.float32, device=device)
    harmful_tensor = torch.tensor(train_harmful, dtype=torch.float32, device=device)

    final_loss = 0.0
    model.train()
    for _epoch in range(int(args.epochs)):
        optimizer.zero_grad(set_to_none=True)
        outputs = model(x_tensor)
        delta_loss = F.smooth_l1_loss(outputs["delta"], delta_tensor)
        safety_loss = F.binary_cross_entropy_with_logits(outputs["harmful_logit"], harmful_tensor)
        loss = delta_loss + float(args.safety_loss_weight) * safety_loss
        loss.backward()
        optimizer.step()
        final_loss = float(loss.detach().cpu())

    # Convert the delta head back to original ratio units during inference by scaling weights.
    with torch.no_grad():
        model.delta_head.weight.div_(float(args.delta_scale))
        model.delta_head.bias.div_(float(args.delta_scale))

    model.eval()
    lookup = probe_delta_lookup(probes)
    metrics_by_split: dict[str, dict[str, Any]] = {}
    all_records: list[dict[str, Any]] = []
    for split_name, split_values in sorted(splits.items()):
        metrics, records = evaluate(
            model,
            split_values,
            probe_by_checkpoint=by_checkpoint,
            probe_deltas=lookup,
            means=means,
            stds=stds,
            probe_rules=candidate_rules,
            full_rules=full_rules,
            neutral_threshold=float(args.neutral_threshold),
            harmful_threshold=float(args.harmful_threshold),
            device=device,
        )
        metrics_by_split[split_name] = metrics
        all_records.extend(records)

    output_dir.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "model_state_dict": model.state_dict(),
            "input_mean": means,
            "input_std": stds,
            "candidate_rules": candidate_rules,
            "full_rules": full_rules,
            "feature_names": feature_names(rows),
            "rule_param_names": RULE_PARAM_NAMES,
            "neutral_threshold": float(args.neutral_threshold),
            "harmful_threshold": float(args.harmful_threshold),
        },
        output_dir / "laur_rule_scorer.pt",
    )
    write_csv(summary_csv_path, all_records)
    summary = {
        "schema_version": "phase4_laur_rule_scorer_experiment_v1",
        "dataset": str(dataset_path),
        "probes": str(probes_path),
        "output_dir": str(output_dir),
        "model_path": str(output_dir / "laur_rule_scorer.pt"),
        "epochs": int(args.epochs),
        "hidden_dim": int(args.hidden_dim),
        "learning_rate": float(args.learning_rate),
        "weight_decay": float(args.weight_decay),
        "delta_scale": float(args.delta_scale),
        "safety_loss_weight": float(args.safety_loss_weight),
        "neutral_threshold": float(args.neutral_threshold),
        "harmful_threshold": float(args.harmful_threshold),
        "seed": int(args.seed),
        "train_pair_count": len(train_x),
        "final_loss": final_loss,
        "metrics_by_split": metrics_by_split,
    }
    summary_json_path.parent.mkdir(parents=True, exist_ok=True)
    summary_json_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(report_path, root=root, summary=summary)
    print(json.dumps({"summary_json": str(summary_json_path), "report": str(report_path)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
