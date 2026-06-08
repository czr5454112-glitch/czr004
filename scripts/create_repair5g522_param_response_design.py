"""Create the deterministic G5.22 parameter response-surface design."""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter, OrderedDict, defaultdict
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g522_common import (  # noqa: E402
    CandidateParams,
    G522_CLOSED_CLAIMS,
    G522_DESIGN_REPORT,
    G522_DESIGN_SUMMARY,
    G522_GEOMETRY_CSV,
    G522_RAW_POOL_CSV,
    G522_RESPONSE_DESIGN_CSV,
    boolish,
    candidate_param_dict,
    candidate_params,
    clamp_params,
    csv_number,
    finite_number,
    g518_retained_candidate_ids,
    g522_candidate_id,
    old14_candidate_ids,
    param_distance,
    params_fingerprint,
    read_rows,
    repo_root,
    selected_g521_candidate_ids,
    write_json_file,
    write_rows,
    write_text_file,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-pool-csv", type=Path, default=Path(G522_RAW_POOL_CSV))
    parser.add_argument("--design-csv", type=Path, default=Path(G522_RESPONSE_DESIGN_CSV))
    parser.add_argument("--geometry-csv", type=Path, default=Path(G522_GEOMETRY_CSV))
    parser.add_argument("--report", type=Path, default=Path(G522_DESIGN_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(G522_DESIGN_SUMMARY))
    return parser.parse_args(argv)


def add_raw(rows: OrderedDict[str, dict[str, Any]], *, region: str, family: str, params: CandidateParams, purpose: str, source: str = "") -> None:
    params = clamp_params(params)
    candidate = g522_candidate_id(params)
    if candidate in rows:
        return
    rows[candidate] = {
        "candidate_id": candidate,
        "candidate_region": region,
        "candidate_family": family,
        "candidate_purpose": purpose,
        "source_candidate": source,
        "candidate_fingerprint": params_fingerprint(params),
        "raw_pool_selected": False,
        "selected_for_execution": False,
        "include_in_probe": False,
        **candidate_param_dict(candidate),
        **G522_CLOSED_CLAIMS,
    }


def raw_pool() -> list[dict[str, Any]]:
    rows: OrderedDict[str, dict[str, Any]] = OrderedDict()
    retained = g518_retained_candidate_ids(limit=8)
    for ref in retained:
        base = candidate_params(ref)
        if base is None:
            continue
        for dc in [-0.15, 0.0, 0.15]:
            for db in [-0.10, 0.15, 0.35]:
                for dw in [-0.20, -0.05, 0.10]:
                    add_raw(
                        rows,
                        region="A_g518_winner_neighborhood",
                        family="winner_neighborhood",
                        source=ref,
                        params=CandidateParams(
                            base.alpha_cong_committed + dc,
                            base.alpha_cong_blocked + db,
                            1.0,
                            base.alpha_flow_wait_or_nonprogress + dw,
                            min(max(base.rho_cong + (-0.02 if db > 0 else 0.0), 0.88), 1.00),
                            min(max(base.rho_flow, 0.90), 1.02),
                            min(max(base.flow_shield_beta + (0.10 if dw > 0 else -0.05), 0.25), 0.70),
                            min(max(base.max_flow_shield + (0.15 if db > 0 else 0.0), 0.50), 1.00),
                            False,
                        ),
                        purpose="local response around recurrent G5.18 winner",
                    )
    for b in [1.15, 1.25, 1.35, 1.45]:
        for w in [0.30, 0.40, 0.50, 0.60]:
            for beta in [0.25, 0.30, 0.35]:
                for max_shield in [0.50, 0.65, 0.80]:
                    add_raw(
                        rows,
                        region="B_static_recovery_feasibility",
                        family="feasibility_oriented",
                        params=CandidateParams(1.00, b, 1.00, w, 0.92, 0.98, beta, max_shield, False),
                        purpose="static-recovery low-risk feasibility variant",
                    )
    for c in [1.20, 1.30, 1.40]:
        for b in [1.55, 1.70, 1.85]:
            for w in [0.75, 0.90, 1.05]:
                for beta in [0.55, 0.65, 0.75]:
                    add_raw(
                        rows,
                        region="C_risk_boundary",
                        family="risk_boundary",
                        params=CandidateParams(c, b, 1.05, w, 0.90, 0.95, beta, 0.90, False),
                        purpose="deliberate high-block/high-beta risk-boundary label",
                    )
    # Deterministic low-discrepancy style coverage.
    lows = [0.80, 1.15, 0.75, 0.30, 0.88, 0.90, 0.25, 0.50]
    highs = [1.30, 1.75, 1.20, 0.80, 1.00, 1.02, 0.70, 1.00]
    primes = [2, 3, 5, 7, 11, 13, 17, 19]
    for i in range(128):
        vals = []
        for low, high, prime in zip(lows, highs, primes):
            frac = ((i + 1) * prime % 97) / 96.0
            vals.append(low + (high - low) * frac)
        add_raw(
            rows,
            region="D_fractional_coverage",
            family="orthogonal_coverage",
            params=CandidateParams(*vals, False),
            purpose="deterministic fractional/low-discrepancy coverage",
        )
    return list(rows.values())


def nearest(candidate: str, refs: list[str]) -> tuple[str, float]:
    params = candidate_params(candidate)
    best = ("", math.inf)
    for ref in refs:
        distance = param_distance(params, candidate_params(ref))
        if distance < best[1] or (distance == best[1] and ref < best[0]):
            best = (ref, distance)
    return best


def annotate_geometry(rows: list[dict[str, Any]], old14: list[str], g518: list[str], g521: list[str]) -> list[dict[str, Any]]:
    out = []
    for row in rows:
        candidate = str(row["candidate_id"])
        n_g518, d_g518 = nearest(candidate, g518)
        n_old, d_old = nearest(candidate, old14)
        n_g521, d_g521 = nearest(candidate, g521)
        annotated = {
            **row,
            "nearest_g518_candidate": n_g518,
            "nearest_g518_distance": csv_number(d_g518),
            "nearest_old14_candidate": n_old,
            "nearest_old14_distance": csv_number(d_old),
            "nearest_g521_candidate": n_g521,
            "nearest_g521_distance": csv_number(d_g521),
            "exact_duplicate_of_retained_g518": d_g518 == 0.0,
            "exact_duplicate_of_old14": d_old == 0.0,
            "exact_duplicate_of_g521": d_g521 == 0.0,
        }
        out.append(annotated)
    return out


def select_g522(pool: list[dict[str, Any]], limit: int = 48) -> list[dict[str, Any]]:
    targets = {
        "A_g518_winner_neighborhood": 12,
        "B_static_recovery_feasibility": 12,
        "C_risk_boundary": 8,
        "D_fractional_coverage": 16,
    }
    selected = []
    used_fingerprints = set()
    for region, cap in targets.items():
        region_rows = [
            row for row in pool
            if row.get("candidate_region") == region
            and not boolish(row.get("exact_duplicate_of_retained_g518"))
            and str(row.get("candidate_fingerprint")) not in used_fingerprints
        ]
        ranked = sorted(
            region_rows,
            key=lambda row: (
                -finite_number(row.get("nearest_g518_distance"), 0.0) if region == "D_fractional_coverage" else finite_number(row.get("nearest_g518_distance"), math.inf),
                boolish(row.get("exact_duplicate_of_g521")),
                str(row.get("candidate_id", "")),
            ),
        )
        for row in ranked:
            fp = str(row.get("candidate_fingerprint", ""))
            if fp in used_fingerprints:
                continue
            used_fingerprints.add(fp)
            selected.append(row)
            if sum(1 for item in selected if item.get("candidate_region") == region) >= cap:
                break
    for index, row in enumerate(selected[:limit]):
        row["raw_pool_selected"] = True
        row["selected_for_execution"] = True
        row["include_in_probe"] = True
        row["selection_rank"] = index + 1
    return selected[:limit]


def control_rows(old14: list[str], g518: list[str], g521: list[str]) -> list[dict[str, Any]]:
    rows = []
    for role, candidates, include in [
        ("old14", old14, True),
        ("g518_retained", g518, True),
        ("g521_previous_wave", g521, False),
    ]:
        for candidate in candidates:
            rows.append(
                {
                    "candidate_id": candidate,
                    "candidate_region": role,
                    "candidate_family": role,
                    "candidate_purpose": "control" if include else "previous-wave analysis-only comparison",
                    "candidate_source": role,
                    "candidate_fingerprint": params_fingerprint(candidate_params(candidate)),
                    "raw_pool_selected": False,
                    "selected_for_execution": include,
                    "include_in_probe": include,
                    "selection_rank": "",
                    **candidate_param_dict(candidate),
                    **G522_CLOSED_CLAIMS,
                }
            )
    return rows


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    old14 = old14_candidate_ids(root)
    g518 = g518_retained_candidate_ids(limit=8)
    g521 = selected_g521_candidate_ids()
    pool = annotate_geometry(raw_pool(), old14, g518, g521)
    selected = select_g522(pool, limit=48)
    selected_ids = {str(row["candidate_id"]) for row in selected}
    for row in pool:
        if str(row["candidate_id"]) in selected_ids:
            row["raw_pool_selected"] = True
            row["selected_for_execution"] = True
            row["include_in_probe"] = True
    design = control_rows(old14, g518, g521) + selected
    geometry = [row for row in pool if str(row.get("candidate_id", "")) in selected_ids]
    counts = Counter(str(row.get("candidate_region", "")) for row in selected)
    raw_fps = [str(row.get("candidate_fingerprint", "")) for row in pool]
    selected_fps = [str(row.get("candidate_fingerprint", "")) for row in selected]
    gates = {
        "old14_count_eq_14": len(old14) == 14,
        "g518_retained_count_eq_8": len(g518) == 8,
        "g521_selected_count_eq_16": len(g521) == 16,
        "raw_pool_count_ge_240": len(pool) >= 240,
        "selected_g522_count_le_48": len(selected) <= 48,
        "selected_g522_count_eq_48": len(selected) == 48,
        "raw_method_string_dedup": len({str(row.get("candidate_id", "")) for row in pool}) == len(pool),
        "selected_fingerprint_dedup": len(set(selected_fps)) == len(selected_fps),
        "no_selected_exact_duplicate_of_g518": not any(boolish(row.get("exact_duplicate_of_retained_g518")) for row in selected),
        "probe_candidate_count_le_70": sum(1 for row in design if boolish(row.get("include_in_probe"))) <= 70,
        "g521_analysis_only": all(not boolish(row.get("include_in_probe")) for row in design if row.get("candidate_region") == "g521_previous_wave"),
    }
    decision = "param_response_design_passed_continue_adapter" if all(gates.values()) else "param_response_design_failed"
    summary = {
        "schema_version": "phase5p5_repair5g522_param_response_design_summary_v1",
        "decision": decision,
        "raw_pool_count": len(pool),
        "raw_unique_fingerprint_count": len(set(raw_fps)),
        "selected_g522_candidate_count": len(selected),
        "old14_candidate_count": len(old14),
        "g518_retained_candidate_count": len(g518),
        "g521_previous_wave_candidate_count": len(g521),
        "probe_candidate_count": sum(1 for row in design if boolish(row.get("include_in_probe"))),
        "selected_region_counts": dict(sorted(counts.items())),
        "g521_candidates_analysis_only": True,
        "selection_uses_g522_solver_outcomes": False,
        "gates": gates,
        **G522_CLOSED_CLAIMS,
    }
    write_rows(args.raw_pool_csv, pool)
    write_rows(args.design_csv, design)
    write_rows(args.geometry_csv, geometry)
    write_json_file(args.summary_json, summary)
    write_text_file(
        args.report,
        "# Repair5G.5.22 Parameter Response Design\n\n"
        f"- decision: `{decision}`\n"
        f"- raw_pool_count: `{len(pool)}`\n"
        f"- selected_g522_candidate_count: `{len(selected)}`\n"
        f"- old14_candidate_count: `{len(old14)}`\n"
        f"- g518_retained_candidate_count: `{len(g518)}`\n"
        f"- g521_previous_wave_candidate_count: `{len(g521)}`\n"
        f"- probe_candidate_count: `{summary['probe_candidate_count']}`\n"
        f"- selected_region_counts: `{dict(sorted(counts.items()))}`\n"
        f"- gates: `{gates}`\n\n"
        "G5.21 candidates are retained as analysis-only previous-wave controls. The probe set is old14 + retained G5.18 + selected G5.22 response-surface candidates.\n",
    )
    print(json.dumps({"decision": decision, "raw_pool_count": len(pool), "selected_g522_candidate_count": len(selected)}))
    return 0 if decision != "param_response_design_failed" else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
