"""Write the Repair5G.5.9 learned bounded dual-channel UpdateLTM policy design."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g59_common import G59_CLOSED_STATUS, repo_root, resolve, write_json, write_text  # noqa: E402


DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g59_learned_bounded_dual_channel_update_policy_design.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g59_learned_bounded_dual_channel_update_policy_design_summary.json"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    permitted_outputs = [
        "bounded alpha_cong_committed",
        "bounded alpha_cong_blocked",
        "bounded alpha_flow_progress",
        "bounded alpha_flow_wait_or_nonprogress",
        "bounded rho_cong",
        "bounded rho_flow",
        "bounded flow_shield_beta",
        "bounded max_flow_shield",
        "safe expert mixture weights",
        "abstention/static/additive fallback probabilities",
    ]
    forbidden_outputs = [
        "agent actions",
        "PIBT priorities",
        "restart nodes",
        "h_i(v) heuristic values",
        "candidate deletion",
        "collision decisions",
        "OPEN/EXPLORED/rewrite/incumbent decisions",
    ]
    summary = {
        "schema_version": "phase5p5_repair5g59_learned_bounded_dual_channel_update_policy_design_summary_v1",
        "decision": "learned_bounded_update_policy_design_ready_offline_only",
        "method_name": "Learned Bounded Dual-Channel UpdateLTM Policy",
        "input_state": "pre-update context / trace / C-F traffic-map summary",
        "output_path": "context -> bounded alpha/rho/beta/max_flow_shield policy -> UpdateLTM -> DirectedTrafficMap -> WeightedDistanceTable",
        "permitted_outputs": permitted_outputs,
        "forbidden_outputs": forbidden_outputs,
        "training_labels_needed": [
            "same-context counterfactual UpdateLTM candidate outcomes",
            "feasibility/abstention labels",
            "static-near-oracle boundary labels",
            "calibrated harmful-vs-static labels",
        ],
        "safety_projection": "clip outputs to bounded candidate-safe ranges and fall back to static/additive when confidence or OOD risk is poor",
        "offline_only_stage_gate": True,
        "future_runtime_preflight_requirements": [
            "force-additive/defer parity",
            "deterministic export",
            "runtime hook sanity with always-static and map-agent policies",
            "fresh observed-ID smoke before reserved IDs",
            "no IDs 166..205 until gates reopen",
        ],
        **G59_CLOSED_STATUS,
    }
    write_json(resolve(args.summary_json, root), summary)
    report = (
        "# Phase5.5 Repair5G.5.9 Learned Bounded Dual-Channel Update Policy Design\n\n"
        "## Design\n\n"
        "The target learned component is not a MAPF action policy and not a restart policy. It maps pre-update trace/context and C/F traffic-map state to bounded UpdateLTM parameters or safe expert mixtures:\n\n"
        "```text\n"
        "context / trace / C-F traffic state\n"
        "  -> bounded alpha/rho/beta/max_flow_shield parameter policy\n"
        "  -> UpdateLTM\n"
        "  -> DirectedTrafficMap\n"
        "  -> WeightedDistanceTable\n"
        "  -> original LaCAM*/PIBT semantics unchanged\n"
        "```\n\n"
        "## Permitted Outputs\n\n"
        + "\n".join(f"- `{item}`" for item in permitted_outputs)
        + "\n\n## Forbidden Outputs\n\n"
        + "\n".join(f"- `{item}`" for item in forbidden_outputs)
        + "\n\n## Stage Gate\n\n"
        "This design is offline-only. Runtime claims require corrected controls, calibrated abstention, counterfactual oracle-gap evidence over the expanded lattice, deterministic export, and parity checks.\n"
    )
    write_text(resolve(args.report, root), report)
    print(json.dumps({"decision": summary["decision"]}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
