"""Helpers for freezing and loading the Repair5D composite diagnostic spec."""

from __future__ import annotations

import json
import math
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any


SPEC_SCHEMA_VERSION = "phase4f_repair5d_best_composite_spec_v1"

EXPECTED_BEST = {
    "mode": "rank_model_top5_safety_model_per_rule_utility_rerank",
    "composite_mode": "top3_per_rule_safety_utility",
    "top_k": 5,
    "ranking_suffix": "phase4f_repair5_expand5000_nextwave_normal_attn_linear_head_rank_safe_eval_seed61.csv",
    "safety_suffix": "phase4f_repair5_expand5000_hightoken_ht_mlp_target_global_eval_seed61.csv",
    "anti_suffix": "phase4f_repair5_expand5000_postnext_hightoken_attn_mlp_head_rank_recall_perrule_eval_seed61.csv",
}

OFFLINE_VALIDATION_KEYS = [
    "sample_count",
    "rule_top1",
    "rule_top3",
    "safe_utility_top1",
    "safe_utility_top3",
    "harmful_recall",
    "harmful_precision",
    "high_margin_capture",
    "selected_vs_additive_delta",
    "selected_vs_additive_utility",
    "utility_regret_to_oracle",
    "selected_harmful_rate",
    "global_additive_or_defer_rate",
]


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


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


def resolve_path(path: str | Path | None, root: Path | None = None) -> Path | None:
    if path is None:
        return None
    value = Path(path)
    if value.is_absolute():
        return value
    return (root or repo_root()) / value


def _finite(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


def load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_composite_spec(path: str | Path) -> dict[str, Any]:
    payload = load_json(path)
    if payload.get("schema_version") != SPEC_SCHEMA_VERSION:
        raise ValueError(f"{path}: expected schema_version {SPEC_SCHEMA_VERSION}")
    if payload.get("phase5p5_allowed") is not False:
        raise ValueError(f"{path}: phase5p5_allowed must remain false")
    if payload.get("phase6_allowed") is not False:
        raise ValueError(f"{path}: phase6_allowed must remain false")
    required = [
        "mode",
        "composite_mode",
        "top_k",
        "ranking_csv",
        "safety_csv",
        "anti_csv",
        "safety_calibration",
        "offline_validation",
    ]
    missing = [key for key in required if key not in payload]
    if missing:
        raise ValueError(f"{path}: missing spec keys {missing}")
    return payload


def select_best_row(grid_summary: dict[str, Any]) -> dict[str, Any]:
    rows = list(grid_summary.get("summary_rows") or [])
    if not rows:
        raise ValueError("composite grid summary has no summary_rows")
    for row in rows:
        if (
            row.get("grid_mode") == EXPECTED_BEST["mode"]
            and row.get("composite_mode") == EXPECTED_BEST["composite_mode"]
            and int(row.get("top_k") or 0) == EXPECTED_BEST["top_k"]
            and str(row.get("ranking_csv", "")).endswith(EXPECTED_BEST["ranking_suffix"])
            and str(row.get("safety_csv", "")).endswith(EXPECTED_BEST["safety_suffix"])
            and str(row.get("anti_csv", "")).endswith(EXPECTED_BEST["anti_suffix"])
        ):
            return row
    raise ValueError("expected Repair5D best composite row was not found")


def build_best_composite_spec(
    *,
    grid_summary: dict[str, Any],
    grid_summary_path: str | Path,
    safety_calibration: str | Path,
    root: Path | None = None,
) -> dict[str, Any]:
    root = root or repo_root()
    row = select_best_row(grid_summary)
    offline_validation = {
        key: (
            int(row[key])
            if key == "sample_count"
            else _finite(row.get(key), 0.0)
        )
        for key in OFFLINE_VALIDATION_KEYS
        if key in row
    }
    spec = {
        "schema_version": SPEC_SCHEMA_VERSION,
        "created_at": datetime.now().isoformat(),
        "branch": git_value(["branch", "--show-current"], root),
        "commit": git_value(["rev-parse", "--short", "HEAD"], root),
        "dirty": dirty_state(root),
        "source_summary_json": str(resolve_path(grid_summary_path, root)),
        "mode": row["grid_mode"],
        "composite_mode": row["composite_mode"],
        "grid_id": row.get("grid_id"),
        "ranking_csv": str(row["ranking_csv"]),
        "safety_csv": str(row["safety_csv"]),
        "anti_csv": str(row["anti_csv"]),
        "safety_calibration": str(resolve_path(safety_calibration, root)),
        "top_k": int(row["top_k"]),
        "default_threshold": 0.35,
        "opportunity_threshold": 0.50,
        "defer_threshold": 0.50,
        "offline_validation": offline_validation,
        "runtime_path": "diagnostic_distill_to_existing_laur_mlp_runtime",
        "diagnostic_only": True,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "boundaries": [
            "LAUR / learned UpdateLTM only",
            "does not predict agent actions",
            "does not replace PIBT or LaCAM*",
            "does not alter conflict semantics",
            "does not add learned restart",
            "does not lower final gates",
        ],
    }
    load_composite_spec_from_payload(spec)
    return spec


def load_composite_spec_from_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get("schema_version") != SPEC_SCHEMA_VERSION:
        raise ValueError(f"expected schema_version {SPEC_SCHEMA_VERSION}")
    if payload.get("phase5p5_allowed") is not False or payload.get("phase6_allowed") is not False:
        raise ValueError("Repair5D composite spec must not unlock Phase5.5 or Phase6")
    if int(payload.get("top_k") or 0) <= 0:
        raise ValueError("top_k must be positive")
    return payload


def write_json(path: str | Path, payload: dict[str, Any]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_spec_markdown(path: str | Path, spec: dict[str, Any]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    metrics = spec.get("offline_validation", {})
    lines = [
        "# Phase4F Repair5D Best Composite Spec",
        "",
        "This freezes the Repair5D composite as diagnostic-only input for Repair5E closed-loop transfer tests.",
        "",
        "## Boundary",
        "",
        "- Phase5.5 allowed: `False`",
        "- Phase6 allowed: `False`",
        "- Scope: LAUR / learned `UpdateLTM` only",
        "- This spec does not change PIBT, LaCAM*, conflict semantics, candidate generation, or restart policy.",
        "",
        "## Composite",
        "",
        f"- mode: `{spec['mode']}`",
        f"- composite_mode: `{spec['composite_mode']}`",
        f"- top_k: `{spec['top_k']}`",
        f"- ranking_csv: `{spec['ranking_csv']}`",
        f"- safety_csv: `{spec['safety_csv']}`",
        f"- anti_csv: `{spec['anti_csv']}`",
        f"- safety_calibration: `{spec['safety_calibration']}`",
        "",
        "## Offline Validation",
        "",
        "| metric | value |",
        "|---|---:|",
    ]
    for key in OFFLINE_VALIDATION_KEYS:
        if key in metrics:
            value = metrics[key]
            lines.append(f"| {key} | {value} |")
    lines.extend(
        [
            "",
            "## Runtime Use",
            "",
            "Repair5E may use this spec for native export or diagnostic distillation only. It must not be treated as Phase5.5 or Phase6 evidence without closed-loop validation against `LaCAM*+LTM`.",
            "",
        ]
    )
    output.write_text("\n".join(lines), encoding="utf-8")
