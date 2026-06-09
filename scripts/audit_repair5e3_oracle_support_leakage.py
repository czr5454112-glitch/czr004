"""Audit Repair5E.3 oracle/static support leakage and provenance.

The auditor is intentionally conservative: it treats path reuse, instance-id
overlap, support files that post-date evaluation logs, and exact context
recovery tables as separate signals. Exact context tables are not automatically
leakage, but they must be reported because E2 used a small map/agent allowlist.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import subprocess
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


DEFAULT_RUNTIME_DIR = "artifacts/models/laur_ltm/repair5e3_split_guarded_selector"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5e3_leakage_ablation_report.md"
DEFAULT_SUMMARY_JSON = "outputs/reports/phase5p5_repair5e3_leakage_ablation_summary.json"
DEFAULT_PROVENANCE_REPORT = "outputs/reports/phase5p5_repair5e3_provenance_audit_report.md"
DEFAULT_PROVENANCE_SUMMARY_JSON = "outputs/reports/phase5p5_repair5e3_provenance_audit_summary.json"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def resolve_path(path: str | Path | None, root: Path) -> Path | None:
    if path is None:
        return None
    value = Path(path)
    return value if value.is_absolute() else root / value


def norm(path: str | Path | None, root: Path) -> str:
    resolved = resolve_path(path, root)
    if resolved is None:
        return ""
    try:
        return str(resolved.resolve()).lower()
    except OSError:
        return str(resolved.absolute()).lower()


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


def git_dirty(root: Path) -> tuple[bool, bool, list[str]]:
    status = git_value(["status", "--short"], root)
    lines = [line for line in status.splitlines() if line.strip()]
    tracked = [line for line in lines if not line.startswith("??")]
    untracked = [line for line in lines if line.startswith("??")]
    return bool(tracked), bool(untracked), lines


def sha256_file(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path | None) -> list[dict[str, Any]]:
    if path is None or not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def read_csv(path: Path | None) -> list[dict[str, str]]:
    if path is None or not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def finite(value: Any, default: float = math.nan) -> float:
    if value is None or isinstance(value, bool):
        return default
    try:
        out = float(value)
    except (TypeError, ValueError):
        return default
    return out if math.isfinite(out) else default


def collect_manifest_paths(manifest: dict[str, Any]) -> set[str]:
    keys = {
        "previous_raw_jsonl",
        "train_support_paths",
        "support_paths",
        "source_support_paths",
        "eval_log_paths",
        "forbidden_eval_support_paths",
    }
    out: set[str] = set()
    for key in keys:
        value = manifest.get(key)
        if isinstance(value, str):
            out.add(value)
        elif isinstance(value, list):
            out.update(str(item) for item in value)
    split = manifest.get("split_metadata")
    if isinstance(split, dict):
        for key in keys:
            value = split.get(key)
            if isinstance(value, str):
                out.add(value)
            elif isinstance(value, list):
                out.update(str(item) for item in value)
    return out


def collect_preflight_eval_paths(paths: list[Path], root: Path) -> list[Path]:
    out: list[Path] = []
    for path in paths:
        summary = read_json(path)
        for key in ("raw_jsonl", "laur_update_log_jsonl", "command_log_jsonl"):
            value = summary.get(key)
            resolved = resolve_path(value, root) if value else None
            if resolved is not None:
                out.append(resolved)
    return out


def instance_keys(rows: list[dict[str, Any]]) -> set[tuple[str, int, int]]:
    out: set[tuple[str, int, int]] = set()
    for row in rows:
        map_name = str(row.get("map", ""))
        agents = int(finite(row.get("agents"), 0.0))
        seed = int(finite(row.get("seed"), 0.0))
        if map_name and agents and seed:
            out.add((map_name, agents, seed))
    return out


def support_instance_keys(manifest: dict[str, Any], root: Path) -> set[tuple[str, int, int]]:
    split = manifest.get("split_metadata") if isinstance(manifest.get("split_metadata"), dict) else {}
    explicit = manifest.get("train_instance_ids", split.get("train_instance_ids"))
    maps = manifest.get("maps", split.get("maps", []))
    agents = manifest.get("agent_counts", split.get("agent_counts", []))
    if isinstance(explicit, list) and isinstance(maps, list) and isinstance(agents, list):
        return {
            (str(map_name), int(agent_count), int(seed))
            for map_name in maps
            for agent_count in agents
            for seed in explicit
        }
    previous = manifest.get("previous_raw_jsonl")
    if isinstance(previous, str):
        return instance_keys(read_jsonl(resolve_path(previous, root)))
    return set()


def recovery_context_rows(manifest: dict[str, Any], support_rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    manifest_rows = manifest.get("recovery_rules")
    if isinstance(manifest_rows, list) and manifest_rows:
        return [row for row in manifest_rows if isinstance(row, dict)]
    out: list[dict[str, Any]] = []
    for row in support_rows:
        out.append(
            {
                "map": row.get("map", ""),
                "map_width": row.get("map_width"),
                "map_height": row.get("map_height"),
                "agents": finite(row.get("agents"), 0.0),
                "rule_id": row.get("rule_id"),
                "support_rows": finite(row.get("support_rows"), 0.0),
                "support_better": finite(row.get("support_better"), 0.0),
                "support_equal": finite(row.get("support_equal"), 0.0),
                "support_worse": finite(row.get("support_worse"), 0.0),
                "source": row.get("source"),
            }
        )
    return out


def audit_leakage(
    *,
    root: Path,
    runtime_dir: Path,
    manifest_path: Path | None,
    support_csv: Path | None,
    eval_jsonl_paths: list[Path],
    preflight_summary_paths: list[Path],
    ablation_summary_path: Path | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    manifest = read_json(manifest_path)
    support_rows = read_csv(support_csv)
    eval_paths = list(eval_jsonl_paths) + collect_preflight_eval_paths(preflight_summary_paths, root)
    eval_paths = [path for path in eval_paths if path is not None]
    eval_rows: list[dict[str, Any]] = []
    for path in eval_paths:
        if path.suffix.lower() == ".jsonl":
            eval_rows.extend(read_jsonl(path))

    manifest_path_strings = {norm(path, root) for path in collect_manifest_paths(manifest)}
    eval_path_strings = {norm(path, root) for path in eval_paths}
    support_path_strings = {norm(path, root) for path in [support_csv, manifest_path] if path is not None}
    support_path_strings.update(manifest_path_strings)
    path_overlap = sorted(value for value in eval_path_strings if value in support_path_strings and value)

    support_keys = support_instance_keys(manifest, root)
    eval_keys = instance_keys(eval_rows)
    instance_overlap = sorted(support_keys & eval_keys)

    support_files = [path for path in [support_csv, manifest_path] if path is not None and path.exists()]
    eval_existing = [path for path in eval_paths if path.exists()]
    generated_after_eval_logs = False
    if support_files and eval_existing:
        newest_eval = max(path.stat().st_mtime for path in eval_existing)
        generated_after_eval_logs = any(path.stat().st_mtime > newest_eval for path in support_files)

    contexts = recovery_context_rows(manifest, support_rows)
    context_counts = Counter(
        (
            str(row.get("map", "")),
            int(finite(row.get("agents"), 0.0)),
            str(row.get("rule_id", "")),
        )
        for row in contexts
    )
    exact_map_agent_recovery_table_used = any(
        row.get("map") and finite(row.get("agents"), 0.0) > 0 for row in contexts
    ) or any(
        row.get("map_width") and row.get("map_height") and finite(row.get("agents"), 0.0) > 0
        for row in contexts
    )
    rule_support_by_context = [
        {
            "map": row.get("map", ""),
            "map_width": row.get("map_width"),
            "map_height": row.get("map_height"),
            "agents": row.get("agents"),
            "rule_id": row.get("rule_id"),
            "support_rows": row.get("support_rows"),
            "support_better": row.get("support_better"),
            "support_equal": row.get("support_equal"),
            "support_worse": row.get("support_worse"),
            "source": row.get("source"),
        }
        for row in contexts
    ]

    ablation_summary = read_json(ablation_summary_path)
    method_stats = ablation_summary.get("paired_method_stats", {}) if ablation_summary else {}
    disabled = method_stats.get("repair5e3_e2_recovery_disabled_parity", {})
    guarded = method_stats.get("repair5e2_guarded_oracle_aligned_selector", {})
    shuffled = method_stats.get("repair5e3_e2_recovery_shuffled_support_diagnostic", {})
    disabled_exact_parity = (
        disabled.get("better") == 0
        and disabled.get("worse") == 0
        and float(disabled.get("mean_delta_ratio_vs_ltm") or 0.0) == 0.0
    ) if disabled else None
    shuffled_not_better_than_guarded = None
    if shuffled and guarded:
        shuffled_mean = shuffled.get("mean_delta_ratio_vs_ltm")
        guarded_mean = guarded.get("mean_delta_ratio_vs_ltm")
        if shuffled_mean is not None and guarded_mean is not None:
            shuffled_not_better_than_guarded = float(shuffled_mean) >= float(guarded_mean)

    leakage_detected = bool(path_overlap or instance_overlap or generated_after_eval_logs)
    summary = {
        "schema_version": "phase5p5_repair5e3_oracle_support_leakage_audit_v1",
        "created_at": datetime.now().isoformat(),
        "diagnostic_only": True,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "runtime_dir": rel(runtime_dir, root),
        "runtime_manifest": rel(manifest_path, root) if manifest_path else None,
        "support_csv": rel(support_csv, root) if support_csv else None,
        "eval_log_paths": [rel(path, root) for path in eval_paths],
        "eval_raw_jsonl_paths_appear_in_train_support_metadata": bool(path_overlap),
        "path_overlaps": path_overlap,
        "support_eval_instance_overlap_count": len(instance_overlap),
        "support_eval_instance_overlap": [
            {"map": key[0], "agents": key[1], "seed": key[2]} for key in instance_overlap
        ],
        "support_generated_after_eval_logs": generated_after_eval_logs,
        "exact_map_agent_recovery_table_used": exact_map_agent_recovery_table_used,
        "groups_depending_on_exact_map_agent_matches": [
            {"map": key[0], "agents": key[1], "rule_id": key[2], "rows": count}
            for key, count in sorted(context_counts.items())
        ],
        "rule_support_by_context": rule_support_by_context,
        "ablation_summary_json": rel(ablation_summary_path, root) if ablation_summary_path else None,
        "ablation_checks": {
            "recovery_disabled_parity_exact": disabled_exact_parity,
            "shuffled_support_not_better_than_guarded": shuffled_not_better_than_guarded,
            "guarded_stats": guarded,
            "disabled_stats": disabled,
            "shuffled_stats": shuffled,
        },
        "leakage_detected": leakage_detected,
        "no_support_eval_leakage_detected": not leakage_detected,
    }
    tracked_dirty, untracked_present, status_lines = git_dirty(root)
    provenance = {
        "schema_version": "phase5p5_repair5e3_provenance_audit_v1",
        "created_at": datetime.now().isoformat(),
        "diagnostic_only": True,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "git_head_sha": git_value(["rev-parse", "HEAD"], root),
        "git_branch": git_value(["branch", "--show-current"], root),
        "git_dirty_tracked": tracked_dirty,
        "git_untracked_present": untracked_present,
        "git_status_short": status_lines,
        "clean_tracked_worktree": not tracked_dirty,
        "runtime_manifest_sha256": sha256_file(manifest_path) if manifest_path else None,
        "runtime_dir": rel(runtime_dir, root),
        "train_support_paths": sorted(str(path) for path in collect_manifest_paths(manifest)),
        "eval_log_paths": [rel(path, root) for path in eval_paths],
        "forbidden_eval_support_paths": [rel(path, root) for path in eval_paths],
        "leakage_summary_json": None,
    }
    return summary, provenance


def write_report(path: Path, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Phase5.5 Repair5E.3 Leakage and Ablation Audit\n\n")
        handle.write("- diagnostic-only: `true`\n")
        handle.write("- phase5p5_allowed: `false`\n")
        handle.write("- phase6_allowed: `false`\n")
        handle.write(f"- leakage_detected: `{summary.get('leakage_detected')}`\n")
        handle.write(
            "- eval paths reused in train/support metadata: "
            f"`{summary.get('eval_raw_jsonl_paths_appear_in_train_support_metadata')}`\n"
        )
        handle.write(f"- support/eval instance overlap count: `{summary.get('support_eval_instance_overlap_count')}`\n")
        handle.write(f"- support generated after eval logs: `{summary.get('support_generated_after_eval_logs')}`\n")
        handle.write(f"- exact map/agent recovery table used: `{summary.get('exact_map_agent_recovery_table_used')}`\n\n")
        handle.write("## Ablation Checks\n\n")
        handle.write(json.dumps(summary.get("ablation_checks"), indent=2, sort_keys=True))
        handle.write("\n\n## Rule Support By Context\n\n")
        handle.write("| map | agents | rule | support | better/equal/worse | source |\n")
        handle.write("|---|---:|---|---:|---:|---|\n")
        for row in summary.get("rule_support_by_context", []):
            handle.write(
                f"| {row.get('map')} | {row.get('agents')} | {row.get('rule_id')} | "
                f"{row.get('support_rows')} | "
                f"{row.get('support_better')}/{row.get('support_equal')}/{row.get('support_worse')} | "
                f"{row.get('source')} |\n"
            )


def write_provenance_report(path: Path, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Phase5.5 Repair5E.3 Provenance Audit\n\n")
        handle.write(f"- git_head_sha: `{summary.get('git_head_sha')}`\n")
        handle.write(f"- git_branch: `{summary.get('git_branch')}`\n")
        handle.write(f"- git_dirty_tracked: `{summary.get('git_dirty_tracked')}`\n")
        handle.write(f"- git_untracked_present: `{summary.get('git_untracked_present')}`\n")
        handle.write(f"- clean tracked worktree: `{summary.get('clean_tracked_worktree')}`\n")
        handle.write(f"- runtime manifest sha256: `{summary.get('runtime_manifest_sha256')}`\n")
        handle.write(f"- runtime_dir: `{summary.get('runtime_dir')}`\n\n")
        handle.write("## Paths\n\n")
        handle.write(f"- train_support_paths: `{summary.get('train_support_paths')}`\n")
        handle.write(f"- eval_log_paths: `{summary.get('eval_log_paths')}`\n")
        handle.write(f"- forbidden_eval_support_paths: `{summary.get('forbidden_eval_support_paths')}`\n")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-dir", type=Path, default=Path(DEFAULT_RUNTIME_DIR))
    parser.add_argument("--runtime-manifest", type=Path)
    parser.add_argument("--support-csv", type=Path)
    parser.add_argument("--eval-jsonl", type=Path, action="append", default=[])
    parser.add_argument("--preflight-summary-json", type=Path, action="append", default=[])
    parser.add_argument("--ablation-summary-json", type=Path)
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY_JSON))
    parser.add_argument("--provenance-report", type=Path, default=Path(DEFAULT_PROVENANCE_REPORT))
    parser.add_argument("--provenance-summary-json", type=Path, default=Path(DEFAULT_PROVENANCE_SUMMARY_JSON))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    runtime_dir = resolve_path(args.runtime_dir, root)
    assert runtime_dir is not None
    manifest = resolve_path(args.runtime_manifest, root)
    if manifest is None:
        candidates = [
            runtime_dir / "repair5e3_split_guarded_selector_manifest.json",
            runtime_dir / "repair5e2_guarded_selector_manifest.json",
        ]
        manifest = next((path for path in candidates if path.exists()), candidates[0])
    support_csv = resolve_path(args.support_csv, root)
    if support_csv is None:
        support_csv = runtime_dir / "repair5e2_recovery_rules.csv"
    eval_jsonl = [path for value in args.eval_jsonl if (path := resolve_path(value, root)) is not None]
    preflight_summaries = [
        path for value in args.preflight_summary_json if (path := resolve_path(value, root)) is not None
    ]
    ablation_summary = resolve_path(args.ablation_summary_json, root)
    report = resolve_path(args.report, root)
    summary_json = resolve_path(args.summary_json, root)
    provenance_report = resolve_path(args.provenance_report, root)
    provenance_summary_json = resolve_path(args.provenance_summary_json, root)
    assert report and summary_json and provenance_report and provenance_summary_json

    summary, provenance = audit_leakage(
        root=root,
        runtime_dir=runtime_dir,
        manifest_path=manifest,
        support_csv=support_csv,
        eval_jsonl_paths=eval_jsonl,
        preflight_summary_paths=preflight_summaries,
        ablation_summary_path=ablation_summary,
    )
    provenance["leakage_summary_json"] = rel(summary_json, root)
    summary_json.parent.mkdir(parents=True, exist_ok=True)
    summary_json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    provenance_summary_json.parent.mkdir(parents=True, exist_ok=True)
    provenance_summary_json.write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(report, summary)
    write_provenance_report(provenance_report, provenance)
    print(
        json.dumps(
            {
                "summary_json": str(summary_json),
                "report": str(report),
                "provenance_summary_json": str(provenance_summary_json),
                "provenance_report": str(provenance_report),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
