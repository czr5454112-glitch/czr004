"""Probe Repair5G.5.1 counterfactual UpdateLTM labels from iteration contexts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g51_common import read_csv_dicts, repo_root, resolve, write_csv_rows, write_json, write_text  # noqa: E402


DEFAULT_CONTEXTS = "outputs/tables/phase5p5_repair5g51_iteration_contexts.csv"
DEFAULT_LABELS = "outputs/tables/phase5p5_repair5g51_counterfactual_update_labels.csv"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g51_counterfactual_update_probe_report.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g51_counterfactual_update_probe_summary.json"

CANDIDATES = [
    "repair5g2_best_frozen_static_candidate",
    "repair5g2_frozen_static_or_selector",
    "repair5g_dual_c_equiv_additive",
    "repair5g2_c_equiv_best_frozen_baseline",
    "repair5g1_shield_c125_b125_w075_d095_beta0p35_max0p75",
    "repair5g1_shield_c100_b125_w075_d100_beta0p35_max0p75",
    "additive_ltm",
]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contexts-csv", type=Path, default=Path(DEFAULT_CONTEXTS))
    parser.add_argument("--labels-csv", type=Path, default=Path(DEFAULT_LABELS))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    parser.add_argument("--max-contexts", type=int, default=500)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    contexts = read_csv_dicts(resolve(args.contexts_csv, root))
    sampled = contexts[: max(0, int(args.max_contexts))]
    labels: list[dict[str, Any]] = []
    for context in sampled:
        replay_ready = str(context.get("traffic_snapshot_available", "")).lower() == "true"
        for candidate in CANDIDATES:
            labels.append(
                {
                    "context_id": context.get("context_id", ""),
                    "candidate_id": candidate,
                    "counterfactual_label_available": replay_ready,
                    "label_status": "available" if replay_ready else "unavailable_no_replay_snapshot",
                    "short_probe_delta_ratio": "",
                    "success_delta": "",
                    "leakage_safe": True,
                }
            )
    write_csv_rows(resolve(args.labels_csv, root), labels)
    coverage = sum(1 for row in labels if row["counterfactual_label_available"])
    summary = {
        "schema_version": "phase5p5_repair5g51_counterfactual_update_probe_summary_v1",
        "context_count": len(sampled),
        "candidate_count": len(CANDIDATES),
        "label_rows": len(labels),
        "available_label_rows": coverage,
        "counterfactual_labels_available": coverage > 0,
        "gap": "missing traffic_before and replayable trace-event checkpoint snapshots",
        "minimal_cpp_checkpoint_export_required": [
            "pre-update traffic map raw/flow edge state",
            "trace event list for the current iteration",
            "LtmIterationStats used by runtime feature extraction",
            "candidate UpdateParams id and applied cost audit after update",
        ],
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "aaai_ready": False,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.1 Counterfactual Update Probe\n\n"
        f"- context_count: `{len(sampled)}`\n"
        f"- label_rows: `{len(labels)}`\n"
        f"- available_label_rows: `{coverage}`\n"
        "- result: `true_counterfactual_labels_unavailable`\n\n"
        "The probe refuses to derive labels from final full-run outcomes because those labels are not causally tied "
        "to the specific pre-update context. Minimal C++ checkpoint export is required before neural selector training.\n",
    )
    print(json.dumps({"available_label_rows": coverage, "label_rows": len(labels)}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
