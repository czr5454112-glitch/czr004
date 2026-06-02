"""Build Repair5F.2 selector context tables.

The output context tables contain only selector-available features plus join
metadata. Candidate outcomes stay in the utility tables and are never copied
into the holdout context table.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5f_selector_common import (  # noqa: E402
    ALLOWED_FEATURES,
    FORBIDDEN_FEATURES,
    METADATA_FIELDS,
    build_context_rows,
    write_csv_rows,
)


DEFAULT_SUPPORT_LONG = "outputs/tables/phase5p5_repair5f_selector_support_utility_long.csv"
DEFAULT_SUPPORT_WIDE = "outputs/tables/phase5p5_repair5f_selector_support_utility_wide.csv"
DEFAULT_SUPPORT_UPDATES = (
    "outputs/logs/phase5p5_repair5f_selector_support_probe/"
    "phase5p5_repair5f_selector_support_probe_laur_updates.jsonl"
)
DEFAULT_HOLDOUT_LONG = "outputs/tables/phase5p5_repair5f_updateparam_utility_rerun_long.csv"
DEFAULT_HOLDOUT_WIDE = "outputs/tables/phase5p5_repair5f_updateparam_utility_rerun_wide.csv"
DEFAULT_HOLDOUT_UPDATES = (
    "outputs/logs/phase5p5_repair5f_candidate_probe_rerun/"
    "phase5p5_repair5f_candidate_probe_rerun_laur_updates.jsonl"
)
DEFAULT_TRAIN_CONTEXTS = "outputs/tables/phase5p5_repair5f_selector_train_contexts.csv"
DEFAULT_HOLDOUT_CONTEXTS = "outputs/tables/phase5p5_repair5f_selector_holdout_contexts.csv"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5f_selector_training_table_report.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5f_selector_training_table_summary.json"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def resolve(path: str | Path, root: Path) -> Path:
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


def assert_inputs(paths: list[Path]) -> None:
    missing = [str(path) for path in paths if not path.exists()]
    if missing:
        raise FileNotFoundError("missing required selector training inputs: " + ", ".join(missing))


def write_report(path: Path, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Phase5.5 Repair5F Selector Training Table\n\n")
        handle.write("This is diagnostic-only selector context construction. It does not permit Phase5.5 or Phase6.\n\n")
        handle.write("## Boundary\n\n")
        handle.write("- phase5p5_allowed: `false`\n")
        handle.write("- phase6_allowed: `false`\n")
        handle.write("- solver_semantic_changes: `false`\n")
        handle.write("- final_holdout_outcomes_in_contexts: `false`\n\n")
        handle.write("## Outputs\n\n")
        handle.write(f"- train_contexts: `{summary['train_contexts_csv']}`\n")
        handle.write(f"- holdout_contexts: `{summary['holdout_contexts_csv']}`\n")
        handle.write(f"- train rows: `{summary['train_context_rows']}`\n")
        handle.write(f"- holdout rows: `{summary['holdout_context_rows']}`\n\n")
        handle.write("## Feature Policy\n\n")
        handle.write("- Selection features are numeric case/runtime features only.\n")
        handle.write("- `seed` and `scen` are retained only as join metadata, not decision features.\n")
        handle.write("- `map_family` is retained only for diagnostics and group reporting.\n")
        handle.write("- Holdout candidate outcomes and holdout best-candidate fields are excluded.\n\n")
        handle.write("Allowed decision features:\n\n")
        for name in summary["allowed_feature_names"]:
            handle.write(f"- `{name}`\n")
        handle.write("\nForbidden leakage fields:\n\n")
        for name in summary["forbidden_feature_names"]:
            handle.write(f"- `{name}`\n")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--support-long-csv", type=Path, default=Path(DEFAULT_SUPPORT_LONG))
    parser.add_argument("--support-wide-csv", type=Path, default=Path(DEFAULT_SUPPORT_WIDE))
    parser.add_argument("--support-laur-updates-jsonl", type=Path, default=Path(DEFAULT_SUPPORT_UPDATES))
    parser.add_argument("--holdout-long-csv", type=Path, default=Path(DEFAULT_HOLDOUT_LONG))
    parser.add_argument("--holdout-wide-csv", type=Path, default=Path(DEFAULT_HOLDOUT_WIDE))
    parser.add_argument("--holdout-laur-updates-jsonl", type=Path, default=Path(DEFAULT_HOLDOUT_UPDATES))
    parser.add_argument("--train-contexts-csv", type=Path, default=Path(DEFAULT_TRAIN_CONTEXTS))
    parser.add_argument("--holdout-contexts-csv", type=Path, default=Path(DEFAULT_HOLDOUT_CONTEXTS))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    support_long = resolve(args.support_long_csv, root)
    support_wide = resolve(args.support_wide_csv, root)
    support_updates = resolve(args.support_laur_updates_jsonl, root)
    holdout_long = resolve(args.holdout_long_csv, root)
    holdout_wide = resolve(args.holdout_wide_csv, root)
    holdout_updates = resolve(args.holdout_laur_updates_jsonl, root)
    train_contexts_csv = resolve(args.train_contexts_csv, root)
    holdout_contexts_csv = resolve(args.holdout_contexts_csv, root)
    report = resolve(args.report, root)
    summary_json = resolve(args.summary_json, root)

    assert_inputs([support_long, support_wide, support_updates, holdout_long, holdout_wide, holdout_updates])

    train_rows = build_context_rows(
        utility_wide_csv=support_wide,
        update_log_jsonl=support_updates,
        split_name="support_train",
        feature_names=ALLOWED_FEATURES,
    )
    holdout_rows = build_context_rows(
        utility_wide_csv=holdout_wide,
        update_log_jsonl=holdout_updates,
        split_name="final_holdout",
        feature_names=ALLOWED_FEATURES,
    )
    fields = [*METADATA_FIELDS, *[name for name in ALLOWED_FEATURES if name not in METADATA_FIELDS]]
    write_csv_rows(train_contexts_csv, train_rows, fields)
    write_csv_rows(holdout_contexts_csv, holdout_rows, fields)

    train_cases = {(row["map"], int(row["agents"]), int(row["seed"])) for row in train_rows}
    holdout_cases = {(row["map"], int(row["agents"]), int(row["seed"])) for row in holdout_rows}
    overlap = sorted(train_cases & holdout_cases)

    summary = {
        "schema_version": "phase5p5_repair5f_selector_training_table_v1",
        "created_at": datetime.now().isoformat(),
        "branch": git_value(["branch", "--show-current"], root),
        "commit": git_value(["rev-parse", "--short", "HEAD"], root),
        "dirty": dirty_state(root),
        "diagnostic_only": True,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "solver_semantic_changes": False,
        "support_long_csv": str(support_long),
        "support_wide_csv": str(support_wide),
        "support_laur_updates_jsonl": str(support_updates),
        "holdout_long_csv": str(holdout_long),
        "holdout_wide_csv": str(holdout_wide),
        "holdout_laur_updates_jsonl": str(holdout_updates),
        "train_contexts_csv": str(train_contexts_csv),
        "holdout_contexts_csv": str(holdout_contexts_csv),
        "report": str(report),
        "summary_json": str(summary_json),
        "train_context_rows": len(train_rows),
        "holdout_context_rows": len(holdout_rows),
        "train_feature_available_rows": sum(1 for row in train_rows if row["source_feature_available"]),
        "holdout_feature_available_rows": sum(1 for row in holdout_rows if row["source_feature_available"]),
        "support_final_overlap_count": len(overlap),
        "support_final_overlap_examples": [
            {"map": item[0], "agents": item[1], "seed": item[2]} for item in overlap[:20]
        ],
        "allowed_feature_names": ALLOWED_FEATURES,
        "metadata_fields_not_decision_features": METADATA_FIELDS,
        "forbidden_feature_names": FORBIDDEN_FEATURES,
        "final_holdout_outcomes_in_contexts": False,
        "feature_based_selection_vs_exact_recovery": (
            "The selector feature list excludes seed/scen/instance identity. map_family is metadata only; "
            "agents and map geometry/runtime summaries are permitted features."
        ),
    }
    summary_json.parent.mkdir(parents=True, exist_ok=True)
    summary_json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(report, summary)
    print(json.dumps({"train_contexts": str(train_contexts_csv), "holdout_contexts": str(holdout_contexts_csv)}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
