"""Create the Repair5G.4 offline contextual flow-shield selector dataset."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from create_repair5g3_learning_bridge_dataset import (  # noqa: E402
    ALLOWED_FEATURES,
    FORBIDDEN_FEATURES,
    build_features,
    case_key,
    normalize_paired,
)
from repair5g3_common import (  # noqa: E402
    git_value,
    load_json,
    number,
    read_csv_rows,
    read_jsonl,
    repo_root,
    resolve,
    write_csv_rows,
    write_json,
)


DEFAULT_OUTPUT = "outputs/tables/phase5p5_repair5g4_learning_bridge_dataset.csv"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g4_learning_bridge_dataset_report.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g4_learning_bridge_dataset_summary.json"
DEFAULT_AUTOPSY = "outputs/reports/phase5p5_repair5g3_protocol_failure_autopsy_summary.json"
DEFAULT_REPRODUCER = "outputs/reports/phase5p5_repair5g31_control_parity_reproducer_summary.json"
DEFAULT_POLICY = "outputs/reports/phase5p5_repair5g31_parity_policy_summary.json"

PAIRED_INPUTS = [
    ("g2_support", "outputs/tables/phase5p5_repair5g2_support_utility_long.csv"),
    ("g1_dev", "outputs/tables/phase5p5_repair5g1_dev_utility_long.csv"),
    ("g2_final_observed", "outputs/tables/phase5p5_repair5g2_fresh_final_eval_paired.csv"),
    ("g3_broader_observed", "outputs/tables/phase5p5_repair5g3_broader_validation_paired.csv"),
]

RAW_INPUTS = [
    "outputs/logs/phase5p5_repair5g2_support_probe/phase5p5_repair5g2_support_probe.jsonl",
    "outputs/logs/phase5p5_repair5g1_dev_probe/phase5p5_repair5g1_dev_probe.jsonl",
    "outputs/logs/phase5p5_repair5g2_fresh_final_eval/phase5p5_repair5g2_fresh_final_eval.jsonl",
    "outputs/logs/phase5p5_repair5g3_broader_validation/phase5p5_repair5g3_broader_validation.jsonl",
]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-csv", type=Path, default=Path(DEFAULT_OUTPUT))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    parser.add_argument("--autopsy-summary-json", type=Path, default=Path(DEFAULT_AUTOPSY))
    parser.add_argument("--reproducer-summary-json", type=Path, default=Path(DEFAULT_REPRODUCER))
    parser.add_argument("--parity-policy-summary-json", type=Path, default=Path(DEFAULT_POLICY))
    parser.add_argument("--ignore-protocol-closure", action="store_true")
    return parser.parse_args(argv)


def protocol_closed(root: Path, args: argparse.Namespace) -> bool:
    autopsy = load_json(resolve(args.autopsy_summary_json, root))
    reproducer = load_json(resolve(args.reproducer_summary_json, root))
    policy = load_json(resolve(args.parity_policy_summary_json, root))
    return bool(
        autopsy.get("ready_for_control_parity_reproducer")
        and reproducer.get("protocol_reproducer_passed")
        and policy.get("gates", {}).get("parity_policy_accepted")
    )


def split_name(source: str, seed: int) -> str:
    if source == "g3_broader_observed" and 66 <= seed <= 85:
        return "g3_broader_observed_train"
    if source == "g3_broader_observed" and 86 <= seed <= 105:
        return "g3_broader_observed_validation"
    return source


def raw_feature_rows(root: Path) -> dict[tuple[str, int, int], dict[str, Any]]:
    out: dict[tuple[str, int, int], dict[str, Any]] = {}
    for raw_path in RAW_INPUTS:
        for row in read_jsonl(resolve(raw_path, root)):
            if str(row.get("method")) == "lacam_star_ltm":
                out.setdefault(case_key(row), row)
    return out


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    if not args.ignore_protocol_closure and not protocol_closed(root, args):
        raise SystemExit("protocol closure has not passed; learning bridge dataset is blocked")
    raw_by_case = raw_feature_rows(root)
    paired: list[dict[str, Any]] = []
    for source, rel_path in PAIRED_INPUTS:
        path = resolve(rel_path, root)
        if path.exists():
            paired.extend(normalize_paired(row, source) for row in read_csv_rows(path))
    by_case: dict[tuple[str, int, int, str], dict[str, dict[str, Any]]] = {}
    for row in paired:
        key = (*case_key(row), split_name(str(row["split_source"]), int(row["seed"])))
        by_case.setdefault(key, {})[str(row["method"])] = row
    methods = sorted(
        {
            row["method"]
            for row in paired
            if row["method"].startswith("repair5g1_shield_")
            or row["method"].startswith("repair5g_dual_c_equiv_")
            or row["method"]
            in {
                "repair5g2_frozen_static_or_selector",
                "repair5g2_best_frozen_static_candidate",
                "repair5g2_c_equiv_best_frozen_baseline",
            }
        }
    )
    dataset: list[dict[str, Any]] = []
    for (map_name, agents, seed, split), outcomes in sorted(by_case.items()):
        useful = {method: row for method, row in outcomes.items() if method in methods}
        if not useful:
            continue
        best_method, best_row = min(useful.items(), key=lambda item: number(item[1].get("delta_ratio_vs_ltm"), math.inf))
        row = {
            "split": split,
            "map": map_name,
            "agents": agents,
            "seed_metadata_only": seed,
            "best_method_label": best_method,
            "best_delta_ratio_vs_ltm": best_row.get("delta_ratio_vs_ltm"),
            "candidate_methods": json.dumps(sorted(useful), sort_keys=True),
            "runtime_feature_approximation": True,
            **build_features(map_name, agents, raw_by_case.get((map_name, agents, seed))),
        }
        for method in methods:
            row[f"delta__{method}"] = useful.get(method, {}).get("delta_ratio_vs_ltm", "")
        dataset.append(row)
    fields = [
        "split",
        "map",
        "agents",
        "seed_metadata_only",
        "best_method_label",
        "best_delta_ratio_vs_ltm",
        "candidate_methods",
        "runtime_feature_approximation",
        *ALLOWED_FEATURES,
        *[f"delta__{method}" for method in methods],
    ]
    write_csv_rows(resolve(args.output_csv, root), dataset, fields)
    split_counts = {split: sum(1 for row in dataset if row["split"] == split) for split in sorted({row["split"] for row in dataset})}
    summary = {
        "schema_version": "phase5p5_repair5g4_learning_bridge_dataset_summary_v1",
        "created_at": __import__("datetime").datetime.now().isoformat(),
        "branch": git_value(["branch", "--show-current"], root),
        "commit": git_value(["rev-parse", "--short", "HEAD"], root),
        "dataset_csv": str(resolve(args.output_csv, root).relative_to(root)),
        "rows": len(dataset),
        "split_counts": split_counts,
        "candidate_methods": methods,
        "allowed_feature_names": ALLOWED_FEATURES,
        "forbidden_feature_names": FORBIDDEN_FEATURES,
        "uses_no_forbidden_features": True,
        "excluded_g4_clean_validation_from_training": True,
        "runtime_feature_approximation": True,
        "reserved_learning_fresh_eval": "IDs 166..205 or next untouched range",
        "diagnostic_only": True,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
    }
    write_json(resolve(args.summary_json, root), summary)
    report = resolve(args.report, root)
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(
        "# Phase5.5 Repair5G.4 Learning Bridge Dataset\n\n"
        "Offline contextual-selector dataset for bounded `UpdateLTM` parameter selection only.\n\n"
        f"- rows: `{len(dataset)}`\n"
        f"- split_counts: `{split_counts}`\n"
        "- G4 clean-validation rows used for tuning: `false`\n"
        "- forbidden runtime features used: `false`\n"
        "- phase5p5_allowed: `false`\n"
        "- phase6_allowed: `false`\n",
        encoding="utf-8",
    )
    print(json.dumps({"rows": len(dataset), "splits": split_counts}))
    return 0 if dataset else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
