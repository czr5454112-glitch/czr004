"""Write Repair5G.5.10 server command plan."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g510_common import G59_CLOSED_STATUS, repo_root, resolve, write_json, write_text  # noqa: E402


DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g510_server_command_plan.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g510_server_command_plan_summary.json"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    expected_primary = 60 * 14 * 2
    expected_full = 60 * 14 * 4
    commands = [
        "powershell -ExecutionPolicy Bypass -File scripts\\build_phase1a_batch.ps1",
        "python scripts/run_repair5g510_executable_lattice_smoke.py --overwrite --max-workers 1",
        "python scripts/analyze_repair5g510_lattice_adapter_parity.py",
        (
            "python scripts/run_repair5g510_goal_aware_dual_channel_lattice_counterfactuals.py "
            "--overwrite --instance-ids 146..155 --budgets-ms 250 500 1000 2000 "
            "--max-contexts-per-group 1 --max-workers 4 --checkpoint-topk-edges 256 --include-full-traffic"
        ),
        "python scripts/analyze_repair5g510_lattice_counterfactual_oracle_gap.py",
        "python scripts/create_repair5g510_feature_matrix_v2.py",
        "python scripts/analyze_repair5g510_feature_signal_v2.py",
        "python scripts/create_repair5g510_confidence_targets_v4.py",
        "python scripts/analyze_repair5g510_confidence_targets_v4.py",
        "python scripts/train_repair5g510_abstention_parameter_policy.py",
        "python scripts/eval_repair5g510_abstention_parameter_policy.py",
        "python scripts/write_repair5g510_decision.py",
    ]
    summary = {
        "schema_version": "phase5p5_repair5g510_server_command_plan_summary_v1",
        "expected_primary_rows": expected_primary,
        "expected_full_rows_with_250_500_1000_2000": expected_full,
        "expected_contexts": 60,
        "expected_candidates": 14,
        "primary_budgets_ms": [1000, 2000],
        "stress_budget_ms": 250,
        "bonus_budget_ms": 500,
        "setup_command": commands[0],
        "resume_command": commands[3].replace("--overwrite ", ""),
        "commands": commands,
        "artifact_pull_back_list": [
            "outputs/tables/phase5p5_repair5g510_lattice_counterfactual_results.csv",
            "outputs/tables/phase5p5_repair5g510_lattice_oracle_by_context.csv",
            "outputs/tables/phase5p5_repair5g510_feature_matrix_v2.csv",
            "outputs/tables/phase5p5_repair5g510_confidence_targets_v4.csv",
            "outputs/reports/phase5p5_repair5g510_*.json",
            "outputs/reports/phase5p5_repair5g510_*.md",
            "outputs/logs/phase5p5_repair5g510_lattice_counterfactuals/*.jsonl",
        ],
        "sanity_checks": [
            "JSON summaries parse with python -m json.tool",
            "CSV result rows >= 3360 for full 250/500/1000/2000 run",
            "candidate_id count is 14 for lattice results",
            "no seed in 166..205",
            "adapter parity summary decision is lattice_adapter_parity_passed",
        ],
        **G59_CLOSED_STATUS,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.10 Server Command Plan\n\n"
        "Use this package if the desktop cannot finish the full observed-ID lattice run.\n\n"
        "## Expected Rows\n\n"
        f"- primary 1000/2000 only: `{expected_primary}` rows\n"
        f"- full 250/500/1000/2000: `{expected_full}` rows\n"
        "- contexts: `60`\n"
        "- candidates: `14`\n\n"
        "## Commands\n\n"
        + "\n".join(f"{index + 1}. `{command}`" for index, command in enumerate(commands))
        + "\n\n## Resume\n\n"
        f"`{summary['resume_command']}`\n\n"
        "## Pull Back\n\n"
        + "\n".join(f"- `{item}`" for item in summary["artifact_pull_back_list"])
        + "\n\n## Sanity Checks\n\n"
        + "\n".join(f"- {item}" for item in summary["sanity_checks"])
        + "\n",
    )
    print(json.dumps({"expected_full_rows": expected_full}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
