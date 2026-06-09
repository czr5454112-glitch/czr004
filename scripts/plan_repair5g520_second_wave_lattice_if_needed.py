"""Plan a local second-wave lattice probe if G5.20 policy gates justify it."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g520_common import (  # noqa: E402
    G520_AUTOPSY_CSV,
    G520_AUTOPSY_SUMMARY,
    G520_CLOSED_CLAIMS,
    G520_POLICY_SUMMARY,
    G520_SECOND_WAVE_CONTEXTS_CSV,
    G520_SECOND_WAVE_REPORT,
    G520_SECOND_WAVE_SUMMARY,
    G520_TARGETS_SUMMARY,
    boolish,
    finite_number,
    read_json_file,
    read_rows,
    write_json_file,
    write_rows,
    write_text_file,
)


PLAN_BLOCKS = [
    {
        "block": "block_heavy",
        "region": "around c0p90,b1p40..1p65,w0p40..0p55,beta0p35..0p50",
        "candidate_cap": 4,
    },
    {
        "block": "high_beta",
        "region": "around c1p20,b1p15..1p35,w0p70,beta0p55..0p65",
        "candidate_cap": 4,
    },
    {
        "block": "wait_conservative",
        "region": "around w0p35..0p50,beta0p30..0p35",
        "candidate_cap": 4,
    },
    {
        "block": "flow_decay",
        "region": "around dc/df combinations that reduce old-oracle regret",
        "candidate_cap": 4,
    },
]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy-summary-json", type=Path, default=Path(G520_POLICY_SUMMARY))
    parser.add_argument("--targets-summary-json", type=Path, default=Path(G520_TARGETS_SUMMARY))
    parser.add_argument("--autopsy-summary-json", type=Path, default=Path(G520_AUTOPSY_SUMMARY))
    parser.add_argument("--autopsy-csv", type=Path, default=Path(G520_AUTOPSY_CSV))
    parser.add_argument("--contexts-csv", type=Path, default=Path(G520_SECOND_WAVE_CONTEXTS_CSV))
    parser.add_argument("--report", type=Path, default=Path(G520_SECOND_WAVE_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(G520_SECOND_WAVE_SUMMARY))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    policy = read_json_file(args.policy_summary_json)
    targets = read_json_file(args.targets_summary_json)
    autopsy = read_json_file(args.autopsy_summary_json)
    best = policy.get("best_policy_summary", {})
    capture_rate = finite_number(best.get("new_candidate_opportunity_capture_rate"), 0.0)
    new_harm = int(finite_number(best.get("new_candidate_harmful_selection_count"), 0))
    gain_too_sparse = boolish(targets.get("candidate_space_gain_too_sparse_for_current_policy"))
    gates = {
        "policy_new_opportunity_capture_rate_lt_0p20": capture_rate < 0.20,
        "new_candidate_harmful_selection_count_gt_0": new_harm > 0,
        "corrected_targets_reveal_candidate_space_gain_too_sparse": gain_too_sparse,
    }
    should_plan = any(gates.values())
    context_rows = []
    if should_plan:
        seen = set()
        for row in read_rows(args.autopsy_csv):
            if row.get("row_type") not in {
                "top_16_g518_new_candidate_win_context",
                "missed_new_opportunity",
                "false_positive_involving_new_candidate",
            }:
                continue
            context = str(row.get("normalized_context_key", ""))
            if not context or context in seen:
                continue
            seen.add(context)
            context_rows.append(
                {
                    "normalized_context_key": context,
                    "map": row.get("map", ""),
                    "agents": row.get("agents", ""),
                    "seed": row.get("seed", ""),
                    "map_agent_group": row.get("map_agent_group", ""),
                    "map_family": row.get("map_family", ""),
                    "oracle_new_candidate": row.get("oracle_new_candidate", ""),
                    "new_candidate_best_gap_vs_old14": row.get("new_candidate_best_gap_vs_old14", ""),
                    "selection_reason": row.get("selection_reason", ""),
                    "probe_plan_role": "target_context",
                    "observed_ids_only": True,
                    "ids_166_205_untouched": True,
                }
            )
            if len(context_rows) >= 24:
                break
    decision = "second_wave_lattice_planned_continue_local_probe" if should_plan else "second_wave_lattice_not_needed_continue_policy_design"
    summary = {
        "schema_version": "phase5p5_repair5g520_second_wave_lattice_plan_summary_v1",
        "decision": decision,
        "plan_created": should_plan,
        "solver_run": False,
        "planning_gates": gates,
        "target_context_count": len(context_rows),
        "target_context_cap": 24,
        "candidate_plan": {
            "old14_controls": "include all old14 controls",
            "new_candidate_cap": 16,
            "blocks": PLAN_BLOCKS,
        },
        "budgets_ms": [1000, 2000],
        "max_workers": 1,
        "observed_ids_only": True,
        "ids_166_205_untouched": True,
        "no_166_205": True,
        **G520_CLOSED_CLAIMS,
    }
    write_rows(args.contexts_csv, context_rows)
    write_json_file(args.summary_json, summary)
    block_lines = "\n".join(f"- {item['block']}: {item['region']} (cap {item['candidate_cap']})" for item in PLAN_BLOCKS)
    write_text_file(
        args.report,
        "# Phase5.5 Repair5G.5.20 Second-Wave Lattice Plan\n\n"
        f"- decision: `{decision}`\n"
        f"- plan_created: `{should_plan}`\n"
        f"- solver_run: `false`\n"
        f"- target_context_count: `{len(context_rows)}`\n"
        f"- budgets_ms: `[1000, 2000]`\n"
        f"- max_workers: `1`\n"
        f"- old14_controls: `all old14`\n"
        f"- new_candidate_cap: `16`\n"
        f"- observed_ids_only: `true`\n"
        f"- ids_166_205_untouched: `true`\n\n"
        "## Planning Gates\n\n"
        f"`{gates}`\n\n"
        "## Candidate Blocks\n\n"
        f"{block_lines}\n\n"
        "This script only plans the probe. It does not run the solver and does not reopen runtime, Phase5.5, Phase6, or AAAI claims.\n",
    )
    print(json.dumps({"decision": decision, "plan_created": should_plan, "target_context_count": len(context_rows)}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
