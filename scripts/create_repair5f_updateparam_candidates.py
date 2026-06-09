"""Create the Repair5F bounded UpdateParams candidate lattice.

The lattice is intentionally sparse. It expands the old eight preset rules into
moderate combinations around additive LTM without opening the full Cartesian
product.
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
from collections import OrderedDict
from dataclasses import asdict, dataclass
from datetime import datetime
from itertools import combinations, product
from pathlib import Path
from typing import Any


DEFAULT_CSV = "outputs/tables/phase5p5_repair5f_candidate_lattice.csv"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5f_candidate_lattice_report.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5f_candidate_lattice_summary.json"

ALPHA_VALUES = [0.5, 0.75, 1.0, 1.25, 1.5]
DECAY_VALUES = [0.90, 0.95, 1.0]
BASE_PARAMS = (1.0, 1.0, 1.0, 1.0)
FULL_CARTESIAN_COUNT = len(ALPHA_VALUES) ** 3 * len(DECAY_VALUES)

OLD_PRESET_PARAMS = {
    "additive_ltm": BASE_PARAMS,
    "commit_heavy": (1.5, 1.0, 1.0, 1.0),
    "block_heavy": (1.0, 1.5, 1.0, 1.0),
    "block_light": (1.0, 0.5, 1.0, 1.0),
    "wait_light": (1.0, 1.0, 0.5, 1.0),
    "wait_heavy": (1.0, 1.0, 1.5, 1.0),
    "decay_095": (1.0, 1.0, 1.0, 0.95),
    "decay_090": (1.0, 1.0, 1.0, 0.90),
}


@dataclass(frozen=True)
class Candidate:
    candidate_id: str
    alpha_commit: float
    alpha_block: float
    alpha_wait_spillover: float
    rho_decay: float
    force_additive: bool
    construction: str
    old_equivalent_rule: str
    is_exact_additive: bool
    is_old_preset_equivalent: bool
    notes: str


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def resolve_path(path: str | Path, root: Path) -> Path:
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


def _fmt(value: float) -> str:
    return f"{int(round(value * 100)):03d}"


def candidate_id_for(params: tuple[float, float, float, float]) -> str:
    if params == BASE_PARAMS:
        return "additive_ltm"
    return f"c{_fmt(params[0])}_b{_fmt(params[1])}_w{_fmt(params[2])}_d{_fmt(params[3])}"


def old_equivalent_for(params: tuple[float, float, float, float]) -> str:
    for rule, rule_params in OLD_PRESET_PARAMS.items():
        if params == rule_params:
            return rule
    return ""


def build_candidates() -> list[Candidate]:
    pending: "OrderedDict[tuple[float, float, float, float], tuple[str, str]]" = OrderedDict()

    def add(params: tuple[float, float, float, float], construction: str, notes: str) -> None:
        if params not in pending:
            pending[params] = (construction, notes)

    add(BASE_PARAMS, "exact_additive_anchor", "Exact additive LTM parity anchor.")

    axis_names = ["alpha_commit", "alpha_block", "alpha_wait_spillover", "rho_decay"]
    for axis_index, axis_name in enumerate(axis_names):
        values = DECAY_VALUES if axis_name == "rho_decay" else ALPHA_VALUES
        for value in values:
            params = list(BASE_PARAMS)
            params[axis_index] = value
            params_tuple = tuple(params)  # type: ignore[assignment]
            if params_tuple == BASE_PARAMS:
                continue
            add(params_tuple, f"one_axis_{axis_name}", "Single bounded one-axis move from additive.")

    moderate_values = [0.75, 1.25]
    for left, right in combinations(range(3), 2):
        for left_value, right_value in product(moderate_values, repeat=2):
            params = [1.0, 1.0, 1.0, 1.0]
            params[left] = left_value
            params[right] = right_value
            add(
                tuple(params),  # type: ignore[arg-type]
                f"two_axis_{axis_names[left]}_{axis_names[right]}",
                "Limited two-axis interaction at moderate alpha values.",
            )

    for decay in [0.95, 0.90]:
        for axis_index in range(3):
            for value in moderate_values:
                params = [1.0, 1.0, 1.0, decay]
                params[axis_index] = value
                add(
                    tuple(params),  # type: ignore[arg-type]
                    f"decay_interaction_{axis_names[axis_index]}",
                    "Conservative decay plus one moderate alpha move.",
                )

    for params in [
        (0.75, 0.75, 1.25, 0.95),
        (1.25, 0.75, 1.25, 0.95),
        (0.75, 1.25, 1.25, 0.95),
        (1.25, 1.25, 0.75, 0.95),
        (0.75, 1.0, 1.25, 0.90),
        (1.0, 0.75, 1.25, 0.90),
        (1.25, 0.75, 1.0, 0.90),
        (0.75, 1.25, 1.0, 0.90),
    ]:
        add(params, "conservative_decay_combo", "Hand-picked bounded blend with decay.")

    candidates: list[Candidate] = []
    for params, (construction, notes) in pending.items():
        old_rule = old_equivalent_for(params)
        exact_additive = params == BASE_PARAMS
        candidates.append(
            Candidate(
                candidate_id=candidate_id_for(params),
                alpha_commit=params[0],
                alpha_block=params[1],
                alpha_wait_spillover=params[2],
                rho_decay=params[3],
                force_additive=exact_additive,
                construction=construction,
                old_equivalent_rule=old_rule,
                is_exact_additive=exact_additive,
                is_old_preset_equivalent=bool(old_rule),
                notes=notes,
            )
        )
    return candidates


def write_csv(path: Path, candidates: list[Candidate]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(asdict(candidates[0]).keys()) if candidates else []
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for candidate in candidates:
            writer.writerow(asdict(candidate))


def build_summary(*, candidates: list[Candidate], csv_path: Path, report: Path, root: Path) -> dict[str, Any]:
    old_equivalents = {
        candidate.old_equivalent_rule: candidate.candidate_id
        for candidate in candidates
        if candidate.old_equivalent_rule
    }
    ranges = {
        "alpha_commit": sorted({candidate.alpha_commit for candidate in candidates}),
        "alpha_block": sorted({candidate.alpha_block for candidate in candidates}),
        "alpha_wait_spillover": sorted({candidate.alpha_wait_spillover for candidate in candidates}),
        "rho_decay": sorted({candidate.rho_decay for candidate in candidates}),
    }
    exact = [candidate.candidate_id for candidate in candidates if candidate.is_exact_additive]
    return {
        "schema_version": "phase5p5_repair5f_candidate_lattice_v1",
        "created_at": datetime.now().isoformat(),
        "branch": git_value(["branch", "--show-current"], root),
        "commit": git_value(["rev-parse", "--short", "HEAD"], root),
        "dirty": dirty_state(root),
        "diagnostic_only": True,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "candidate_count": len(candidates),
        "full_cartesian_count": FULL_CARTESIAN_COUNT,
        "sparse_vs_full_cartesian": f"{len(candidates)} / {FULL_CARTESIAN_COUNT}",
        "parameter_ranges": ranges,
        "exact_additive_candidate_id": exact[0] if exact else None,
        "old_preset_equivalent_candidates": old_equivalents,
        "old_preset_equivalent_count": len(old_equivalents),
        "new_candidate_count": sum(1 for candidate in candidates if not candidate.is_old_preset_equivalent),
        "candidate_ids": [candidate.candidate_id for candidate in candidates],
        "outputs": {
            "csv": rel(csv_path, root),
            "report": rel(report, root),
        },
        "construction_notes": [
            "Exact additive anchor.",
            "All bounded one-axis variations around additive.",
            "Limited two-axis interactions using 0.75/1.25 alpha values.",
            "Conservative decay interactions using rho in {0.90, 0.95}.",
            "No contraflow, local saturation, spillover radius, learned restart, or richer traffic-map state.",
        ],
    }


def write_report(path: Path, summary: dict[str, Any], candidates: list[Candidate]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Phase5.5 Repair5F Candidate Lattice\n\n")
        handle.write("This is a diagnostic-only bounded UpdateParams lattice for learned UpdateLTM.\n\n")
        handle.write("## Boundary\n\n")
        handle.write("- phase5p5_allowed: `false`\n")
        handle.write("- phase6_allowed: `false`\n")
        handle.write("- solver_semantic_changes: `false`\n")
        handle.write("- learned_restart_enabled: `false`\n")
        handle.write("- richer_traffic_map_state_enabled: `false`\n\n")
        handle.write("## Summary\n\n")
        handle.write(f"- candidate_count: `{summary['candidate_count']}`\n")
        handle.write(f"- full_cartesian_count: `{summary['full_cartesian_count']}`\n")
        handle.write(f"- sparse_vs_full_cartesian: `{summary['sparse_vs_full_cartesian']}`\n")
        handle.write(f"- exact_additive_candidate_id: `{summary['exact_additive_candidate_id']}`\n")
        handle.write(f"- old_preset_equivalent_count: `{summary['old_preset_equivalent_count']}`\n")
        handle.write(f"- new_candidate_count: `{summary['new_candidate_count']}`\n\n")
        handle.write("## Old Preset Equivalents\n\n")
        for rule, candidate_id in sorted(summary["old_preset_equivalent_candidates"].items()):
            handle.write(f"- `{rule}` -> `{candidate_id}`\n")
        handle.write("\n## Candidate Table\n\n")
        handle.write("| candidate_id | commit | block | wait | decay | construction | old preset |\n")
        handle.write("|---|---:|---:|---:|---:|---|---|\n")
        for candidate in candidates:
            handle.write(
                "| "
                f"{candidate.candidate_id} | "
                f"{candidate.alpha_commit:g} | "
                f"{candidate.alpha_block:g} | "
                f"{candidate.alpha_wait_spillover:g} | "
                f"{candidate.rho_decay:g} | "
                f"{candidate.construction} | "
                f"{candidate.old_equivalent_rule or ''} |\n"
            )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-csv", type=Path, default=Path(DEFAULT_CSV))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    csv_path = resolve_path(args.output_csv, root)
    report = resolve_path(args.report, root)
    summary_json = resolve_path(args.summary_json, root)
    candidates = build_candidates()
    write_csv(csv_path, candidates)
    summary = build_summary(candidates=candidates, csv_path=csv_path, report=report, root=root)
    summary_json.parent.mkdir(parents=True, exist_ok=True)
    summary_json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(report, summary, candidates)
    print(json.dumps({"csv": rel(csv_path, root), "report": rel(report, root), "summary_json": rel(summary_json, root)}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
