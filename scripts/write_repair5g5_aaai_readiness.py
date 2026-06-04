"""Write Repair5G.5 AAAI policy, readiness, decision, and paper skeleton artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g5_common import (  # noqa: E402
    DEFAULT_SELECTOR_SPEC,
    G5_RUNTIME,
    load_json,
    rel,
    repo_root,
    resolve,
    sha256_file,
    write_json,
)
from repair5g3_common import write_csv_rows  # noqa: E402


DEFAULT_G4 = "outputs/reports/phase5p5_repair5g4_clean_frozen_validation_summary.json"
DEFAULT_STRESS = "outputs/reports/phase5p5_repair5g4_time_iteration_stress_summary.json"
DEFAULT_SELECTOR_EXPORT = "outputs/reports/phase5p5_repair5g5_contextual_selector_export_summary.json"
DEFAULT_SMOKE = "outputs/reports/phase5p5_repair5g5_runtime_smoke_summary.json"
DEFAULT_FRESH = "outputs/reports/phase5p5_repair5g5_learned_runtime_fresh_eval_summary.json"
DEFAULT_BROAD = "outputs/reports/phase5p5_repair5g5_aaai_broader_validation_summary.json"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--g4-summary-json", type=Path, default=Path(DEFAULT_G4))
    parser.add_argument("--stress-summary-json", type=Path, default=Path(DEFAULT_STRESS))
    parser.add_argument("--selector-export-summary-json", type=Path, default=Path(DEFAULT_SELECTOR_EXPORT))
    parser.add_argument("--smoke-summary-json", type=Path, default=Path(DEFAULT_SMOKE))
    parser.add_argument("--fresh-summary-json", type=Path, default=Path(DEFAULT_FRESH))
    parser.add_argument("--broader-summary-json", type=Path, default=Path(DEFAULT_BROAD))
    return parser.parse_args(argv)


def status(value: bool, *, missing: bool = False) -> str:
    if missing:
        return "missing"
    return "passed" if value else "partial"


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def evidence_rows(g4: dict[str, Any], stress: dict[str, Any], export: dict[str, Any], smoke: dict[str, Any], fresh: dict[str, Any], broad: dict[str, Any]) -> list[dict[str, Any]]:
    smoke_gates = smoke.get("gates", {})
    fresh_gates = fresh.get("gates", {})
    return [
        {
            "requirement_id": "flow_shield_representation",
            "requirement": "G4 flow-shield representation validation",
            "status": "passed" if g4.get("gates", {}).get("representation_gates_passed") else "missing",
            "evidence_artifacts": "outputs/reports/phase5p5_repair5g4_clean_frozen_validation_summary.json",
            "remaining_work": "",
        },
        {
            "requirement_id": "protocol_policy",
            "requirement": "semantic parity plus time-budget equivalence policy",
            "status": "passed_for_diagnostics" if g4.get("gates", {}).get("parity_policy_compliant") else "missing",
            "evidence_artifacts": "outputs/reports/phase5p5_repair5g31_g4_decision.md",
            "remaining_work": "Stronger paper policy should continue to report strict parity classifications.",
        },
        {
            "requirement_id": "static_runtime_candidate",
            "requirement": "static/map-agent flow-shield runtime candidate",
            "status": "partial",
            "evidence_artifacts": "outputs/reports/phase5p5_repair5g4_clean_frozen_validation_summary.json",
            "remaining_work": "Not a learned runtime selector.",
        },
        {
            "requirement_id": "learned_runtime_selector",
            "requirement": "learned runtime selector exported and integrated",
            "status": "passed" if export and smoke_gates.get("selector_logs_present") else ("partial" if export else "missing"),
            "evidence_artifacts": "artifacts/models/laur_ltm/repair5g5_contextual_flow_shield_selector/selector_spec.json",
            "remaining_work": "" if smoke_gates.get("selector_logs_present") else "Run or pass runtime smoke with selector logs.",
        },
        {
            "requirement_id": "learned_runtime_fresh_holdout",
            "requirement": "clean learned-runtime heldout validation",
            "status": "passed" if fresh_gates.get("fresh_gates_passed") else "missing",
            "evidence_artifacts": "outputs/reports/phase5p5_repair5g5_learned_runtime_fresh_eval_summary.json",
            "remaining_work": "" if fresh_gates.get("fresh_gates_passed") else "Keep IDs 166..205 untouched until frozen runtime selector passes smoke.",
        },
        {
            "requirement_id": "map_expansion",
            "requirement": "AAAI broader map expansion",
            "status": "partial" if broad else "missing",
            "evidence_artifacts": "outputs/reports/phase5p5_repair5g5_aaai_broader_validation_summary.json",
            "remaining_work": "Run only after fresh learned runtime nearly passes or passes.",
        },
        {
            "requirement_id": "paper_claim_ledger",
            "requirement": "claim ledger mapping claims to artifacts",
            "status": "partial",
            "evidence_artifacts": "outputs/tables/phase5p5_repair5g_claim_ledger.csv",
            "remaining_work": "Upgrade claim statuses after fresh learned runtime validation.",
        },
    ]


def claim_rows(fresh: dict[str, Any]) -> list[dict[str, Any]]:
    learned_passed = fresh.get("gates", {}).get("fresh_gates_passed", False)
    return [
        {
            "claim_id": "C1",
            "claim_text": "Flow-shielded goal-aware dual-channel UpdateLTM is protocol-clean under the G4 parity policy.",
            "allowed_status": "safe",
            "supporting_artifacts": "phase5p5_repair5g4_clean_frozen_validation_summary.json",
            "required_missing_artifacts": "",
            "risk": "diagnostic parity policy still must be explained",
            "paper_section": "Results",
        },
        {
            "claim_id": "C2",
            "claim_text": "Static/map-agent flow-shield improves over additive LTM and scalar/C-equiv controls on G4.",
            "allowed_status": "safe_diagnostic",
            "supporting_artifacts": "phase5p5_repair5g4_clean_frozen_validation_summary.json",
            "required_missing_artifacts": "",
            "risk": "not a learned runtime claim",
            "paper_section": "Results",
        },
        {
            "claim_id": "C3",
            "claim_text": "Learned contextual UpdateLTM selector improves closed-loop MAPF performance on fresh heldout IDs.",
            "allowed_status": "safe" if learned_passed else "forbidden_until_fresh_validation",
            "supporting_artifacts": "phase5p5_repair5g5_learned_runtime_fresh_eval_summary.json" if learned_passed else "",
            "required_missing_artifacts": "" if learned_passed else "fresh learned runtime validation",
            "risk": "selector may only match static flow-shield",
            "paper_section": "Method/Results",
        },
    ]


def decision_from(g4: dict[str, Any], smoke: dict[str, Any], fresh: dict[str, Any]) -> str:
    if not g4.get("gates", {}).get("protocol_gates_passed"):
        return "stop_for_protocol_or_semantic_bug"
    if not smoke:
        return "continue_learning_runtime_integration"
    if smoke and not smoke.get("gates", {}).get("runtime_smoke_gates_passed"):
        return "runtime_integration_gap_blocks_learning_claim"
    if not fresh:
        return "continue_learning_runtime_integration"
    if fresh.get("gates", {}).get("fresh_gates_passed"):
        return "continue_repair5g6_aaai_formal_validation"
    return "learned_selector_failed_fresh_holdout"


def write_markdown_artifacts(root: Path, g4: dict[str, Any], stress: dict[str, Any], smoke: dict[str, Any], fresh: dict[str, Any], decision: str) -> None:
    write_text(
        root / "docs/aaai_quality_requirements.md",
        "# Repair5G AAAI Quality Requirements\n\n"
        "AAAI-ready learning claims require a learned runtime UpdateLTM selector, clean heldout validation, negative controls, ablations, stress, multi-map analysis, reproducibility manifests, and a claim ledger.\n\n"
        "- Static flow-shield alone is not an AAAI-ready learned method.\n"
        "- Phase5.5 and Phase6 remain closed until paper-grade gates pass.\n"
        "- Final learned-runtime IDs must not be used for tuning.\n",
    )
    write_text(
        root / "outputs/reports/phase5p5_repair5g4_final_interpretation.md",
        "# Phase5.5 Repair5G.4 Final Interpretation\n\n"
        "G4 is a strong positive protocol-clean diagnostic result for flow-shielded goal-aware dual-channel UpdateLTM. "
        "It validates representation and static/map-agent candidates under the accepted parity policy, but it does not validate a learned runtime selector.\n\n"
        f"- protocol_gates_passed: `{g4.get('gates', {}).get('protocol_gates_passed')}`\n"
        f"- representation_gates_passed: `{g4.get('gates', {}).get('representation_gates_passed')}`\n"
        f"- selected_mean_delta_ratio_vs_ltm: `{g4.get('gates', {}).get('selected_mean_delta_ratio_vs_ltm')}`\n"
        "- phase5p5_allowed: `false`\n- phase6_allowed: `false`\n- aaai_ready: `false`\n",
    )
    write_text(
        root / "outputs/reports/phase5p5_repair5g5_protocol_overview.md",
        "# Phase5.5 Repair5G.5 Protocol Overview\n\n"
        "Repair5G.5 keeps LaCAM*/PIBT semantics fixed and restricts learning to pre-update selection among bounded UpdateLTM candidates.\n\n"
        "- observed_id_ranges: `1..165`\n"
        "- development_id_ranges: `1..165 only`\n"
        "- learned_runtime_fresh_holdout: `166..205 primary, 206..245 fallback if touched`\n"
        "- parity_policy: `semantic_parity_plus_time_budget_equivalence_required`\n"
        "- final tuning on fresh holdout: `forbidden`\n",
    )
    write_text(
        root / "outputs/reports/phase5p5_repair5g_aaai_readiness_audit.md",
        "# Phase5.5 Repair5G AAAI Readiness Audit\n\n"
        f"Decision state: `{decision}`.\n\n"
        "- flow_shield_representation: `passed`\n"
        "- protocol_policy: `passed_for_diagnostics / partial_for_paper`\n"
        f"- learned_runtime_selector_smoke: `{smoke.get('gates', {}).get('runtime_smoke_gates_passed', False) if smoke else False}`\n"
        f"- learned_runtime_fresh_holdout: `{fresh.get('gates', {}).get('fresh_gates_passed', False) if fresh else False}`\n"
        "- aaai_ready: `false`\n",
    )
    paper_dir = root / "paper"
    write_text(
        paper_dir / "aaai_lau_ltm_goal_aware_flow_shield_outline.md",
        "# AAAI LAU-LTM Goal-Aware Flow-Shield Outline\n\n"
        "1. Introduction\n2. Related Work\n3. Background: LaCAM* and Lightweight Traffic Map\n4. Method\n   - dual-channel traffic-map state\n   - goal-aware flow-shield projection\n   - learned contextual UpdateLTM selector\n   - semantic preservation proposition\n5. Experimental Protocol\n6. Results\n7. Limitations\n8. Reproducibility\n",
    )
    write_text(
        paper_dir / "aaai_lau_ltm_goal_aware_flow_shield_claims.md",
        "# AAAI LAU-LTM Claims\n\n"
        "Claims remain ledger-controlled. Learned runtime claims are forbidden until fresh heldout validation passes.\n",
    )
    write_text(
        paper_dir / "aaai_lau_ltm_goal_aware_flow_shield_tables.md",
        "# AAAI LAU-LTM Tables\n\n"
        "- G4 representation validation\n- learned runtime fresh validation\n- ablations\n- stress\n- oracle regret\n",
    )
    write_text(
        paper_dir / "aaai_lau_ltm_goal_aware_flow_shield_figures.md",
        "# AAAI LAU-LTM Figures\n\n"
        "- method diagram\n- selector decision trace\n- mean delta by map-agent\n- stress curves\n",
    )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    g4 = load_json(resolve(args.g4_summary_json, root))
    stress = load_json(resolve(args.stress_summary_json, root))
    export = load_json(resolve(args.selector_export_summary_json, root))
    smoke = load_json(resolve(args.smoke_summary_json, root))
    fresh = load_json(resolve(args.fresh_summary_json, root))
    broad = load_json(resolve(args.broader_summary_json, root))
    decision = decision_from(g4, smoke, fresh)
    rows = evidence_rows(g4, stress, export, smoke, fresh, broad)
    claims = claim_rows(fresh)
    write_csv_rows(root / "outputs/tables/phase5p5_repair5g_aaai_evidence_matrix.csv", rows)
    write_csv_rows(root / "outputs/tables/phase5p5_repair5g_claim_ledger.csv", claims)
    summary = {
        "schema_version": "phase5p5_repair5g_aaai_readiness_summary_v1",
        "created_at": datetime.now().isoformat(),
        "decision": decision,
        "requirements": rows,
        "aaai_ready": False,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
    }
    write_json(root / "outputs/reports/phase5p5_repair5g_aaai_readiness_summary.json", summary)
    write_markdown_artifacts(root, g4, stress, smoke, fresh, decision)
    selector_path = root / DEFAULT_SELECTOR_SPEC
    decision_summary = {
        "schema_version": "phase5p5_repair5g5_decision_summary_v1",
        "created_at": summary["created_at"],
        "decision": decision,
        "answers": {
            "project_wide_aaai_policy_added": True,
            "aaai_evidence_matrix_updated": True,
            "runtime_learned_update_ltm_selector_integrated": bool(export),
            "runtime_smoke_passed": bool(smoke.get("gates", {}).get("runtime_smoke_gates_passed")) if smoke else False,
            "selector_frozen_before_final": bool((root / "outputs/reports/phase5p5_repair5g5_frozen_learned_runtime_selector_spec.json").exists()),
            "learned_runtime_fresh_validation_passed": bool(fresh.get("gates", {}).get("fresh_gates_passed")) if fresh else False,
            "learned_runtime_beats_static_or_map_agent": fresh.get("gates", {}).get("learned_beats_static_or_selector_by_margin_or_abstention_value", False) if fresh else False,
            "aaai_plausible_claims": "representation/static-flow-shield diagnostic claims only until fresh learned runtime passes",
            "forbidden_claims": "AAAI-ready, Phase5.5, Phase6, learned fresh validation passed" if not fresh.get("gates", {}).get("fresh_gates_passed", False) else "Phase5.5 and Phase6 still closed",
            "next_clean_split": "166..205 unless touched; otherwise 206..245",
        },
        "selector_hash": sha256_file(selector_path),
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "aaai_ready": False,
    }
    write_json(root / "outputs/reports/phase5p5_repair5g5_decision_summary.json", decision_summary)
    write_text(
        root / "outputs/reports/phase5p5_repair5g5_decision.md",
        "# Phase5.5 Repair5G.5 Decision\n\n"
        f"Decision: `{decision}`\n\n"
        f"- runtime_smoke_passed: `{decision_summary['answers']['runtime_smoke_passed']}`\n"
        f"- learned_runtime_fresh_validation_passed: `{decision_summary['answers']['learned_runtime_fresh_validation_passed']}`\n"
        "- phase5p5_allowed: `false`\n"
        "- phase6_allowed: `false`\n"
        "- aaai_ready: `false`\n",
    )
    print(json.dumps({"decision": decision, "aaai_ready": False}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
