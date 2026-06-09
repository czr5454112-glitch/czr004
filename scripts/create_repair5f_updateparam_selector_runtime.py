"""Export the Repair5F.3 bounded UpdateParams selector runtime artifact.

The F2 selector collapsed to one candidate on the final holdout. This exporter
therefore writes a one-rule runtime directory while preserving the full
selector provenance and candidate lattice in the artifact manifest.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import subprocess
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    import sys

    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5f_selector_common import ALLOWED_FEATURES, FORBIDDEN_FEATURES  # noqa: E402


DEFAULT_CANDIDATE_CSV = "outputs/tables/phase5p5_repair5f_candidate_lattice.csv"
DEFAULT_SUPPORT_LONG = "outputs/tables/phase5p5_repair5f_selector_support_utility_long.csv"
DEFAULT_THRESHOLD_SWEEP_CSV = "outputs/tables/phase5p5_repair5f_selector_threshold_sweep.csv"
DEFAULT_THRESHOLD_SWEEP_SUMMARY = "outputs/reports/phase5p5_repair5f_selector_threshold_sweep_summary.json"
DEFAULT_SELECTOR_SPEC = "outputs/reports/phase5p5_repair5f_selector_spec.json"
DEFAULT_SIMULATION_SUMMARY = "outputs/reports/phase5p5_repair5f_selector_simulation_summary.json"
DEFAULT_SIMULATION_DECISIONS = "outputs/tables/phase5p5_repair5f_selector_simulation_decisions.csv"
DEFAULT_SIMULATION_PAIRED = "outputs/tables/phase5p5_repair5f_selector_simulation_paired.csv"
DEFAULT_OUTPUT_DIR = "artifacts/models/laur_ltm/repair5f_bounded_updateparam_selector"
DEFAULT_STATIC_OUTPUT_DIR = "artifacts/models/laur_ltm/repair5f_static_c100_b100_w075_d090"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5f_selector_runtime_export_report.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5f_selector_runtime_export_summary.json"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def resolve(path: str | Path, root: Path) -> Path:
    value = Path(path)
    return value if value.is_absolute() else root / value


def rel(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


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


def file_sha256(path: Path) -> str:
    if not path.exists():
        return ""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes"}


def summarize_decision_evidence(decisions_csv: Path, selected_candidate_id: str) -> dict[str, Any]:
    rows = [row for row in read_csv_rows(decisions_csv) if row.get("selected_candidate_id") == selected_candidate_id]
    predicted_deltas = [to_float(row.get("predicted_delta_ratio")) for row in rows]
    predicted_margins = [to_float(row.get("predicted_margin_ratio")) for row in rows]
    support_counts = [int(to_float(row.get("support_count"))) for row in rows]
    nearest = [to_float(row.get("nearest_distance")) for row in rows if str(row.get("nearest_distance", "")).strip()]
    worse_rates = [to_float(row.get("candidate_worse_rate")) for row in rows]
    group_worse_rates = [to_float(row.get("group_worse_rate")) for row in rows]

    def avg(values: list[float]) -> float | None:
        return sum(values) / len(values) if values else None

    return {
        "decision_rows": len(rows),
        "mean_predicted_delta_ratio": avg(predicted_deltas),
        "mean_predicted_margin_ratio": avg(predicted_margins),
        "min_support_count": min(support_counts) if support_counts else 0,
        "mean_support_count": avg([float(value) for value in support_counts]),
        "mean_nearest_distance": avg(nearest),
        "mean_candidate_worse_rate": avg(worse_rates),
        "mean_group_worse_rate": avg(group_worse_rates),
    }


def candidate_params(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "candidate_id": row["candidate_id"],
        "alpha_commit": to_float(row["alpha_commit"]),
        "alpha_block": to_float(row["alpha_block"]),
        "alpha_wait_spillover": to_float(row["alpha_wait_spillover"]),
        "rho_decay": to_float(row["rho_decay"]),
        "force_additive": to_bool(row.get("force_additive")),
        "construction": row.get("construction", ""),
        "old_equivalent_rule": row.get("old_equivalent_rule", ""),
        "is_exact_additive": to_bool(row.get("is_exact_additive")),
        "is_old_preset_equivalent": to_bool(row.get("is_old_preset_equivalent")),
    }


def write_runtime_core(output_dir: Path, selected: dict[str, Any], evidence: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "features.txt").write_text("bias\n", encoding="utf-8")
    (output_dir / "mean.csv").write_text("0\n", encoding="utf-8")
    (output_dir / "std.csv").write_text("1\n", encoding="utf-8")
    (output_dir / "layer0_weight.csv").write_text("0\n", encoding="utf-8")
    (output_dir / "layer0_bias.csv").write_text("1\n", encoding="utf-8")
    (output_dir / "rule_head_weight.csv").write_text("0\n", encoding="utf-8")
    (output_dir / "rule_head_bias.csv").write_text("0\n", encoding="utf-8")
    with (output_dir / "rules.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(
            [
                "rule_id",
                "alpha_commit",
                "alpha_block",
                "alpha_wait",
                "rho_decay",
                "saturation_scale",
                "contraflow_penalty",
                "force_additive",
                "predicted_delta_ratio",
                "predicted_margin_ratio",
                "nearest_support_count",
                "selected_rule_source",
                "guard_reason",
            ]
        )
        writer.writerow(
            [
                selected["candidate_id"],
                f"{selected['alpha_commit']:.12g}",
                f"{selected['alpha_block']:.12g}",
                f"{selected['alpha_wait_spillover']:.12g}",
                f"{selected['rho_decay']:.12g}",
                "1",
                "0",
                "true" if selected["force_additive"] else "false",
                f"{float(evidence.get('mean_predicted_delta_ratio') or 0.0):.12g}",
                f"{float(evidence.get('mean_predicted_margin_ratio') or 0.0):.12g}",
                str(int(evidence.get("min_support_count") or 0)),
                "repair5f_support_trained_static_updateparam",
                "support_trained_static_policy",
            ]
        )


def write_manifest(output_dir: Path, manifest: dict[str, Any]) -> None:
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output_dir / "selector_runtime_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def write_report(path: Path, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    selected = summary["selected_spec"]
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Phase5.5 Repair5F.3 Runtime Export\n\n")
        handle.write("This runtime export is diagnostic-only and does not permit Phase5.5 or Phase6.\n\n")
        handle.write("## Boundary\n\n")
        handle.write("- runtime_export_created: `true`\n")
        handle.write("- diagnostic_only: `true`\n")
        handle.write("- phase5p5_allowed: `false`\n")
        handle.write("- phase6_allowed: `false`\n")
        handle.write("- context_adaptive_claim_allowed: `false`\n\n")
        handle.write("## Selected Runtime Candidate\n\n")
        handle.write(f"- candidate_id: `{selected['candidate_id']}`\n")
        handle.write(f"- alpha_commit: `{selected['alpha_commit']}`\n")
        handle.write(f"- alpha_block: `{selected['alpha_block']}`\n")
        handle.write(f"- alpha_wait_spillover: `{selected['alpha_wait_spillover']}`\n")
        handle.write(f"- rho_decay: `{selected['rho_decay']}`\n\n")
        handle.write("## Interpretation\n\n")
        handle.write(
            "The F2 selector selected the same bounded candidate on every final-holdout case. "
            "The exported runtime is therefore a support-trained static bounded UpdateParams policy, "
            "not evidence for context-adaptive selection.\n\n"
        )
        handle.write("## Artifacts\n\n")
        handle.write(f"- selector runtime: `{summary['output_dir']}`\n")
        handle.write(f"- static ablation runtime: `{summary['static_output_dir']}`\n")
        handle.write(f"- summary JSON: `{summary['summary_json']}`\n")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-lattice-csv", type=Path, default=Path(DEFAULT_CANDIDATE_CSV))
    parser.add_argument("--support-long-csv", type=Path, default=Path(DEFAULT_SUPPORT_LONG))
    parser.add_argument("--threshold-sweep-csv", type=Path, default=Path(DEFAULT_THRESHOLD_SWEEP_CSV))
    parser.add_argument("--threshold-sweep-summary-json", type=Path, default=Path(DEFAULT_THRESHOLD_SWEEP_SUMMARY))
    parser.add_argument("--selector-spec-json", type=Path, default=Path(DEFAULT_SELECTOR_SPEC))
    parser.add_argument("--simulation-summary-json", type=Path, default=Path(DEFAULT_SIMULATION_SUMMARY))
    parser.add_argument("--simulation-decisions-csv", type=Path, default=Path(DEFAULT_SIMULATION_DECISIONS))
    parser.add_argument("--simulation-paired-csv", type=Path, default=Path(DEFAULT_SIMULATION_PAIRED))
    parser.add_argument("--output-dir", type=Path, default=Path(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--static-output-dir", type=Path, default=Path(DEFAULT_STATIC_OUTPUT_DIR))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    candidate_csv = resolve(args.candidate_lattice_csv, root)
    support_long = resolve(args.support_long_csv, root)
    threshold_csv = resolve(args.threshold_sweep_csv, root)
    threshold_summary = resolve(args.threshold_sweep_summary_json, root)
    selector_spec = resolve(args.selector_spec_json, root)
    simulation_summary_path = resolve(args.simulation_summary_json, root)
    simulation_decisions = resolve(args.simulation_decisions_csv, root)
    simulation_paired = resolve(args.simulation_paired_csv, root)
    output_dir = resolve(args.output_dir, root)
    static_output_dir = resolve(args.static_output_dir, root)
    report = resolve(args.report, root)
    summary_json = resolve(args.summary_json, root)

    for path in [
        candidate_csv,
        support_long,
        threshold_csv,
        threshold_summary,
        selector_spec,
        simulation_summary_path,
        simulation_decisions,
        simulation_paired,
    ]:
        if not path.exists():
            raise FileNotFoundError(path)

    simulation_summary = read_json(simulation_summary_path)
    selector_payload = read_json(selector_spec)
    lattice_rows = [candidate_params(row) for row in read_csv_rows(candidate_csv)]
    by_candidate = {row["candidate_id"]: row for row in lattice_rows}
    selected_distribution = simulation_summary.get("selected_candidate_distribution") or {}
    selected_ids = sorted(selected_distribution)
    if not selected_ids:
        raise ValueError("simulation summary has no selected candidates")
    if len(selected_ids) != 1:
        raise ValueError(f"F3 first export expects one selected candidate, got {selected_ids}")
    selected_id = selected_ids[0]
    if selected_id not in by_candidate:
        raise ValueError(f"selected candidate missing from lattice: {selected_id}")
    selected = by_candidate[selected_id]
    additive = by_candidate.get("additive_ltm")
    if additive is None:
        raise ValueError("candidate lattice is missing additive_ltm")

    decision_evidence = summarize_decision_evidence(simulation_decisions, selected_id)
    write_runtime_core(output_dir, selected, decision_evidence)
    write_runtime_core(static_output_dir, selected, decision_evidence)

    shutil.copyfile(candidate_csv, output_dir / "candidate_lattice.csv")
    shutil.copyfile(candidate_csv, static_output_dir / "candidate_lattice.csv")
    shutil.copyfile(selector_spec, output_dir / "selector_spec.json")
    shutil.copyfile(simulation_summary_path, output_dir / "selector_simulation_summary.json")

    selected_rows = read_csv_rows(simulation_decisions)
    candidate_counts = Counter(row.get("selected_candidate_id") for row in selected_rows)
    manifest = {
        "schema_version": "phase5p5_repair5f_updateparam_selector_runtime_v1",
        "created_at": datetime.now().isoformat(),
        "source_commit": git_value(["rev-parse", "HEAD"], root),
        "source_commit_short": git_value(["rev-parse", "--short", "HEAD"], root),
        "branch": git_value(["branch", "--show-current"], root),
        "dirty": dirty_state(root),
        "selector_type": selector_payload.get("selector_spec", {}).get("selector_type"),
        "selector_spec": selector_payload.get("selector_spec"),
        "selected_spec": selected,
        "selected_candidate_ids": selected_ids,
        "selected_candidate_distribution": dict(candidate_counts),
        "allowed_feature_names": list(ALLOWED_FEATURES),
        "forbidden_feature_names": list(FORBIDDEN_FEATURES),
        "candidate_lattice_hash": file_sha256(candidate_csv),
        "support_utility_table_hash": file_sha256(support_long),
        "threshold_sweep_hash": file_sha256(threshold_csv),
        "threshold_sweep_summary_hash": file_sha256(threshold_summary),
        "simulation_summary_hash": file_sha256(simulation_summary_path),
        "simulation_decisions_hash": file_sha256(simulation_decisions),
        "simulation_paired_hash": file_sha256(simulation_paired),
        "script_hash": file_sha256(Path(__file__)),
        "selectable_candidates": lattice_rows,
        "update_params_by_candidate": {row["candidate_id"]: row for row in lattice_rows},
        "additive_fallback_candidate": additive,
        "runtime_behavior": {
            "policy": "support_trained_static_candidate",
            "select_at_first_eligible_post_first_solution_update": True,
            "lock_candidate_for_run": True,
            "selected_rule_source": "repair5f_support_trained_static_updateparam",
            "evidence_logged_in_rules_csv": True,
        },
        "support_evidence": decision_evidence,
        "f2_selector_metrics": simulation_summary.get("selector_metrics"),
        "f2_table_simulation_passed": simulation_summary.get("table_simulation_passed"),
        "runtime_export_created": True,
        "diagnostic_only": True,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "context_adaptive_claim_allowed": False,
        "static_candidate_ablation_required": True,
    }
    write_manifest(output_dir, manifest)

    static_manifest = dict(manifest)
    static_manifest["schema_version"] = "phase5p5_repair5f_static_updateparam_runtime_v1"
    static_manifest["runtime_behavior"] = {
        **manifest["runtime_behavior"],
        "policy": "static_candidate_ablation",
    }
    write_manifest(static_output_dir, static_manifest)

    summary = {
        **manifest,
        "output_dir": rel(output_dir, root),
        "static_output_dir": rel(static_output_dir, root),
        "report": rel(report, root),
        "summary_json": rel(summary_json, root),
    }
    summary_json.parent.mkdir(parents=True, exist_ok=True)
    summary_json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(report, summary)
    print(json.dumps({"output_dir": rel(output_dir, root), "static_output_dir": rel(static_output_dir, root)}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
