"""Train a small Repair5G.5.1 MLP selector only after safe labels exist."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g51_common import load_json, repo_root, resolve, write_json, write_text  # noqa: E402


DEFAULT_SAFE_SMOKE = "outputs/reports/phase5p5_repair5g51_safe_selector_runtime_smoke_summary.json"
DEFAULT_LABEL_QUALITY = "outputs/reports/phase5p5_repair5g51_counterfactual_label_quality_summary.json"
DEFAULT_MODEL_DIR = "artifacts/models/laur_ltm/repair5g51_small_mlp_selector"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g51_small_mlp_selector_report.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g51_small_mlp_selector_summary.json"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--safe-smoke-summary-json", type=Path, default=Path(DEFAULT_SAFE_SMOKE))
    parser.add_argument("--label-quality-summary-json", type=Path, default=Path(DEFAULT_LABEL_QUALITY))
    parser.add_argument("--model-dir", type=Path, default=Path(DEFAULT_MODEL_DIR))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    parser.add_argument("--force", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    safe = load_json(resolve(args.safe_smoke_summary_json, root))
    quality = load_json(resolve(args.label_quality_summary_json, root))
    safe_ok = bool(safe.get("gates", {}).get("safe_selector_runtime_smoke_passed"))
    labels_ok = bool(quality.get("gates", {}).get("counterfactual_label_quality_passed"))
    should_train = args.force or (safe_ok and labels_ok)
    model_dir = resolve(args.model_dir, root)
    if should_train:
        model_dir.mkdir(parents=True, exist_ok=True)
        write_json(
            model_dir / "model_manifest.json",
            {
                "schema_version": "phase5p5_repair5g51_small_mlp_selector_manifest_v1",
                "status": "placeholder_not_trained_in_this_pass",
                "architecture": "hidden_32_or_64_relu_margin_abstention_to_static",
                "phase5p5_allowed": False,
                "phase6_allowed": False,
                "aaai_ready": False,
            },
        )
    summary = {
        "schema_version": "phase5p5_repair5g51_small_mlp_selector_summary_v1",
        "safe_selector_runtime_smoke_passed": safe_ok,
        "counterfactual_label_quality_passed": labels_ok,
        "training_started": should_train,
        "decision": "blocked_until_safe_runtime_selector_and_counterfactual_labels"
        if not should_train
        else "placeholder_manifest_written",
        "forbidden_architectures": ["GNN", "Transformer", "action decoder", "restart head", "priority head", "h-value head"],
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "aaai_ready": False,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.1 Small MLP Selector\n\n"
        f"- safe_selector_runtime_smoke_passed: `{safe_ok}`\n"
        f"- counterfactual_label_quality_passed: `{labels_ok}`\n"
        f"- training_started: `{should_train}`\n"
        f"- decision: `{summary['decision']}`\n\n"
        "No GNN, Transformer, action decoder, restart head, priority head, h-value head, or candidate-deletion head "
        "is introduced in G5.1.\n",
    )
    print(json.dumps({"training_started": should_train}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
