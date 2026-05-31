"""Train the Repair5C top-k rule reranker from existing attention eval CSVs."""

from __future__ import annotations

import argparse
import ast
import csv
import json
import random
import subprocess
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(ROOT / "src"))

from czr004_teacher.stable_attention_dataset_laur import read_jsonl  # noqa: E402
from czr004_teacher.stable_attention_tokens_laur import EXECUTABLE_RULE_IDS, RULE_FAMILY_IDS, rule_family  # noqa: E402
from models.laur_attention_reranker import MODEL_NAME, MODEL_SCHEMA_VERSION, build_model, parameter_count  # noqa: E402

try:
    import torch
    import torch.nn.functional as F
except ImportError as exc:  # pragma: no cover
    raise RuntimeError("PyTorch is required for Repair5C reranker training") from exc


DEFAULT_DATASET = (
    "artifacts/teacher/laur/full_repair5_attention_native_expand5000_rawtrace_hightoken/update_labels/"
    "phase4_laur_attention_native_expand5000_rawtrace_hightoken_dataset.jsonl.zst"
)
DEFAULT_BASE_EVAL_CSV = (
    "outputs/tables/"
    "phase4f_repair5_expand5000_postnext_hightoken_attn_mlp_head_rank_recall_perrule_eval_seed61.csv"
)
DEFAULT_CALIBRATION_JSON = "outputs/reports/phase4f_repair5_per_rule_safety_calibration.json"
DEFAULT_MODEL_PATH = "artifacts/models/laur_ltm/repair5c_top3_reranker_seed61/model.pt"
DEFAULT_REPORT = "outputs/reports/phase4f_repair5c_top3_reranker_train.md"
DEFAULT_SUMMARY_JSON = "outputs/reports/phase4f_repair5c_top3_reranker_train_summary.json"

CANDIDATE_FEATURE_NAMES = [
    "rank_score",
    "score_minus_additive",
    "harmful_probability",
    "safety_margin",
    "rank_minus_harmful",
    "opportunity_probability",
    "defer_probability",
    "anti_margin",
    "is_additive",
    "is_high_margin_sample",
    "family_id_norm",
]


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def resolve_path(path: str | Path | None, root: Path) -> Path | None:
    if path is None:
        return None
    value = Path(path)
    return value if value.is_absolute() else root / value


def git_value(args: list[str], cwd: Path) -> str:
    try:
        return subprocess.check_output(["git", *args], cwd=cwd, text=True).strip()
    except (FileNotFoundError, subprocess.CalledProcessError):
        return ""


def dirty_state(root: Path) -> str:
    status = git_value(["status", "--short"], root)
    if not status:
        return "clean"
    tracked = [line for line in status.splitlines() if not line.startswith("??")]
    untracked = [line for line in status.splitlines() if line.startswith("??")]
    if tracked and untracked:
        return "tracked-dirty_untracked-present"
    if tracked:
        return "tracked-dirty"
    return "untracked-present"


def parse_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    text = str(value or "").strip()
    if not text:
        return []
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        try:
            parsed = ast.literal_eval(text)
        except (SyntaxError, ValueError):
            return []
    return parsed if isinstance(parsed, list) else []


def finite(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    if number != number or number in {float("inf"), float("-inf")}:
        return default
    return number


def topk_indices(values: list[float], k: int) -> list[int]:
    return sorted(range(len(values)), key=lambda index: values[index], reverse=True)[: max(1, int(k))]


def load_eval_rows(path: Path) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            checkpoint_id = str(row.get("checkpoint_id", ""))
            if checkpoint_id:
                rows[checkpoint_id] = row
    return rows


def load_label_rows(path: Path) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for row in read_jsonl(path):
        if row.get("rule_ids") != EXECUTABLE_RULE_IDS:
            continue
        checkpoint_id = str(row.get("checkpoint_id", ""))
        if checkpoint_id:
            rows[checkpoint_id] = row
    return rows


def load_thresholds(path: Path | None, default_threshold: float) -> list[float]:
    if path is None or not path.exists():
        return [float(default_threshold)] * len(EXECUTABLE_RULE_IDS)
    payload = json.loads(path.read_text(encoding="utf-8"))
    by_rule = payload.get("threshold_by_rule") or {}
    if by_rule:
        return [finite(by_rule.get(rule), default_threshold) for rule in EXECUTABLE_RULE_IDS]
    threshold = payload.get("threshold")
    if threshold is None and isinstance(payload.get("global_threshold"), dict):
        threshold = payload["global_threshold"].get("threshold")
    return [finite(threshold, default_threshold)] * len(EXECUTABLE_RULE_IDS)


def _family_id_norm(rule_id: str) -> float:
    family = rule_family(rule_id)
    index = RULE_FAMILY_IDS.index(family) if family in RULE_FAMILY_IDS else 0
    return float(index) / float(max(1, len(RULE_FAMILY_IDS) - 1))


def build_reranker_example(
    label: dict[str, Any],
    eval_row: dict[str, Any],
    *,
    thresholds: list[float],
    top_k: int,
) -> dict[str, Any] | None:
    scores = [finite(value) for value in parse_list(eval_row.get("rule_scores"))]
    harmful_probs = [finite(value) for value in parse_list(eval_row.get("harmful_probs"))]
    if len(scores) != len(EXECUTABLE_RULE_IDS) or len(harmful_probs) != len(EXECUTABLE_RULE_IDS):
        return None
    additive = EXECUTABLE_RULE_IDS.index("additive_ltm")
    candidates = topk_indices(scores, top_k)
    utilities = [finite(value) for value in label["risk_adjusted_utility_vector"]]
    deltas = [finite(value) for value in label["probe_delta_vector"]]
    harmful_labels = [1 if value else 0 for value in label["probe_harmful_vector"]]
    target_index = int(label["target"]["target_rule_index"])
    if label["decision_target"] == "use_nonadditive" and target_index in candidates:
        target_pos = candidates.index(target_index)
    else:
        safe_candidates = [index for index in candidates if index != additive and not harmful_labels[index]]
        best = max(safe_candidates, key=lambda index: utilities[index]) if safe_candidates else candidates[0]
        target_pos = candidates.index(best)
    opportunity = finite(eval_row.get("opportunity_prob"))
    defer = finite(eval_row.get("defer_prob"))
    features: list[list[float]] = []
    for index in candidates:
        threshold = thresholds[index] if index < len(thresholds) else thresholds[-1]
        safety_margin = float(threshold) - float(harmful_probs[index])
        features.append(
            [
                float(scores[index]),
                float(scores[index] - scores[additive]),
                float(harmful_probs[index]),
                safety_margin,
                float(scores[index] - harmful_probs[index]),
                opportunity,
                defer,
                opportunity - defer,
                1.0 if index == additive else 0.0,
                1.0 if bool(label["has_high_margin_nonadditive_opportunity"]) else 0.0,
                _family_id_norm(EXECUTABLE_RULE_IDS[index]),
            ]
        )
    return {
        "split": label["split"],
        "checkpoint_id": label["checkpoint_id"],
        "candidate_rule_indices": candidates,
        "candidate_features": features,
        "candidate_utilities": [utilities[index] for index in candidates],
        "candidate_deltas": [deltas[index] for index in candidates],
        "candidate_harmful_labels": [harmful_labels[index] for index in candidates],
        "target_pos": int(target_pos),
        "target_rule_index": target_index,
        "additive_delta": deltas[additive],
        "additive_utility": utilities[additive],
        "decision_target": label["decision_target"],
        "has_high_margin_nonadditive_opportunity": bool(label["has_high_margin_nonadditive_opportunity"]),
    }


def build_examples(
    labels: dict[str, dict[str, Any]],
    eval_rows: dict[str, dict[str, Any]],
    *,
    thresholds: list[float],
    top_k: int,
) -> list[dict[str, Any]]:
    examples: list[dict[str, Any]] = []
    for checkpoint_id in sorted(set(labels) & set(eval_rows)):
        example = build_reranker_example(labels[checkpoint_id], eval_rows[checkpoint_id], thresholds=thresholds, top_k=top_k)
        if example is not None:
            examples.append(example)
    return examples


def feature_stats(examples: list[dict[str, Any]]) -> dict[str, list[float]]:
    vectors = [
        feature
        for example in examples
        for feature in example["candidate_features"]
    ]
    if not vectors:
        return {"mean": [0.0] * len(CANDIDATE_FEATURE_NAMES), "std": [1.0] * len(CANDIDATE_FEATURE_NAMES)}
    mean = [sum(row[index] for row in vectors) / len(vectors) for index in range(len(CANDIDATE_FEATURE_NAMES))]
    std: list[float] = []
    for index in range(len(CANDIDATE_FEATURE_NAMES)):
        variance = sum((row[index] - mean[index]) ** 2 for row in vectors) / len(vectors)
        value = variance ** 0.5
        std.append(value if value > 1.0e-12 else 1.0)
    return {"mean": mean, "std": std}


def standardize_features(features: list[list[float]], stats: dict[str, list[float]]) -> list[list[float]]:
    return [
        [
            (float(value) - float(stats["mean"][index])) / float(stats["std"][index])
            for index, value in enumerate(row)
        ]
        for row in features
    ]


def batched(values: list[dict[str, Any]], batch_size: int, *, shuffle: bool = False) -> list[list[dict[str, Any]]]:
    rows = list(values)
    if shuffle:
        random.shuffle(rows)
    size = max(1, int(batch_size))
    return [rows[index : index + size] for index in range(0, len(rows), size)]


def rows_to_batch(rows: list[dict[str, Any]], stats: dict[str, list[float]], device: torch.device) -> dict[str, Any]:
    return {
        "candidate_features": torch.tensor(
            [standardize_features(row["candidate_features"], stats) for row in rows],
            dtype=torch.float32,
            device=device,
        ),
        "candidate_rule_indices": torch.tensor(
            [row["candidate_rule_indices"] for row in rows],
            dtype=torch.long,
            device=device,
        ),
        "candidate_mask": torch.ones((len(rows), len(rows[0]["candidate_rule_indices"])), dtype=torch.bool, device=device),
        "target_pos": torch.tensor([int(row["target_pos"]) for row in rows], dtype=torch.long, device=device),
        "candidate_utilities": torch.tensor(
            [row["candidate_utilities"] for row in rows],
            dtype=torch.float32,
            device=device,
        ),
    }


def evaluate_examples(
    model: Any,
    examples: list[dict[str, Any]],
    *,
    stats: dict[str, list[float]],
    device: torch.device,
    batch_size: int,
) -> dict[str, Any]:
    if not examples:
        return {"sample_count": 0}
    model.eval()
    records: list[dict[str, Any]] = []
    with torch.no_grad():
        for batch_rows in batched(examples, batch_size):
            batch = rows_to_batch(batch_rows, stats, device)
            scores = model(batch)["candidate_scores"].detach().cpu().tolist()
            for row, row_scores in zip(batch_rows, scores):
                selected_pos = int(max(range(len(row_scores)), key=lambda index: float(row_scores[index])))
                selected_rule_index = int(row["candidate_rule_indices"][selected_pos])
                target_pos = int(row["target_pos"])
                utilities = [finite(value) for value in row["candidate_utilities"]]
                deltas = [finite(value) for value in row["candidate_deltas"]]
                harmful = [int(value) for value in row["candidate_harmful_labels"]]
                oracle_pos = int(max(range(len(utilities)), key=lambda index: utilities[index]))
                records.append(
                    {
                        "split": row["split"],
                        "checkpoint_id": row["checkpoint_id"],
                        "selected_rule_index": selected_rule_index,
                        "selected_rule": EXECUTABLE_RULE_IDS[selected_rule_index],
                        "target_pos": target_pos,
                        "target_in_candidates": int(int(row["target_rule_index"]) in row["candidate_rule_indices"]),
                        "top1": int(selected_pos == target_pos),
                        "selected_utility": utilities[selected_pos],
                        "oracle_utility": utilities[oracle_pos],
                        "utility_regret": utilities[oracle_pos] - utilities[selected_pos],
                        "selected_delta": deltas[selected_pos],
                        "selected_vs_additive_delta": deltas[selected_pos] - finite(row["additive_delta"]),
                        "selected_harmful": harmful[selected_pos],
                        "high_margin": int(bool(row["has_high_margin_nonadditive_opportunity"])),
                    }
                )
    high_margin = [row for row in records if row["high_margin"]]
    return {
        "sample_count": len(records),
        "top1_among_candidates": sum(row["top1"] for row in records) / len(records),
        "target_in_candidates_rate": sum(row["target_in_candidates"] for row in records) / len(records),
        "utility_regret": sum(row["utility_regret"] for row in records) / len(records),
        "selected_vs_additive_delta": sum(row["selected_vs_additive_delta"] for row in records) / len(records),
        "selected_harmful_rate": sum(row["selected_harmful"] for row in records) / len(records),
        "high_margin_capture_proxy": (
            sum(
                1
                for row in high_margin
                if row["selected_rule"] != "additive_ltm"
                and not row["selected_harmful"]
                and finite(row["selected_vs_additive_delta"]) > 0.0
            )
            / len(high_margin)
            if high_margin
            else 0.0
        ),
        "selected_rule_distribution": dict(sorted(Counter(row["selected_rule"] for row in records).items())),
    }


def write_report(path: Path, *, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    validation = summary.get("metrics_by_split", {}).get("validation", {})
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Phase4F Repair5C Top-K Reranker Train Report\n\n")
        handle.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S %z').strip()}\n\n")
        handle.write("## Boundary\n\n")
        handle.write("This is an offline reranker diagnostic. It does not permit Phase5.5 runtime promotion.\n\n")
        handle.write("## Validation\n\n")
        for key in (
            "sample_count",
            "top1_among_candidates",
            "target_in_candidates_rate",
            "utility_regret",
            "selected_vs_additive_delta",
            "selected_harmful_rate",
            "high_margin_capture_proxy",
        ):
            handle.write(f"- {key}: `{validation.get(key)}`\n")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=Path(DEFAULT_DATASET))
    parser.add_argument("--base-eval-csv", type=Path, default=Path(DEFAULT_BASE_EVAL_CSV))
    parser.add_argument("--calibration-json", type=Path, default=Path(DEFAULT_CALIBRATION_JSON))
    parser.add_argument("--model-path", type=Path, default=Path(DEFAULT_MODEL_PATH))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY_JSON))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--seed", type=int, default=61)
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--epochs", type=int, default=25)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--lr", type=float, default=1.0e-3)
    parser.add_argument("--weight-decay", type=float, default=1.0e-4)
    parser.add_argument("--lambda-utility", type=float, default=0.1)
    parser.add_argument("--hidden-dim", type=int, default=48)
    parser.add_argument("--dropout", type=float, default=0.1)
    parser.add_argument("--device", choices=["cpu", "cuda", "auto"], default="auto")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    random.seed(int(args.seed))
    torch.manual_seed(int(args.seed))
    device = torch.device("cuda" if args.device == "auto" and torch.cuda.is_available() else ("cpu" if args.device == "auto" else args.device))
    dataset_path = resolve_path(args.dataset, root)
    eval_csv = resolve_path(args.base_eval_csv, root)
    calibration_json = resolve_path(args.calibration_json, root)
    model_path = resolve_path(args.model_path, root)
    summary_json = resolve_path(args.summary_json, root)
    report = resolve_path(args.report, root)
    if None in (dataset_path, eval_csv, model_path, summary_json, report):
        raise ValueError("dataset/eval/model/output paths are required")
    assert dataset_path and eval_csv and model_path and summary_json and report
    thresholds = load_thresholds(calibration_json, 0.35)
    examples = build_examples(
        load_label_rows(dataset_path),
        load_eval_rows(eval_csv),
        thresholds=thresholds,
        top_k=int(args.top_k),
    )
    splits: dict[str, list[dict[str, Any]]] = {"train": [], "validation": []}
    for example in examples:
        splits.setdefault(str(example["split"]), []).append(example)
    train_examples = splits.get("train") or examples
    validation_examples = splits.get("validation") or examples
    stats = feature_stats(train_examples)
    model_args = {
        "feature_dim": len(CANDIDATE_FEATURE_NAMES),
        "num_rules": len(EXECUTABLE_RULE_IDS),
        "hidden_dim": int(args.hidden_dim),
        "dropout": float(args.dropout),
    }
    model = build_model(MODEL_NAME, **model_args).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=float(args.lr), weight_decay=float(args.weight_decay))
    epoch_records: list[dict[str, Any]] = []
    for epoch in range(1, int(args.epochs) + 1):
        model.train()
        total = 0.0
        count = 0
        for batch_rows in batched(train_examples, int(args.batch_size), shuffle=True):
            batch = rows_to_batch(batch_rows, stats, device)
            outputs = model(batch)
            scores = outputs["candidate_scores"]
            ce = F.cross_entropy(scores, batch["target_pos"])
            utility_loss = F.mse_loss(scores, batch["candidate_utilities"])
            loss = ce + float(args.lambda_utility) * utility_loss
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            optimizer.step()
            total += float(loss.detach().cpu()) * len(batch_rows)
            count += len(batch_rows)
        epoch_records.append({"epoch": epoch, "train_loss": total / max(1, count)})
    metrics_by_split = {
        split: evaluate_examples(model, rows, stats=stats, device=device, batch_size=int(args.batch_size))
        for split, rows in sorted(splits.items())
        if rows
    }
    checkpoint = {
        "schema_version": MODEL_SCHEMA_VERSION,
        "model_name": MODEL_NAME,
        "model_args": model_args,
        "model_state_dict": model.state_dict(),
        "feature_stats": stats,
        "feature_names": CANDIDATE_FEATURE_NAMES,
        "top_k": int(args.top_k),
        "thresholds": thresholds,
        "seed": int(args.seed),
    }
    model_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(checkpoint, model_path)
    summary = {
        "schema_version": "phase4f_repair5c_topk_reranker_train_summary_v1",
        "created_at": datetime.now().isoformat(),
        "branch": git_value(["branch", "--show-current"], root),
        "commit": git_value(["rev-parse", "--short", "HEAD"], root),
        "dirty": dirty_state(root),
        "dataset": str(dataset_path),
        "base_eval_csv": str(eval_csv),
        "calibration_json": str(calibration_json) if calibration_json else None,
        "model_path": str(model_path),
        "model_name": MODEL_NAME,
        "parameter_count": parameter_count(model),
        "seed": int(args.seed),
        "top_k": int(args.top_k),
        "epochs": int(args.epochs),
        "epoch_records": epoch_records,
        "metrics_by_split": metrics_by_split,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
    }
    summary_json.parent.mkdir(parents=True, exist_ok=True)
    summary_json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(report, summary=summary)
    print(json.dumps({"model_path": str(model_path), "summary_json": str(summary_json), "report": str(report)}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
