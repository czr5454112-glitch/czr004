from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gcst.label_v52_set import (  # noqa: E402
    candidate_manifest_rows,
    context_dataset_sha256,
    context_manifest_row,
    contexts_from_groups,
    label_v52_summary,
)
from gcst.real_label_graph_dataset import DEFAULT_CONTEXT_DIR, G560_TRAINING_ROWS, load_label_groups  # noqa: E402
from gcst.scaling_dataset import (  # noqa: E402
    assert_split_hashes_disjoint,
    fixed_validation_ids,
    make_grouped_split_manifest,
    nested_stratified_subsets,
    validation_manifest_sha256,
)


ROUND = "phase5p5_repair5g563"
SUMMARY_JSON = Path(f"outputs/reports/{ROUND}_labelv52_set_dataset_summary.json")
CONTEXTS_CSV = Path(f"outputs/tables/{ROUND}_labelv52_context_manifest.csv")
CANDIDATES_CSV = Path(f"outputs/tables/{ROUND}_labelv52_candidate_manifest.csv")
SPLIT_CSV = Path(f"outputs/tables/{ROUND}_grouped_split_manifest.csv")
SCALING_JSON = Path(f"outputs/reports/{ROUND}_nested_scaling_manifest.json")


def resolve(path: str | Path) -> Path:
    p = Path(path)
    return p if p.is_absolute() else ROOT / p


def write_json(path: str | Path, data: dict[str, Any]) -> None:
    p = resolve(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_rows(path: str | Path, rows: list[dict[str, Any]]) -> None:
    p = resolve(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with p.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build G5.63 Label-v5.2 set-valued dataset artifacts.")
    parser.add_argument("--rows-path", type=Path, default=G560_TRAINING_ROWS)
    parser.add_argument("--context-dir", type=Path, default=DEFAULT_CONTEXT_DIR)
    parser.add_argument("--max-contexts", type=int, default=1000)
    parser.add_argument("--quality-margin", type=float, default=0.0)
    parser.add_argument("--min-verified-coverage", type=int, default=4)
    parser.add_argument("--seed", type=int, default=563)
    parser.add_argument("--sizes", default="64,128,256,512,1000")
    args = parser.parse_args(argv)

    groups = load_label_groups(resolve(args.rows_path), resolve(args.context_dir), max_contexts=args.max_contexts)
    if not groups:
        raise SystemExit("no Label-v5.1 groups with local scenario files available")
    contexts = contexts_from_groups(
        groups,
        quality_margin=args.quality_margin,
        min_verified_coverage=args.min_verified_coverage,
    )
    context_rows = [context_manifest_row(context) for context in contexts]
    candidate_rows = [row for context in contexts for row in candidate_manifest_rows(context)]
    split_rows = make_grouped_split_manifest(context_rows, seed=args.seed)
    assert_split_hashes_disjoint(split_rows)
    train_rows = [row for row in split_rows if row["g563_split"] == "train"]
    sizes = [int(token) for token in args.sizes.split(",") if token.strip()]
    nested = nested_stratified_subsets(train_rows, sizes, seed=args.seed)
    validation_ids = fixed_validation_ids(split_rows)
    scaling_manifest = {
        "schema_version": f"{ROUND}_nested_scaling_manifest_v1",
        "seed": args.seed,
        "sizes": sorted(nested),
        "subsets": {str(size): ids for size, ids in nested.items()},
        "nested": all(nested[a] == nested[b][: len(nested[a])] for a, b in zip(sorted(nested), sorted(nested)[1:])),
        "fixed_validation_ids": validation_ids,
        "fixed_validation_manifest_sha256": validation_manifest_sha256(validation_ids),
        "unit": "independent_context",
    }
    summary = label_v52_summary(contexts)
    summary.update(
        {
            "schema_version": f"{ROUND}_labelv52_set_dataset_summary_v1",
            "decision": "g563_labelv52_set_dataset_ready",
            "dataset_sha256": context_dataset_sha256(contexts),
            "rows_path": str(resolve(args.rows_path)).replace("\\", "/"),
            "context_dir": str(resolve(args.context_dir)).replace("\\", "/"),
            "quality_margin": args.quality_margin,
            "min_verified_coverage": args.min_verified_coverage,
            "grouped_split_hashes_disjoint": True,
            "fixed_validation_manifest_sha256": scaling_manifest["fixed_validation_manifest_sha256"],
            "nested_scaling_subsets": scaling_manifest["nested"],
        }
    )
    write_rows(CONTEXTS_CSV, context_rows)
    write_rows(CANDIDATES_CSV, candidate_rows)
    write_rows(SPLIT_CSV, split_rows)
    write_json(SCALING_JSON, scaling_manifest)
    write_json(SUMMARY_JSON, summary)
    print(json.dumps({"decision": summary["decision"], "contexts": summary["contexts"], "candidate_rows": summary["candidate_rows"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
