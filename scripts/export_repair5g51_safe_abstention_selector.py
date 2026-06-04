"""Export the Repair5G.5.1 safe-abstention runtime selector."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g51_common import (  # noqa: E402
    DEFAULT_SAFE_SELECTOR_DIR,
    load_json,
    rel,
    repo_root,
    resolve,
    safe_selector_path,
    selector_spec_payload,
    sha256_file,
    write_json,
    write_selector_artifact,
    write_text,
)


DEFAULT_TUNING = "outputs/reports/phase5p5_repair5g51_safe_abstention_selector_tuning_summary.json"
DEFAULT_FROZEN = "outputs/reports/phase5p5_repair5g2_frozen_selector_spec.json"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g51_safe_abstention_selector_report.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g51_safe_abstention_selector_summary.json"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tuning-summary-json", type=Path, default=Path(DEFAULT_TUNING))
    parser.add_argument("--frozen-selector-spec-json", type=Path, default=Path(DEFAULT_FROZEN))
    parser.add_argument("--model-dir", type=Path, default=Path(DEFAULT_SAFE_SELECTOR_DIR))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    return parser.parse_args(argv)


def write_report(path: Path, summary: dict[str, Any]) -> None:
    write_text(
        path,
        "# Phase5.5 Repair5G.5.1 Safe-Abstention Selector Export Report\n\n"
        "The exported safe selector defaults to the validated frozen map-agent flow-shield policy. "
        "No high-risk early-iteration C-equiv branch is enabled in the first safe bridge.\n\n"
        f"- selector_spec: `{summary['selector_spec']}`\n"
        f"- selector_spec_hash: `{summary['selector_spec_hash']}`\n"
        f"- selected_selector: `{summary['selected_selector']}`\n"
        f"- safe_selector_uses_no_forbidden_features: `{summary['safe_selector_uses_no_forbidden_features']}`\n"
        f"- safe_selector_default_is_validated_flow_shield: `{summary['safe_selector_default_is_validated_flow_shield']}`\n\n"
        "`phase5p5_allowed=false`, `phase6_allowed=false`, and `aaai_ready=false` remain closed.\n",
    )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    tuning = load_json(resolve(args.tuning_summary_json, root))
    if not tuning.get("offline_gates_passed"):
        raise SystemExit("safe abstention tuning gates did not pass")
    frozen = load_json(resolve(args.frozen_selector_spec_json, root))
    static_candidate = str(
        frozen.get("selected_static_candidate", "repair5g1_shield_c125_b125_w075_d095_beta0p35_max0p75")
    )
    c_equiv_candidate = str(
        frozen.get("selected_c_equiv_baseline", "repair5g_dual_c_equiv_c100_b100_w075_d100")
    )
    model_dir = resolve(args.model_dir, root)
    selected = tuning.get("selected_selector", {})
    payload = selector_spec_payload(
        selector_name="repair5g51_safe_abstention_selector",
        left_method="repair5g2_frozen_static_or_selector",
        right_method="repair5g2_frozen_static_or_selector",
        fallback_static="repair5g2_frozen_static_or_selector",
        feature="ltm_iterations",
        threshold=-1.0,
        selector_type="safe_static_default_abstention_bridge",
        policy_note=(
            "Default to validated frozen map-agent flow-shield. Additive/C-equiv abstentions remain disabled "
            "until iteration-level counterfactual labels justify them."
        ),
        static_candidate=static_candidate,
        c_equiv_candidate=c_equiv_candidate,
    )
    manifest = write_selector_artifact(root, model_dir, payload)
    summary = {
        "schema_version": "phase5p5_repair5g51_safe_abstention_selector_summary_v1",
        "selector_spec": rel(model_dir / "selector_spec.json", root),
        "export_manifest": rel(model_dir / "export_manifest.json", root),
        "selector_spec_hash": manifest["selector_spec_hash"],
        "export_manifest_hash": sha256_file(model_dir / "export_manifest.json"),
        "selected_selector": selected.get("selector_name"),
        "selected_source_method": selected.get("source_method"),
        "safe_selector_uses_no_forbidden_features": True,
        "safe_selector_default_is_validated_flow_shield": True,
        "forbidden_early_ltm_iteration_c_equiv_branch": True,
        "diagnostic_only": True,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "aaai_ready": False,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_report(resolve(args.report, root), summary)
    print(json.dumps({"selector_spec_hash": summary["selector_spec_hash"]}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
