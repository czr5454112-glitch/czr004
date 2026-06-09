"""Evaluate a Repair5C top-k LAUR reranker checkpoint."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(ROOT / "src"))

from models.laur_attention_reranker import build_model  # noqa: E402
from train.train_laur_attention_reranker import (  # noqa: E402
    DEFAULT_BASE_EVAL_CSV,
    DEFAULT_CALIBRATION_JSON,
    DEFAULT_DATASET,
    DEFAULT_MODEL_PATH,
    build_examples,
    evaluate_examples,
    load_eval_rows,
    load_label_rows,
    load_thresholds,
)

try:
    import torch
except ImportError as exc:  # pragma: no cover
    raise RuntimeError("PyTorch is required for Repair5C reranker evaluation") from exc


DEFAULT_SUMMARY_JSON = "outputs/reports/phase4f_repair5c_top3_reranker_eval_summary.json"
DEFAULT_REPORT = "outputs/reports/phase4f_repair5c_top3_reranker_eval.md"


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


def write_report(path: Path, *, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    validation = summary.get("metrics_by_split", {}).get("validation", {})
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Phase4F Repair5C Top-K Reranker Eval\n\n")
        handle.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S %z').strip()}\n\n")
        handle.write("This is offline diagnostic evidence only. Phase5.5 runtime remains forbidden.\n\n")
        handle.write("## Validation\n\n")
        for key, value in validation.items():
            if isinstance(value, (int, float, str, bool)) or value is None:
                handle.write(f"- {key}: `{value}`\n")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=Path(DEFAULT_DATASET))
    parser.add_argument("--base-eval-csv", type=Path, default=Path(DEFAULT_BASE_EVAL_CSV))
    parser.add_argument("--calibration-json", type=Path, default=Path(DEFAULT_CALIBRATION_JSON))
    parser.add_argument("--model", type=Path, default=Path(DEFAULT_MODEL_PATH))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY_JSON))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--device", choices=["cpu", "cuda", "auto"], default="auto")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    dataset_path = resolve_path(args.dataset, root)
    eval_csv = resolve_path(args.base_eval_csv, root)
    calibration_json = resolve_path(args.calibration_json, root)
    model_path = resolve_path(args.model, root)
    summary_json = resolve_path(args.summary_json, root)
    report = resolve_path(args.report, root)
    if None in (dataset_path, eval_csv, model_path, summary_json, report):
        raise ValueError("dataset/eval/model/output paths are required")
    assert dataset_path and eval_csv and model_path and summary_json and report
    checkpoint = torch.load(model_path, map_location="cpu", weights_only=False)
    device = torch.device("cuda" if args.device == "auto" and torch.cuda.is_available() else ("cpu" if args.device == "auto" else args.device))
    thresholds = checkpoint.get("thresholds") or load_thresholds(calibration_json, 0.35)
    examples = build_examples(
        load_label_rows(dataset_path),
        load_eval_rows(eval_csv),
        thresholds=thresholds,
        top_k=int(checkpoint.get("top_k", 3)),
    )
    splits: dict[str, list[dict[str, Any]]] = {}
    for example in examples:
        splits.setdefault(str(example["split"]), []).append(example)
    model = build_model(checkpoint["model_name"], **checkpoint["model_args"]).to(device)
    model.load_state_dict(checkpoint["model_state_dict"])
    stats = checkpoint["feature_stats"]
    metrics_by_split = {
        split: evaluate_examples(model, rows, stats=stats, device=device, batch_size=int(args.batch_size))
        for split, rows in sorted(splits.items())
        if rows
    }
    summary = {
        "schema_version": "phase4f_repair5c_topk_reranker_eval_summary_v1",
        "created_at": datetime.now().isoformat(),
        "branch": git_value(["branch", "--show-current"], root),
        "commit": git_value(["rev-parse", "--short", "HEAD"], root),
        "dirty": dirty_state(root),
        "dataset": str(dataset_path),
        "base_eval_csv": str(eval_csv),
        "model": str(model_path),
        "metrics_by_split": metrics_by_split,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
    }
    summary_json.parent.mkdir(parents=True, exist_ok=True)
    summary_json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(report, summary=summary)
    print(json.dumps({"summary_json": str(summary_json), "report": str(report)}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
