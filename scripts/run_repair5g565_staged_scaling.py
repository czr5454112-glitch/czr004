from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gcst.rich_scaling_protocol import read_rows, select_top_rich_methods  # noqa: E402


ROUND = "phase5p5_repair5g565"
SCREEN = f"{ROUND}_screening"
TABLES = ROOT / "outputs/tables"
REPORTS = ROOT / "outputs/reports"


def run_cmd(args: list[str]) -> None:
    print(json.dumps({"event": "staged_scaling_command", "args": args}, sort_keys=True), flush=True)
    subprocess.run(args, cwd=ROOT, check=True)


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the G5.65 MD staged scaling protocol.")
    parser.add_argument("--rows-path", required=True)
    parser.add_argument("--context-dir", required=True)
    parser.add_argument("--max-contexts", type=int, default=1000)
    parser.add_argument("--screening-epochs", type=int, default=30)
    parser.add_argument("--confirmatory-epochs", type=int, default=30)
    parser.add_argument("--min-epochs", type=int, default=30)
    parser.add_argument("--early-stop-patience", type=int, default=10)
    parser.add_argument("--hidden-dim", type=int, default=64)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--amp-bf16", action="store_true")
    args = parser.parse_args(argv)

    common = [
        sys.executable,
        "scripts/run_repair5g565_current_bank_scaling.py",
        "--rows-path",
        args.rows_path,
        "--context-dir",
        args.context_dir,
        "--max-contexts",
        str(args.max_contexts),
        "--seeds",
        "565,566,567",
        "--hidden-dim",
        str(args.hidden_dim),
        "--batch-size",
        str(args.batch_size),
        "--min-epochs",
        str(args.min_epochs),
        "--early-stop-patience",
        str(args.early_stop_patience),
        "--device",
        args.device,
    ]
    if args.amp_bf16:
        common.append("--amp-bf16")
    run_cmd(
        common
        + [
            "--folds",
            "4",
            "--fold-indices",
            "0",
            "--sizes",
            "64,128,256,512,all",
            "--methods",
            "B0,B1,B2,E0,E1,E2",
            "--epochs",
            str(args.screening_epochs),
            "--artifact-prefix",
            SCREEN,
            "--stage-label",
            "screening",
        ]
    )
    screening_rows = read_rows(TABLES / f"{SCREEN}_scaling_by_fold_seed_size.csv")
    top = select_top_rich_methods(screening_rows, top_k=2)
    if len(top) < 2:
        raise RuntimeError("screening did not produce two rich methods; refusing fallback selection")
    confirm_methods = ",".join(["B0", "B1", "B2", *top])
    write_json(
        REPORTS / f"{ROUND}_staged_scaling_protocol_summary.json",
        {
            "schema_version": f"{ROUND}_staged_scaling_protocol_summary_v1",
            "decision": "g565_staged_scaling_screening_completed_confirmatory_started",
            "screening_artifact_prefix": SCREEN,
            "screening_methods": ["B0", "B1", "B2", "E0", "E1", "E2"],
            "selected_rich_methods": top,
            "confirmatory_methods": confirm_methods.split(","),
            "selection_uses_solver_outcomes": False,
            "scientific_scope_downgraded": False,
        },
    )
    run_cmd(
        common
        + [
            "--folds",
            "4",
            "--sizes",
            "128,256,512,all",
            "--methods",
            confirm_methods,
            "--epochs",
            str(args.confirmatory_epochs),
            "--artifact-prefix",
            ROUND,
            "--stage-label",
            "confirmatory",
        ]
    )
    summary = json.loads((REPORTS / f"{ROUND}_staged_scaling_protocol_summary.json").read_text(encoding="utf-8"))
    summary["decision"] = "g565_staged_scaling_protocol_completed"
    write_json(REPORTS / f"{ROUND}_staged_scaling_protocol_summary.json", summary)
    print(json.dumps({"decision": summary["decision"], "selected_rich_methods": top}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
