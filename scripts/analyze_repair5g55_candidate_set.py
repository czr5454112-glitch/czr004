"""Analyze the Repair5G.5.5 candidate-set audit."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g55_common import (  # noqa: E402
    G55_BASE_CANDIDATES,
    compact_json_bool,
    read_csv_rows,
    repo_root,
    resolve,
    write_csv_rows,
    write_json,
    write_text,
)


DEFAULT_CSV = "outputs/tables/phase5p5_repair5g55_candidate_set.csv"
DEFAULT_COMPONENTS = "outputs/tables/phase5p5_repair5g55_candidate_set_by_component.csv"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g55_candidate_set_audit.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g55_candidate_set_audit_summary.json"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-set-csv", type=Path, default=Path(DEFAULT_CSV))
    parser.add_argument("--by-component-csv", type=Path, default=Path(DEFAULT_COMPONENTS))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    rows = read_csv_rows(resolve(args.candidate_set_csv, root))
    present = {str(row.get("candidate_id", "")) for row in rows}
    missing_base = [candidate for candidate in G55_BASE_CANDIDATES if candidate not in present]
    unsupported = [str(row.get("candidate_id", "")) for row in rows if not compact_json_bool(row.get("registry_supported"))]
    component_counts = Counter(str(row.get("component", "")) for row in rows)
    component_rows = [
        {
            "component": component,
            "candidate_rows": count,
            "default_scaled_label_rows": sum(
                1
                for row in rows
                if str(row.get("component", "")) == component
                and compact_json_bool(row.get("include_in_default_scaled_labels"))
            ),
            "local_lattice_rows": sum(
                1
                for row in rows
                if str(row.get("component", "")) == component
                and compact_json_bool(row.get("include_in_local_lattice"))
            ),
        }
        for component, count in sorted(component_counts.items())
    ]
    write_csv_rows(resolve(args.by_component_csv, root), component_rows)
    gates = {
        "candidate_set_rows_gt_0": len(rows) > 0,
        "base_candidates_present": not missing_base,
        "unsupported_candidate_count": len(unsupported),
        "default_candidate_count": sum(1 for row in rows if compact_json_bool(row.get("include_in_default_scaled_labels"))),
        "local_lattice_supported": not any(
            (not compact_json_bool(row.get("registry_supported"))) and compact_json_bool(row.get("include_in_local_lattice"))
            for row in rows
        ),
        "candidate_space_not_exploded": len(rows) <= 32,
    }
    gates["candidate_set_audit_passed"] = (
        gates["candidate_set_rows_gt_0"]
        and gates["base_candidates_present"]
        and gates["unsupported_candidate_count"] == 0
        and gates["local_lattice_supported"]
        and gates["candidate_space_not_exploded"]
    )
    summary = {
        "schema_version": "phase5p5_repair5g55_candidate_set_audit_summary_v1",
        "candidate_rows": len(rows),
        "missing_base_candidates": missing_base,
        "unsupported_candidates": unsupported,
        "component_counts": dict(sorted(component_counts.items())),
        "gates": gates,
        "decision": "candidate_set_supported" if gates["candidate_set_audit_passed"] else "candidate_set_audit_failed",
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "aaai_ready": False,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.5 Candidate-Set Audit\n\n"
        f"- candidate_rows: `{len(rows)}`\n"
        f"- missing_base_candidates: `{json.dumps(missing_base)}`\n"
        f"- unsupported_candidates: `{json.dumps(unsupported)}`\n"
        f"- candidate_set_audit_passed: `{gates['candidate_set_audit_passed']}`\n"
        f"- decision: `{summary['decision']}`\n\n"
        "The default label-scaling candidate set remains compact; local lattice rows are audited for later expansion only.\n",
    )
    print(json.dumps({"candidate_set_audit_passed": gates["candidate_set_audit_passed"], "candidate_rows": len(rows)}))
    return 0 if gates["candidate_set_audit_passed"] else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
