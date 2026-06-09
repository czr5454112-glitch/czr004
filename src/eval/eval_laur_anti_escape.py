"""Compute the Repair5 anti-escape gate from attention-native eval records."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(ROOT / "src"))

from train.train_laur_attention_native import anti_escape_metrics  # noqa: E402


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def resolve_path(path: str | Path | None, root: Path, *, seed: int | None = None) -> Path | None:
    if path is None:
        return None
    text = str(path)
    if seed is not None:
        text = text.format(seed=seed)
    value = Path(text)
    return value if value.is_absolute() else root / value


def load_config(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}
    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError("PyYAML is required to read Repair5 configs") from exc
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def _bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value).strip().lower() in {"1", "true", "yes"}


def _float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def read_records(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        records = list(csv.DictReader(handle))
    normalized: list[dict[str, Any]] = []
    for record in records:
        normalized.append(
            {
                **record,
                "has_nonadditive_opportunity": _bool(record.get("has_nonadditive_opportunity")),
                "has_high_margin_nonadditive_opportunity": _bool(
                    record.get("has_high_margin_nonadditive_opportunity")
                ),
                "selected_rule_harmful": _bool(record.get("selected_rule_harmful")),
                "selected_vs_additive_delta": _float(record.get("selected_vs_additive_delta")),
                "opportunity_margin": _float(record.get("opportunity_margin"), 0.010),
            }
        )
    return normalized


def write_report(path: Path, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Phase4F Repair5 Anti-Escape Gate\n\n")
        handle.write(f"- validation opportunity count: `{summary.get('validation_opportunity_count')}`\n")
        handle.write(
            f"- validation high-margin opportunity count: "
            f"`{summary.get('validation_high_margin_opportunity_count')}`\n"
        )
        handle.write(f"- high-margin capture rate: `{summary.get('high_margin_nonadditive_capture_rate')}`\n")
        handle.write(f"- avoidable additive/defer rate: `{summary.get('avoidable_additive_or_defer_rate')}`\n")
        handle.write(f"- mean selected-vs-additive delta: `{summary.get('anti_escape_mean_selected_vs_additive_delta')}`\n")
        handle.write(f"- opportunity non-additive selection rate: `{summary.get('opportunity_nonadditive_selection_rate')}`\n")
        handle.write(f"- global additive/defer rate: `{summary.get('global_additive_or_defer_rate')}`\n")
        handle.write(f"- selected rules: `{summary.get('selected_rule_distribution')}`\n")
        handle.write(f"- decisions: `{summary.get('decision_distribution')}`\n")
        handle.write(f"- passed: `{summary.get('passed')}`\n")
        handle.write(f"- reason: `{summary.get('reason')}`\n\n")
        handle.write(
            "A pass here is required but not sufficient for runtime. It only checks that "
            "the model did not pass by escaping to additive/defer on high-margin safe "
            "non-additive opportunity samples.\n"
        )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--records-csv", type=Path)
    parser.add_argument("--summary-json", type=Path)
    parser.add_argument("--report-md", type=Path)
    parser.add_argument("--seed", type=int)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    config = load_config(resolve_path(args.config, root))
    eval_config = config.get("attention_native", {}).get("eval", {}) if isinstance(config.get("attention_native"), dict) else {}
    train_config = (
        config.get("attention_native", {}).get("training", {})
        if isinstance(config.get("attention_native"), dict)
        else {}
    )
    anti_thresholds = config.get("anti_escape", {}) if isinstance(config.get("anti_escape"), dict) else {}
    seed = int(args.seed if args.seed is not None else train_config.get("seed", eval_config.get("seed", 61)))
    records_path = resolve_path(args.records_csv or eval_config.get("eval_summary_csv"), root, seed=seed)
    summary_path = resolve_path(
        args.summary_json or config.get("outputs", {}).get("anti_escape_gate_summary_json"),
        root,
        seed=seed,
    )
    report_path = resolve_path(args.report_md or config.get("outputs", {}).get("anti_escape_report_md"), root, seed=seed)
    if None in (records_path, summary_path, report_path):
        raise ValueError("records/summary/report paths are required")
    assert records_path and summary_path and report_path
    records = [record for record in read_records(records_path) if str(record.get("split")) == "validation"]
    summary = anti_escape_metrics(records, thresholds=anti_thresholds)
    summary["schema_version"] = "phase4f_repair5_anti_escape_gate_summary_v1"
    summary["records_csv"] = str(records_path)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(report_path, summary)
    print(json.dumps({"summary_json": str(summary_path), "report": str(report_path)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
