"""Guarded local rich feature probe launcher for G5.14.

The default mode is dry-run planning. Use --execute only when existing checkpoint
artifacts are absent and a local observed-ID probe is explicitly needed.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g512_common import observed_id_guard, repo_root, resolve, write_json, write_text  # noqa: E402
from repair5g514_common import G514_CLOSED_CLAIMS  # noqa: E402


DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g514_local_rich_feature_probe_plan.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g514_local_rich_feature_probe_plan_summary.json"
DEFAULT_MAPS = ["random-32-32-20", "maze-32-32-4", "warehouse-10-20-10-2-1"]
DEFAULT_AGENTS = [50, 100]
DEFAULT_IDS = list(range(146, 156))
DEFAULT_BUDGETS = [1000, 2000]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--maps", nargs="*", default=DEFAULT_MAPS)
    parser.add_argument("--agents", nargs="*", type=int, default=DEFAULT_AGENTS)
    parser.add_argument("--ids", "--instance-ids", dest="ids", nargs="*", type=int, default=DEFAULT_IDS)
    parser.add_argument("--budgets", nargs="*", type=int, default=DEFAULT_BUDGETS)
    parser.add_argument("--max-contexts-per-group", type=int, default=1)
    parser.add_argument("--max-workers", type=int, default=1)
    parser.add_argument("--checkpoint-topk-edges", type=int, default=64)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    try:
        observed_id_guard(args.ids, label="G5.14 local rich feature probe ids")
    except ValueError as exc:
        summary = {
            "schema_version": "phase5p5_repair5g514_local_probe_guard_summary_v1",
            "decision": "reserved_id_guard_rejected_probe",
            "error": str(exc),
            "ids": args.ids,
            **G514_CLOSED_CLAIMS,
        }
        write_json(resolve(args.summary_json, root), summary)
        print(json.dumps({"decision": summary["decision"], "error": str(exc)}))
        return 2
    if args.max_workers != 1:
        summary = {
            "schema_version": "phase5p5_repair5g514_local_probe_guard_summary_v1",
            "decision": "max_workers_must_be_one_stop",
            "max_workers": args.max_workers,
            **G514_CLOSED_CLAIMS,
        }
        write_json(resolve(args.summary_json, root), summary)
        print(json.dumps({"decision": summary["decision"], "max_workers": args.max_workers}))
        return 2

    command = [
        "python",
        "scripts/run_phase1a_batch.py",
        "--max-workers",
        "1",
        "--repair5g-export-update-checkpoints-jsonl",
        "outputs/logs/phase5p5_repair5g514_local_rich_feature_probe/checkpoints.jsonl",
        "--repair5g-checkpoint-topk-edges",
        str(args.checkpoint_topk_edges),
    ]
    decision = "local_probe_plan_recorded_not_run" if not args.execute else "local_probe_execute_not_implemented_stop"
    summary = {
        "schema_version": "phase5p5_repair5g514_local_probe_guard_summary_v1",
        "decision": decision,
        "maps": args.maps,
        "agents": args.agents,
        "ids": args.ids,
        "budgets": args.budgets,
        "max_contexts_per_group": args.max_contexts_per_group,
        "max_workers": args.max_workers,
        "checkpoint_export_enabled": True,
        "shared_concurrent_jsonl_append_allowed": False,
        "ids_166_205_untouched": True,
        "observed_ids_only": True,
        "planned_command": command,
        "note": "Existing rich checkpoints should be parsed first. This guarded wrapper intentionally does not execute solver work unless implementation is extended after artifact absence is confirmed.",
        **G514_CLOSED_CLAIMS,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.14 Local Rich Feature Probe Plan\n\n"
        f"- decision: `{decision}`\n"
        f"- maps: `{args.maps}`\n"
        f"- agents: `{args.agents}`\n"
        f"- ids: `{args.ids}`\n"
        f"- budgets: `{args.budgets}`\n"
        f"- max_contexts_per_group: `{args.max_contexts_per_group}`\n"
        f"- max_workers: `{args.max_workers}`\n"
        "- checkpoint_export_enabled: `true`\n"
        "- shared_concurrent_jsonl_append_allowed: `false`\n"
        "- ids_166_205_untouched: `true`\n"
        "- runtime_claim_allowed: `false`\n\n"
        "This wrapper records the safe local probe shape and enforces the reserved-ID and single-worker guards. "
        "The current G5.14 run should not execute it when existing checkpoint artifacts are usable.\n",
    )
    print(json.dumps({"decision": decision, "ids": args.ids, "max_workers": args.max_workers}))
    return 0 if not args.execute else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
