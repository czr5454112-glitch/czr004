"""Aggregate Phase4F Repair5 gates across seeds before any Phase5.5 runtime work."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(ROOT / "src"))

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


def load_json(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _passed(summary: dict[str, Any], *keys: str) -> bool:
    current: Any = summary
    for key in keys:
        if not isinstance(current, dict):
            return False
        current = current.get(key)
    if isinstance(current, dict):
        return bool(current.get("passed"))
    return bool(current)


def _validation(summary: dict[str, Any]) -> dict[str, Any]:
    return summary.get("metrics_by_split", {}).get("validation", {})


def safety_gate(summary: dict[str, Any]) -> dict[str, Any]:
    validation = _validation(summary)
    recall = float(validation.get("harmful_update_recall") or 0.0)
    precision = float(validation.get("harmful_update_precision") or 0.0)
    checks = {
        "harmful_recall": {"value": recall, "threshold": 0.80, "passed": recall >= 0.80},
        "harmful_precision": {"value": precision, "threshold": 0.30, "passed": precision >= 0.30},
    }
    checks["passed"] = all(bool(value["passed"]) for value in checks.values())
    return checks


def aggregate_final_gate(
    summaries: list[dict[str, Any]],
    *,
    label_audit: dict[str, Any] | None = None,
    required_seeds: list[int] | None = None,
) -> dict[str, Any]:
    seeds = [int(summary.get("seed", -1)) for summary in summaries]
    required = required_seeds or [61, 103, 107]
    missing = [seed for seed in required if seed not in seeds]
    seed_results: list[dict[str, Any]] = []
    for summary in summaries:
        seed = int(summary.get("seed", -1))
        phase4f = summary.get("phase4f_gate", {})
        attention = _validation(summary).get("attention_native_gate", {})
        anti = summary.get("anti_escape_gate", {})
        safety = safety_gate(summary)
        seed_results.append(
            {
                "seed": seed,
                "summary": summary.get("model") or summary.get("model_path"),
                "original_phase4f_gate_passed": bool(phase4f.get("passed")),
                "attention_native_gate_passed": bool(attention.get("passed")),
                "safety_gate_passed": bool(safety.get("passed")),
                "anti_escape_gate_passed": bool(anti.get("passed")),
                "missing_required_gate_fields": [
                    name
                    for name, gate in (
                        ("phase4f_gate", phase4f),
                        ("metrics_by_split.validation.attention_native_gate", attention),
                        ("anti_escape_gate", anti),
                    )
                    if not isinstance(gate, dict) or "passed" not in gate
                ],
                "safety_gate": safety,
                "anti_escape_reason": anti.get("reason"),
                "runtime_allowed_for_seed": bool(
                    phase4f.get("passed")
                    and attention.get("passed")
                    and safety.get("passed")
                    and anti.get("passed")
                ),
            }
        )
    label_passed = True if label_audit is None else bool(label_audit.get("passed"))
    multi_seed_passed = not missing and bool(seed_results) and all(result["runtime_allowed_for_seed"] for result in seed_results)
    runtime_allowed = bool(label_passed and multi_seed_passed)
    if runtime_allowed:
        conclusion = "all Repair5 offline gates pass; Phase5.5 parity/smoke is allowed only, not Phase6-scale performance"
    elif any(result["original_phase4f_gate_passed"] and not result["anti_escape_gate_passed"] for result in seed_results):
        conclusion = "model still escapes to LTM/additive"
    elif any(result["anti_escape_gate_passed"] and not result["safety_gate_passed"] for result in seed_results):
        conclusion = "non-additive learning unsafe"
    elif missing:
        conclusion = "multi-seed evidence incomplete"
    else:
        conclusion = "Repair5 offline gates failed"
    return {
        "schema_version": "phase4f_repair5_final_gate_summary_v1",
        "label_audit_passed": label_passed,
        "required_seeds": required,
        "available_seeds": seeds,
        "missing_seeds": missing,
        "seed_results": seed_results,
        "multi_seed_gate": {
            "passed": multi_seed_passed,
            "required": required,
            "available": seeds,
        },
        "runtime_allowed": runtime_allowed,
        "phase5p5_allowed": runtime_allowed,
        "phase6_allowed": False,
        "conclusion": conclusion,
    }


def write_report(path: Path, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Phase4F Repair5 Final Gate\n\n")
        handle.write(f"- label audit passed: `{summary.get('label_audit_passed')}`\n")
        handle.write(f"- required seeds: `{summary.get('required_seeds')}`\n")
        handle.write(f"- available seeds: `{summary.get('available_seeds')}`\n")
        handle.write(f"- missing seeds: `{summary.get('missing_seeds')}`\n")
        handle.write(f"- multi-seed gate: `{summary.get('multi_seed_gate', {}).get('passed')}`\n")
        handle.write(f"- Phase5.5 runtime allowed: `{summary.get('phase5p5_allowed')}`\n")
        handle.write(f"- Phase6 allowed: `{summary.get('phase6_allowed')}`\n")
        handle.write(f"- conclusion: `{summary.get('conclusion')}`\n\n")
        for result in summary.get("seed_results", []):
            handle.write(
                f"- seed `{result.get('seed')}`: original `{result.get('original_phase4f_gate_passed')}`, "
                f"attention `{result.get('attention_native_gate_passed')}`, "
                f"safety `{result.get('safety_gate_passed')}`, "
                f"anti_escape `{result.get('anti_escape_gate_passed')}`, "
                f"runtime `{result.get('runtime_allowed_for_seed')}`\n"
            )
        handle.write(
            "\nPhase5.5 is only parity/smoke permission. Phase6 remains forbidden until "
            "closed-loop smoke and learned-benefit pilot evidence are separately sufficient.\n"
        )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--summary-json", action="append", type=Path, default=[])
    parser.add_argument("--label-audit-json", type=Path)
    parser.add_argument("--output-json", type=Path)
    parser.add_argument("--report-md", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    config = load_config(resolve_path(args.config, root))
    eval_config = config.get("attention_native", {}).get("eval", {}) if isinstance(config.get("attention_native"), dict) else {}
    outputs = config.get("outputs", {}) if isinstance(config.get("outputs"), dict) else {}
    seeds = [int(seed) for seed in eval_config.get("promotion_seeds", [61, 103, 107])]
    summary_paths = [resolve_path(path, root) for path in args.summary_json]
    if not summary_paths:
        template = eval_config.get("eval_summary_json")
        summary_paths = [resolve_path(template, root, seed=seed) for seed in seeds]
    summaries = [payload for payload in (load_json(path) for path in summary_paths) if payload]
    label_audit_path = resolve_path(args.label_audit_json or outputs.get("label_audit_json"), root)
    label_audit = load_json(label_audit_path)
    output_path = resolve_path(args.output_json or outputs.get("final_gate_summary_json"), root)
    report_path = resolve_path(args.report_md or outputs.get("final_gate_report_md"), root)
    if None in (output_path, report_path):
        raise ValueError("output/report paths are required")
    assert output_path and report_path
    summary = aggregate_final_gate(summaries, label_audit=label_audit, required_seeds=seeds)
    summary["summary_paths"] = [str(path) for path in summary_paths if path is not None]
    summary["label_audit_json"] = str(label_audit_path) if label_audit_path else None
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(report_path, summary)
    print(json.dumps({"summary_json": str(output_path), "report": str(report_path)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
