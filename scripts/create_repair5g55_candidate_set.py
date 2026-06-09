"""Create the Repair5G.5.5 candidate set and bounded local-lattice audit."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g_candidate_registry import build_registry, direct_candidate_row  # noqa: E402
from repair5g55_common import (  # noqa: E402
    G55_BASE_CANDIDATES,
    default_candidate_list,
    load_json,
    local_lattice_candidates,
    repo_root,
    resolve,
    write_csv_rows,
    write_json,
    write_text,
)


DEFAULT_FROZEN_SPEC = "outputs/reports/phase5p5_repair5g2_frozen_selector_spec.json"
DEFAULT_SELECTOR_SPEC = (
    "artifacts/models/laur_ltm/repair5g5_contextual_flow_shield_selector/selector_spec.json"
)
DEFAULT_CSV = "outputs/tables/phase5p5_repair5g55_candidate_set.csv"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g55_candidate_set.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g55_candidate_set_summary.json"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frozen-selector-spec-json", type=Path, default=Path(DEFAULT_FROZEN_SPEC))
    parser.add_argument("--selector-spec-json", type=Path, default=Path(DEFAULT_SELECTOR_SPEC))
    parser.add_argument("--output-csv", type=Path, default=Path(DEFAULT_CSV))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    parser.add_argument("--no-local-lattice", action="store_true")
    return parser.parse_args(argv)


def candidate_row(candidate: str, registry_by_name: dict[str, object], *, source: str) -> dict[str, object]:
    registry_row = registry_by_name.get(candidate) or direct_candidate_row(candidate)
    if registry_row is None:
        return {
            "candidate_id": candidate,
            "resolved_candidate_id": "",
            "component": "unsupported",
            "candidate_source": source,
            "include_in_default_scaled_labels": candidate in G55_BASE_CANDIDATES,
            "include_in_local_lattice": candidate in set(local_lattice_candidates()),
            "registry_supported": False,
            "updateparams_hash": "",
            "goal_projection_mode": "",
            "flow_shield_beta": "",
            "max_flow_shield": "",
            "rho_cong_decay": "",
            "diagnostic_only": True,
            "phase5p5_allowed": False,
            "phase6_allowed": False,
            "aaai_ready": False,
        }
    row = registry_row.to_csv_row()  # type: ignore[attr-defined]
    return {
        "candidate_id": candidate,
        "resolved_candidate_id": row.get("canonical_candidate_id", candidate),
        "component": row.get("component", ""),
        "candidate_source": source,
        "include_in_default_scaled_labels": candidate in G55_BASE_CANDIDATES,
        "include_in_local_lattice": candidate in set(local_lattice_candidates()),
        "registry_supported": True,
        "updateparams_hash": row.get("updateparams_hash", ""),
        "goal_projection_mode": row.get("goal_projection_mode", ""),
        "flow_shield_beta": row.get("flow_shield_beta", ""),
        "max_flow_shield": row.get("max_flow_shield", ""),
        "rho_cong_decay": row.get("rho_cong_decay", ""),
        "diagnostic_only": True,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "aaai_ready": False,
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    frozen = load_json(resolve(args.frozen_selector_spec_json, root))
    selector = load_json(resolve(args.selector_spec_json, root))
    registry_rows = build_registry(frozen, selector)
    registry_by_name = {row.method_name: row for row in registry_rows}
    candidates = default_candidate_list(include_lattice=not args.no_local_lattice)
    lattice = set(local_lattice_candidates())
    rows = [
        candidate_row(
            candidate,
            registry_by_name,
            source="base_start_set" if candidate in G55_BASE_CANDIDATES else "bounded_local_lattice",
        )
        for candidate in candidates
    ]
    write_csv_rows(resolve(args.output_csv, root), rows)
    lattice_rows = [row for row in rows if row["candidate_id"] in lattice]
    unsupported = [row["candidate_id"] for row in rows if not row["registry_supported"]]
    summary = {
        "schema_version": "phase5p5_repair5g55_candidate_set_summary_v1",
        "candidate_rows": len(rows),
        "base_candidate_count": len(G55_BASE_CANDIDATES),
        "local_lattice_candidate_count": len(lattice_rows),
        "unsupported_candidates": unsupported,
        "runtime_registry_supports_local_lattice": all(row["registry_supported"] for row in lattice_rows),
        "default_scaled_label_candidate_count": sum(1 for row in rows if row["include_in_default_scaled_labels"]),
        "candidate_set_csv": str(resolve(args.output_csv, root)),
        "diagnostic_only": True,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "aaai_ready": False,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.5 Candidate Set\n\n"
        f"- candidate_rows: `{len(rows)}`\n"
        f"- base_candidate_count: `{len(G55_BASE_CANDIDATES)}`\n"
        f"- local_lattice_candidate_count: `{len(lattice_rows)}`\n"
        f"- runtime_registry_supports_local_lattice: `{summary['runtime_registry_supports_local_lattice']}`\n"
        f"- unsupported_candidates: `{json.dumps(unsupported)}`\n\n"
        "The default scaled-label run keeps the seven G5.4 candidates. The bounded lattice is audited for later expansion and is not a benchmark-tuning claim.\n",
    )
    print(json.dumps({"candidate_rows": len(rows), "unsupported_candidates": unsupported}))
    return 0 if not unsupported else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
