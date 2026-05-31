"""Create the Repair5E.1 diagnostic OOD-guard runtime artifact.

The artifact copies the frozen Repair5D composite distill runtime files and
adds a manifest/report explaining that the actual guard is activated by the
phase1a_batch CLI option --laur-ood-z-threshold.
"""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any


DEFAULT_SOURCE = "artifacts/models/laur_ltm/repair5d_composite_distilled"
DEFAULT_OUTPUT = "artifacts/models/laur_ltm/repair5d_composite_distilled_ood_guard"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5e_ood_guard_report.md"
RUNTIME_FILES = [
    "features.txt",
    "mean.csv",
    "std.csv",
    "rules.csv",
    "layer0_weight.csv",
    "layer0_bias.csv",
    "rule_head_weight.csv",
    "rule_head_bias.csv",
    "safety_head_weight.csv",
    "safety_head_bias.csv",
    "delta_head_weight.csv",
    "delta_head_bias.csv",
    "laur_mlp_v1_weights.json",
    "laur_mlp_v1_rules.json",
    "laur_mlp_v1_feature_stats.json",
]


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def resolve_path(path: str | Path, root: Path) -> Path:
    value = Path(path)
    return value if value.is_absolute() else root / value


def write_report(path: Path, manifest: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Phase5.5 Repair5E.1 OOD Guard Diagnostic Repair\n\n")
        handle.write("This targeted repair implements Option 3 from the Case-B transfer analysis: ")
        handle.write("an OOD/defer guard around the existing Repair5D composite distill bridge.\n\n")
        handle.write("## Boundary\n\n")
        handle.write("- diagnostic-only: `true`\n")
        handle.write("- Phase5.5 allowed: `false`\n")
        handle.write("- Phase6 allowed: `false`\n")
        handle.write("- solver semantic changes: `false`\n")
        handle.write(f"- candidate runtime: `{manifest['diagnostic_runtime_dir']}`\n")
        handle.write(f"- source runtime: `{manifest['source_runtime_dir']}`\n")
        handle.write(f"- guard CLI: `{manifest['guard_cli']} {manifest['guard_threshold']}`\n\n")
        handle.write("## Behavior\n\n")
        handle.write(
            "The runtime computes z-scores using the distill model's frozen `mean.csv` and `std.csv`. "
            "If the maximum absolute runtime feature z-score is at or above the threshold, the "
            "diagnostic candidate defers to `additive_ltm` for that update.\n\n"
        )
        handle.write("Every learned update is logged with OOD metrics: ")
        handle.write("`feature_max_abs_z`, `feature_mean_abs_z`, `feature_outside_3sigma_count`, ")
        handle.write("`feature_outside_5sigma_count`, `ood_guard_triggered`, and `ood_z_threshold`.\n\n")
        handle.write("This is not a production runtime claim and does not unlock Phase5.5 or Phase6.\n")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-runtime-dir", type=Path, default=Path(DEFAULT_SOURCE))
    parser.add_argument("--output-runtime-dir", type=Path, default=Path(DEFAULT_OUTPUT))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--guard-threshold", type=float, default=5.0)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    source = resolve_path(args.source_runtime_dir, root)
    output = resolve_path(args.output_runtime_dir, root)
    report = resolve_path(args.report, root)
    if not source.exists():
        raise FileNotFoundError(source)
    output.mkdir(parents=True, exist_ok=True)
    missing: list[str] = []
    for name in RUNTIME_FILES:
        src = source / name
        if not src.exists():
            missing.append(name)
            continue
        shutil.copy2(src, output / name)
    if missing:
        raise FileNotFoundError(f"missing runtime files: {missing}")

    manifest = {
        "schema_version": "phase5p5_repair5e_ood_guard_runtime_v1",
        "created_at": datetime.now().isoformat(),
        "source_runtime_dir": str(source.relative_to(root)),
        "diagnostic_runtime_dir": str(output.relative_to(root)),
        "selected_repair": "OOD/defer guard around existing Repair5D distill bridge",
        "guard_cli": "--laur-ood-z-threshold",
        "guard_threshold": float(args.guard_threshold),
        "diagnostic_only": True,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "notes": [
            "Model weights are copied from the frozen Repair5D composite distill bridge.",
            "The guard is activated by phase1a_batch runtime CLI, not by changing solver semantics.",
            "If max runtime feature absolute z-score is at or above the threshold, the LAUR update defers to additive_ltm.",
        ],
    }
    manifest_path = output / "repair5e_ood_guard_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(report, manifest)
    print(json.dumps({"runtime_dir": str(output), "manifest": str(manifest_path), "report": str(report)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
