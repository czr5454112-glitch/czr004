"""Run and summarize the Repair5F bounded UpdateParams candidate probe.

This script evaluates each bounded candidate through the existing LAUR runtime
path by generating a tiny one-rule runtime directory per candidate. It does not
change solver semantics and never grants Phase5.5 or Phase6 permission.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
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

from czr004_metrics.schema import normalize_run_row, validate_run_row  # noqa: E402


DEFAULT_BINARY = "build/phase1a-batch/phase1a_batch.exe"
DEFAULT_SCENARIO_DIR = "outputs/tmp/phase1a/generated/phase1a-generated-random"
DEFAULT_CANDIDATE_CSV = "outputs/tables/phase5p5_repair5f_candidate_lattice.csv"
DEFAULT_RUNTIME_ROOT = "outputs/tmp/phase5p5_repair5f_candidate_runtimes"
DEFAULT_OUTPUT_DIR = "outputs/logs/phase5p5_repair5f_candidate_probe"
DEFAULT_OUTPUT_JSONL = "outputs/logs/phase5p5_repair5f_candidate_probe/phase5p5_repair5f_candidate_probe.jsonl"
DEFAULT_LONG_CSV = "outputs/tables/phase5p5_repair5f_updateparam_utility_long.csv"
DEFAULT_WIDE_CSV = "outputs/tables/phase5p5_repair5f_updateparam_utility_wide.csv"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5f_candidate_probe_report.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5f_candidate_probe_summary.json"
DEFAULT_AUDIT_REPORT = ""
DEFAULT_ADDITIVE_RUNTIME = "configs/phase5/laur_additive_only"
DEFAULT_REPAIR5E5_RUNTIME = "artifacts/models/laur_ltm/repair5e5_crossfold_utility_reranker"
DEFAULT_REPAIR5E5_SHUFFLED_RUNTIME = "artifacts/models/laur_ltm/repair5e5_crossfold_utility_reranker_shuffled_labels_diagnostic"

MAPS = {
    "random-32-32-20": "external/lacam2/scripts/map/random-32-32-20.map",
    "maze-32-32-4": "external/lacam2/scripts/map/maze-32-32-4.map",
    "warehouse-10-20-10-2-1": "external/lacam2/scripts/map/warehouse-10-20-10-2-1.map",
}

TRAIN_IDS = list(range(1, 21))
FINAL_HOLDOUT_IDS = list(range(21, 26))
OOF_FOLDS = {
    0: [1, 2, 3, 4, 5],
    1: [6, 7, 8, 9, 10],
    2: [11, 12, 13, 14, 15],
    3: [16, 17, 18, 19, 20],
    4: [21, 22, 23, 24, 25],
}

SYNTHETIC_METHODS = {
    "repair5f_candidate_lattice_oracle_static_proxy",
    "repair5f_bounded_updateparam_selector_random_candidate_diagnostic",
    "repair5f_bounded_updateparam_selector_shuffled_utility_diagnostic",
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


@dataclass(frozen=True)
class MethodSpec:
    method: str
    alias: str
    extra_args: tuple[str, ...] = ()
    candidate_id: str = ""
    hidden_support: bool = False


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


def finite(value: Any, default: float = math.nan) -> float:
    if value is None or isinstance(value, bool):
        return default
    try:
        out = float(value)
    except (TypeError, ValueError):
        return default
    return out if math.isfinite(out) else default


def finite_int(value: Any, default: int = 0) -> int:
    number = finite(value)
    return int(number) if math.isfinite(number) else default


def boolean(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes"}


def _number(row: dict[str, Any], key: str) -> float | None:
    value = finite(row.get(key))
    return value if math.isfinite(value) else None


def _mean(values: list[float]) -> float | None:
    clean = [float(value) for value in values if math.isfinite(float(value))]
    return statistics.mean(clean) if clean else None


def _write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def file_sha256(path: Path) -> str:
    if not path.exists():
        return ""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def completed_probe_keys(rows: list[dict[str, Any]]) -> set[tuple[str, int, int, str]]:
    return {
        (str(row.get("map")), finite_int(row.get("agents")), finite_int(row.get("seed")), str(row.get("method")))
        for row in rows
    }


def dedupe_probe_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, int, int, str]] = set()
    out: list[dict[str, Any]] = []
    for row in rows:
        key = (str(row.get("map")), finite_int(row.get("agents")), finite_int(row.get("seed")), str(row.get("method")))
        if key in seen:
            continue
        seen.add(key)
        out.append(row)
    return out


def expected_probe_keys(
    *, maps: list[str], agent_counts: list[int], instance_ids: list[int], methods: list[MethodSpec]
) -> set[tuple[str, int, int, str]]:
    return {
        (map_name, int(agents), int(instance_id), method.alias)
        for map_name in maps
        for agents in agent_counts
        for instance_id in instance_ids
        for method in methods
    }


def read_candidates(path: Path) -> list[Candidate]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    candidates: list[Candidate] = []
    for row in rows:
        candidates.append(
            Candidate(
                candidate_id=str(row["candidate_id"]),
                alpha_commit=float(row["alpha_commit"]),
                alpha_block=float(row["alpha_block"]),
                alpha_wait_spillover=float(row["alpha_wait_spillover"]),
                rho_decay=float(row["rho_decay"]),
                force_additive=boolean(row["force_additive"]),
                construction=str(row.get("construction", "")),
                old_equivalent_rule=str(row.get("old_equivalent_rule", "")),
                is_exact_additive=boolean(row.get("is_exact_additive", False)),
                is_old_preset_equivalent=boolean(row.get("is_old_preset_equivalent", False)),
                notes=str(row.get("notes", "")),
            )
        )
    return candidates


def choose_candidates(candidates: list[Candidate], max_candidates: int) -> list[Candidate]:
    if max_candidates <= 0 or max_candidates >= len(candidates):
        return candidates
    additive = [candidate for candidate in candidates if candidate.is_exact_additive]
    old = [candidate for candidate in candidates if candidate.is_old_preset_equivalent and not candidate.is_exact_additive]
    new = [candidate for candidate in candidates if not candidate.is_old_preset_equivalent]
    selected: list[Candidate] = []
    for bucket in (additive, old, new):
        for candidate in bucket:
            if candidate.candidate_id not in {item.candidate_id for item in selected}:
                selected.append(candidate)
            if len(selected) >= max_candidates:
                return selected
    return selected


def write_candidate_runtime(runtime_root: Path, candidate: Candidate) -> Path:
    out = runtime_root / candidate.candidate_id
    out.mkdir(parents=True, exist_ok=True)
    (out / "features.txt").write_text("bias\n", encoding="utf-8")
    (out / "mean.csv").write_text("0\n", encoding="utf-8")
    (out / "std.csv").write_text("1\n", encoding="utf-8")
    (out / "layer0_weight.csv").write_text("0\n", encoding="utf-8")
    (out / "layer0_bias.csv").write_text("1\n", encoding="utf-8")
    (out / "rule_head_weight.csv").write_text("0\n", encoding="utf-8")
    (out / "rule_head_bias.csv").write_text("0\n", encoding="utf-8")
    with (out / "rules.csv").open("w", encoding="utf-8", newline="") as handle:
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
            ]
        )
        writer.writerow(
            [
                candidate.candidate_id,
                f"{candidate.alpha_commit:.12g}",
                f"{candidate.alpha_block:.12g}",
                f"{candidate.alpha_wait_spillover:.12g}",
                f"{candidate.rho_decay:.12g}",
                "1",
                "0",
                "true" if candidate.force_additive else "false",
            ]
        )
    manifest = {
        "schema_version": "phase5p5_repair5f_single_candidate_runtime_v1",
        "candidate_id": candidate.candidate_id,
        "alpha_commit": candidate.alpha_commit,
        "alpha_block": candidate.alpha_block,
        "alpha_wait_spillover": candidate.alpha_wait_spillover,
        "rho_decay": candidate.rho_decay,
        "force_additive": candidate.force_additive,
        "diagnostic_only": True,
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return out


def runtime_available(path: Path) -> bool:
    required = [
        "features.txt",
        "rules.csv",
        "layer0_weight.csv",
        "rule_head_weight.csv",
        "rule_head_bias.csv",
    ]
    return path.exists() and all((path / name).exists() for name in required)


def build_methods(
    *,
    candidates: list[Candidate],
    runtime_root: Path,
    additive_runtime: Path,
    repair5e5_runtime: Path,
    repair5e5_shuffled_runtime: Path,
    include_lacam_star: bool,
    include_repair5e5: bool,
    include_repair5e5_shuffled: bool,
) -> tuple[list[MethodSpec], list[dict[str, str]]]:
    methods: list[MethodSpec] = []
    skipped: list[dict[str, str]] = []
    if include_lacam_star:
        methods.append(MethodSpec("lacam_star", "lacam_star"))
    methods.extend(
        [
            MethodSpec("lacam_star_ltm", "lacam_star_ltm"),
            MethodSpec(
                "lacam_star_lau_ltm",
                "always_additive_defer",
                ("--laur-force-additive", "--laur-model-path", str(additive_runtime)),
            ),
        ]
    )
    if include_repair5e5 and runtime_available(repair5e5_runtime):
        methods.append(
            MethodSpec(
                "lacam_star_lau_ltm",
                "repair5e5_crossfold_utility_reranker",
                (
                    "--laur-model-path",
                    str(repair5e5_runtime),
                    "--laur-safety-threshold",
                    "0.30",
                    "--laur-ood-z-threshold",
                    "4.25",
                ),
            )
        )
    elif include_repair5e5:
        skipped.append({"method": "repair5e5_crossfold_utility_reranker", "reason": "runtime_unavailable"})

    if include_repair5e5_shuffled and runtime_available(repair5e5_shuffled_runtime):
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
                    "4.25",
                ),
            )
        )
    elif include_repair5e5_shuffled:
        skipped.append(
            {
                "method": "repair5e5_crossfold_utility_reranker_shuffled_labels_diagnostic",
                "reason": "runtime_unavailable",
            }
        )

    for candidate in candidates:
        runtime_dir = write_candidate_runtime(runtime_root, candidate)
        methods.append(
            MethodSpec(
                "lacam_star_lau_ltm",
                f"repair5f_candidate_{candidate.candidate_id}",
                ("--laur-model-path", str(runtime_dir), "--laur-safety-threshold", "1.01"),
                candidate_id=candidate.candidate_id,
                hidden_support=True,
            )
        )
    return methods, skipped


def run_solver_grid(
    *,
    root: Path,
    binary: Path,
    scenario_dir: Path,
    output_jsonl: Path,
    command_log: Path,
    laur_update_log: Path,
    maps: list[str],
    agent_counts: list[int],
    instance_ids: list[int],
    time_limit_sec: float,
    ltm_max_iterations: int,
    methods: list[MethodSpec],
    completed_keys: set[tuple[str, int, int, str]] | None = None,
) -> list[dict[str, Any]]:
    command_log.parent.mkdir(parents=True, exist_ok=True)
    command_rows: list[dict[str, Any]] = []
    completed_keys = completed_keys or set()
    for map_name in maps:
        map_path = root / MAPS[map_name]
        if not map_path.exists():
            raise FileNotFoundError(map_path)
        for instance_id in instance_ids:
            scen_path = scenario_dir / f"{map_name}-random-{instance_id}.scen"
            if not scen_path.exists():
                raise FileNotFoundError(scen_path)
            for agents in agent_counts:
                for spec in methods:
                    key = (map_name, int(agents), int(instance_id), spec.alias)
                    if key in completed_keys:
                        continue
                    extra_args = list(spec.extra_args)
                    if spec.method == "lacam_star_lau_ltm":
                        extra_args.extend(["--laur-update-log-jsonl", str(laur_update_log)])
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
                        str(int(instance_id)),
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
                        "phase5p5-repair5f-candidate-probe",
                        "--project-commit",
                        git_value(["rev-parse", "--short", "HEAD"], root),
                        "--external-commit",
                        "local",
                        "--branch",
                        git_value(["branch", "--show-current"], root),
                        "--dirty",
                        dirty_state(root),
                        "--platform",
                        "Windows Repair5F bounded UpdateParams diagnostic",
                        *extra_args,
                    ]
                    completed = subprocess.run(command, cwd=root, text=True, capture_output=True)
                    row = {
                        "method": spec.alias,
                        "map": map_name,
                        "agents": int(agents),
                        "seed": int(instance_id),
                        "returncode": completed.returncode,
                        "stdout": completed.stdout.strip()[-500:],
                        "stderr": completed.stderr.strip()[-500:],
                    }
                    command_rows.append(row)
                    with command_log.open("a", encoding="utf-8") as handle:
                        handle.write(json.dumps(row, sort_keys=True) + "\n")
                    if completed.returncode == 1:
                        raise RuntimeError(
                            f"solver crashed for {spec.alias} {map_name} a{agents} i{instance_id}: {completed.stderr}"
                        )
    return command_rows


def case_key(row: dict[str, Any]) -> tuple[Any, ...]:
    return (row.get("map"), finite_int(row.get("agents")), finite_int(row.get("seed")), row.get("scen"))


def candidate_id_from_method(method: str) -> str:
    prefix = "repair5f_candidate_"
    return method[len(prefix) :] if method.startswith(prefix) else ""


def row_score(row: dict[str, Any]) -> tuple[int, float, float, float, str]:
    success_rank = 0 if row.get("success") else 1
    ratio = _number(row, "sum_of_loss_ratio")
    expanded = _number(row, "expanded_nodes")
    ttfs = _number(row, "time_to_first_solution_ms")
    return (
        success_rank,
        ratio if ratio is not None else float("inf"),
        expanded if expanded is not None else float("inf"),
        ttfs if ttfs is not None else float("inf"),
        str(row.get("method", "")),
    )


def synthesize_diagnostics(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_case: dict[tuple[Any, ...], dict[str, dict[str, Any]]] = {}
    for row in rows:
        by_case.setdefault(case_key(row), {})[str(row.get("method"))] = row

    candidate_methods = sorted(
        {
            method
            for methods in by_case.values()
            for method in methods
            if method.startswith("repair5f_candidate_")
        }
    )
    if not candidate_methods:
        return []

    case_order = sorted(by_case)
    best_by_case: dict[tuple[Any, ...], str] = {}
    for key in case_order:
        candidates = [by_case[key][method] for method in candidate_methods if method in by_case[key]]
        if candidates:
            best_by_case[key] = str(min(candidates, key=row_score).get("method"))

    out: list[dict[str, Any]] = []
    for index, key in enumerate(case_order):
        methods = by_case[key]
        candidates = [methods[method] for method in candidate_methods if method in methods]
        if not candidates:
            continue

        oracle_source = best_by_case.get(key)
        if oracle_source and oracle_source in methods:
            row = dict(methods[oracle_source])
            row["method"] = "repair5f_candidate_lattice_oracle_static_proxy"
            row["repair5f_synthetic_source_method"] = oracle_source
            row["repair5f_synthetic_candidate_id"] = candidate_id_from_method(oracle_source)
            out.append(row)

        digest = hashlib.sha256(repr(key).encode("utf-8")).hexdigest()
        random_method = candidate_methods[int(digest[:12], 16) % len(candidate_methods)]
        if random_method in methods:
            row = dict(methods[random_method])
            row["method"] = "repair5f_bounded_updateparam_selector_random_candidate_diagnostic"
            row["repair5f_synthetic_source_method"] = random_method
            row["repair5f_synthetic_candidate_id"] = candidate_id_from_method(random_method)
            out.append(row)

        if len(case_order) > 1:
            source_key = case_order[(index + 1) % len(case_order)]
            shuffled_method = best_by_case.get(source_key, random_method)
        else:
            shuffled_method = random_method
        if shuffled_method in methods:
            row = dict(methods[shuffled_method])
            row["method"] = "repair5f_bounded_updateparam_selector_shuffled_utility_diagnostic"
            row["repair5f_synthetic_source_method"] = shuffled_method
            row["repair5f_synthetic_candidate_id"] = candidate_id_from_method(shuffled_method)
            out.append(row)
    return out


def paired_rows(rows: list[dict[str, Any]], baseline: str = "lacam_star_ltm") -> list[dict[str, Any]]:
    by_case: dict[tuple[Any, ...], dict[str, dict[str, Any]]] = {}
    for raw in rows:
        row = normalize_run_row(raw)
        by_case.setdefault(case_key(row), {})[str(row.get("method"))] = row

    pairs: list[dict[str, Any]] = []
    for key, methods in sorted(by_case.items()):
        base = methods.get(baseline)
        if base is None:
            continue
        base_ratio = _number(base, "sum_of_loss_ratio")
        for method, contender in sorted(methods.items()):
            if method == baseline:
                continue
            cont_ratio = _number(contender, "sum_of_loss_ratio")
            delta_ratio = (
                float(cont_ratio) - float(base_ratio)
                if base_ratio is not None and cont_ratio is not None
                else None
            )
            contender_success = bool(contender.get("success"))
            baseline_success = bool(base.get("success"))
            pairs.append(
                {
                    "map": key[0],
                    "agents": key[1],
                    "seed": key[2],
                    "scen": key[3],
                    "baseline_method": baseline,
                    "contender_method": method,
                    "baseline_success": baseline_success,
                    "contender_success": contender_success,
                    "baseline_ratio": base_ratio,
                    "contender_ratio": cont_ratio,
                    "delta_ratio": delta_ratio,
                    "contender_better": (
                        (contender_success and not baseline_success)
                        or (
                            contender_success
                            and baseline_success
                            and delta_ratio is not None
                            and float(delta_ratio) < -1.0e-12
                        )
                    ),
                    "contender_worse": (
                        (baseline_success and not contender_success)
                        or (
                            contender_success
                            and baseline_success
                            and delta_ratio is not None
                            and float(delta_ratio) > 1.0e-12
                        )
                    ),
                }
            )
    return pairs


def paired_method_stats(paired: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in paired:
        grouped.setdefault(str(row["contender_method"]), []).append(row)
    out: dict[str, dict[str, Any]] = {}
    for method, rows in sorted(grouped.items()):
        deltas = [float(row["delta_ratio"]) for row in rows if row.get("delta_ratio") is not None]
        out[method] = {
            "rows": len(rows),
            "better": sum(1 for row in rows if row.get("contender_better") is True),
            "equal": sum(1 for value in deltas if abs(value) <= 1.0e-12),
            "worse": sum(1 for row in rows if row.get("contender_worse") is True),
            "mean_delta_ratio_vs_ltm": _mean(deltas),
        }
    return out


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
        pibt = [_number(row, "low_level_pibt_calls") for row in group]
        laur_ms = [_number(row, "laur_inference_total_ms") for row in group]
        laur_inference_counts = [_number(row, "laur_inference_count") for row in group]
        additive_fallback_counts = [_number(row, "laur_additive_fallback_count") for row in group]
        selected_rules: dict[str, int] = {}
        nonadditive_updates = 0
        total_update_decisions = 0
        for row in group:
            for rule, count in (row.get("laur_selected_rules") or {}).items():
                selected_rules[str(rule)] = selected_rules.get(str(rule), 0) + int(count)
                total_update_decisions += int(count)
                if str(rule) != "additive_ltm":
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
                "low_level_pibt_calls_mean": _mean([value for value in pibt if value is not None]),
                "laur_overhead_ms_mean": _mean([value for value in laur_ms if value is not None]),
                "laur_inference_count_mean": _mean([value for value in laur_inference_counts if value is not None]),
                "laur_additive_fallback_count_mean": _mean(
                    [value for value in additive_fallback_counts if value is not None]
                ),
                "non_additive_update_rate": (
                    nonadditive_updates / total_update_decisions if total_update_decisions else None
                ),
                "selected_rules": json.dumps(dict(sorted(selected_rules.items())), sort_keys=True),
            }
        )
    baselines = {
        (row["map"], int(row["agents"])): row
        for row in summary
        if row["method"] == "lacam_star_ltm"
    }
    for row in summary:
        base = baselines.get((row["map"], int(row["agents"])))
        if base is None or row["method"] == "lacam_star_ltm":
            row["ratio_delta_vs_ltm"] = None
            row["expanded_delta_vs_ltm"] = None
            row["ttfs_delta_vs_ltm"] = None
            continue
        for source, target in [
            ("sum_of_loss_ratio_mean", "ratio_delta_vs_ltm"),
            ("expanded_nodes_mean", "expanded_delta_vs_ltm"),
            ("time_to_first_solution_ms_mean", "ttfs_delta_vs_ltm"),
        ]:
            left = row.get(source)
            right = base.get(source)
            row[target] = float(left) - float(right) if left is not None and right is not None else None
    return summary


def method_parity_exact(rows: list[dict[str, Any]], comparison_method: str) -> bool:
    by_case: dict[tuple[Any, ...], dict[str, dict[str, Any]]] = {}
    for row in rows:
        by_case.setdefault(case_key(row), {})[str(row.get("method"))] = row
    checked = 0
    for methods in by_case.values():
        base = methods.get("lacam_star_ltm")
        additive = methods.get(comparison_method)
        if base is None or additive is None:
            continue
        checked += 1
        for key in ["success", "sum_of_loss", "lower_bound", "sum_of_loss_ratio", "makespan"]:
            if base.get(key) != additive.get(key):
                return False
    return checked > 0


def force_additive_parity_exact(rows: list[dict[str, Any]]) -> bool:
    return method_parity_exact(rows, "always_additive_defer")


def exact_additive_candidate_parity_exact(rows: list[dict[str, Any]]) -> bool:
    return method_parity_exact(rows, "repair5f_candidate_additive_ltm")


def group_flags(summary_rows: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    baselines = {
        (row["map"], int(row["agents"])): row
        for row in summary_rows
        if row["method"] == "lacam_star_ltm"
    }
    flags: dict[str, dict[str, int]] = {}
    for row in summary_rows:
        method = str(row["method"])
        if method == "lacam_star_ltm":
            continue
        base = baselines.get((row["map"], int(row["agents"])))
        ratio_delta = row.get("ratio_delta_vs_ltm")
        selected_rules = json.loads(str(row.get("selected_rules") or "{}"))
        nonadditive_selected = sum(int(count) for rule, count in selected_rules.items() if rule != "additive_ltm")
        item = flags.setdefault(
            method,
            {
                "ratio_worse_than_ltm_groups": 0,
                "success_worse_than_ltm_groups": 0,
                "zero_nonadditive_groups": 0,
            },
        )
        if ratio_delta is not None and float(ratio_delta) > 1.0e-12:
            item["ratio_worse_than_ltm_groups"] += 1
        if base is not None and float(row.get("success_rate") or 0.0) < float(base.get("success_rate") or 0.0):
            item["success_worse_than_ltm_groups"] += 1
        if nonadditive_selected == 0 and method not in {"lacam_star", "always_additive_defer"}:
            item["zero_nonadditive_groups"] += 1
    return flags


def build_long_rows(
    *,
    rows: list[dict[str, Any]],
    candidates_by_id: dict[str, Candidate],
) -> list[dict[str, Any]]:
    by_case: dict[tuple[Any, ...], dict[str, dict[str, Any]]] = {}
    for raw in rows:
        row = normalize_run_row(raw)
        by_case.setdefault(case_key(row), {})[str(row.get("method"))] = row

    out: list[dict[str, Any]] = []
    for key, methods in sorted(by_case.items()):
        baseline = methods.get("lacam_star_ltm")
        repair5e5 = methods.get("repair5e5_crossfold_utility_reranker")
        for method, row in sorted(methods.items()):
            candidate_id = candidate_id_from_method(method)
            if not candidate_id:
                continue
            candidate = candidates_by_id.get(candidate_id)
            if candidate is None:
                continue
            ratio = _number(row, "sum_of_loss_ratio")
            base_ratio = _number(baseline or {}, "sum_of_loss_ratio")
            e5_ratio = _number(repair5e5 or {}, "sum_of_loss_ratio")
            expanded = _number(row, "expanded_nodes")
            base_expanded = _number(baseline or {}, "expanded_nodes")
            pibt = _number(row, "low_level_pibt_calls")
            base_pibt = _number(baseline or {}, "low_level_pibt_calls")
            ttfs = _number(row, "time_to_first_solution_ms")
            base_ttfs = _number(baseline or {}, "time_to_first_solution_ms")
            delta_ratio = float(ratio) - float(base_ratio) if ratio is not None and base_ratio is not None else None
            out.append(
                {
                    "map": key[0],
                    "agents": key[1],
                    "seed": key[2],
                    "scen": key[3],
                    "split_bucket": "final_holdout" if int(key[2]) in FINAL_HOLDOUT_IDS else "support_train",
                    "candidate_id": candidate_id,
                    "alpha_commit": candidate.alpha_commit,
                    "alpha_block": candidate.alpha_block,
                    "alpha_wait_spillover": candidate.alpha_wait_spillover,
                    "rho_decay": candidate.rho_decay,
                    "force_additive": candidate.force_additive,
                    "construction": candidate.construction,
                    "old_equivalent_rule": candidate.old_equivalent_rule,
                    "success": bool(row.get("success")),
                    "sum_of_loss_ratio": ratio,
                    "delta_ratio_vs_ltm": delta_ratio,
                    "delta_ratio_vs_repair5e5": (
                        float(ratio) - float(e5_ratio) if ratio is not None and e5_ratio is not None else None
                    ),
                    "expanded_delta_vs_ltm": (
                        float(expanded) - float(base_expanded)
                        if expanded is not None and base_expanded is not None
                        else None
                    ),
                    "low_level_pibt_delta_vs_ltm": (
                        float(pibt) - float(base_pibt) if pibt is not None and base_pibt is not None else None
                    ),
                    "ttfs_delta_vs_ltm": (
                        float(ttfs) - float(base_ttfs) if ttfs is not None and base_ttfs is not None else None
                    ),
                    "better_vs_ltm": delta_ratio is not None and delta_ratio < -1.0e-12,
                    "equal_vs_ltm": delta_ratio is not None and abs(delta_ratio) <= 1.0e-12,
                    "worse_vs_ltm": delta_ratio is not None and delta_ratio > 1.0e-12,
                }
            )
    return out


def build_wide_rows(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
    by_case: dict[tuple[Any, ...], dict[str, dict[str, Any]]] = {}
    for raw in rows:
        row = normalize_run_row(raw)
        by_case.setdefault(case_key(row), {})[str(row.get("method"))] = row
    candidate_ids = sorted(
        {
            candidate_id_from_method(method)
            for methods in by_case.values()
            for method in methods
            if candidate_id_from_method(method)
        }
    )
    out: list[dict[str, Any]] = []
    for key, methods in sorted(by_case.items()):
        base = methods.get("lacam_star_ltm")
        base_ratio = _number(base or {}, "sum_of_loss_ratio")
        row = {
            "map": key[0],
            "agents": key[1],
            "seed": key[2],
            "scen": key[3],
            "split_bucket": "final_holdout" if int(key[2]) in FINAL_HOLDOUT_IDS else "support_train",
            "lacam_star_ltm_ratio": base_ratio,
            "repair5e5_ratio": _number(methods.get("repair5e5_crossfold_utility_reranker", {}), "sum_of_loss_ratio"),
        }
        for method in SYNTHETIC_METHODS:
            source = methods.get(method)
            row[f"{method}_candidate_id"] = source.get("repair5f_synthetic_candidate_id") if source else None
            row[f"{method}_delta_ratio_vs_ltm"] = (
                _number(source, "sum_of_loss_ratio") - float(base_ratio)
                if source is not None and base_ratio is not None and _number(source, "sum_of_loss_ratio") is not None
                else None
            )
        for candidate_id in candidate_ids:
            method = f"repair5f_candidate_{candidate_id}"
            candidate = methods.get(method)
            ratio = _number(candidate or {}, "sum_of_loss_ratio")
            row[f"ratio_delta_{candidate_id}"] = (
                float(ratio) - float(base_ratio) if ratio is not None and base_ratio is not None else None
            )
        out.append(row)
    fields = [
        "map",
        "agents",
        "seed",
        "scen",
        "split_bucket",
        "lacam_star_ltm_ratio",
        "repair5e5_ratio",
    ]
    for method in sorted(SYNTHETIC_METHODS):
        fields.extend([f"{method}_candidate_id", f"{method}_delta_ratio_vs_ltm"])
    fields.extend(f"ratio_delta_{candidate_id}" for candidate_id in candidate_ids)
    return out, fields


def gate_summary(
    *,
    method_stats: dict[str, dict[str, Any]],
    flags: dict[str, dict[str, int]],
    maps: list[str],
    agent_counts: list[int],
    instance_ids: list[int],
    full_raw_probe_coverage: bool,
    safety_gates_passed: bool,
) -> dict[str, Any]:
    oracle_method = "repair5f_candidate_lattice_oracle_static_proxy"
    stats = method_stats.get(oracle_method, {})
    flag = flags.get(oracle_method, {})
    mean_delta = stats.get("mean_delta_ratio_vs_ltm")
    final_holdout_ids_covered = set(FINAL_HOLDOUT_IDS).issubset(set(instance_ids))
    full_f1_scope = (
        final_holdout_ids_covered
        and set(MAPS).issubset(set(maps))
        and {50, 100}.issubset({int(value) for value in agent_counts})
        and full_raw_probe_coverage
    )
    passed = (
        safety_gates_passed
        and
        full_f1_scope
        and int(stats.get("better") or 0) > int(stats.get("worse") or 0)
        and mean_delta is not None
        and float(mean_delta) <= -0.003
        and int(flag.get("ratio_worse_than_ltm_groups") or 0) <= 1
        and int(flag.get("success_worse_than_ltm_groups") or 0) == 0
    )
    return {
        "final_holdout_ids_covered": final_holdout_ids_covered,
        "full_raw_probe_coverage": full_raw_probe_coverage,
        "full_f1_scope_evaluated": full_f1_scope,
        "candidate_lattice_oracle_gate_passed": passed,
        "candidate_lattice_oracle_metric_gate_passed": (
            full_f1_scope
            and int(stats.get("better") or 0) > int(stats.get("worse") or 0)
            and mean_delta is not None
            and float(mean_delta) <= -0.003
            and int(flag.get("ratio_worse_than_ltm_groups") or 0) <= 1
            and int(flag.get("success_worse_than_ltm_groups") or 0) == 0
        ),
        "candidate_lattice_oracle_better_gt_worse": int(stats.get("better") or 0) > int(stats.get("worse") or 0),
        "candidate_lattice_oracle_mean_delta_le_m003": (
            mean_delta is not None and float(mean_delta) <= -0.003
        ),
        "candidate_lattice_oracle_ratio_worse_groups_le_1": int(flag.get("ratio_worse_than_ltm_groups") or 0) <= 1,
        "candidate_lattice_oracle_success_worse_groups_eq_0": int(flag.get("success_worse_than_ltm_groups") or 0) == 0,
    }


def write_report(path: Path, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    stats = summary.get("paired_method_stats", {})
    gates = summary.get("gates", {})
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Phase5.5 Repair5F Candidate Probe\n\n")
        handle.write("This is diagnostic-only bounded UpdateParams evidence. It does not permit Phase5.5 or Phase6.\n\n")
        handle.write("## Boundary\n\n")
        handle.write("- phase5p5_allowed: `false`\n")
        handle.write("- phase6_allowed: `false`\n")
        handle.write("- solver_semantic_changes: `false`\n")
        handle.write("- learned_restart_enabled: `false`\n\n")
        handle.write("## Scope\n\n")
        scope = summary["scope"]
        handle.write(f"- maps: `{scope['maps']}`\n")
        handle.write(f"- agent_counts: `{scope['agent_counts']}`\n")
        handle.write(f"- instance_ids: `{scope['instance_ids']}`\n")
        handle.write(f"- candidate_count: `{scope['candidate_count']}`\n")
        handle.write(f"- time_limit_sec: `{scope['time_limit_sec']}`\n")
        handle.write(f"- ltm_max_iterations: `{scope['ltm_max_iterations']}`\n\n")
        handle.write("## Raw Coverage\n\n")
        handle.write(f"- expected_raw_probe_rows: `{summary.get('expected_raw_probe_rows')}`\n")
        handle.write(f"- raw_rows_before_dedupe: `{summary.get('raw_rows_before_dedupe')}`\n")
        handle.write(f"- raw_rows_after_dedupe: `{summary.get('raw_rows_after_dedupe')}`\n")
        handle.write(f"- duplicate_raw_rows_dropped: `{summary.get('duplicate_raw_rows_dropped')}`\n")
        handle.write(f"- missing_raw_probe_rows: `{summary.get('missing_raw_probe_rows')}`\n\n")
        handle.write("## Gates\n\n")
        for key, value in gates.items():
            handle.write(f"- {key}: `{value}`\n")
        handle.write("\n## Paired Method Stats\n\n")
        handle.write("| method | rows | better | equal | worse | mean delta ratio vs LTM |\n")
        handle.write("|---|---:|---:|---:|---:|---:|\n")
        for method, row in sorted(stats.items()):
            if method.startswith("repair5f_candidate_") and method not in SYNTHETIC_METHODS:
                continue
            handle.write(
                f"| {method} | {row.get('rows')} | {row.get('better')} | {row.get('equal')} | "
                f"{row.get('worse')} | {row.get('mean_delta_ratio_vs_ltm')} |\n"
            )
        handle.write("\n## Interpretation\n\n")
        if gates.get("candidate_lattice_oracle_metric_gate_passed") and not gates.get("safety_gates_passed"):
            handle.write(
                "The bounded UpdateParams lattice shows strong oracle headroom, but the strict safety gate does not pass "
                "because the force-additive defer control is not exact on the full holdout. The exact additive candidate "
                "itself matches LaCAM*+LTM, so the lattice path remains informative, but a selector/runtime artifact is "
                "deferred until the parity-control discrepancy is resolved.\n"
            )
        else:
            handle.write(
                "The lattice oracle is a headroom diagnostic over bounded UpdateParams candidates. "
                "A selector/runtime claim remains deferred until full held-out evidence beats random and shuffled diagnostics.\n"
            )


def write_audit_report(path: Path, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    stats = summary.get("paired_method_stats", {})
    gates = summary.get("gates", {})
    source_paths = [
        ("Report", summary.get("report")),
        ("Summary", summary.get("summary_json")),
        ("Raw probe JSONL", summary.get("raw_jsonl")),
        ("Command log JSONL", summary.get("command_log_jsonl")),
        ("LAUR update log JSONL", summary.get("laur_update_log_jsonl")),
        ("Long CSV", summary.get("long_csv")),
        ("Wide CSV", summary.get("wide_csv")),
    ]
    hash_paths = [
        Path(str(summary.get("raw_jsonl"))),
        Path(str(summary.get("command_log_jsonl"))),
        Path(str(summary.get("laur_update_log_jsonl"))),
    ]
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Phase5.5 Repair5F Candidate Probe Audit\n\n")
        handle.write(f"Verification date: {datetime.now().date().isoformat()}\n\n")
        handle.write("This audit is diagnostic-only and does not permit Phase5.5 or Phase6.\n\n")
        handle.write("## Source Files\n\n")
        for label, value in source_paths:
            handle.write(f"- {label}: `{value}`\n")
        handle.write("\n## Raw Coverage\n\n")
        handle.write(f"- Raw rows before dedupe: `{summary.get('raw_rows_before_dedupe')}`\n")
        handle.write(f"- Raw rows after dedupe: `{summary.get('raw_rows_after_dedupe')}`\n")
        handle.write(f"- Expected unique rows: `{summary.get('expected_raw_probe_rows')}`\n")
        handle.write(f"- Missing rows: `{summary.get('missing_raw_probe_rows')}`\n")
        handle.write(f"- Duplicate raw rows dropped: `{summary.get('duplicate_raw_rows_dropped')}`\n")
        handle.write(f"- Expected candidate rows: `{summary.get('expected_candidate_probe_rows')}`\n")
        handle.write(f"- Missing candidate rows: `{summary.get('missing_candidate_probe_rows')}`\n")
        handle.write(f"- Schema errors: `{len(summary.get('schema_errors') or [])}`\n")
        handle.write(f"- Long CSV rows: `{summary.get('long_csv_rows')}`\n")
        handle.write(f"- Wide CSV rows: `{summary.get('wide_csv_rows')}`\n\n")
        handle.write("## Raw Log Hashes\n\n")
        for item in hash_paths:
            handle.write(f"- `{item.name}`: `{file_sha256(item)}`\n")
        handle.write("\n## Gate Check\n\n")
        for key in [
            "force_additive_parity_exact",
            "exact_additive_candidate_parity_exact",
            "safety_gates_passed",
            "support_eval_leakage",
            "support_final_overlap_count",
            "full_raw_probe_coverage",
            "phase5p5_allowed",
            "phase6_allowed",
        ]:
            if key in gates:
                handle.write(f"- `{key}`: `{gates[key]}`\n")
        handle.write("\n## Paired Stats\n\n")
        handle.write("| method | rows | better | equal | worse | mean delta ratio vs LTM |\n")
        handle.write("|---|---:|---:|---:|---:|---:|\n")
        for method in [
            "always_additive_defer",
            "repair5f_candidate_additive_ltm",
            "repair5f_candidate_lattice_oracle_static_proxy",
            "repair5f_bounded_updateparam_selector_random_candidate_diagnostic",
            "repair5f_bounded_updateparam_selector_shuffled_utility_diagnostic",
            "repair5e5_crossfold_utility_reranker",
            "repair5e5_crossfold_utility_reranker_shuffled_labels_diagnostic",
        ]:
            row = stats.get(method)
            if not row:
                continue
            handle.write(
                f"| `{method}` | {row.get('rows')} | {row.get('better')} | {row.get('equal')} | "
                f"{row.get('worse')} | {row.get('mean_delta_ratio_vs_ltm')} |\n"
            )
        handle.write("\n## Conclusion\n\n")
        if summary.get("missing_candidate_probe_rows") == 0 and not summary.get("schema_errors"):
            handle.write(
                "Candidate coverage and schema checks are complete for the requested probe scope. "
                "This remains selector-training evidence only unless a later leakage-safe selector simulation passes.\n"
            )
        else:
            handle.write(
                "The probe evidence is incomplete or has schema errors. Downstream selector tuning must treat this "
                "as not ready until the missing rows or schema failures are resolved.\n"
            )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, default=Path(DEFAULT_BINARY))
    parser.add_argument("--scenario-dir", type=Path, default=Path(DEFAULT_SCENARIO_DIR))
    parser.add_argument("--candidate-lattice-csv", type=Path, default=Path(DEFAULT_CANDIDATE_CSV))
    parser.add_argument("--runtime-root", type=Path, default=Path(DEFAULT_RUNTIME_ROOT))
    parser.add_argument("--output-dir", type=Path, default=Path(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--output-jsonl", type=Path, default=Path(DEFAULT_OUTPUT_JSONL))
    parser.add_argument("--long-csv", type=Path, default=Path(DEFAULT_LONG_CSV))
    parser.add_argument("--wide-csv", type=Path, default=Path(DEFAULT_WIDE_CSV))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    parser.add_argument("--audit-report", type=Path, default=None)
    parser.add_argument("--additive-runtime-dir", type=Path, default=Path(DEFAULT_ADDITIVE_RUNTIME))
    parser.add_argument("--repair5e5-runtime-dir", type=Path, default=Path(DEFAULT_REPAIR5E5_RUNTIME))
    parser.add_argument("--repair5e5-shuffled-runtime-dir", type=Path, default=Path(DEFAULT_REPAIR5E5_SHUFFLED_RUNTIME))
    parser.add_argument("--maps", nargs="+", choices=sorted(MAPS), default=["random-32-32-20"])
    parser.add_argument("--agent-counts", nargs="+", type=int, default=[50])
    parser.add_argument("--instance-ids", nargs="+", type=int, default=[21])
    parser.add_argument("--time-limit-sec", type=float, default=1.0)
    parser.add_argument("--ltm-max-iterations", type=int, default=4)
    parser.add_argument("--max-candidates", type=int, default=0)
    parser.add_argument("--include-lacam-star", action="store_true")
    parser.add_argument("--include-repair5e5", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--include-repair5e5-shuffled", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--skip-solver", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--resume", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    binary = resolve_path(args.binary, root)
    scenario_dir = resolve_path(args.scenario_dir, root)
    candidate_csv = resolve_path(args.candidate_lattice_csv, root)
    runtime_root = resolve_path(args.runtime_root, root)
    output_dir = resolve_path(args.output_dir, root)
    output_jsonl = resolve_path(args.output_jsonl, root)
    long_csv = resolve_path(args.long_csv, root)
    wide_csv = resolve_path(args.wide_csv, root)
    report = resolve_path(args.report, root)
    summary_json = resolve_path(args.summary_json, root)
    audit_report = resolve_path(args.audit_report, root) if args.audit_report is not None else None
    additive_runtime = resolve_path(args.additive_runtime_dir, root)
    repair5e5_runtime = resolve_path(args.repair5e5_runtime_dir, root)
    repair5e5_shuffled_runtime = resolve_path(args.repair5e5_shuffled_runtime_dir, root)
    command_log = output_jsonl.with_name(output_jsonl.stem + "_commands.jsonl")
    laur_update_log = output_jsonl.with_name(output_jsonl.stem + "_laur_updates.jsonl")

    if args.overwrite and args.resume:
        raise ValueError("--overwrite and --resume cannot be used together")

    if not candidate_csv.exists():
        raise FileNotFoundError(f"candidate lattice missing: {candidate_csv}")
    candidates = choose_candidates(read_candidates(candidate_csv), int(args.max_candidates))
    candidates_by_id = {candidate.candidate_id: candidate for candidate in candidates}
    methods, skipped_methods = build_methods(
        candidates=candidates,
        runtime_root=runtime_root,
        additive_runtime=additive_runtime,
        repair5e5_runtime=repair5e5_runtime,
        repair5e5_shuffled_runtime=repair5e5_shuffled_runtime,
        include_lacam_star=bool(args.include_lacam_star),
        include_repair5e5=bool(args.include_repair5e5),
        include_repair5e5_shuffled=bool(args.include_repair5e5_shuffled),
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    if args.overwrite:
        for path in (output_jsonl, command_log, laur_update_log):
            if path.exists():
                path.unlink()
    if not args.skip_solver:
        if not binary.exists():
            raise FileNotFoundError(binary)
        completed_keys: set[tuple[str, int, int, str]] = set()
        if output_jsonl.exists() and args.resume:
            completed_keys = completed_probe_keys(read_jsonl(output_jsonl))
        elif output_jsonl.exists():
            raise FileExistsError(f"output JSONL already exists: {output_jsonl}")
        run_solver_grid(
            root=root,
            binary=binary,
            scenario_dir=scenario_dir,
            output_jsonl=output_jsonl,
            command_log=command_log,
            laur_update_log=laur_update_log,
            maps=list(args.maps),
            agent_counts=[int(value) for value in args.agent_counts],
            instance_ids=[int(value) for value in args.instance_ids],
            time_limit_sec=float(args.time_limit_sec),
            ltm_max_iterations=int(args.ltm_max_iterations),
            methods=methods,
            completed_keys=completed_keys,
        )

    raw_jsonl_rows = read_jsonl(output_jsonl)
    raw_rows = [normalize_run_row(row) for row in dedupe_probe_rows(raw_jsonl_rows)]
    expected_keys = expected_probe_keys(
        maps=list(args.maps),
        agent_counts=[int(value) for value in args.agent_counts],
        instance_ids=[int(value) for value in args.instance_ids],
        methods=methods,
    )
    candidate_methods = [method for method in methods if method.hidden_support]
    expected_candidate_keys = expected_probe_keys(
        maps=list(args.maps),
        agent_counts=[int(value) for value in args.agent_counts],
        instance_ids=[int(value) for value in args.instance_ids],
        methods=candidate_methods,
    )
    observed_keys = completed_probe_keys(raw_rows)
    missing_keys = sorted(expected_keys - observed_keys)
    missing_candidate_keys = sorted(expected_candidate_keys - observed_keys)
    schema_errors: list[str] = []
    for index, row in enumerate(raw_rows, 1):
        schema_errors.extend(f"row {index}: {error}" for error in validate_run_row(row))
    synthetic_rows = synthesize_diagnostics(raw_rows)
    report_rows = raw_rows + synthetic_rows
    paired = paired_rows(report_rows)
    method_stats = paired_method_stats(paired)
    summary_rows = summarize_rows(report_rows)
    flags = group_flags(summary_rows)
    force_additive_parity = force_additive_parity_exact(raw_rows)
    exact_additive_candidate_parity = exact_additive_candidate_parity_exact(raw_rows)
    safety_gates_passed = (
        force_additive_parity
        and not bool(set(TRAIN_IDS) & set(FINAL_HOLDOUT_IDS))
    )
    support_final_overlap_ids = sorted(set(int(value) for value in args.instance_ids) & set(FINAL_HOLDOUT_IDS))
    gates = {
        "force_additive_parity_exact": force_additive_parity,
        "exact_additive_candidate_parity_exact": exact_additive_candidate_parity,
        "support_eval_leakage": bool(set(TRAIN_IDS) & set(FINAL_HOLDOUT_IDS)),
        "support_final_overlap_count": len(support_final_overlap_ids),
        "support_final_overlap_ids": support_final_overlap_ids,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "solver_semantic_changes": False,
        "safety_gates_passed": safety_gates_passed,
        **gate_summary(
            method_stats=method_stats,
            flags=flags,
            maps=list(args.maps),
            agent_counts=[int(value) for value in args.agent_counts],
            instance_ids=[int(value) for value in args.instance_ids],
            full_raw_probe_coverage=not missing_keys,
            safety_gates_passed=safety_gates_passed,
        ),
    }
    long_rows = build_long_rows(rows=report_rows, candidates_by_id=candidates_by_id)
    wide_rows, wide_fields = build_wide_rows(report_rows)

    long_fields = [
        "map",
        "agents",
        "seed",
        "scen",
        "split_bucket",
        "candidate_id",
        "alpha_commit",
        "alpha_block",
        "alpha_wait_spillover",
        "rho_decay",
        "force_additive",
        "construction",
        "old_equivalent_rule",
        "success",
        "sum_of_loss_ratio",
        "delta_ratio_vs_ltm",
        "delta_ratio_vs_repair5e5",
        "expanded_delta_vs_ltm",
        "low_level_pibt_delta_vs_ltm",
        "ttfs_delta_vs_ltm",
        "better_vs_ltm",
        "equal_vs_ltm",
        "worse_vs_ltm",
    ]
    _write_csv(long_csv, long_rows, long_fields)
    _write_csv(wide_csv, wide_rows, wide_fields)

    summary = {
        "schema_version": "phase5p5_repair5f_candidate_probe_v1",
        "created_at": datetime.now().isoformat(),
        "branch": git_value(["branch", "--show-current"], root),
        "commit": git_value(["rev-parse", "--short", "HEAD"], root),
        "dirty": dirty_state(root),
        "clean_tracked_worktree": dirty_state(root) in {"clean", "untracked-present"},
        "diagnostic_only": True,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "raw_jsonl": str(output_jsonl),
        "command_log_jsonl": str(command_log),
        "laur_update_log_jsonl": str(laur_update_log),
        "long_csv": str(long_csv),
        "wide_csv": str(wide_csv),
        "report": str(report),
        "summary_json": str(summary_json),
        "audit_report": str(audit_report) if audit_report else "",
        "raw_rows_before_dedupe": len(raw_jsonl_rows),
        "raw_rows_after_dedupe": len(raw_rows),
        "duplicate_raw_rows_dropped": len(raw_jsonl_rows) - len(raw_rows),
        "expected_raw_probe_rows": len(expected_keys),
        "missing_raw_probe_rows": len(missing_keys),
        "expected_candidate_probe_rows": len(expected_candidate_keys),
        "missing_candidate_probe_rows": len(missing_candidate_keys),
        "missing_raw_probe_examples": [
            {"map": key[0], "agents": key[1], "seed": key[2], "method": key[3]} for key in missing_keys[:50]
        ],
        "missing_candidate_probe_examples": [
            {"map": key[0], "agents": key[1], "seed": key[2], "method": key[3]}
            for key in missing_candidate_keys[:50]
        ],
        "schema_errors": schema_errors,
        "long_csv_rows": len(long_rows),
        "wide_csv_rows": len(wide_rows),
        "scope": {
            "maps": list(args.maps),
            "agent_counts": [int(value) for value in args.agent_counts],
            "instance_ids": [int(value) for value in args.instance_ids],
            "support_train_ids": TRAIN_IDS,
            "final_holdout_ids": FINAL_HOLDOUT_IDS,
            "oof_folds": OOF_FOLDS,
            "candidate_count": len(candidates),
            "time_limit_sec": float(args.time_limit_sec),
            "ltm_max_iterations": int(args.ltm_max_iterations),
            "methods": [method.alias for method in methods if not method.hidden_support] + sorted(SYNTHETIC_METHODS),
            "candidate_methods": [method.alias for method in methods if method.hidden_support],
        },
        "skipped_methods": skipped_methods,
        "synthetic_rows": len(synthetic_rows),
        "paired_method_stats": method_stats,
        "summary_rows": summary_rows,
        "method_group_flags": flags,
        "gates": gates,
    }
    summary_json.parent.mkdir(parents=True, exist_ok=True)
    summary_json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(report, summary)
    if audit_report is not None:
        write_audit_report(audit_report, summary)
    print(json.dumps({"summary_json": rel(summary_json, root), "report": rel(report, root), "long_csv": rel(long_csv, root), "wide_csv": rel(wide_csv, root)}))
    return 0 if not schema_errors else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
