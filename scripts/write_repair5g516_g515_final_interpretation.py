"""Write the G5.15 final interpretation carried into Repair5G.5.16."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g512_common import read_json, repo_root, resolve, write_text  # noqa: E402
from repair5g516_common import DEFAULT_G515_DECISION_SUMMARY, DEFAULT_G515_SAFETY_SUMMARY  # noqa: E402


DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g515_final_interpretation.md"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    decision = read_json(resolve(DEFAULT_G515_DECISION_SUMMARY, root))
    safety = read_json(resolve(DEFAULT_G515_SAFETY_SUMMARY, root))
    primary = decision.get("primary_policy", {})
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.15 Final Interpretation\n\n"
        "- conclusion: `G5.15 is not a direction failure; it shows the interaction ranker is safe-ish but not stronger than reproduced v4 under strict risk-adjusted utility.`\n"
        f"- decision: `{decision.get('decision', '')}`\n"
        f"- primary_policy_name: `{decision.get('primary_policy_name', '')}`\n"
        f"- mean_delta_vs_static: `{primary.get('mean_delta_vs_static', '')}`\n"
        f"- harmful_vs_static_rate: `{primary.get('harmful_vs_static_rate', '')}`\n"
        f"- coverage: `{primary.get('coverage', '')}`\n"
        f"- risk_adjusted_utility_lambda_0p10: `{primary.get('risk_adjusted_utility_lambda_0p10', primary.get('risk_adjusted_utility_lambda_0p1', ''))}`\n"
        f"- missed_helpful_contexts: `{safety.get('missed_helpful_contexts', '')}`\n"
        f"- harmful_false_positive_contexts: `{safety.get('harmful_false_positive_contexts', '')}`\n"
        f"- high_uncertainty_contexts: `{safety.get('high_uncertainty_contexts', '')}`\n"
        "- interpretation: `The rich-by-candidate interaction matrix and pairwise ranker reduced harmful false positives, but the policy still fails to convert enough oracle gap into safe opportunity capture. The next local round should focus on error-bank augmentation, targeted lattice repair, and pessimistic safety bounds rather than runtime export.`\n"
        "- phase5p5_allowed: `false`\n"
        "- phase6_allowed: `false`\n"
        "- aaai_ready: `false`\n"
        "- runtime_claim_allowed: `false`\n"
        "- learned_runtime_policy_validated: `false`\n",
    )
    print(json.dumps({"decision": "g515_final_interpretation_written", "report": str(resolve(args.report, root))}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
