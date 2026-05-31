"""Build a diagnostic-only Phase5.5 LAUR preflight plan.

The script does not run the solver and does not unlock runtime. It records
whether existing offline evidence is strong enough to justify a tiny
oracle-transfer / learned-candidate closed-loop diagnostic.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "src"))


DEFAULT_OUTPUT_JSON = "outputs/reports/phase5p5_laur_diagnostic_preflight_plan.json"
DEFAULT_REPORT = "outputs/reports/phase5p5_laur_diagnostic_preflight_plan.md"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def resolve_path(path: str | Path | None, root: Path) -> Path | None:
    if path is None:
        return None
    value = Path(path)
    return value if value.is_absolute() else root / value


def load_json(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


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


def _validation_metrics(summary: dict[str, Any] | None) -> dict[str, Any]:
    if not summary:
        return {}
    return summary.get("metrics_by_split", {}).get("validation", {})


def _best_composite_mode(summary: dict[str, Any] | None) -> dict[str, Any] | None:
    if not summary:
        return None
    modes = summary.get("metrics_by_mode", {})
    if not isinstance(modes, dict) or not modes:
        return None
    mode, metrics = max(
        modes.items(),
        key=lambda item: (
            float(item[1].get("selected_vs_additive_delta") or 0.0),
            float(item[1].get("high_margin_capture") or 0.0),
            -float(item[1].get("utility_regret_to_oracle") or 0.0),
        ),
    )
    return {"mode": mode, "metrics": metrics}


def build_preflight_plan(
    *,
    attention_summary: dict[str, Any] | None = None,
    composite_summary: dict[str, Any] | None = None,
    reranker_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    attention_validation = _validation_metrics(attention_summary)
    reranker_validation = _validation_metrics(reranker_summary)
    best_composite = _best_composite_mode(composite_summary)
    offline_signals: dict[str, Any] = {
        "attention_selected_vs_additive_delta": attention_validation.get("selected_vs_additive_delta_mean"),
        "attention_high_margin_capture": (
            attention_validation.get("anti_escape_gate", {}) or {}
        ).get("high_margin_nonadditive_capture_rate"),
        "composite_best_mode": best_composite,
        "reranker_validation": reranker_validation,
    }
    composite_promising = bool(
        best_composite
        and float(best_composite["metrics"].get("selected_vs_additive_delta") or 0.0) > 0.0
        and float(best_composite["metrics"].get("harmful_recall") or 0.0) >= 0.80
    )
    reranker_promising = bool(
        reranker_validation
        and float(reranker_validation.get("selected_vs_additive_delta") or 0.0) > 0.0
        and float(reranker_validation.get("selected_harmful_rate") or 1.0) <= 0.20
    )
    attention_promising = bool(
        attention_validation
        and float(attention_validation.get("selected_vs_additive_delta_mean") or 0.0) > 0.0
    )
    diagnostic_preflight_warranted = bool(composite_promising or reranker_promising or attention_promising)
    return {
        "schema_version": "phase5p5_laur_diagnostic_preflight_plan_v1",
        "created_at": datetime.now().isoformat(),
        "diagnostic_preflight_warranted": diagnostic_preflight_warranted,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "offline_signals": offline_signals,
        "required_boundary": [
            "diagnostic-only",
            "no Phase5.5 promotion",
            "no solver semantic changes",
            "include LaCAM*, LaCAM*+LTM, Repair3, learned candidate, oracle replay/teacher-forced if feasible",
            "report success, sum_of_loss_ratio, expanded nodes, TTFS, defer rate, non-additive rate, selected-vs-additive delta",
        ],
        "recommended_scope": {
            "max_maps": 2,
            "max_agent_counts": 2,
            "max_instances_per_setting": 3,
            "time_budget_seconds": 3,
            "candidates": [
                "LaCAM*",
                "LaCAM*+LTM",
                "Repair3 safe runtime",
                "Repair5C composite/reranker diagnostic",
                "always-additive/defer",
                "oracle replay or teacher-forced update choices if feasible",
            ],
        },
        "stop_conditions": [
            "offline candidate is worse than additive LTM on success or sum_of_loss_ratio",
            "non-additive rate collapses to zero",
            "strict safety mask blocks all learned choices",
            "oracle replay fails to transfer any measurable advantage",
        ],
    }


def write_report(path: Path, *, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Phase5.5 LAUR Diagnostic Preflight Plan\n\n")
        handle.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S %z').strip()}\n\n")
        handle.write("## Boundary\n\n")
        handle.write(
            "This is a diagnostic preflight plan only. Phase5.5 runtime remains forbidden, "
            "and Phase6 remains forbidden until closed-loop learned benefit over additive LTM is shown.\n\n"
        )
        handle.write(f"- diagnostic preflight warranted: `{summary.get('diagnostic_preflight_warranted')}`\n")
        handle.write(f"- Phase5.5 allowed: `{summary.get('phase5p5_allowed')}`\n")
        handle.write(f"- Phase6 allowed: `{summary.get('phase6_allowed')}`\n\n")
        handle.write("## Required Comparisons\n\n")
        for candidate in summary.get("recommended_scope", {}).get("candidates", []):
            handle.write(f"- {candidate}\n")
        handle.write("\n## Stop Conditions\n\n")
        for condition in summary.get("stop_conditions", []):
            handle.write(f"- {condition}\n")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--attention-summary-json", type=Path)
    parser.add_argument("--composite-summary-json", type=Path)
    parser.add_argument("--reranker-summary-json", type=Path)
    parser.add_argument("--output-json", type=Path, default=Path(DEFAULT_OUTPUT_JSON))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    output_json = resolve_path(args.output_json, root)
    report = resolve_path(args.report, root)
    if None in (output_json, report):
        raise ValueError("output/report paths are required")
    assert output_json and report
    summary = build_preflight_plan(
        attention_summary=load_json(resolve_path(args.attention_summary_json, root)),
        composite_summary=load_json(resolve_path(args.composite_summary_json, root)),
        reranker_summary=load_json(resolve_path(args.reranker_summary_json, root)),
    )
    summary["branch"] = git_value(["branch", "--show-current"], root)
    summary["commit"] = git_value(["rev-parse", "--short", "HEAD"], root)
    summary["dirty"] = dirty_state(root)
    summary["inputs"] = {
        "attention_summary_json": str(resolve_path(args.attention_summary_json, root)) if args.attention_summary_json else None,
        "composite_summary_json": str(resolve_path(args.composite_summary_json, root)) if args.composite_summary_json else None,
        "reranker_summary_json": str(resolve_path(args.reranker_summary_json, root)) if args.reranker_summary_json else None,
    }
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(report, summary=summary)
    print(json.dumps({"summary_json": str(output_json), "report": str(report)}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
