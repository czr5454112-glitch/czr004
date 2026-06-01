"""Assemble Repair5E.5 five-fold support logs from available static-probe runs."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


DEFAULT_OUTPUT_DIR = "outputs/logs/phase5p5_repair5e5_crossfold_support"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5e5_crossfold_support_report.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5e5_crossfold_support_summary.json"

DEFAULT_RAW_JSONL = [
    "outputs/logs/phase5p5_repair5e4_train_support/phase5p5_repair5e4_train_support.jsonl",
    "outputs/logs/phase5p5_repair5e4_preflight/phase5p5_repair5e4_preflight.jsonl",
    "outputs/logs/phase5p5_repair5e5_support_ids21_25/phase5p5_repair5e5_support_ids21_25.jsonl",
]

DEFAULT_UPDATE_JSONL = [
    "outputs/logs/phase5p5_repair5e4_train_support/phase5p5_repair5e4_train_support_laur_updates.jsonl",
    "outputs/logs/phase5p5_repair5e4_preflight/phase5p5_repair5e4_preflight_laur_updates.jsonl",
    "outputs/logs/phase5p5_repair5e5_support_ids21_25/phase5p5_repair5e5_support_ids21_25_laur_updates.jsonl",
]

FOLDS = {
    0: [1, 2, 3, 4, 5],
    1: [6, 7, 8, 9, 10],
    2: [11, 12, 13, 14, 15],
    3: [16, 17, 18, 19, 20],
    4: [21, 22, 23, 24, 25],
}

SUPPORT_METHODS = {
    "lacam_star_ltm",
    "always_additive_defer",
    "oracle_probe_static_block_heavy",
    "oracle_probe_static_block_light",
    "oracle_probe_static_commit_heavy",
    "oracle_probe_static_decay_090",
    "oracle_probe_static_decay_095",
    "oracle_probe_static_wait_heavy",
    "oracle_probe_static_wait_light",
}


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


def sha256_file(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def finite_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def method_supported(method: str) -> bool:
    return method in SUPPORT_METHODS


def row_key(row: dict[str, Any]) -> tuple[str, int, int, str, str]:
    return (
        str(row.get("map", "")),
        finite_int(row.get("agents")),
        finite_int(row.get("seed")),
        str(row.get("scen", "")),
        str(row.get("method", "")),
    )


def dedupe_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: dict[tuple[str, int, int, str, str], dict[str, Any]] = {}
    for row in rows:
        method = str(row.get("method", ""))
        if method_supported(method):
            deduped[row_key(row)] = row
    return [deduped[key] for key in sorted(deduped)]


def update_row_key(row: dict[str, Any]) -> tuple[str, int, int, str, int, str]:
    return (
        str(row.get("map", "")),
        finite_int(row.get("agents")),
        finite_int(row.get("seed")),
        str(row.get("scen", "")),
        finite_int(row.get("iteration")),
        str(row.get("method", "")),
    )


def dedupe_update_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: dict[tuple[str, int, int, str, int, str], dict[str, Any]] = {}
    for row in rows:
        method = str(row.get("method", ""))
        if method_supported(method):
            deduped[update_row_key(row)] = row
    return [deduped[key] for key in sorted(deduped)]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")


def build_summary(
    *,
    raw_paths: list[Path],
    update_paths: list[Path],
    raw_rows: list[dict[str, Any]],
    update_rows: list[dict[str, Any]],
    output_dir: Path,
    root: Path,
) -> dict[str, Any]:
    available_ids = sorted({finite_int(row.get("seed")) for row in raw_rows if finite_int(row.get("seed")) > 0})
    folds_summary: dict[str, Any] = {}
    all_ids = sorted(set(range(1, 26)) & set(available_ids))
    for fold_id, eval_ids in FOLDS.items():
        train_ids = [value for value in all_ids if value not in set(eval_ids)]
        fold_raw = [row for row in raw_rows if finite_int(row.get("seed")) in set(train_ids)]
        fold_updates = [row for row in update_rows if finite_int(row.get("seed")) in set(train_ids)]
        fold_dir = output_dir / f"fold_{fold_id}"
        raw_path = fold_dir / f"phase5p5_repair5e5_crossfold_support_fold_{fold_id}.jsonl"
        update_path = fold_dir / f"phase5p5_repair5e5_crossfold_support_fold_{fold_id}_laur_updates.jsonl"
        write_jsonl(raw_path, fold_raw)
        write_jsonl(update_path, fold_updates)
        overlap = sorted(set(train_ids) & set(eval_ids))
        folds_summary[f"fold_{fold_id}"] = {
            "eval_instance_ids": eval_ids,
            "train_support_instance_ids": train_ids,
            "support_eval_overlap": overlap,
            "raw_rows": len(fold_raw),
            "update_rows": len(fold_updates),
            "raw_jsonl": rel(raw_path, root),
            "update_jsonl": rel(update_path, root),
            "raw_jsonl_sha256": sha256_file(raw_path),
            "update_jsonl_sha256": sha256_file(update_path),
            "method_counts": dict(Counter(str(row.get("method", "")) for row in fold_raw)),
        }
    leakage_detected = any(fold["support_eval_overlap"] for fold in folds_summary.values())
    return {
        "schema_version": "phase5p5_repair5e5_crossfold_support_v1",
        "created_at": datetime.now().isoformat(),
        "diagnostic_only": True,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "fold_definitions": {f"fold_{key}_eval": value for key, value in FOLDS.items()},
        "available_instance_ids": available_ids,
        "missing_instance_ids": [value for value in range(1, 26) if value not in set(available_ids)],
        "raw_rows": len(raw_rows),
        "update_rows": len(update_rows),
        "support_methods": sorted(SUPPORT_METHODS),
        "leakage_detected": leakage_detected,
        "inputs": {
            "raw_jsonl": [rel(path, root) for path in raw_paths],
            "raw_jsonl_sha256": {rel(path, root): sha256_file(path) for path in raw_paths},
            "update_jsonl": [rel(path, root) for path in update_paths],
            "update_jsonl_sha256": {rel(path, root): sha256_file(path) for path in update_paths},
        },
        "folds": folds_summary,
    }


def write_report(path: Path, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Phase5.5 Repair5E.5 Cross-Fold Support\n\n")
        handle.write("- diagnostic_only: `true`\n")
        handle.write("- phase5p5_allowed: `false`\n")
        handle.write("- phase6_allowed: `false`\n")
        handle.write(f"- leakage_detected: `{summary['leakage_detected']}`\n")
        handle.write(f"- available_instance_ids: `{summary['available_instance_ids']}`\n")
        handle.write(f"- missing_instance_ids: `{summary['missing_instance_ids']}`\n")
        handle.write(f"- raw_rows: `{summary['raw_rows']}`\n")
        handle.write(f"- update_rows: `{summary['update_rows']}`\n\n")
        handle.write("## Folds\n\n")
        for fold_name, fold in summary["folds"].items():
            handle.write(f"### {fold_name}\n\n")
            handle.write(f"- eval_instance_ids: `{fold['eval_instance_ids']}`\n")
            handle.write(f"- train_support_instance_ids: `{fold['train_support_instance_ids']}`\n")
            handle.write(f"- support_eval_overlap: `{fold['support_eval_overlap']}`\n")
            handle.write(f"- raw_rows: `{fold['raw_rows']}`\n")
            handle.write(f"- update_rows: `{fold['update_rows']}`\n\n")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-jsonl", type=Path, action="append", default=[])
    parser.add_argument("--update-jsonl", type=Path, action="append", default=[])
    parser.add_argument("--output-dir", type=Path, default=Path(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    raw_paths = [resolve_path(path, root) for path in (args.raw_jsonl or [Path(path) for path in DEFAULT_RAW_JSONL])]
    update_paths = [
        resolve_path(path, root) for path in (args.update_jsonl or [Path(path) for path in DEFAULT_UPDATE_JSONL])
    ]
    output_dir = resolve_path(args.output_dir, root)
    report = resolve_path(args.report, root)
    summary_json = resolve_path(args.summary_json, root)

    raw_rows = dedupe_rows([row for path in raw_paths for row in read_jsonl(path)])
    update_rows = dedupe_update_rows([row for path in update_paths for row in read_jsonl(path)])
    summary = build_summary(
        raw_paths=raw_paths,
        update_paths=update_paths,
        raw_rows=raw_rows,
        update_rows=update_rows,
        output_dir=output_dir,
        root=root,
    )
    summary_json.parent.mkdir(parents=True, exist_ok=True)
    summary_json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(report, summary)
    print(json.dumps({"summary_json": rel(summary_json, root), "report": rel(report, root)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
