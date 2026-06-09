"""Create a bounded Repair5G.5.9 goal-aware dual-channel UpdateLTM lattice."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g59_common import G59_CLOSED_STATUS, repo_root, resolve, write_csv_rows, write_json, write_text  # noqa: E402


DEFAULT_CANDIDATES = "outputs/tables/phase5p5_repair5g59_candidate_lattice.csv"
DEFAULT_JSON = "outputs/reports/phase5p5_repair5g59_candidate_lattice_candidates.json"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g59_candidate_lattice_creation_summary.json"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g59_candidate_lattice_creation.md"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-csv", type=Path, default=Path(DEFAULT_CANDIDATES))
    parser.add_argument("--candidate-json", type=Path, default=Path(DEFAULT_JSON))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    return parser.parse_args(argv)


def lattice() -> list[dict[str, object]]:
    base = [
        ("repair5g59_static_flow_shield", 1.25, 1.25, 1.0, 0.75, 0.95, 1.0, 0.35, 0.75, "static baseline"),
        ("repair5g59_additive_fallback", 1.0, 1.0, 0.0, 1.0, 1.0, 1.0, 0.0, 0.0, "additive fallback"),
        ("repair5g59_c_only_f_disabled", 1.25, 1.25, 0.0, 0.75, 0.95, 1.0, 0.0, 0.0, "C-only / F-disabled ablation"),
        ("repair5g59_light_cong_light_flow", 1.0, 1.0, 0.75, 0.75, 0.98, 1.0, 0.25, 0.50, "lighter congestion with modest flow shield"),
        ("repair5g59_block_heavy_flow_guard", 1.0, 1.5, 1.0, 0.50, 0.95, 1.0, 0.35, 0.75, "blocked-edge emphasis"),
        ("repair5g59_commit_heavy_flow_guard", 1.5, 1.0, 1.0, 0.75, 0.95, 1.0, 0.35, 0.75, "committed-edge emphasis"),
        ("repair5g59_slow_decay_high_shield", 1.25, 1.25, 1.0, 0.75, 0.98, 1.0, 0.50, 1.00, "slow decay with larger shield"),
        ("repair5g59_fast_decay_low_shield", 1.25, 1.25, 1.0, 0.75, 0.90, 1.0, 0.20, 0.50, "fast decay conservative shield"),
        ("repair5g59_wait_conservative", 1.25, 1.25, 1.0, 0.50, 0.95, 1.0, 0.35, 0.75, "lower wait/nonprogress spread"),
        ("repair5g59_wait_aggressive", 1.25, 1.25, 1.0, 1.00, 0.95, 1.0, 0.35, 0.75, "higher wait/nonprogress spread"),
        ("repair5g59_flow_decay", 1.25, 1.25, 1.0, 0.75, 0.95, 0.95, 0.35, 0.75, "decay both C and F channels"),
        ("repair5g59_high_beta_cap_safe", 1.25, 1.25, 1.0, 0.75, 0.95, 1.0, 0.60, 0.75, "higher beta but capped shield"),
        ("repair5g59_low_beta_high_cap", 1.25, 1.25, 1.0, 0.75, 0.95, 1.0, 0.20, 1.25, "lower beta with wider cap"),
        ("repair5g59_static_abstain_candidate", 1.25, 1.25, 1.0, 0.75, 0.95, 1.0, 0.35, 0.75, "static-abstain alias"),
    ]
    rows = []
    for index, (candidate_id, ac, ab, af, wait, rc, rf, beta, max_shield, note) in enumerate(base):
        rows.append(
            {
                "candidate_id": candidate_id,
                "candidate_index": index,
                "alpha_cong_committed": ac,
                "alpha_cong_blocked": ab,
                "alpha_flow_progress": af,
                "alpha_flow_wait_or_nonprogress": wait,
                "rho_cong": rc,
                "rho_flow": rf,
                "flow_shield_beta": beta,
                "max_flow_shield": max_shield,
                "static_fallback": candidate_id in {"repair5g59_static_flow_shield", "repair5g59_static_abstain_candidate"},
                "additive_fallback": candidate_id == "repair5g59_additive_fallback",
                "c_only_f_disabled": candidate_id == "repair5g59_c_only_f_disabled",
                "update_ltm_only": True,
                "forbidden_outputs": "",
                "note": note,
            }
        )
    return rows


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    rows = lattice()
    csv_path = resolve(args.candidate_csv, root)
    json_path = resolve(args.candidate_json, root)
    write_csv_rows(csv_path, rows)
    write_json(json_path, {"schema_version": "phase5p5_repair5g59_candidate_lattice_candidates_v1", "candidates": rows})
    gates = {
        "candidate_count_le_16": len(rows) <= 16,
        "update_ltm_only": all(row.get("update_ltm_only") is True for row in rows),
        "no_forbidden_outputs": all(not row.get("forbidden_outputs") for row in rows),
        "static_fallback_included": any(row.get("static_fallback") for row in rows),
        "additive_fallback_included": any(row.get("additive_fallback") for row in rows),
        "c_only_f_disabled_ablation_included": any(row.get("c_only_f_disabled") for row in rows),
    }
    summary = {
        "schema_version": "phase5p5_repair5g59_candidate_lattice_creation_summary_v1",
        "decision": "candidate_lattice_created_local_smoke_size",
        "candidate_count": len(rows),
        "candidate_csv": str(csv_path),
        "candidate_json": str(json_path),
        "gates": gates,
        **G59_CLOSED_STATUS,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.9 Candidate Lattice Creation\n\n"
        f"- candidate_count: `{len(rows)}`\n"
        f"- candidate_count_le_16: `{gates['candidate_count_le_16']}`\n"
        f"- update_ltm_only: `{gates['update_ltm_only']}`\n"
        f"- no_forbidden_outputs: `{gates['no_forbidden_outputs']}`\n\n"
        "The lattice is a bounded UpdateLTM candidate design. It does not output actions, priorities, h-values, restarts, or candidate deletions.\n",
    )
    print(json.dumps({"decision": summary["decision"], "candidate_count": len(rows)}))
    return 0 if all(gates.values()) else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
