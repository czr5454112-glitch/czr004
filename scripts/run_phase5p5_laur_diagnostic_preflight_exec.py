"""Run a diagnostic-only Phase5.5/Repair5E LAUR closed-loop preflight.

This runner executes the existing solver binary on a tiny MAPF scope and
summarizes the result. It is intentionally diagnostic-only: it never grants
Phase5.5 or Phase6 permission. Repair5E can run a frozen Repair5D composite
through a distilled MLP runtime bridge and, optionally, a static-rule oracle
probe as an upper-bound diagnostic.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "src"))
    sys.path.insert(0, str(ROOT / "scripts"))

from czr004_metrics.schema import normalize_run_row, validate_run_row  # noqa: E402

try:  # noqa: E402
    from export_phase5_laur_mlp_runtime import export_runtime_dir
except Exception:  # pragma: no cover - export is optional for blocked setups.
    export_runtime_dir = None  # type: ignore[assignment]


DEFAULT_BINARY = "build/phase1a-batch/phase1a_batch.exe"
DEFAULT_SCENARIO_DIR = "outputs/tmp/phase1a/generated/phase1a-generated-random"
DEFAULT_OUTPUT_DIR = "outputs/logs/phase5p5_laur_diagnostic_preflight"
DEFAULT_SUMMARY_JSON = "outputs/reports/phase5p5_laur_diagnostic_preflight_summary.json"
DEFAULT_REPORT = "outputs/reports/phase5p5_laur_diagnostic_preflight_report.md"
DEFAULT_SUMMARY_CSV = "outputs/tables/phase5p5_laur_diagnostic_preflight_summary.csv"
DEFAULT_PAIRED_CSV = "outputs/tables/phase5p5_laur_diagnostic_preflight_paired.csv"
DEFAULT_REPAIR3_WEIGHTS = "artifacts/models/laur_ltm/full_repair3_stable_tie001_mlp/laur_mlp_v1_weights.json"
DEFAULT_REPAIR3_RUNTIME = "outputs/tmp/phase5/laur_repair3_stable_tie001_mlp_runtime"
DEFAULT_REPAIR5D_SPEC = "outputs/reports/phase4f_repair5d_best_composite_spec.json"
DEFAULT_REPAIR5D_RUNTIME = "artifacts/models/laur_ltm/repair5d_composite_distilled"
DEFAULT_REPAIR5E_OOD_GUARD_RUNTIME = "artifacts/models/laur_ltm/repair5d_composite_distilled_ood_guard"
DEFAULT_REPAIR5E2_RUNTIME = "artifacts/models/laur_ltm/repair5e2_guarded_oracle_aligned_selector"
DEFAULT_REPAIR5E3_RUNTIME = "artifacts/models/laur_ltm/repair5e3_split_guarded_selector"
DEFAULT_REPAIR5E3_E2_SHUFFLED_RUNTIME = "artifacts/models/laur_ltm/repair5e3_e2_shuffled_support_diagnostic"
DEFAULT_REPAIR5E4_RUNTIME = "artifacts/models/laur_ltm/repair5e4_closed_loop_utility_selector"
DEFAULT_REPAIR5E4_SHUFFLED_RUNTIME = "artifacts/models/laur_ltm/repair5e4_closed_loop_utility_selector_shuffled_labels_diagnostic"
DEFAULT_REPAIR5E4_E3_CALIBRATED_RUNTIME = "artifacts/models/laur_ltm/repair5e4_calibrated_guard_only_on_e3_split"
DEFAULT_REPAIR5E5_RUNTIME = "artifacts/models/laur_ltm/repair5e5_crossfold_utility_reranker"
DEFAULT_REPAIR5E5_SHUFFLED_RUNTIME = "artifacts/models/laur_ltm/repair5e5_crossfold_utility_reranker_shuffled_labels_diagnostic"
DEFAULT_REPAIR5E5_LOOSE_RUNTIME = "artifacts/models/laur_ltm/repair5e5_crossfold_utility_reranker_loose_threshold_diagnostic"
DEFAULT_REPAIR5E5_STRICT_RUNTIME = "artifacts/models/laur_ltm/repair5e5_crossfold_utility_reranker_strict_threshold_diagnostic"
DEFAULT_ORACLE_SUMMARY_JSON = "outputs/reports/phase5p5_oracle_update_preflight_summary.json"
DEFAULT_ORACLE_REPORT = "outputs/reports/phase5p5_oracle_update_preflight_report.md"

MAPS = {
    "random-32-32-20": "external/lacam2/scripts/map/random-32-32-20.map",
    "maze-32-32-4": "external/lacam2/scripts/map/maze-32-32-4.map",
    "warehouse-10-20-10-2-1": "external/lacam2/scripts/map/warehouse-10-20-10-2-1.map",
}

NONADDITIVE_RULES = {
    "commit_heavy",
    "block_heavy",
    "block_light",
    "wait_light",
    "wait_heavy",
    "decay_095",
    "decay_090",
}

ORACLE_STATIC_RULES = tuple(sorted(NONADDITIVE_RULES))


@dataclass(frozen=True)
class MethodSpec:
    method: str
    alias: str
    extra_args: tuple[str, ...] = ()
    diagnostic_note: str = ""
    hide_from_report: bool = False


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


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


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def _write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _mean(values: list[float]) -> float | None:
    finite_values = [float(value) for value in values if math.isfinite(float(value))]
    return statistics.mean(finite_values) if finite_values else None


def _number(row: dict[str, Any], key: str) -> float | None:
    value = row.get(key)
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _jsonl_name(output_dir: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return output_dir / f"phase5p5_laur_diagnostic_preflight_{stamp}.jsonl"


def ensure_repair3_runtime(root: Path, weights: Path, runtime_dir: Path) -> tuple[Path | None, str]:
    required = [
        "features.txt",
        "rules.csv",
        "layer0_weight.csv",
        "rule_head_weight.csv",
        "rule_head_bias.csv",
    ]
    if all((runtime_dir / name).exists() for name in required):
        return runtime_dir, "existing_runtime_dir"
    if weights.exists() and export_runtime_dir is not None:
        export_runtime_dir(weights, runtime_dir)
        return runtime_dir, "exported_from_weights_json"
    if weights.exists():
        return None, "weights_exist_but_export_helper_unavailable"
    return None, "missing_repair3_weights_json"


def build_methods(
    *,
    root: Path,
    additive_model: Path,
    repair3_runtime: Path | None,
    repair5d_runtime: Path | None,
    repair5e_ood_guard_runtime: Path | None,
    repair5e2_runtime: Path | None = None,
    repair5e3_runtime: Path | None = None,
    repair5e3_e2_shuffled_runtime: Path | None = None,
    repair5e4_runtime: Path | None = None,
    repair5e4_shuffled_runtime: Path | None = None,
    repair5e4_e3_calibrated_runtime: Path | None = None,
    repair5e5_runtime: Path | None = None,
    repair5e5_shuffled_runtime: Path | None = None,
    repair5e5_loose_runtime: Path | None = None,
    repair5e5_strict_runtime: Path | None = None,
    include_static_proxies: bool,
    include_oracle_static_probe: bool,
    include_ood_guard_candidate: bool = False,
    include_repair5e2_candidate: bool = False,
    include_repair5e3_candidate: bool = False,
    include_repair5e3_e2_ablation_candidates: bool = False,
    include_repair5e4_candidate: bool = False,
    include_repair5e4_ablation_candidates: bool = False,
    include_repair5e5_candidate: bool = False,
    include_repair5e5_ablation_candidates: bool = False,
    ood_guard_z_threshold: float = 5.0,
    repair5e2_ood_guard_z_threshold: float = 5.0,
    repair5e3_ood_guard_z_threshold: float = 5.0,
    repair5e4_ood_guard_z_threshold: float = 5.0,
    repair5e5_ood_guard_z_threshold: float = 5.0,
) -> tuple[list[MethodSpec], list[dict[str, Any]]]:
    methods = [
        MethodSpec("lacam_star", "lacam_star"),
        MethodSpec("lacam_star_ltm", "lacam_star_ltm"),
        MethodSpec(
            "lacam_star_lau_ltm",
            "always_additive_defer",
            ("--laur-force-additive", "--laur-model-path", str(additive_model)),
            "force-additive/defer parity diagnostic",
        ),
    ]
    skipped: list[dict[str, Any]] = []
    if repair3_runtime is not None:
        methods.append(
            MethodSpec(
                "lacam_star_lau_ltm",
                "repair3_safe_runtime",
                ("--laur-model-path", str(repair3_runtime), "--laur-safety-threshold", "0.30"),
                "conservative Repair3 runtime reference",
            )
        )
    else:
        skipped.append({"method": "repair3_safe_runtime", "reason": "runtime_model_unavailable"})

    if repair5d_runtime is not None:
        methods.extend(
            [
                MethodSpec(
                    "lacam_star_lau_ltm",
                    "repair5d_composite_diagnostic_distilled",
                    ("--laur-model-path", str(repair5d_runtime), "--laur-safety-threshold", "0.30"),
                    "Repair5D composite distilled into existing LAUR MLP runtime, diagnostic only",
                ),
                MethodSpec(
                    "lacam_star_lau_ltm",
                    "repair5d_force_additive_defer_parity",
                    ("--laur-force-additive", "--laur-model-path", str(repair5d_runtime)),
                    "Repair5D runtime path with forced additive/defer parity",
                ),
            ]
        )
        skipped.append(
            {
                "method": "repair5d_native_composite_export",
                "reason": "not_feasible_current_cxx_runtime_accepts_single_mlp_runtime_only_distilled_bridge_used",
            }
        )
    else:
        skipped.append({"method": "repair5d_composite_diagnostic_distilled", "reason": "runtime_model_unavailable"})
        skipped.append({"method": "repair5d_force_additive_defer_parity", "reason": "runtime_model_unavailable"})

    if include_ood_guard_candidate and repair5e_ood_guard_runtime is not None:
        methods.extend(
            [
                MethodSpec(
                    "lacam_star_lau_ltm",
                    "repair5e_caseb_ood_guard_distilled",
                    (
                        "--laur-model-path",
                        str(repair5e_ood_guard_runtime),
                        "--laur-safety-threshold",
                        "0.30",
                        "--laur-ood-z-threshold",
                        str(float(ood_guard_z_threshold)),
                    ),
                    "Repair5E.1 diagnostic OOD/defer guard around Repair5D distill bridge",
                ),
                MethodSpec(
                    "lacam_star_lau_ltm",
                    "repair5e_caseb_ood_guard_force_additive_parity",
                    (
                        "--laur-force-additive",
                        "--laur-model-path",
                        str(repair5e_ood_guard_runtime),
                        "--laur-ood-z-threshold",
                        str(float(ood_guard_z_threshold)),
                    ),
                    "Repair5E.1 OOD guard path with forced additive/defer parity",
                ),
            ]
        )
    elif include_ood_guard_candidate:
        skipped.append(
            {
                "method": "repair5e_caseb_ood_guard_distilled",
                "reason": "runtime_model_unavailable",
            }
        )

    if include_repair5e2_candidate and repair5e2_runtime is not None:
        methods.extend(
            [
                MethodSpec(
                    "lacam_star_lau_ltm",
                    "repair5e2_guarded_oracle_aligned_selector",
                    (
                        "--laur-model-path",
                        str(repair5e2_runtime),
                        "--laur-safety-threshold",
                        "0.30",
                        "--laur-ood-z-threshold",
                        str(float(repair5e2_ood_guard_z_threshold)),
                    ),
                    "Repair5E.2 guarded oracle-aligned non-additive recovery selector, diagnostic only",
                ),
                MethodSpec(
                    "lacam_star_lau_ltm",
                    "repair5e2_guarded_oracle_aligned_selector_force_additive_parity",
                    (
                        "--laur-force-additive",
                        "--laur-model-path",
                        str(repair5e2_runtime),
                        "--laur-ood-z-threshold",
                        str(float(repair5e2_ood_guard_z_threshold)),
                    ),
                    "Repair5E.2 runtime path with forced additive/defer parity",
                ),
            ]
        )
    elif include_repair5e2_candidate:
        skipped.append(
            {
                "method": "repair5e2_guarded_oracle_aligned_selector",
                "reason": "runtime_model_unavailable",
            }
        )

    if include_repair5e3_candidate and repair5e3_runtime is not None:
        methods.extend(
            [
                MethodSpec(
                    "lacam_star_lau_ltm",
                    "repair5e3_split_guarded_selector",
                    (
                        "--laur-model-path",
                        str(repair5e3_runtime),
                        "--laur-safety-threshold",
                        "0.30",
                        "--laur-ood-z-threshold",
                        str(float(repair5e3_ood_guard_z_threshold)),
                    ),
                    "Repair5E.3 train-only split guarded selector, diagnostic only",
                ),
                MethodSpec(
                    "lacam_star_lau_ltm",
                    "repair5e3_split_guarded_selector_force_additive_parity",
                    (
                        "--laur-force-additive",
                        "--laur-model-path",
                        str(repair5e3_runtime),
                        "--laur-ood-z-threshold",
                        str(float(repair5e3_ood_guard_z_threshold)),
                    ),
                    "Repair5E.3 runtime path with forced additive/defer parity",
                ),
            ]
        )
    elif include_repair5e3_candidate:
        skipped.append(
            {
                "method": "repair5e3_split_guarded_selector",
                "reason": "runtime_model_unavailable",
            }
        )

    if include_repair5e3_e2_ablation_candidates and repair5e2_runtime is not None:
        methods.append(
            MethodSpec(
                "lacam_star_lau_ltm",
                "repair5e3_e2_recovery_disabled_parity",
                (
                    "--laur-force-additive",
                    "--laur-model-path",
                    str(repair5e2_runtime),
                    "--laur-ood-z-threshold",
                    str(float(repair5e2_ood_guard_z_threshold)),
                ),
                "Repair5E.3 ablation: disable E2 recovery by forcing additive/defer parity",
            )
        )
    elif include_repair5e3_e2_ablation_candidates:
        skipped.append(
            {
                "method": "repair5e3_e2_recovery_disabled_parity",
                "reason": "repair5e2_runtime_model_unavailable",
            }
        )

    if include_repair5e3_e2_ablation_candidates and repair5e3_e2_shuffled_runtime is not None:
        methods.append(
            MethodSpec(
                "lacam_star_lau_ltm",
                "repair5e3_e2_recovery_shuffled_support_diagnostic",
                (
                    "--laur-model-path",
                    str(repair5e3_e2_shuffled_runtime),
                    "--laur-safety-threshold",
                    "0.30",
                    "--laur-ood-z-threshold",
                    str(float(repair5e2_ood_guard_z_threshold)),
                ),
                "Repair5E.3 ablation: shuffled E2 support table diagnostic",
            )
        )
    elif include_repair5e3_e2_ablation_candidates:
        skipped.append(
            {
                "method": "repair5e3_e2_recovery_shuffled_support_diagnostic",
                "reason": "shuffled_runtime_model_unavailable",
            }
        )

    if include_repair5e4_ablation_candidates and repair5e4_e3_calibrated_runtime is not None:
        methods.append(
            MethodSpec(
                "lacam_star_lau_ltm",
                "repair5e4_calibrated_guard_only_on_e3_split",
                (
                    "--laur-model-path",
                    str(repair5e4_e3_calibrated_runtime),
                    "--laur-safety-threshold",
                    "0.30",
                    "--laur-ood-z-threshold",
                    str(float(repair5e4_ood_guard_z_threshold)),
                ),
                "Repair5E.4 ablation: E3 split selector with calibrated E4 OOD stats",
            )
        )
    elif include_repair5e4_ablation_candidates:
        skipped.append(
            {
                "method": "repair5e4_calibrated_guard_only_on_e3_split",
                "reason": "runtime_model_unavailable",
            }
        )

    if include_repair5e4_candidate and repair5e4_runtime is not None:
        methods.extend(
            [
                MethodSpec(
                    "lacam_star_lau_ltm",
                    "repair5e4_closed_loop_utility_selector",
                    (
                        "--laur-model-path",
                        str(repair5e4_runtime),
                        "--laur-safety-threshold",
                        "0.30",
                        "--laur-ood-z-threshold",
                        str(float(repair5e4_ood_guard_z_threshold)),
                    ),
                    "Repair5E.4 closed-loop utility nearest-neighbor selector, diagnostic only",
                ),
                MethodSpec(
                    "lacam_star_lau_ltm",
                    "repair5e4_closed_loop_utility_selector_force_additive_parity",
                    (
                        "--laur-force-additive",
                        "--laur-model-path",
                        str(repair5e4_runtime),
                        "--laur-ood-z-threshold",
                        str(float(repair5e4_ood_guard_z_threshold)),
                    ),
                    "Repair5E.4 runtime path with forced additive/defer parity",
                ),
            ]
        )
    elif include_repair5e4_candidate:
        skipped.append(
            {
                "method": "repair5e4_closed_loop_utility_selector",
                "reason": "runtime_model_unavailable",
            }
        )

    if include_repair5e4_ablation_candidates and repair5e4_runtime is not None:
        methods.extend(
            [
                MethodSpec(
                    "lacam_star_lau_ltm",
                    "repair5e4_closed_loop_utility_selector_recovery_disabled_parity",
                    (
                        "--laur-force-additive",
                        "--laur-model-path",
                        str(repair5e4_runtime),
                        "--laur-ood-z-threshold",
                        str(float(repair5e4_ood_guard_z_threshold)),
                    ),
                    "Repair5E.4 ablation: disable utility recovery by forcing additive/defer parity",
                ),
                MethodSpec(
                    "lacam_star_lau_ltm",
                    "repair5e4_closed_loop_utility_selector_no_ood_guard_diagnostic",
                    (
                        "--laur-model-path",
                        str(repair5e4_runtime),
                        "--laur-safety-threshold",
                        "0.30",
                    ),
                    "Repair5E.4 ablation: utility selector with OOD guard disabled, diagnostic only",
                ),
            ]
        )
    elif include_repair5e4_ablation_candidates:
        skipped.append(
            {
                "method": "repair5e4_closed_loop_utility_selector_ablation",
                "reason": "runtime_model_unavailable",
            }
        )

    if include_repair5e4_ablation_candidates and repair5e4_shuffled_runtime is not None:
        methods.append(
            MethodSpec(
                "lacam_star_lau_ltm",
                "repair5e4_closed_loop_utility_selector_shuffled_labels_diagnostic",
                (
                    "--laur-model-path",
                    str(repair5e4_shuffled_runtime),
                    "--laur-safety-threshold",
                    "0.30",
                    "--laur-ood-z-threshold",
                    str(float(repair5e4_ood_guard_z_threshold)),
                ),
                "Repair5E.4 ablation: shuffled utility labels diagnostic",
            )
        )
    elif include_repair5e4_ablation_candidates:
        skipped.append(
            {
                "method": "repair5e4_closed_loop_utility_selector_shuffled_labels_diagnostic",
                "reason": "shuffled_runtime_model_unavailable",
            }
        )

    if include_repair5e5_candidate and repair5e5_runtime is not None:
        methods.extend(
            [
                MethodSpec(
                    "lacam_star_lau_ltm",
                    "repair5e5_crossfold_utility_reranker",
                    (
                        "--laur-model-path",
                        str(repair5e5_runtime),
                        "--laur-safety-threshold",
                        "0.30",
                        "--laur-ood-z-threshold",
                        str(float(repair5e5_ood_guard_z_threshold)),
                    ),
                    "Repair5E.5 cross-fold utility reranker, diagnostic only",
                ),
                MethodSpec(
                    "lacam_star_lau_ltm",
                    "repair5e5_crossfold_utility_reranker_force_additive_parity",
                    (
                        "--laur-force-additive",
                        "--laur-model-path",
                        str(repair5e5_runtime),
                        "--laur-ood-z-threshold",
                        str(float(repair5e5_ood_guard_z_threshold)),
                    ),
                    "Repair5E.5 runtime path with forced additive/defer parity",
                ),
            ]
        )
    elif include_repair5e5_candidate:
        skipped.append(
            {
                "method": "repair5e5_crossfold_utility_reranker",
                "reason": "runtime_model_unavailable",
            }
        )

    if include_repair5e5_ablation_candidates and repair5e5_runtime is not None:
        methods.extend(
            [
                MethodSpec(
                    "lacam_star_lau_ltm",
                    "repair5e5_crossfold_utility_reranker_recovery_disabled_parity",
                    (
                        "--laur-force-additive",
                        "--laur-model-path",
                        str(repair5e5_runtime),
                        "--laur-ood-z-threshold",
                        str(float(repair5e5_ood_guard_z_threshold)),
                    ),
                    "Repair5E.5 ablation: disable utility recovery by forcing additive/defer parity",
                ),
                MethodSpec(
                    "lacam_star_lau_ltm",
                    "repair5e5_crossfold_utility_reranker_no_ood_guard_diagnostic",
                    (
                        "--laur-model-path",
                        str(repair5e5_runtime),
                        "--laur-safety-threshold",
                        "0.30",
                    ),
                    "Repair5E.5 ablation: cross-fold utility reranker with OOD guard disabled",
                ),
            ]
        )
    elif include_repair5e5_ablation_candidates:
        skipped.append(
            {
                "method": "repair5e5_crossfold_utility_reranker_ablation",
                "reason": "runtime_model_unavailable",
            }
        )

    if include_repair5e5_ablation_candidates and repair5e5_shuffled_runtime is not None:
        methods.append(
            MethodSpec(
                "lacam_star_lau_ltm",
                "repair5e5_crossfold_utility_reranker_shuffled_labels_diagnostic",
                (
                    "--laur-model-path",
                    str(repair5e5_shuffled_runtime),
                    "--laur-safety-threshold",
                    "0.30",
                    "--laur-ood-z-threshold",
                    str(float(repair5e5_ood_guard_z_threshold)),
                ),
                "Repair5E.5 ablation: shuffled cross-fold utility labels",
            )
        )
    elif include_repair5e5_ablation_candidates:
        skipped.append(
            {
                "method": "repair5e5_crossfold_utility_reranker_shuffled_labels_diagnostic",
                "reason": "shuffled_runtime_model_unavailable",
            }
        )

    if include_repair5e5_ablation_candidates and repair5e5_loose_runtime is not None:
        methods.append(
            MethodSpec(
                "lacam_star_lau_ltm",
                "repair5e5_crossfold_utility_reranker_loose_threshold_diagnostic",
                (
                    "--laur-model-path",
                    str(repair5e5_loose_runtime),
                    "--laur-safety-threshold",
                    "0.30",
                    "--laur-ood-z-threshold",
                    str(float(repair5e5_ood_guard_z_threshold)),
                ),
                "Repair5E.5 ablation: loose threshold diagnostic",
            )
        )
    elif include_repair5e5_ablation_candidates:
        skipped.append(
            {
                "method": "repair5e5_crossfold_utility_reranker_loose_threshold_diagnostic",
                "reason": "loose_runtime_model_unavailable",
            }
        )

    if include_repair5e5_ablation_candidates and repair5e5_strict_runtime is not None:
        methods.append(
            MethodSpec(
                "lacam_star_lau_ltm",
                "repair5e5_crossfold_utility_reranker_strict_threshold_diagnostic",
                (
                    "--laur-model-path",
                    str(repair5e5_strict_runtime),
                    "--laur-safety-threshold",
                    "0.30",
                    "--laur-ood-z-threshold",
                    str(float(repair5e5_ood_guard_z_threshold)),
                ),
                "Repair5E.5 ablation: strict threshold diagnostic",
            )
        )
    elif include_repair5e5_ablation_candidates:
        skipped.append(
            {
                "method": "repair5e5_crossfold_utility_reranker_strict_threshold_diagnostic",
                "reason": "strict_runtime_model_unavailable",
            }
        )

    if include_static_proxies:
        for rule in ("block_heavy", "wait_light", "decay_095"):
            methods.append(
                MethodSpec(
                    "lacam_star_lau_ltm",
                    f"static_{rule}",
                    ("--laur-static-rule", rule, "--laur-allow-pre-first-solution"),
                    "static rule proxy, not a learned Repair5C runtime",
                )
            )

    if include_oracle_static_probe:
        for rule in ORACLE_STATIC_RULES:
            methods.append(
                MethodSpec(
                    "lacam_star_lau_ltm",
                    f"oracle_probe_static_{rule}",
                    ("--laur-static-rule", rule),
                    "support row for static-rule oracle upper-bound diagnostic",
                    hide_from_report=True,
                )
            )
        skipped.append(
            {
                "method": "oracle_teacher_forced_best_safe_update_full_hook",
                "reason": "full_per_update_teacher_force_hook_not_available_static_rule_probe_proxy_executed",
            }
        )
    else:
        skipped.append(
            {
                "method": "oracle_teacher_forced_best_safe_update",
                "reason": "not_executed_pass_include_oracle_static_probe_for_static_upper_bound_proxy",
            }
        )
    return methods, skipped


def run_solver_grid(
    *,
    root: Path,
    binary: Path,
    output_jsonl: Path,
    command_log: Path,
    maps: list[str],
    agent_counts: list[int],
    instance_ids: list[int],
    time_limit_sec: float,
    ltm_max_iterations: int,
    scenario_dir: Path,
    methods: list[MethodSpec],
    laur_update_log_jsonl: Path,
) -> list[dict[str, Any]]:
    command_log.parent.mkdir(parents=True, exist_ok=True)
    command_rows: list[dict[str, Any]] = []
    for map_name in maps:
        map_path = root / MAPS[map_name]
        if not map_path.exists():
            raise FileNotFoundError(f"missing map path {map_path}")
        for instance_id in instance_ids:
            scen_path = scenario_dir / f"{map_name}-random-{instance_id}.scen"
            if not scen_path.exists():
                raise FileNotFoundError(f"missing scenario path {scen_path}")
            for agents in agent_counts:
                for spec in methods:
                    extra_args = list(spec.extra_args)
                    if spec.method == "lacam_star_lau_ltm":
                        extra_args.extend(["--laur-update-log-jsonl", str(laur_update_log_jsonl)])
                    command = [
                        str(binary),
                        "--method",
                        spec.method,
                        "--method-alias",
                        spec.alias,
                        "--map",
                        str(map_path),
                        "--scen",
                        str(scen_path),
                        "--agents",
                        str(int(agents)),
                        "--seed",
                        str(instance_id),
                        "--time-limit-sec",
                        str(float(time_limit_sec)),
                        "--ltm-max-iterations",
                        str(int(ltm_max_iterations)),
                        "--output-jsonl",
                        str(output_jsonl),
                        "--map-name",
                        map_name,
                        "--scen-id",
                        scen_path.name,
                        "--manifest",
                        "phase5p5-diagnostic-preflight",
                        "--project-commit",
                        git_value(["rev-parse", "--short", "HEAD"], root),
                        "--external-commit",
                        "local",
                        "--branch",
                        git_value(["branch", "--show-current"], root),
                        "--dirty",
                        dirty_state(root),
                        "--platform",
                        "Windows Phase5.5 LAUR diagnostic preflight",
                        *extra_args,
                    ]
                    completed = subprocess.run(command, cwd=root, text=True, capture_output=True)
                    row = {
                        "method": spec.alias,
                        "map": map_name,
                        "agents": agents,
                        "seed": instance_id,
                        "returncode": completed.returncode,
                        "stdout": completed.stdout.strip()[-500:],
                        "stderr": completed.stderr.strip()[-500:],
                    }
                    command_rows.append(row)
                    with command_log.open("a", encoding="utf-8") as handle:
                        handle.write(json.dumps(row, sort_keys=True) + "\n")
                    if completed.returncode == 1:
                        raise RuntimeError(f"solver crashed for {spec.alias} {map_name} a{agents} i{instance_id}: {completed.stderr}")
    return command_rows


def summarize_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, int, str], list[dict[str, Any]]] = {}
    for raw in rows:
        row = normalize_run_row(raw)
        grouped.setdefault((str(row["map"]), int(row["agents"]), str(row["method"])), []).append(row)

    summary: list[dict[str, Any]] = []
    for (map_name, agents, method), group in sorted(grouped.items()):
        ratios = [_number(row, "sum_of_loss_ratio") for row in group if row.get("success")]
        expanded = [_number(row, "expanded_nodes") for row in group]
        ttfs = [_number(row, "time_to_first_solution_ms") for row in group]
        returned = [_number(row, "returned_solutions_count") for row in group]
        pibt = [_number(row, "low_level_pibt_calls") for row in group]
        laur_ms = [_number(row, "laur_inference_total_ms") for row in group]
        inference_counts = [_number(row, "laur_inference_count") for row in group]
        fallback_counts = [_number(row, "laur_additive_fallback_count") for row in group]
        safety_counts = [_number(row, "laur_safety_disabled_count") for row in group]
        nonadditive_updates = 0
        total_update_decisions = 0
        selected_rules: dict[str, int] = {}
        for row in group:
            for rule, count in (row.get("laur_selected_rules") or {}).items():
                selected_rules[str(rule)] = selected_rules.get(str(rule), 0) + int(count)
                total_update_decisions += int(count)
                if str(rule) in NONADDITIVE_RULES:
                    nonadditive_updates += int(count)
            total_update_decisions += int(row.get("laur_additive_fallback_count") or 0)
        summary.append(
            {
                "map": map_name,
                "agents": agents,
                "method": method,
                "runs": len(group),
                "successes": sum(1 for row in group if row.get("success")),
                "success_rate": sum(1 for row in group if row.get("success")) / len(group) if group else 0.0,
                "sum_of_loss_ratio_mean": _mean([value for value in ratios if value is not None]),
                "expanded_nodes_mean": _mean([value for value in expanded if value is not None]),
                "time_to_first_solution_ms_mean": _mean([value for value in ttfs if value is not None]),
                "returned_solutions_count_mean": _mean([value for value in returned if value is not None]),
                "low_level_pibt_calls_mean": _mean([value for value in pibt if value is not None]),
                "laur_overhead_ms_mean": _mean([value for value in laur_ms if value is not None]),
                "laur_inference_count_mean": _mean([value for value in inference_counts if value is not None]),
                "laur_additive_fallback_count_mean": _mean([value for value in fallback_counts if value is not None]),
                "laur_safety_disabled_count_mean": _mean([value for value in safety_counts if value is not None]),
                "fallback_defer_rate": (
                    sum(value for value in fallback_counts if value is not None) / total_update_decisions
                    if total_update_decisions
                    else None
                ),
                "non_additive_update_rate": (
                    nonadditive_updates / total_update_decisions if total_update_decisions else None
                ),
                "selected_harmful_update_rate": None,
                "selected_rules": json.dumps(dict(sorted(selected_rules.items())), sort_keys=True),
            }
        )
    return summary


def add_ltm_group_deltas(summary_rows: list[dict[str, Any]], baseline: str = "lacam_star_ltm") -> list[dict[str, Any]]:
    baselines = {
        (row["map"], int(row["agents"])): row
        for row in summary_rows
        if row["method"] == baseline
    }
    out: list[dict[str, Any]] = []
    for row in summary_rows:
        next_row = dict(row)
        base = baselines.get((row["map"], int(row["agents"])))
        if base is None or row["method"] == baseline:
            next_row["ratio_delta_vs_ltm"] = None
            next_row["expanded_delta_vs_ltm"] = None
            next_row["ttfs_delta_vs_ltm"] = None
        else:
            ratio = row.get("sum_of_loss_ratio_mean")
            base_ratio = base.get("sum_of_loss_ratio_mean")
            expanded = row.get("expanded_nodes_mean")
            base_expanded = base.get("expanded_nodes_mean")
            ttfs = row.get("time_to_first_solution_ms_mean")
            base_ttfs = base.get("time_to_first_solution_ms_mean")
            next_row["ratio_delta_vs_ltm"] = (
                float(ratio) - float(base_ratio)
                if ratio is not None and base_ratio is not None
                else None
            )
            next_row["expanded_delta_vs_ltm"] = (
                float(expanded) - float(base_expanded)
                if expanded is not None and base_expanded is not None
                else None
            )
            next_row["ttfs_delta_vs_ltm"] = (
                float(ttfs) - float(base_ttfs)
                if ttfs is not None and base_ttfs is not None
                else None
            )
        out.append(next_row)
    return out


def paired_rows(rows: list[dict[str, Any]], baseline: str = "lacam_star_ltm") -> list[dict[str, Any]]:
    by_key: dict[tuple[Any, ...], dict[str, dict[str, Any]]] = {}
    for raw in rows:
        row = normalize_run_row(raw)
        key = (row.get("map"), int(row.get("agents", 0)), row.get("seed"), row.get("scen"))
        by_key.setdefault(key, {})[str(row.get("method"))] = row

    pairs: list[dict[str, Any]] = []
    for key, methods in sorted(by_key.items()):
        if baseline not in methods:
            continue
        base = methods[baseline]
        for method, contender in sorted(methods.items()):
            if method == baseline:
                continue
            base_ratio = _number(base, "sum_of_loss_ratio")
            cont_ratio = _number(contender, "sum_of_loss_ratio")
            pairs.append(
                {
                    "map": key[0],
                    "agents": key[1],
                    "seed": key[2],
                    "scen": key[3],
                    "baseline_method": baseline,
                    "contender_method": method,
                    "baseline_success": bool(base.get("success")),
                    "contender_success": bool(contender.get("success")),
                    "baseline_ratio": base_ratio,
                    "contender_ratio": cont_ratio,
                    "delta_ratio": (
                        float(cont_ratio) - float(base_ratio)
                        if base_ratio is not None and cont_ratio is not None
                        else None
                    ),
                    "contender_better": (
                        bool(base.get("success"))
                        and bool(contender.get("success"))
                        and base_ratio is not None
                        and cont_ratio is not None
                        and float(cont_ratio) < float(base_ratio)
                    ),
                }
            )
    return pairs


def is_oracle_probe_row(row: dict[str, Any]) -> bool:
    return str(row.get("method", "")).startswith("oracle_probe_static_")


def synthesize_oracle_static_proxy_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Choose the best static-rule probe per scenario as an oracle proxy row."""

    grouped: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
    for raw in rows:
        row = normalize_run_row(raw)
        if not is_oracle_probe_row(row):
            continue
        key = (row.get("map"), int(row.get("agents", 0)), row.get("seed"), row.get("scen"))
        grouped.setdefault(key, []).append(row)

    def score(row: dict[str, Any]) -> tuple[int, float, float, float]:
        success = 0 if row.get("success") else 1
        ratio = _number(row, "sum_of_loss_ratio")
        expanded = _number(row, "expanded_nodes")
        ttfs = _number(row, "time_to_first_solution_ms")
        return (
            success,
            float(ratio) if ratio is not None else float("inf"),
            float(expanded) if expanded is not None else float("inf"),
            float(ttfs) if ttfs is not None else float("inf"),
        )

    out: list[dict[str, Any]] = []
    for candidates in grouped.values():
        best = min(candidates, key=score)
        row = dict(best)
        source_method = str(row.get("method", ""))
        row["method"] = "oracle_teacher_forced_best_safe_update_static_proxy"
        row["oracle_upper_bound_diagnostic"] = True
        row["oracle_proxy_source_method"] = source_method
        row["oracle_proxy_scope"] = "best_static_preset_rule_per_scenario_not_per_update_teacher_force"
        out.append(row)
    return out


def paired_method_stats(paired: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in paired:
        grouped.setdefault(str(row["contender_method"]), []).append(row)
    out: dict[str, dict[str, Any]] = {}
    for method, rows in sorted(grouped.items()):
        deltas = [
            float(row["delta_ratio"])
            for row in rows
            if row.get("delta_ratio") is not None
        ]
        out[method] = {
            "rows": len(rows),
            "better": sum(1 for row in rows if row.get("contender_better") is True),
            "worse": sum(1 for value in deltas if value > 1.0e-12),
            "equal": sum(1 for value in deltas if abs(value) <= 1.0e-12),
            "mean_delta_ratio_vs_ltm": _mean(deltas),
        }
    return out


def decision_table_interpretation(
    method_stats: dict[str, dict[str, Any]],
    method_flags: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    method_flags = method_flags or {}

    def clean_positive(method: str) -> bool:
        stats = method_stats.get(method, {})
        flags = method_flags.get(method, {})
        return (
            stats.get("mean_delta_ratio_vs_ltm") is not None
            and float(stats["mean_delta_ratio_vs_ltm"]) < 0.0
            and int(stats.get("better") or 0) > int(stats.get("worse") or 0)
            and int(flags.get("success_worse_than_ltm_groups") or 0) == 0
            and int(flags.get("ratio_worse_than_ltm_groups") or 0) <= 1
        )

    oracle = method_stats.get("oracle_teacher_forced_best_safe_update_static_proxy", {})
    oracle_positive = (
        oracle.get("mean_delta_ratio_vs_ltm") is not None
        and float(oracle["mean_delta_ratio_vs_ltm"]) < 0.0
        and int(oracle.get("better") or 0) > int(oracle.get("worse") or 0)
    )
    has_e5 = "repair5e5_crossfold_utility_reranker" in method_stats
    if has_e5:
        e5_positive = clean_positive("repair5e5_crossfold_utility_reranker")
        if e5_positive:
            case = "A"
            action = "larger_multi_map_validation_then_phase5p5_runtime_export_design"
        elif oracle_positive:
            case = "B"
            action = "e5_not_promotable_inspect_crossfold_utility_reranker"
        else:
            case = "C"
            action = "do_not_promote_repair5e5_consider_repair5f_side_branch_after_diagnostics"
        return {
            "case": case,
            "recommended_action": action,
            "repair5e5_crossfold_utility_reranker_positive": e5_positive,
            "oracle_positive": oracle_positive,
            "phase5p5_allowed": False,
            "phase6_allowed": False,
        }
    has_e4 = "repair5e4_closed_loop_utility_selector" in method_stats
    if has_e4:
        e4_positive = clean_positive("repair5e4_closed_loop_utility_selector")
        if e4_positive:
            case = "A"
            action = "larger_multi_map_validation_then_phase5p5_runtime_export_design"
        elif oracle_positive:
            case = "B"
            action = "e4_not_promotable_inspect_utility_labels_guard_and_feature_calibration"
        else:
            case = "C"
            action = "do_not_promote_repair5e4_rebuild_closed_loop_evidence"
        return {
            "case": case,
            "recommended_action": action,
            "repair5e4_closed_loop_utility_selector_positive": e4_positive,
            "oracle_positive": oracle_positive,
            "phase5p5_allowed": False,
            "phase6_allowed": False,
        }
    has_e3 = "repair5e3_split_guarded_selector" in method_stats
    if has_e3:
        e3_positive = clean_positive("repair5e3_split_guarded_selector")
        e2_positive = clean_positive("repair5e2_guarded_oracle_aligned_selector")
        if e3_positive:
            case = "A"
            action = "larger_multi_map_validation_then_phase5p5_runtime_export_design"
        elif e2_positive:
            case = "B"
            action = "improve_utility_or_ranking_labels_do_not_jump_to_delta_updateparams"
        elif "repair5e2_guarded_oracle_aligned_selector" in method_stats:
            case = "C"
            action = "treat_e2_as_same_scope_oracle_support_overfit_train_better_selector_do_not_promote"
        elif oracle_positive:
            case = "D"
            action = "open_repair5f_discussion_bounded_delta_updateparams_or_richer_ltm_representation"
        else:
            case = "C"
            action = "do_not_promote_rebuild_train_eval_selector_evidence"
        return {
            "case": case,
            "recommended_action": action,
            "repair5e2_survives_heldout": e2_positive,
            "repair5e3_split_selector_positive": e3_positive,
            "oracle_positive": oracle_positive,
            "phase5p5_allowed": False,
            "phase6_allowed": False,
        }

    repair5d = method_stats.get("repair5d_composite_diagnostic_distilled", {})
    repair5d_positive = (
        repair5d.get("mean_delta_ratio_vs_ltm") is not None
        and float(repair5d["mean_delta_ratio_vs_ltm"]) <= 0.0
        and int(repair5d.get("worse") or 0) <= int(repair5d.get("better") or 0)
    )
    if repair5d_positive and oracle_positive:
        case = "A"
        action = "prepare_multi_seed_composite_grid_and_formal_phase5p5_runtime_path"
    elif oracle_positive and not repair5d_positive:
        case = "B"
        action = "improve_composite_or_reranker_do_not_jump_to_delta_updateparams"
    elif not oracle_positive:
        case = "C"
        action = "stop_offline_gate_optimization_and_redesign_labels_or_output_space"
    else:
        case = "D"
        action = "tighten_selected_safety_and_defer_before_more_training"
    return {
        "case": case,
        "recommended_action": action,
        "repair5d_positive": repair5d_positive,
        "oracle_positive": oracle_positive,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
    }


def stop_condition_snapshot(summary_rows: list[dict[str, Any]], paired: list[dict[str, Any]]) -> dict[str, Any]:
    ltm_by_group = {
        (row["map"], int(row["agents"])): row
        for row in summary_rows
        if row["method"] == "lacam_star_ltm"
    }
    method_flags: dict[str, dict[str, Any]] = {}
    for row in summary_rows:
        method = str(row["method"])
        if method == "lacam_star_ltm":
            continue
        base = ltm_by_group.get((row["map"], int(row["agents"])))
        if not base:
            continue
        flags = method_flags.setdefault(
            method,
            {
                "success_worse_than_ltm_groups": 0,
                "ratio_worse_than_ltm_groups": 0,
                "zero_nonadditive_groups": 0,
            },
        )
        if float(row.get("success_rate") or 0.0) < float(base.get("success_rate") or 0.0):
            flags["success_worse_than_ltm_groups"] += 1
        ratio = row.get("sum_of_loss_ratio_mean")
        base_ratio = base.get("sum_of_loss_ratio_mean")
        if ratio is not None and base_ratio is not None and float(ratio) > float(base_ratio):
            flags["ratio_worse_than_ltm_groups"] += 1
        if row.get("non_additive_update_rate") == 0.0:
            flags["zero_nonadditive_groups"] += 1
    return {
        "method_flags": method_flags,
        "paired_rows": len(paired),
        "strict_safety_mask_blocks_all_learned_choices": any(
            row["method"] == "repair3_safe_runtime" and row.get("non_additive_update_rate") == 0.0
            for row in summary_rows
        ),
        "repair5c_composite_closed_loop_executed": False,
        "repair5d_composite_closed_loop_executed": any(
            row["method"] == "repair5d_composite_diagnostic_distilled"
            for row in summary_rows
        ),
        "oracle_replay_executed": any(
            row["method"] == "oracle_teacher_forced_best_safe_update_static_proxy"
            for row in summary_rows
        ),
        "oracle_replay_scope": "static_rule_proxy" if any(
            row["method"] == "oracle_teacher_forced_best_safe_update_static_proxy"
            for row in summary_rows
        ) else "not_executed",
    }


def write_report(path: Path, *, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Phase5.5 Repair5E LAUR Diagnostic Preflight Report\n\n")
        handle.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S %z').strip()}\n\n")
        handle.write("## Boundary\n\n")
        handle.write(
            "This is diagnostic-only closed-loop evidence. It does not permit Phase5.5 runtime promotion, "
            "does not permit Phase6, and does not change solver semantics.\n\n"
        )
        handle.write(f"- Phase5.5 allowed: `{summary.get('phase5p5_allowed')}`\n")
        handle.write(f"- Phase6 allowed: `{summary.get('phase6_allowed')}`\n")
        handle.write(f"- raw JSONL: `{summary.get('raw_jsonl')}`\n")
        handle.write(f"- LAUR update log JSONL: `{summary.get('laur_update_log_jsonl')}`\n")
        handle.write(f"- command log: `{summary.get('command_log_jsonl')}`\n\n")
        handle.write("## Provenance\n\n")
        handle.write(f"- git branch: `{summary.get('branch')}`\n")
        handle.write(f"- git commit: `{summary.get('commit')}`\n")
        handle.write(f"- git dirty state: `{summary.get('dirty')}`\n")
        handle.write(f"- clean tracked worktree: `{summary.get('clean_tracked_worktree')}`\n\n")

        handle.write("## Scope\n\n")
        scope = summary.get("scope", {})
        for key, value in scope.items():
            handle.write(f"- {key}: `{value}`\n")
        handle.write("\n## Runtime Availability\n\n")
        for skipped in summary.get("skipped_methods", []):
            handle.write(f"- `{skipped['method']}`: `{skipped['reason']}`\n")
        handle.write("\n## Group Summary\n\n")
        handle.write(
            "| map | agents | method | runs | success | ratio | d ratio | expanded | d expanded | TTFS ms | d TTFS | pibt | fallback | non-additive | overhead ms |\n"
        )
        handle.write("|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|\n")
        for row in summary.get("summary_rows", []):
            handle.write(
                f"| {row['map']} | {row['agents']} | {row['method']} | {row['runs']} | "
                f"{row['success_rate']:.6f} | {row.get('sum_of_loss_ratio_mean')} | "
                f"{row.get('ratio_delta_vs_ltm')} | "
                f"{row.get('expanded_nodes_mean')} | {row.get('expanded_delta_vs_ltm')} | "
                f"{row.get('time_to_first_solution_ms_mean')} | {row.get('ttfs_delta_vs_ltm')} | "
                f"{row.get('low_level_pibt_calls_mean')} | {row.get('fallback_defer_rate')} | "
                f"{row.get('non_additive_update_rate')} | {row.get('laur_overhead_ms_mean')} |\n"
            )
        handle.write("\n## Stop Condition Snapshot\n\n")
        handle.write(json.dumps(summary.get("stop_conditions"), indent=2, sort_keys=True))
        handle.write("\n\n## Decision Table Interpretation\n\n")
        handle.write(json.dumps(summary.get("decision_table_interpretation"), indent=2, sort_keys=True))
        handle.write("\n")


def write_oracle_report(path: Path, *, oracle: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Phase5.5 Oracle Update Preflight Diagnostic\n\n")
        handle.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S %z').strip()}\n\n")
        handle.write("This is an upper-bound diagnostic only. The full per-update teacher-force hook is not implemented; Repair5E used a best static preset-rule proxy per scenario.\n\n")
        handle.write("- phase5p5_allowed: `False`\n")
        handle.write("- phase6_allowed: `False`\n")
        handle.write(f"- scope: `{oracle.get('oracle_scope')}`\n")
        handle.write(f"- support rows: `{oracle.get('support_rows')}`\n")
        stats = oracle.get("paired_stats", {})
        handle.write(f"- paired rows: `{stats.get('rows')}`\n")
        handle.write(f"- better/equal/worse vs LTM: `{stats.get('better')}` / `{stats.get('equal')}` / `{stats.get('worse')}`\n")
        handle.write(f"- mean delta ratio vs LTM: `{stats.get('mean_delta_ratio_vs_ltm')}`\n\n")
        handle.write("## Interpretation\n\n")
        handle.write(
            "The static proxy is positive if its mean paired ratio delta is below zero and it wins more rows than it loses. "
            "Positive proxy evidence means there is closed-loop headroom in the preset update space, but it is not a learned runtime claim.\n"
        )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, default=Path(DEFAULT_BINARY))
    parser.add_argument("--scenario-dir", type=Path, default=Path(DEFAULT_SCENARIO_DIR))
    parser.add_argument("--output-dir", type=Path, default=Path(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--output-jsonl", type=Path)
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY_JSON))
    parser.add_argument("--summary-csv", type=Path, default=Path(DEFAULT_SUMMARY_CSV))
    parser.add_argument("--paired-csv", type=Path, default=Path(DEFAULT_PAIRED_CSV))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--oracle-summary-json", type=Path, default=Path(DEFAULT_ORACLE_SUMMARY_JSON))
    parser.add_argument("--oracle-report", type=Path, default=Path(DEFAULT_ORACLE_REPORT))
    parser.add_argument("--repair3-weights-json", type=Path, default=Path(DEFAULT_REPAIR3_WEIGHTS))
    parser.add_argument("--repair3-runtime-dir", type=Path, default=Path(DEFAULT_REPAIR3_RUNTIME))
    parser.add_argument("--repair5d-spec-json", type=Path, default=Path(DEFAULT_REPAIR5D_SPEC))
    parser.add_argument("--repair5d-runtime-dir", type=Path, default=Path(DEFAULT_REPAIR5D_RUNTIME))
    parser.add_argument("--repair5e-ood-guard-runtime-dir", type=Path, default=Path(DEFAULT_REPAIR5E_OOD_GUARD_RUNTIME))
    parser.add_argument("--repair5e2-runtime-dir", type=Path, default=Path(DEFAULT_REPAIR5E2_RUNTIME))
    parser.add_argument("--repair5e3-runtime-dir", type=Path, default=Path(DEFAULT_REPAIR5E3_RUNTIME))
    parser.add_argument(
        "--repair5e3-e2-shuffled-runtime-dir",
        type=Path,
        default=Path(DEFAULT_REPAIR5E3_E2_SHUFFLED_RUNTIME),
    )
    parser.add_argument("--repair5e4-runtime-dir", type=Path, default=Path(DEFAULT_REPAIR5E4_RUNTIME))
    parser.add_argument("--repair5e4-shuffled-runtime-dir", type=Path, default=Path(DEFAULT_REPAIR5E4_SHUFFLED_RUNTIME))
    parser.add_argument(
        "--repair5e4-e3-calibrated-runtime-dir",
        type=Path,
        default=Path(DEFAULT_REPAIR5E4_E3_CALIBRATED_RUNTIME),
    )
    parser.add_argument("--repair5e5-runtime-dir", type=Path, default=Path(DEFAULT_REPAIR5E5_RUNTIME))
    parser.add_argument("--repair5e5-shuffled-runtime-dir", type=Path, default=Path(DEFAULT_REPAIR5E5_SHUFFLED_RUNTIME))
    parser.add_argument("--repair5e5-loose-runtime-dir", type=Path, default=Path(DEFAULT_REPAIR5E5_LOOSE_RUNTIME))
    parser.add_argument("--repair5e5-strict-runtime-dir", type=Path, default=Path(DEFAULT_REPAIR5E5_STRICT_RUNTIME))
    parser.add_argument("--maps", nargs="+", choices=sorted(MAPS), default=list(MAPS))
    parser.add_argument("--agent-counts", nargs="+", type=int, default=[50, 100])
    parser.add_argument("--instances-per-setting", type=int, default=3)
    parser.add_argument(
        "--instance-start",
        type=int,
        default=1,
        help="First scenario instance id when --instance-ids is not supplied.",
    )
    parser.add_argument(
        "--instance-ids",
        nargs="+",
        type=int,
        help="Explicit scenario instance ids for held-out/train split validation.",
    )
    parser.add_argument("--time-limit-sec", type=float, default=3.0)
    parser.add_argument("--ltm-max-iterations", type=int, default=4)
    parser.add_argument("--include-static-proxies", action="store_true")
    parser.add_argument("--include-oracle-static-probe", action="store_true")
    parser.add_argument("--include-ood-guard-candidate", action="store_true")
    parser.add_argument("--include-repair5e2-candidate", action="store_true")
    parser.add_argument("--include-repair5e3-candidate", action="store_true")
    parser.add_argument("--include-repair5e3-e2-ablation-candidates", action="store_true")
    parser.add_argument("--include-repair5e4-candidate", action="store_true")
    parser.add_argument("--include-repair5e4-ablation-candidates", action="store_true")
    parser.add_argument("--include-repair5e5-candidate", action="store_true")
    parser.add_argument("--include-repair5e5-ablation-candidates", action="store_true")
    parser.add_argument(
        "--only-method-aliases",
        nargs="+",
        help=(
            "Restrict execution and summarization to specific report aliases. "
            "If oracle_teacher_forced_best_safe_update_static_proxy is listed, "
            "the hidden oracle_probe_static_* support rows are retained."
        ),
    )
    parser.add_argument("--ood-guard-z-threshold", type=float, default=5.0)
    parser.add_argument("--repair5e2-ood-guard-z-threshold", type=float, default=5.0)
    parser.add_argument("--repair5e3-ood-guard-z-threshold", type=float, default=5.0)
    parser.add_argument("--repair5e4-ood-guard-z-threshold", type=float, default=5.0)
    parser.add_argument("--repair5e5-ood-guard-z-threshold", type=float, default=5.0)
    parser.add_argument("--skip-solver", action="store_true", help="Only summarize an existing --output-jsonl.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    binary = resolve_path(args.binary, root)
    scenario_dir = resolve_path(args.scenario_dir, root)
    output_dir = resolve_path(args.output_dir, root)
    summary_json = resolve_path(args.summary_json, root)
    summary_csv = resolve_path(args.summary_csv, root)
    paired_csv = resolve_path(args.paired_csv, root)
    report = resolve_path(args.report, root)
    oracle_summary_json = resolve_path(args.oracle_summary_json, root)
    oracle_report = resolve_path(args.oracle_report, root)
    repair3_weights = resolve_path(args.repair3_weights_json, root)
    repair3_runtime_dir = resolve_path(args.repair3_runtime_dir, root)
    repair5d_spec_json = resolve_path(args.repair5d_spec_json, root)
    repair5d_runtime_dir = resolve_path(args.repair5d_runtime_dir, root)
    repair5e_ood_guard_runtime_dir = resolve_path(args.repair5e_ood_guard_runtime_dir, root)
    repair5e2_runtime_dir = resolve_path(args.repair5e2_runtime_dir, root)
    repair5e3_runtime_dir = resolve_path(args.repair5e3_runtime_dir, root)
    repair5e3_e2_shuffled_runtime_dir = resolve_path(args.repair5e3_e2_shuffled_runtime_dir, root)
    repair5e4_runtime_dir = resolve_path(args.repair5e4_runtime_dir, root)
    repair5e4_shuffled_runtime_dir = resolve_path(args.repair5e4_shuffled_runtime_dir, root)
    repair5e4_e3_calibrated_runtime_dir = resolve_path(args.repair5e4_e3_calibrated_runtime_dir, root)
    repair5e5_runtime_dir = resolve_path(args.repair5e5_runtime_dir, root)
    repair5e5_shuffled_runtime_dir = resolve_path(args.repair5e5_shuffled_runtime_dir, root)
    repair5e5_loose_runtime_dir = resolve_path(args.repair5e5_loose_runtime_dir, root)
    repair5e5_strict_runtime_dir = resolve_path(args.repair5e5_strict_runtime_dir, root)
    if None in (
        binary,
        scenario_dir,
        output_dir,
        summary_json,
        summary_csv,
        paired_csv,
        report,
        oracle_summary_json,
        oracle_report,
        repair3_weights,
        repair3_runtime_dir,
        repair5d_spec_json,
        repair5d_runtime_dir,
        repair5e_ood_guard_runtime_dir,
        repair5e2_runtime_dir,
        repair5e3_runtime_dir,
        repair5e3_e2_shuffled_runtime_dir,
        repair5e4_runtime_dir,
        repair5e4_shuffled_runtime_dir,
        repair5e4_e3_calibrated_runtime_dir,
        repair5e5_runtime_dir,
        repair5e5_shuffled_runtime_dir,
        repair5e5_loose_runtime_dir,
        repair5e5_strict_runtime_dir,
    ):
        raise ValueError("required paths could not be resolved")
    assert binary and scenario_dir and output_dir and summary_json and summary_csv and paired_csv and report
    assert oracle_summary_json and oracle_report
    assert repair3_weights and repair3_runtime_dir
    assert repair5d_spec_json and repair5d_runtime_dir and repair5e_ood_guard_runtime_dir
    assert repair5e2_runtime_dir and repair5e3_runtime_dir and repair5e3_e2_shuffled_runtime_dir
    assert repair5e4_runtime_dir and repair5e4_shuffled_runtime_dir and repair5e4_e3_calibrated_runtime_dir
    assert repair5e5_runtime_dir and repair5e5_shuffled_runtime_dir and repair5e5_loose_runtime_dir
    assert repair5e5_strict_runtime_dir

    output_dir.mkdir(parents=True, exist_ok=True)
    output_jsonl = resolve_path(args.output_jsonl, root) if args.output_jsonl else _jsonl_name(output_dir)
    assert output_jsonl
    command_log = output_jsonl.with_name(output_jsonl.stem + "_commands.jsonl")
    laur_update_log = output_jsonl.with_name(output_jsonl.stem + "_laur_updates.jsonl")
    additive_model = root / "configs/phase5/laur_additive_only"
    repair3_runtime, repair3_status = ensure_repair3_runtime(root, repair3_weights, repair3_runtime_dir)
    required_runtime_files = [
        "features.txt",
        "rules.csv",
        "layer0_weight.csv",
        "rule_head_weight.csv",
        "rule_head_bias.csv",
    ]
    repair5d_runtime = (
        repair5d_runtime_dir
        if repair5d_spec_json.exists()
        and all((repair5d_runtime_dir / name).exists() for name in required_runtime_files)
        else None
    )
    repair5e_ood_guard_runtime = (
        repair5e_ood_guard_runtime_dir
        if all((repair5e_ood_guard_runtime_dir / name).exists() for name in required_runtime_files)
        else None
    )
    repair5e2_runtime = (
        repair5e2_runtime_dir
        if all((repair5e2_runtime_dir / name).exists() for name in required_runtime_files)
        and (repair5e2_runtime_dir / "repair5e2_recovery_rules.csv").exists()
        else None
    )
    repair5e3_runtime = (
        repair5e3_runtime_dir
        if all((repair5e3_runtime_dir / name).exists() for name in required_runtime_files)
        and (repair5e3_runtime_dir / "repair5e2_recovery_rules.csv").exists()
        else None
    )
    repair5e3_e2_shuffled_runtime = (
        repair5e3_e2_shuffled_runtime_dir
        if all((repair5e3_e2_shuffled_runtime_dir / name).exists() for name in required_runtime_files)
        and (repair5e3_e2_shuffled_runtime_dir / "repair5e2_recovery_rules.csv").exists()
        else None
    )
    repair5e4_runtime = (
        repair5e4_runtime_dir
        if all((repair5e4_runtime_dir / name).exists() for name in required_runtime_files)
        and (repair5e4_runtime_dir / "repair5e4_utility_selector.csv").exists()
        else None
    )
    repair5e4_shuffled_runtime = (
        repair5e4_shuffled_runtime_dir
        if all((repair5e4_shuffled_runtime_dir / name).exists() for name in required_runtime_files)
        and (repair5e4_shuffled_runtime_dir / "repair5e4_utility_selector.csv").exists()
        else None
    )
    repair5e4_e3_calibrated_runtime = (
        repair5e4_e3_calibrated_runtime_dir
        if all((repair5e4_e3_calibrated_runtime_dir / name).exists() for name in required_runtime_files)
        and (repair5e4_e3_calibrated_runtime_dir / "repair5e2_recovery_rules.csv").exists()
        else None
    )
    repair5e5_runtime = (
        repair5e5_runtime_dir
        if all((repair5e5_runtime_dir / name).exists() for name in required_runtime_files)
        and (repair5e5_runtime_dir / "repair5e4_utility_selector.csv").exists()
        else None
    )
    repair5e5_shuffled_runtime = (
        repair5e5_shuffled_runtime_dir
        if all((repair5e5_shuffled_runtime_dir / name).exists() for name in required_runtime_files)
        and (repair5e5_shuffled_runtime_dir / "repair5e4_utility_selector.csv").exists()
        else None
    )
    repair5e5_loose_runtime = (
        repair5e5_loose_runtime_dir
        if all((repair5e5_loose_runtime_dir / name).exists() for name in required_runtime_files)
        and (repair5e5_loose_runtime_dir / "repair5e4_utility_selector.csv").exists()
        else None
    )
    repair5e5_strict_runtime = (
        repair5e5_strict_runtime_dir
        if all((repair5e5_strict_runtime_dir / name).exists() for name in required_runtime_files)
        and (repair5e5_strict_runtime_dir / "repair5e4_utility_selector.csv").exists()
        else None
    )
    methods, skipped_methods = build_methods(
        root=root,
        additive_model=additive_model,
        repair3_runtime=repair3_runtime,
        repair5d_runtime=repair5d_runtime,
        repair5e_ood_guard_runtime=repair5e_ood_guard_runtime,
        repair5e2_runtime=repair5e2_runtime,
        repair5e3_runtime=repair5e3_runtime,
        repair5e3_e2_shuffled_runtime=repair5e3_e2_shuffled_runtime,
        repair5e4_runtime=repair5e4_runtime,
        repair5e4_shuffled_runtime=repair5e4_shuffled_runtime,
        repair5e4_e3_calibrated_runtime=repair5e4_e3_calibrated_runtime,
        repair5e5_runtime=repair5e5_runtime,
        repair5e5_shuffled_runtime=repair5e5_shuffled_runtime,
        repair5e5_loose_runtime=repair5e5_loose_runtime,
        repair5e5_strict_runtime=repair5e5_strict_runtime,
        include_static_proxies=bool(args.include_static_proxies),
        include_oracle_static_probe=bool(args.include_oracle_static_probe),
        include_ood_guard_candidate=bool(args.include_ood_guard_candidate),
        include_repair5e2_candidate=bool(args.include_repair5e2_candidate),
        include_repair5e3_candidate=bool(args.include_repair5e3_candidate),
        include_repair5e3_e2_ablation_candidates=bool(args.include_repair5e3_e2_ablation_candidates),
        include_repair5e4_candidate=bool(args.include_repair5e4_candidate),
        include_repair5e4_ablation_candidates=bool(args.include_repair5e4_ablation_candidates),
        include_repair5e5_candidate=bool(args.include_repair5e5_candidate),
        include_repair5e5_ablation_candidates=bool(args.include_repair5e5_ablation_candidates),
        ood_guard_z_threshold=float(args.ood_guard_z_threshold),
        repair5e2_ood_guard_z_threshold=float(args.repair5e2_ood_guard_z_threshold),
        repair5e3_ood_guard_z_threshold=float(args.repair5e3_ood_guard_z_threshold),
        repair5e4_ood_guard_z_threshold=float(args.repair5e4_ood_guard_z_threshold),
        repair5e5_ood_guard_z_threshold=float(args.repair5e5_ood_guard_z_threshold),
    )
    only_aliases = set(args.only_method_aliases or [])
    oracle_requested_by_filter = "oracle_teacher_forced_best_safe_update_static_proxy" in only_aliases
    if only_aliases:
        methods = [
            method
            for method in methods
            if method.alias in only_aliases or (oracle_requested_by_filter and method.hide_from_report)
        ]
    skipped_methods.append({"method": "repair3_runtime_export", "reason": repair3_status})
    skipped_methods.append(
        {
            "method": "repair5d_spec",
            "reason": "available" if repair5d_spec_json.exists() else "missing_spec_json",
        }
    )
    skipped_methods.append(
        {
            "method": "repair5d_runtime_distill",
            "reason": "available" if repair5d_runtime is not None else "missing_runtime_dir_or_required_files",
        }
    )
    skipped_methods.append(
        {
            "method": "repair5e_ood_guard_runtime",
            "reason": "available" if repair5e_ood_guard_runtime is not None else "missing_runtime_dir_or_required_files",
        }
    )
    skipped_methods.append(
        {
            "method": "repair5e2_guarded_oracle_aligned_selector_runtime",
            "reason": "available" if repair5e2_runtime is not None else "missing_runtime_dir_or_required_files",
        }
    )
    skipped_methods.append(
        {
            "method": "repair5e3_split_guarded_selector_runtime",
            "reason": "available" if repair5e3_runtime is not None else "missing_runtime_dir_or_required_files",
        }
    )
    skipped_methods.append(
        {
            "method": "repair5e3_e2_shuffled_support_diagnostic_runtime",
            "reason": "available" if repair5e3_e2_shuffled_runtime is not None else "missing_runtime_dir_or_required_files",
        }
    )
    skipped_methods.append(
        {
            "method": "repair5e4_closed_loop_utility_selector_runtime",
            "reason": "available" if repair5e4_runtime is not None else "missing_runtime_dir_or_required_files",
        }
    )
    skipped_methods.append(
        {
            "method": "repair5e4_closed_loop_utility_selector_shuffled_labels_runtime",
            "reason": "available" if repair5e4_shuffled_runtime is not None else "missing_runtime_dir_or_required_files",
        }
    )
    skipped_methods.append(
        {
            "method": "repair5e4_calibrated_guard_only_on_e3_split_runtime",
            "reason": "available" if repair5e4_e3_calibrated_runtime is not None else "missing_runtime_dir_or_required_files",
        }
    )
    skipped_methods.append(
        {
            "method": "repair5e5_crossfold_utility_reranker_runtime",
            "reason": "available" if repair5e5_runtime is not None else "missing_runtime_dir_or_required_files",
        }
    )
    skipped_methods.append(
        {
            "method": "repair5e5_crossfold_utility_reranker_shuffled_labels_runtime",
            "reason": "available" if repair5e5_shuffled_runtime is not None else "missing_runtime_dir_or_required_files",
        }
    )
    skipped_methods.append(
        {
            "method": "repair5e5_crossfold_utility_reranker_loose_threshold_runtime",
            "reason": "available" if repair5e5_loose_runtime is not None else "missing_runtime_dir_or_required_files",
        }
    )
    skipped_methods.append(
        {
            "method": "repair5e5_crossfold_utility_reranker_strict_threshold_runtime",
            "reason": "available" if repair5e5_strict_runtime is not None else "missing_runtime_dir_or_required_files",
        }
    )

    instance_ids = (
        [int(value) for value in args.instance_ids]
        if args.instance_ids
        else list(range(int(args.instance_start), int(args.instance_start) + int(args.instances_per_setting)))
    )

    if not args.skip_solver:
        if not binary.exists():
            raise FileNotFoundError(f"missing solver binary {binary}")
        if output_jsonl.exists():
            raise FileExistsError(f"output JSONL already exists: {output_jsonl}")
        run_solver_grid(
            root=root,
            binary=binary,
            output_jsonl=output_jsonl,
            command_log=command_log,
            maps=list(args.maps),
            agent_counts=[int(value) for value in args.agent_counts],
            instance_ids=instance_ids,
            time_limit_sec=float(args.time_limit_sec),
            ltm_max_iterations=int(args.ltm_max_iterations),
            scenario_dir=scenario_dir,
            methods=methods,
            laur_update_log_jsonl=laur_update_log,
        )

    raw_rows = _read_jsonl(output_jsonl)
    normalized_rows = [normalize_run_row(row) for row in raw_rows]
    if only_aliases:
        allowed_raw_aliases = set(only_aliases)
        if oracle_requested_by_filter:
            allowed_raw_aliases.update(f"oracle_probe_static_{rule}" for rule in ORACLE_STATIC_RULES)
        normalized_rows = [
            row for row in normalized_rows if str(row.get("method", "")) in allowed_raw_aliases
        ]
    schema_errors: list[str] = []
    for index, row in enumerate(normalized_rows, 1):
        schema_errors.extend(f"row {index}: {error}" for error in validate_run_row(row))
    oracle_proxy_rows = synthesize_oracle_static_proxy_rows(normalized_rows)
    report_rows = [row for row in normalized_rows if not is_oracle_probe_row(row)] + oracle_proxy_rows
    summary_rows = add_ltm_group_deltas(summarize_rows(report_rows))
    paired = paired_rows(report_rows)
    method_stats = paired_method_stats(paired)
    stop_conditions = stop_condition_snapshot(summary_rows, paired)
    decision_interpretation = decision_table_interpretation(
        method_stats,
        stop_conditions.get("method_flags", {}),
    )
    oracle_summary = {
        "schema_version": "phase5p5_oracle_update_preflight_v1",
        "created_at": datetime.now().isoformat(),
        "oracle_scope": "static_rule_proxy",
        "full_teacher_force_hook_executed": False,
        "static_proxy_executed": bool(oracle_proxy_rows),
        "support_rows": sum(1 for row in normalized_rows if is_oracle_probe_row(row)),
        "oracle_rows": len(oracle_proxy_rows),
        "paired_stats": method_stats.get("oracle_teacher_forced_best_safe_update_static_proxy", {}),
        "phase5p5_allowed": False,
        "phase6_allowed": False,
    }
    summary = {
        "schema_version": "phase5p5_laur_diagnostic_preflight_exec_v1",
        "created_at": datetime.now().isoformat(),
        "branch": git_value(["branch", "--show-current"], root),
        "commit": git_value(["rev-parse", "--short", "HEAD"], root),
        "dirty": dirty_state(root),
        "clean_tracked_worktree": dirty_state(root) in {"clean", "untracked-present"},
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "raw_jsonl": str(output_jsonl),
        "command_log_jsonl": str(command_log),
        "laur_update_log_jsonl": str(laur_update_log),
        "summary_csv": str(summary_csv),
        "paired_csv": str(paired_csv),
        "oracle_summary_json": str(oracle_summary_json),
        "oracle_report": str(oracle_report),
        "schema_errors": schema_errors,
        "scope": {
            "maps": list(args.maps),
            "agent_counts": [int(value) for value in args.agent_counts],
            "instances_per_setting": int(args.instances_per_setting),
            "instance_ids": instance_ids,
            "time_limit_sec": float(args.time_limit_sec),
            "ltm_max_iterations": int(args.ltm_max_iterations),
            "methods": [method.alias for method in methods if not method.hide_from_report]
            + (["oracle_teacher_forced_best_safe_update_static_proxy"] if oracle_proxy_rows else []),
            "support_methods": [method.alias for method in methods if method.hide_from_report],
        },
        "skipped_methods": skipped_methods,
        "oracle_proxy_rows": len(oracle_proxy_rows),
        "paired_method_stats": method_stats,
        "decision_table_interpretation": decision_interpretation,
        "summary_rows": summary_rows,
        "paired_row_count": len(paired),
        "stop_conditions": stop_conditions,
    }
    _write_csv(
        summary_csv,
        summary_rows,
        [
            "map",
            "agents",
            "method",
            "runs",
            "successes",
            "success_rate",
            "sum_of_loss_ratio_mean",
            "expanded_nodes_mean",
            "time_to_first_solution_ms_mean",
            "returned_solutions_count_mean",
            "low_level_pibt_calls_mean",
            "laur_overhead_ms_mean",
            "laur_inference_count_mean",
            "laur_additive_fallback_count_mean",
            "laur_safety_disabled_count_mean",
            "fallback_defer_rate",
            "non_additive_update_rate",
            "selected_harmful_update_rate",
            "selected_rules",
            "ratio_delta_vs_ltm",
            "expanded_delta_vs_ltm",
            "ttfs_delta_vs_ltm",
        ],
    )
    _write_csv(
        paired_csv,
        paired,
        [
            "map",
            "agents",
            "seed",
            "scen",
            "baseline_method",
            "contender_method",
            "baseline_success",
            "contender_success",
            "baseline_ratio",
            "contender_ratio",
            "delta_ratio",
            "contender_better",
        ],
    )
    summary_json.parent.mkdir(parents=True, exist_ok=True)
    summary_json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    oracle_summary_json.parent.mkdir(parents=True, exist_ok=True)
    oracle_summary_json.write_text(json.dumps(oracle_summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(report, summary=summary)
    write_oracle_report(oracle_report, oracle=oracle_summary)
    print(
        json.dumps(
            {
                "summary_json": str(summary_json),
                "summary_csv": str(summary_csv),
                "paired_csv": str(paired_csv),
                "report": str(report),
                "oracle_summary_json": str(oracle_summary_json),
                "oracle_report": str(oracle_report),
            }
        )
    )
    return 0 if not schema_errors else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
