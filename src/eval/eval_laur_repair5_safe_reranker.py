"""Safe reranker wrapper diagnostic for Repair5D LAUR.

Pipeline: base top-k candidates -> per-rule/per-family safety mask -> reranker
over remaining safe candidates -> utility-margin defer decision. This is an
offline diagnostic and cannot promote Phase5.5 runtime.
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(ROOT / "src"))

from czr004_teacher.stable_attention_tokens_laur import EXECUTABLE_RULE_IDS, rule_family  # noqa: E402
from eval.eval_laur_repair5_composite_inference import (  # noqa: E402
    DEFAULT_CALIBRATION_JSON,
    DEFAULT_DATASET,
    DEFAULT_RANKING_CSV,
    finite,
    load_eval_rows,
    load_label_rows,
    parse_list,
    resolve_path,
    thresholds_from_calibration,
    topk_indices,
)
from train.train_laur_attention_reranker import (  # noqa: E402
    CANDIDATE_FEATURE_NAMES,
    DEFAULT_MODEL_PATH,
    build_reranker_example,
    standardize_features,
)

try:
    import torch
except ImportError:  # pragma: no cover
    torch = None  # type: ignore[assignment]

try:
    from models.laur_attention_reranker import build_model
except Exception:  # pragma: no cover
    build_model = None  # type: ignore[assignment]


DEFAULT_SUMMARY_JSON = "outputs/reports/phase4f_repair5_safe_reranker_summary.json"
DEFAULT_RECORDS_CSV = "outputs/tables/phase4f_repair5_safe_reranker.csv"
DEFAULT_REPORT = "outputs/reports/phase4f_repair5_safe_reranker.md"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


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


def load_json(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


class RerankerScorer:
    def __init__(self, model_path: Path | None, *, device_name: str = "cpu") -> None:
        self.available = False
        self.reason = "not_requested"
        self.checkpoint: dict[str, Any] = {}
        self.model: Any = None
        self.device: Any = None
        if model_path is None:
            return
        if torch is None or build_model is None:
            self.reason = "torch_or_model_builder_unavailable"
            return
        if not model_path.exists():
            self.reason = "model_path_missing"
            return
        self.checkpoint = torch.load(model_path, map_location="cpu", weights_only=False)
        self.device = torch.device(device_name)
        self.model = build_model(self.checkpoint["model_name"], **self.checkpoint["model_args"]).to(self.device)
        self.model.load_state_dict(self.checkpoint["model_state_dict"])
        self.model.eval()
        self.available = True
        self.reason = "loaded"

    def score(self, label: dict[str, Any], eval_row: dict[str, Any], *, thresholds: list[float], top_k: int) -> dict[int, float]:
        if not self.available:
            return {}
        example = build_reranker_example(label, eval_row, thresholds=thresholds, top_k=top_k)
        if example is None:
            return {}
        features = standardize_features(example["candidate_features"], self.checkpoint["feature_stats"])
        with torch.no_grad():
            batch = {
                "candidate_features": torch.tensor([features], dtype=torch.float32, device=self.device),
                "candidate_rule_indices": torch.tensor([example["candidate_rule_indices"]], dtype=torch.long, device=self.device),
                "candidate_mask": torch.ones((1, len(example["candidate_rule_indices"])), dtype=torch.bool, device=self.device),
            }
            scores = self.model(batch)["candidate_scores"].detach().cpu().tolist()[0]
        return {int(rule_index): float(score) for rule_index, score in zip(example["candidate_rule_indices"], scores)}


def oracle_best_safe(utilities: list[float], harmful_labels: list[int]) -> int | None:
    additive = EXECUTABLE_RULE_IDS.index("additive_ltm")
    candidates = [
        index
        for index, label in enumerate(harmful_labels)
        if index != additive and not int(label)
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda index: (utilities[index], -index))


def safe_reranker_records(
    *,
    labels: dict[str, dict[str, Any]],
    eval_rows: dict[str, dict[str, Any]],
    calibration: dict[str, Any],
    scorer: RerankerScorer | None,
    top_k: int,
    safety_scope: str,
    default_threshold: float,
    opportunity_threshold: float,
    defer_threshold: float,
    min_utility_margin: float,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    additive = EXECUTABLE_RULE_IDS.index("additive_ltm")
    thresholds = thresholds_from_calibration(calibration, mode=safety_scope, default_threshold=default_threshold)
    records: list[dict[str, Any]] = []
    for checkpoint_id in sorted(set(labels) & set(eval_rows)):
        label = labels[checkpoint_id]
        eval_row = eval_rows[checkpoint_id]
        scores = [finite(value) for value in parse_list(eval_row.get("rule_scores"))]
        harmful_probs = [finite(value) for value in parse_list(eval_row.get("harmful_probs"))]
        if len(scores) != len(EXECUTABLE_RULE_IDS) or len(harmful_probs) != len(EXECUTABLE_RULE_IDS):
            continue
        candidates = topk_indices(scores, top_k)
        harmful_labels = [1 if value else 0 for value in label["probe_harmful_vector"]]
        utilities = [finite(value) for value in label["risk_adjusted_utility_vector"]]
        deltas = [finite(value) for value in label["probe_delta_vector"]]
        target_index = int(label["target"]["target_rule_index"])
        unsafe = [
            float(harmful_probs[index]) >= float(thresholds[index])
            for index in range(len(EXECUTABLE_RULE_IDS))
        ]
        safe_candidates = [index for index in candidates if index != additive and not unsafe[index]]
        opportunity = finite(eval_row.get("opportunity_prob"))
        defer = finite(eval_row.get("defer_prob"))
        selected = additive
        selected_decision = "defer_ltm"
        reason = "no_safe_candidate"
        if opportunity < opportunity_threshold:
            reason = "low_opportunity"
        elif defer >= defer_threshold:
            reason = "defer_probability"
        elif safe_candidates:
            reranker_scores = scorer.score(label, eval_row, thresholds=thresholds, top_k=top_k) if scorer else {}
            if reranker_scores:
                selected = max(safe_candidates, key=lambda index: (reranker_scores.get(index, -1.0e9), scores[index], -index))
                reason = "safe_reranker_score"
            else:
                selected = max(safe_candidates, key=lambda index: (utilities[index], scores[index], -index))
                reason = "safe_oracle_utility_fallback"
            if utilities[selected] - utilities[additive] >= min_utility_margin:
                selected_decision = "use_nonadditive"
            else:
                reason = "utility_margin_defer"
                selected = additive
        oracle_best = oracle_best_safe(utilities, harmful_labels)
        records.append(
            {
                "split": label["split"],
                "checkpoint_id": checkpoint_id,
                "run_id": label["run_id"],
                "map_name": label["map_name"],
                "agents": label["agents"],
                "seed": label["seed"],
                "iteration": label["iteration"],
                "top_k": top_k,
                "safety_scope": safety_scope,
                "target_rule": label["target_rule"],
                "target_in_candidates": target_index in candidates,
                "top1_among_candidates": bool(target_index == candidates[0]) if candidates else False,
                "selected_decision": selected_decision,
                "selected_rule": EXECUTABLE_RULE_IDS[selected],
                "selection_reason": reason,
                "candidate_rules": json.dumps([EXECUTABLE_RULE_IDS[index] for index in candidates]),
                "safe_candidate_rules": json.dumps([EXECUTABLE_RULE_IDS[index] for index in safe_candidates]),
                "selected_delta": deltas[selected],
                "additive_delta": deltas[additive],
                "selected_vs_additive_delta": deltas[selected] - deltas[additive],
                "selected_utility": utilities[selected],
                "additive_utility": utilities[additive],
                "selected_vs_additive_utility": utilities[selected] - utilities[additive],
                "oracle_best_safe_rule": EXECUTABLE_RULE_IDS[oracle_best] if oracle_best is not None else "",
                "utility_regret_to_oracle": utilities[oracle_best] - utilities[selected] if oracle_best is not None else 0.0,
                "selected_harmful": bool(harmful_labels[selected]),
                "has_high_margin_nonadditive_opportunity": bool(label["has_high_margin_nonadditive_opportunity"]),
                "opportunity_margin": finite(label.get("audit", {}).get("label_params", {}).get("opportunity_margin"), 0.010),
            }
        )
    return records, summarize_records(records)


def summarize_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    if not records:
        return {"sample_count": 0}
    high_margin = [row for row in records if bool(row["has_high_margin_nonadditive_opportunity"])]
    captured = [
        row
        for row in high_margin
        if row["selected_decision"] == "use_nonadditive"
        and row["selected_rule"] != "additive_ltm"
        and not bool(row["selected_harmful"])
        and float(row["selected_vs_additive_delta"]) >= float(row["opportunity_margin"])
    ]
    return {
        "sample_count": len(records),
        "top1_among_candidates": sum(1 for row in records if bool(row["top1_among_candidates"])) / len(records),
        "target_in_candidate_set": sum(1 for row in records if bool(row["target_in_candidates"])) / len(records),
        "selected_vs_additive_delta": sum(float(row["selected_vs_additive_delta"]) for row in records) / len(records),
        "selected_vs_additive_utility": sum(float(row["selected_vs_additive_utility"]) for row in records) / len(records),
        "utility_regret_to_oracle": sum(float(row["utility_regret_to_oracle"]) for row in records) / len(records),
        "selected_harmful_rate": sum(1 for row in records if bool(row["selected_harmful"])) / len(records),
        "high_margin_capture": len(captured) / len(high_margin) if high_margin else 0.0,
        "fallback_defer_rate": sum(1 for row in records if row["selected_decision"] == "defer_ltm") / len(records),
        "selected_rule_distribution": dict(sorted(Counter(str(row["selected_rule"]) for row in records).items())),
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()), extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_report(path: Path, *, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    metrics = summary.get("metrics", {})
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Phase4F Repair5 Safe Reranker Diagnostic\n\n")
        handle.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S %z').strip()}\n\n")
        handle.write("This is an offline safe-reranker wrapper diagnostic. Phase5.5 and Phase6 remain forbidden.\n\n")
        handle.write("## Metrics\n\n")
        for key, value in metrics.items():
            if isinstance(value, (int, float, str, bool)) or value is None:
                handle.write(f"- {key}: `{value}`\n")
        handle.write("\n## Reranker\n\n")
        handle.write(f"- model status: `{summary.get('reranker_status')}`\n")
        handle.write(f"- model path: `{summary.get('model_path')}`\n")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=Path(DEFAULT_DATASET))
    parser.add_argument("--base-eval-csv", type=Path, default=Path(DEFAULT_RANKING_CSV))
    parser.add_argument("--calibration-json", type=Path, default=Path(DEFAULT_CALIBRATION_JSON))
    parser.add_argument("--model", type=Path, default=Path(DEFAULT_MODEL_PATH))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY_JSON))
    parser.add_argument("--records-csv", type=Path, default=Path(DEFAULT_RECORDS_CSV))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--split", default="validation")
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--safety-scope", choices=["per_rule", "per_family", "global"], default="per_rule")
    parser.add_argument("--default-threshold", type=float, default=0.35)
    parser.add_argument("--opportunity-threshold", type=float, default=0.50)
    parser.add_argument("--defer-threshold", type=float, default=0.50)
    parser.add_argument("--min-utility-margin", type=float, default=0.0)
    parser.add_argument("--device", choices=["cpu", "cuda"], default="cpu")
    parser.add_argument("--no-model", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    dataset = resolve_path(args.dataset, root)
    base_eval_csv = resolve_path(args.base_eval_csv, root)
    calibration_json = resolve_path(args.calibration_json, root)
    model_path = None if args.no_model else resolve_path(args.model, root)
    summary_json = resolve_path(args.summary_json, root)
    records_csv = resolve_path(args.records_csv, root)
    report = resolve_path(args.report, root)
    if None in (dataset, base_eval_csv, summary_json, records_csv, report):
        raise ValueError("required paths could not be resolved")
    assert dataset and base_eval_csv and summary_json and records_csv and report
    scorer = RerankerScorer(model_path, device_name=str(args.device)) if model_path is not None else None
    records, metrics = safe_reranker_records(
        labels=load_label_rows(dataset, split=str(args.split)),
        eval_rows=load_eval_rows(base_eval_csv, split=str(args.split)),
        calibration=load_json(calibration_json),
        scorer=scorer,
        top_k=int(args.top_k),
        safety_scope=str(args.safety_scope),
        default_threshold=float(args.default_threshold),
        opportunity_threshold=float(args.opportunity_threshold),
        defer_threshold=float(args.defer_threshold),
        min_utility_margin=float(args.min_utility_margin),
    )
    summary = {
        "schema_version": "phase4f_repair5_safe_reranker_v1",
        "created_at": datetime.now().isoformat(),
        "branch": git_value(["branch", "--show-current"], root),
        "commit": git_value(["rev-parse", "--short", "HEAD"], root),
        "dirty": dirty_state(root),
        "dataset": str(dataset),
        "base_eval_csv": str(base_eval_csv),
        "model_path": str(model_path) if model_path is not None else None,
        "reranker_status": scorer.reason if scorer is not None else "disabled_oracle_utility_fallback",
        "split": str(args.split),
        "top_k": int(args.top_k),
        "safety_scope": str(args.safety_scope),
        "metrics": metrics,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
    }
    write_csv(records_csv, records)
    summary_json.parent.mkdir(parents=True, exist_ok=True)
    summary_json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(report, summary=summary)
    print(json.dumps({"summary_json": str(summary_json), "records_csv": str(records_csv), "report": str(report)}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
