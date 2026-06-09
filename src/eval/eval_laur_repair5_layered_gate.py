"""Layered diagnostic gates for Phase4F Repair5 attention-native results.

This script does not grant runtime permission. It re-scores existing Repair5
offline summaries into development and promotion-candidate tiers while leaving
the strict Repair5 final gate as the only Phase5.5 unlock.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(ROOT / "src"))


DEV_THRESHOLDS = {
    "top1": 0.25,
    "top3": 0.60,
    "recall": 0.70,
    "precision": 0.25,
    "opportunity_capture_margin": 0.0,
    "avoidable_fallback_margin": 0.0,
}

PROMOTION_THRESHOLDS = {
    "top1": 0.32,
    "top3": 0.65,
    "recall": 0.78,
    "precision": 0.28,
    "opportunity_capture_margin": 0.05,
    "avoidable_fallback_margin": 0.05,
}

RUNTIME_THRESHOLDS = {
    "top1": 0.35,
    "top3": 0.70,
    "recall": 0.80,
    "precision": 0.30,
}

DEFAULT_SUMMARY_GLOBS = [
    "outputs/reports/phase4f_repair5_attention_native_eval_seed*_summary.json",
    "outputs/reports/phase4f_repair5_rawtrace_edge_eval_seed*_summary.json",
    "outputs/reports/phase4f_repair5_rawtrace_edge_sf_*_eval_seed*_summary.json",
    "outputs/reports/phase4f_repair5_expand5000_*_eval_seed*_summary.json",
]


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validation(summary: dict[str, Any]) -> dict[str, Any]:
    return summary.get("metrics_by_split", {}).get("validation", {})


def anti_escape(summary: dict[str, Any]) -> dict[str, Any]:
    anti = summary.get("anti_escape_gate")
    if isinstance(anti, dict):
        return anti
    maybe_validation = validation(summary).get("anti_escape_gate")
    return maybe_validation if isinstance(maybe_validation, dict) else {}


def metric_float(mapping: dict[str, Any], key: str, default: float = 0.0) -> float:
    try:
        value = mapping.get(key, default)
        return float(default if value is None else value)
    except (TypeError, ValueError):
        return float(default)


def positive_delta(metrics: dict[str, Any]) -> float:
    selected_delta = metric_float(metrics, "predicted_rule_validation_mean_delta_ratio")
    selected_vs_additive = metric_float(metrics, "selected_vs_additive_delta_mean")
    return max(selected_delta, selected_vs_additive)


def check_min(value: float, threshold: float) -> dict[str, Any]:
    return {"value": value, "threshold": threshold, "passed": value >= threshold}


def check_positive(value: float) -> dict[str, Any]:
    return {"value": value, "threshold": 0.0, "passed": value > 0.0}


def check_opportunity_reference(
    anti: dict[str, Any],
    *,
    reference_capture: float,
    reference_fallback: float,
    capture_margin: float,
    fallback_margin: float,
) -> dict[str, Any]:
    high_margin_count = int(metric_float(anti, "validation_high_margin_opportunity_count", 0.0))
    capture = metric_float(anti, "high_margin_nonadditive_capture_rate")
    fallback = metric_float(
        anti,
        "avoidable_additive_or_defer_rate",
        metric_float(anti, "avoidable_additive_fallback_rate", 1.0),
    )
    inconclusive = high_margin_count < 50
    capture_threshold = float(reference_capture) + float(capture_margin)
    fallback_threshold = float(reference_fallback) - float(fallback_margin)
    return {
        "high_margin_count": {
            "value": high_margin_count,
            "threshold": 50,
            "passed": high_margin_count >= 50,
        },
        "capture_vs_reference": {
            "value": capture,
            "reference": reference_capture,
            "threshold": capture_threshold,
            "passed": (not inconclusive) and capture > capture_threshold,
        },
        "avoidable_fallback_vs_reference": {
            "value": fallback,
            "reference": reference_fallback,
            "threshold": fallback_threshold,
            "passed": (not inconclusive) and fallback < fallback_threshold,
        },
        "inconclusive": inconclusive,
    }


def infer_label_audit_path(summary: dict[str, Any], root: Path) -> Path | None:
    dataset = str(summary.get("dataset") or "")
    candidates: list[str] = []
    if "expand5000_rawtrace_hightoken" in dataset:
        candidates.append("outputs/reports/phase4f_repair5_attention_native_expand5000_rawtrace_hightoken_label_audit.json")
    if "expand5000_rawtrace" in dataset:
        candidates.append("outputs/reports/phase4f_repair5_attention_native_expand5000_rawtrace_label_audit.json")
    if "attention_native_rawtrace" in dataset or "rawtrace" in dataset:
        candidates.append("outputs/reports/phase4f_repair5_attention_native_rawtrace_label_audit.json")
    candidates.append("outputs/reports/phase4f_repair5_attention_native_label_audit.json")
    for candidate in candidates:
        path = root / candidate
        if path.exists():
            return path
    return None


def label_audit_check(summary: dict[str, Any], root: Path) -> dict[str, Any]:
    path = infer_label_audit_path(summary, root)
    if path is None:
        return {"passed": False, "reason": "missing_label_audit", "path": None}
    try:
        audit = load_json(path)
    except Exception as exc:  # pragma: no cover - defensive report path
        return {"passed": False, "reason": f"label_audit_read_error:{exc}", "path": str(path)}
    return {"passed": bool(audit.get("passed")), "reason": audit.get("reason"), "path": str(path)}


def seed_from_path_or_summary(path: Path, summary: dict[str, Any]) -> int | None:
    if summary.get("seed") is not None:
        try:
            return int(summary["seed"])
        except (TypeError, ValueError):
            pass
    match = re.search(r"seed(\d+)", path.name)
    return int(match.group(1)) if match else None


def variant_name(path: Path) -> str:
    name = path.name
    name = re.sub(r"_eval_seed\d+_summary\.json$", "", name)
    name = re.sub(r"_train_seed\d+_summary\.json$", "", name)
    return name


def summarize_one(
    path: Path,
    *,
    root: Path,
    reference_capture: float,
    reference_fallback: float,
) -> dict[str, Any]:
    summary = load_json(path)
    metrics = validation(summary)
    anti = anti_escape(summary)
    audit = label_audit_check(summary, root)
    seed = seed_from_path_or_summary(path, summary)
    values = {
        "top1": metric_float(metrics, "rule_top1_accuracy"),
        "top3": metric_float(metrics, "rule_top3_accuracy"),
        "harmful_recall": metric_float(metrics, "harmful_update_recall"),
        "harmful_precision": metric_float(metrics, "harmful_update_precision"),
        "delta": metric_float(metrics, "predicted_rule_validation_mean_delta_ratio"),
        "selected_vs_additive_delta": metric_float(metrics, "selected_vs_additive_delta_mean"),
        "positive_delta_proxy": positive_delta(metrics),
        "anti_capture": metric_float(anti, "high_margin_nonadditive_capture_rate"),
        "avoidable_fallback": metric_float(
            anti,
            "avoidable_additive_or_defer_rate",
            metric_float(anti, "avoidable_additive_fallback_rate", 1.0),
        ),
        "anti_passed": bool(anti.get("passed")),
        "attention_native_passed": bool((metrics.get("attention_native_gate") or {}).get("passed")),
        "phase4f_passed": bool((summary.get("phase4f_gate") or {}).get("passed")),
    }

    dev_anti = check_opportunity_reference(
        anti,
        reference_capture=reference_capture,
        reference_fallback=reference_fallback,
        capture_margin=DEV_THRESHOLDS["opportunity_capture_margin"],
        fallback_margin=DEV_THRESHOLDS["avoidable_fallback_margin"],
    )
    promotion_anti = check_opportunity_reference(
        anti,
        reference_capture=reference_capture,
        reference_fallback=reference_fallback,
        capture_margin=PROMOTION_THRESHOLDS["opportunity_capture_margin"],
        fallback_margin=PROMOTION_THRESHOLDS["avoidable_fallback_margin"],
    )
    development_checks = {
        "label_audit": audit,
        "positive_delta_proxy": check_positive(values["positive_delta_proxy"]),
        "top1": check_min(values["top1"], DEV_THRESHOLDS["top1"]),
        "top3": check_min(values["top3"], DEV_THRESHOLDS["top3"]),
        "harmful_recall": check_min(values["harmful_recall"], DEV_THRESHOLDS["recall"]),
        "harmful_precision": check_min(values["harmful_precision"], DEV_THRESHOLDS["precision"]),
        "opportunity_capture": dev_anti["capture_vs_reference"],
        "avoidable_fallback": dev_anti["avoidable_fallback_vs_reference"],
        "high_margin_count": dev_anti["high_margin_count"],
    }
    promotion_checks = {
        "label_audit": audit,
        "positive_delta_proxy": check_positive(values["positive_delta_proxy"]),
        "top1": check_min(values["top1"], PROMOTION_THRESHOLDS["top1"]),
        "top3": check_min(values["top3"], PROMOTION_THRESHOLDS["top3"]),
        "harmful_recall": check_min(values["harmful_recall"], PROMOTION_THRESHOLDS["recall"]),
        "harmful_precision": check_min(values["harmful_precision"], PROMOTION_THRESHOLDS["precision"]),
        "opportunity_capture": promotion_anti["capture_vs_reference"],
        "avoidable_fallback": promotion_anti["avoidable_fallback_vs_reference"],
        "high_margin_count": promotion_anti["high_margin_count"],
    }
    runtime_checks = {
        "strict_phase4f_gate": {"passed": values["phase4f_passed"]},
        "strict_attention_native_gate": {"passed": values["attention_native_passed"]},
        "strict_anti_escape_gate": {"passed": values["anti_passed"]},
        "top1": check_min(values["top1"], RUNTIME_THRESHOLDS["top1"]),
        "top3": check_min(values["top3"], RUNTIME_THRESHOLDS["top3"]),
        "harmful_recall": check_min(values["harmful_recall"], RUNTIME_THRESHOLDS["recall"]),
        "harmful_precision": check_min(values["harmful_precision"], RUNTIME_THRESHOLDS["precision"]),
        "positive_delta_proxy": check_positive(values["positive_delta_proxy"]),
    }

    development_passed = all(bool(check.get("passed")) for check in development_checks.values())
    promotion_passed = all(bool(check.get("passed")) for check in promotion_checks.values())
    runtime_seed_passed = all(bool(check.get("passed")) for check in runtime_checks.values())
    if development_passed and not promotion_passed:
        interpretation = "early_promising_not_promotable"
    elif promotion_passed and not runtime_seed_passed:
        interpretation = "promotion_candidate_not_runtime"
    elif runtime_seed_passed:
        interpretation = "strict_seed_gate_passed_requires_multiseed_final_gate"
    else:
        interpretation = "diagnostic_fail"

    return {
        "summary_json": str(path),
        "variant": variant_name(path),
        "seed": seed,
        "dataset": summary.get("dataset"),
        "values": values,
        "development_gate": {
            "passed": development_passed,
            "thresholds": DEV_THRESHOLDS,
            "anti_reference": {"capture": reference_capture, "fallback": reference_fallback},
            "checks": development_checks,
            "anti_inconclusive": dev_anti["inconclusive"],
        },
        "promotion_candidate_gate": {
            "passed": promotion_passed,
            "thresholds": PROMOTION_THRESHOLDS,
            "anti_reference": {"capture": reference_capture, "fallback": reference_fallback},
            "checks": promotion_checks,
            "anti_inconclusive": promotion_anti["inconclusive"],
        },
        "runtime_claim_seed_gate": {
            "passed": runtime_seed_passed,
            "thresholds": RUNTIME_THRESHOLDS,
            "checks": runtime_checks,
            "note": "Diagnostic only. Phase5.5 still requires the existing strict final multi-seed gate.",
        },
        "interpretation": interpretation,
    }


def aggregate_groups(results: list[dict[str, Any]], required_seeds: list[int]) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for result in results:
        groups.setdefault(str(result["variant"]), []).append(result)
    output = []
    for variant, items in sorted(groups.items()):
        seeds = sorted(seed for seed in (item.get("seed") for item in items) if seed is not None)
        dev_passed = [item for item in items if item["development_gate"]["passed"]]
        promotion_passed = [item for item in items if item["promotion_candidate_gate"]["passed"]]
        strict_passed = [item for item in items if item["runtime_claim_seed_gate"]["passed"]]
        missing = [seed for seed in required_seeds if seed not in seeds]
        output.append(
            {
                "variant": variant,
                "available_seeds": seeds,
                "missing_required_seeds": missing,
                "development_pass_count": len(dev_passed),
                "promotion_candidate_pass_count": len(promotion_passed),
                "strict_seed_pass_count": len(strict_passed),
                "promotion_candidate_multiseed_2_of_3": bool(
                    not missing and len({item.get("seed") for item in promotion_passed}) >= 2
                ),
                "runtime_claim_multiseed_allowed": False,
                "runtime_note": "Use eval_laur_repair5_final_gate.py for the only Phase5.5 unlock.",
            }
        )
    return output


def collect_summary_paths(root: Path, patterns: list[str]) -> list[Path]:
    paths: list[Path] = []
    for pattern in patterns:
        for path in sorted(root.glob(pattern)):
            if path.is_file() and path not in paths:
                paths.append(path)
    return paths


def write_markdown(path: Path, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    results = summary["results"]
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Phase4F Repair5 Layered Gate Diagnostic\n\n")
        handle.write("This report is diagnostic only. It does not lower the strict Repair5 runtime/final gate.\n\n")
        handle.write("## Counts\n\n")
        handle.write(f"- summaries: `{len(results)}`\n")
        handle.write(f"- development pass: `{sum(1 for item in results if item['development_gate']['passed'])}`\n")
        handle.write(
            f"- promotion-candidate pass: `{sum(1 for item in results if item['promotion_candidate_gate']['passed'])}`\n"
        )
        handle.write(
            f"- strict seed gate pass: `{sum(1 for item in results if item['runtime_claim_seed_gate']['passed'])}`\n"
        )
        handle.write("- Phase5.5 allowed: `False` from this diagnostic report\n")
        handle.write("- Phase6 allowed: `False`\n\n")
        handle.write("## Top Results\n\n")
        handle.write(
            "| variant | seed | dev | candidate | strict seed | top1 | top3 | recall | precision | anti capture | anti pass | interpretation |\n"
        )
        handle.write("|---|---:|---|---|---|---:|---:|---:|---:|---:|---|---|\n")
        ranked = sorted(
            results,
            key=lambda item: (
                item["promotion_candidate_gate"]["passed"],
                item["development_gate"]["passed"],
                item["values"]["top3"],
                item["values"]["top1"],
            ),
            reverse=True,
        )
        for item in ranked[:50]:
            values = item["values"]
            handle.write(
                f"| `{item['variant']}` | `{item.get('seed')}` | "
                f"{item['development_gate']['passed']} | {item['promotion_candidate_gate']['passed']} | "
                f"{item['runtime_claim_seed_gate']['passed']} | "
                f"{values['top1']:.4f} | {values['top3']:.4f} | "
                f"{values['harmful_recall']:.4f} | {values['harmful_precision']:.4f} | "
                f"{values['anti_capture']:.4f} | {values['anti_passed']} | `{item['interpretation']}` |\n"
            )
        handle.write("\n## Boundary\n\n")
        handle.write(
            "Development or promotion-candidate pass means only that the direction deserves more analysis, "
            "larger training, or tightly scoped closed-loop smoke planning. It is not runtime permission. "
            "Phase5.5 still requires the strict original Phase4F, attention-native, safety, anti-escape, "
            "and multi-seed final gate. Phase6 requires later closed-loop learned-benefit evidence.\n"
        )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary-glob", action="append", default=[])
    parser.add_argument("--output-json", type=Path, default=Path("outputs/reports/phase4f_repair5_layered_gate_summary.json"))
    parser.add_argument("--report-md", type=Path, default=Path("outputs/reports/phase4f_repair5_layered_gate_report.md"))
    parser.add_argument("--reference-capture", type=float, default=0.0)
    parser.add_argument("--reference-fallback", type=float, default=1.0)
    parser.add_argument("--required-seeds", type=int, nargs="*", default=[61, 103, 107])
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    patterns = args.summary_glob or DEFAULT_SUMMARY_GLOBS
    paths = collect_summary_paths(root, patterns)
    results = [
        summarize_one(
            path,
            root=root,
            reference_capture=float(args.reference_capture),
            reference_fallback=float(args.reference_fallback),
        )
        for path in paths
    ]
    summary = {
        "schema_version": "phase4f_repair5_layered_gate_summary_v1",
        "summary_globs": patterns,
        "reference": {
            "name": "always_additive_or_external_baseline",
            "capture": float(args.reference_capture),
            "fallback": float(args.reference_fallback),
        },
        "required_seeds": args.required_seeds,
        "counts": {
            "summaries": len(results),
            "development_pass": sum(1 for item in results if item["development_gate"]["passed"]),
            "promotion_candidate_pass": sum(1 for item in results if item["promotion_candidate_gate"]["passed"]),
            "strict_seed_pass": sum(1 for item in results if item["runtime_claim_seed_gate"]["passed"]),
        },
        "groups": aggregate_groups(results, args.required_seeds),
        "results": results,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "boundary": (
            "Diagnostic layered gates do not lower or replace the strict Repair5 final gate. "
            "Runtime remains forbidden unless eval_laur_repair5_final_gate.py passes."
        ),
    }
    output_path = args.output_json if args.output_json.is_absolute() else root / args.output_json
    report_path = args.report_md if args.report_md.is_absolute() else root / args.report_md
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_markdown(report_path, summary)
    print(json.dumps({"summary_json": str(output_path), "report": str(report_path), "counts": summary["counts"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
