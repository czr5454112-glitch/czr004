from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gcst.real_label_graph_dataset import DEFAULT_CONTEXT_DIR, G560_TRAINING_ROWS, load_label_groups  # noqa: E402


ROUND = "phase5p5_repair5g565"
REPORTS = ROOT / "outputs/reports"
TABLES = ROOT / "outputs/tables"
MIN_PHYSICAL_MAP_HASHES = 32
MIN_MAP_FAMILIES = 10
MIN_AGENT_COUNT_TIERS = 4
MIN_BUDGET_TIERS = 4


def resolve(path: str | Path) -> Path:
    p = Path(path)
    return p if p.is_absolute() else ROOT / p


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def expansion_gate(rows: list[dict[str, Any]], target_contexts: int) -> dict[str, Any]:
    physical_hashes = {
        str(row.get("physical_map_sha256") or row.get("g560_physical_map_sha256") or "")
        for row in rows
        if row.get("physical_map_sha256") or row.get("g560_physical_map_sha256")
    }
    map_families = {str(row.get("map_family") or "") for row in rows if row.get("map_family")}
    agent_count_tiers = {str(row.get("agent_count") or row.get("agents") or "") for row in rows if row.get("agent_count") or row.get("agents")}
    budget_tiers = {str(row.get("budget_ms") or row.get("nominal_budget_ms") or "") for row in rows if row.get("budget_ms") or row.get("nominal_budget_ms")}
    od_regimes = {str(row.get("start_goal_regime") or row.get("od_regime") or "") for row in rows if row.get("start_goal_regime") or row.get("od_regime")}
    target_ok = len(rows) >= int(target_contexts)
    physical_ok = len(physical_hashes) >= MIN_PHYSICAL_MAP_HASHES
    family_ok = len(map_families) >= MIN_MAP_FAMILIES
    agent_ok = len(agent_count_tiers) >= MIN_AGENT_COUNT_TIERS
    budget_ok = len(budget_tiers) >= MIN_BUDGET_TIERS
    block_reasons: list[str] = []
    if not target_ok:
        block_reasons.append("insufficient_independent_contexts")
    if not physical_ok:
        block_reasons.append("insufficient_physical_map_hashes")
    if not family_ok:
        block_reasons.append("insufficient_map_families")
    if not agent_ok:
        block_reasons.append("insufficient_agent_count_tiers")
    if not budget_ok:
        block_reasons.append("insufficient_budget_tiers")
    return {
        "ready": bool(target_ok and physical_ok and family_ok and agent_ok and budget_ok),
        "target_contexts": int(target_contexts),
        "manifest_rows": len(rows),
        "unique_physical_map_hashes": len(physical_hashes),
        "unique_map_families": len(map_families),
        "unique_agent_count_tiers": len(agent_count_tiers),
        "unique_budget_tiers": len(budget_tiers),
        "unique_od_regimes_recorded": len(od_regimes),
        "min_physical_map_hashes": MIN_PHYSICAL_MAP_HASHES,
        "min_map_families": MIN_MAP_FAMILIES,
        "min_agent_count_tiers": MIN_AGENT_COUNT_TIERS,
        "min_budget_tiers": MIN_BUDGET_TIERS,
        "min_target_satisfied": target_ok,
        "min_physical_map_hashes_satisfied": physical_ok,
        "min_map_families_satisfied": family_ok,
        "min_agent_count_tiers_satisfied": agent_ok,
        "min_budget_tiers_satisfied": budget_ok,
        "block_reasons": block_reasons,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate a conditional G5.65 context-expansion manifest.")
    parser.add_argument("--rows-path", type=Path, default=G560_TRAINING_ROWS)
    parser.add_argument("--context-dir", type=Path, default=DEFAULT_CONTEXT_DIR)
    parser.add_argument("--target-contexts", type=int, default=5000)
    parser.add_argument("--max-manifest-contexts", type=int, default=1000)
    args = parser.parse_args(argv)

    scaling = read_json(REPORTS / f"{ROUND}_current_bank_scaling_summary.json")
    fresh = read_json(REPORTS / f"{ROUND}_fresh_solver_panel_summary.json")
    alpha = read_json(REPORTS / f"{ROUND}_alpha_response_summary.json")
    supported = scaling.get("decision") == "g565_current_bank_rich_scaling_supported"
    transfer_positive = fresh.get("decision") == "g565_fresh_solver_transfer_positive"
    alpha_repaired = (
        alpha.get("decision") == "g565_alpha_calibration_repaired_tail"
        and alpha.get("fresh_fixed_panel_reran_after_alpha") is True
        and alpha.get("alpha_trust_head_trained") is True
    )
    trigger = bool(supported or transfer_positive or alpha_repaired)
    manifest_limit = max(int(args.target_contexts), int(args.max_manifest_contexts)) if trigger else 0
    groups = load_label_groups(resolve(args.rows_path), resolve(args.context_dir), max_contexts=manifest_limit)
    rows = []
    if trigger:
        for idx, group in enumerate(groups):
            rows.append(
                {
                    "expansion_row_id": f"g565_expand_{idx:06d}",
                    "g560_evaluation_uid": group.evaluation_uid,
                    "split": group.split,
                    "map": group.map,
                    "map_family": group.map_family,
                    "agent_count": group.agent_count,
                    "budget_ms": group.budget_ms,
                    "agent_density": group.rows[0].get("agent_density", ""),
                    "start_goal_regime": group.rows[0].get("start_goal_regime", ""),
                    "physical_map_sha256": group.physical_map_sha256_expected,
                    "scenario_sha256": group.scenario_sha256_expected,
                    "selected_for_expanded_training": True,
                }
            )
    gate = expansion_gate(rows, args.target_contexts)
    ready = bool(trigger and gate["ready"])
    summary = {
        "schema_version": f"{ROUND}_context_expansion_summary_v1",
        "decision": (
            "g565_context_expansion_manifest_ready"
            if ready
            else "g565_context_expansion_blocked_incomplete_scope"
            if trigger
            else "g565_context_expansion_not_triggered"
        ),
        "scaling_decision": scaling.get("decision"),
        "fresh_solver_decision": fresh.get("decision"),
        "alpha_response_decision": alpha.get("decision"),
        "alpha_trust_head_trained": alpha.get("alpha_trust_head_trained"),
        "fresh_fixed_panel_reran_after_alpha": alpha.get("fresh_fixed_panel_reran_after_alpha"),
        "trigger_rule": "scaling_supported OR fresh_transfer_positive OR fully_calibrated_alpha_repair",
        "expansion_triggered": trigger,
        "available_contexts_loaded": len(groups),
        **gate,
    }
    write_rows(TABLES / f"{ROUND}_context_expansion_manifest.csv", rows)
    write_json(REPORTS / f"{ROUND}_context_expansion_summary.json", summary)
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
