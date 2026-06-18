"""Finalize local G5.57 artifacts after fetching the compact server bundle.

This script chains the safe local steps that happen after the remote run has
written a compact bundle:

1. ingest the compact bundle into repo-relative reports/tables/manifests;
2. audit the final summaries and static-claim guardrails;
3. update the G5.57 plan and project master docs from the final summary;
4. run local validation checks.

It deliberately does not stage, commit, push, or store SSH credentials.
"""

from __future__ import annotations

import argparse
import glob
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SUMMARY_PATH = ROOT / "outputs/reports/phase5p5_repair5g557_local_finalize_summary.json"

G557_STAGE_SCRIPT_PATHS = [
    "scripts/repair5g557_common.py",
    "scripts/verify_repair5g557_g556_artifacts.py",
    "scripts/create_repair5g557_literature_code_audit.py",
    "scripts/create_repair5g557_context_bank.py",
    "scripts/create_repair5g557_graph_feature_cache.py",
    "scripts/create_repair5g557_traffic_prior_features.py",
    "scripts/create_repair5g557_probe_traffic_plan.py",
    "scripts/run_repair5g557_probe_traffic.py",
    "scripts/analyze_repair5g557_probe_traffic.py",
    "scripts/create_repair5g557_theta_candidate_slate.py",
    "scripts/create_repair5g557_label_matrix_plan.py",
    "scripts/run_repair5g557_theta_label_matrix.py",
    "scripts/analyze_repair5g557_label_matrix.py",
    "scripts/create_repair5g557_label_v3_dataset.py",
    "scripts/train_eval_repair5g557_ttgt_outcome_model.py",
    "scripts/train_eval_repair5g557_gcst_generator.py",
    "scripts/train_eval_repair5g557_controls.py",
    "scripts/analyze_repair5g557_model_ablation.py",
    "scripts/generate_repair5g557_static_theta_policy.py",
    "scripts/create_repair5g557_stage1_execution_plan.py",
    "scripts/run_repair5g557_stage1_execution.py",
    "scripts/analyze_repair5g557_stage1_execution.py",
    "scripts/create_repair5g557_stage2_heldout_map_plan.py",
    "scripts/run_repair5g557_stage2_heldout_map.py",
    "scripts/analyze_repair5g557_stage2_heldout_map.py",
    "scripts/create_repair5g557_blind_plan.py",
    "scripts/run_repair5g557_blind.py",
    "scripts/analyze_repair5g557_blind.py",
    "scripts/write_repair5g557_decision.py",
]

LOCAL_HELPER_PATHS = [
    "scripts/audit_repair5g557_final_artifacts.py",
    "scripts/audit_repair5g557_git_payload.py",
    "scripts/fetch_repair5g557_remote_bundles.py",
    "scripts/ingest_repair5g557_remote_bundle.py",
    "scripts/update_repair5g557_docs_from_final.py",
    "scripts/finalize_repair5g557_remote_results.py",
    "tests/test_repair5g557_doc_update.py",
    "tests/test_repair5g557_fetch_bundles.py",
    "tests/test_repair5g557_final_audit.py",
    "tests/test_repair5g557_finalize.py",
    "tests/test_repair5g557_git_payload_audit.py",
    "tests/test_repair5g557_ingest_bundle.py",
]

PY_COMPILE_PATHS = G557_STAGE_SCRIPT_PATHS + LOCAL_HELPER_PATHS

TEST_PATHS = [
    "tests/test_repair5g557_doc_update.py",
    "tests/test_repair5g557_fetch_bundles.py",
    "tests/test_repair5g557_final_audit.py",
    "tests/test_repair5g557_finalize.py",
    "tests/test_repair5g557_git_payload_audit.py",
    "tests/test_repair5g557_ingest_bundle.py",
]

DIFF_CHECK_PATHS = [
    *G557_STAGE_SCRIPT_PATHS,
    *LOCAL_HELPER_PATHS,
    "czr004_g557_graph_conditioned_static_theta_aaai_plan.md",
    "deep-research-report.md",
    "phase4_6_laur_ltm_codex_execution_plan.md",
]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True, help="Local czr004_g557_compact_results_*.tar.gz")
    parser.add_argument("--summary-json", type=Path, default=SUMMARY_PATH)
    parser.add_argument("--require-strict-pass", action="store_true")
    parser.add_argument("--skip-tests", action="store_true")
    parser.add_argument("--skip-doc-update", action="store_true")
    return parser.parse_args(argv)


def repo_path(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def tail_text(text: str, limit: int = 4000) -> str:
    return text if len(text) <= limit else text[-limit:]


def run_command(name: str, command: list[str]) -> dict[str, Any]:
    proc = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
    return {
        "name": name,
        "command": command,
        "returncode": proc.returncode,
        "stdout_tail": tail_text(proc.stdout),
        "stderr_tail": tail_text(proc.stderr),
        "passed": proc.returncode == 0,
    }


def parse_g557_summaries() -> dict[str, Any]:
    parsed: dict[str, str] = {}
    errors: dict[str, str] = {}
    for path in glob.glob(str(ROOT / "outputs/reports/phase5p5_repair5g557_*summary.json")):
        rel = str(Path(path).relative_to(ROOT)).replace("\\", "/")
        try:
            with open(path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            parsed[rel] = str(data.get("decision", data.get("schema_version", "json_object"))) if isinstance(data, dict) else "not_object"
        except Exception as exc:
            errors[rel] = str(exc)
    return {"parsed": parsed, "errors": errors, "passed": not errors and bool(parsed)}


def check_external_lacam_clean() -> dict[str, Any]:
    proc = subprocess.run(
        ["git", "status", "--short", "--", "external/lacam2/lacam2"],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    stdout = proc.stdout.strip()
    return {
        "name": "external_lacam2_clean",
        "returncode": proc.returncode,
        "stdout": stdout,
        "stderr": proc.stderr.strip(),
        "passed": proc.returncode == 0 and stdout == "",
    }


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    bundle = repo_path(args.bundle)
    if not bundle.exists():
        raise FileNotFoundError(bundle)

    commands: list[dict[str, Any]] = []
    commands.append(
        run_command(
            "ingest_bundle",
            [sys.executable, "scripts/ingest_repair5g557_remote_bundle.py", "--bundle", str(bundle)],
        )
    )
    if commands[-1]["returncode"] == 0:
        audit_cmd = [sys.executable, "scripts/audit_repair5g557_final_artifacts.py"]
        if args.require_strict_pass:
            audit_cmd.append("--require-strict-pass")
        commands.append(run_command("audit_final_artifacts", audit_cmd))
    if commands[-1]["returncode"] == 0 and not args.skip_doc_update:
        commands.append(run_command("update_docs", [sys.executable, "scripts/update_repair5g557_docs_from_final.py"]))

    validation: list[dict[str, Any]] = []
    if commands[-1]["returncode"] == 0:
        validation.append(run_command("py_compile", [sys.executable, "-m", "py_compile", *PY_COMPILE_PATHS]))
        validation.append(parse_g557_summaries())
        if not args.skip_tests:
            validation.append(run_command("pytest_repair5g557_helpers", ["pytest", "-q", *TEST_PATHS]))
        validation.append(run_command("git_diff_check", ["git", "diff", "--check", "--", *DIFF_CHECK_PATHS]))
        validation.append(check_external_lacam_clean())

    passed = all(step.get("passed") for step in commands) and all(step.get("passed") for step in validation)
    summary = {
        "schema_version": "phase5p5_repair5g557_local_finalize_summary_v1",
        "bundle": str(bundle),
        "passed": bool(passed),
        "commands": commands,
        "validation": validation,
    }
    write_json(repo_path(args.summary_json), summary)
    print(json.dumps({"passed": passed, "commands": len(commands), "validation": len(validation)}, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
