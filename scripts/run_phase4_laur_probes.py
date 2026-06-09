"""Run the Phase4D LAU update-rule short-probe smoke pipeline."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from czr004_teacher.update_sequences import (  # noqa: E402
    audit_probe_labels,
    build_best_rule_labels,
    read_probe_jsonl,
)


def load_config(path: Path) -> dict[str, Any]:
    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError("PyYAML is required to read Phase4 LAUR config") from exc
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def resolve_repo_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def ensure_within_root(path: Path) -> Path:
    resolved = path.resolve()
    root = ROOT.resolve()
    if resolved != root and root not in resolved.parents:
        raise ValueError(f"refusing to remove path outside repository: {resolved}")
    return resolved


def remove_file_if_exists(path: Path) -> None:
    resolved = ensure_within_root(path)
    if resolved.exists():
        if resolved.is_dir():
            raise IsADirectoryError(resolved)
        resolved.unlink()


def git_value(args: list[str], cwd: Path = ROOT) -> str:
    try:
        return subprocess.check_output(["git", *args], cwd=cwd, text=True).strip()
    except subprocess.CalledProcessError:
        return ""


def dirty_state() -> str:
    tracked = git_value(["status", "--porcelain", "--untracked-files=no"])
    untracked = git_value(["status", "--porcelain", "--untracked-files=normal"])
    has_untracked = any(line.startswith("??") for line in untracked.splitlines())
    if tracked:
        return "tracked-dirty"
    if has_untracked:
        return "tracked-clean_untracked-present"
    return "clean"


def default_run_id(config: dict[str, Any]) -> str:
    return (
        f"{config['map_name']}__a{int(config['agents'])}"
        f"__s{int(config['seed'])}__phase4c_smoke"
    )


def file_size(path: Path) -> int:
    return path.stat().st_size if path.exists() else 0


def command_string(command: list[str]) -> str:
    return subprocess.list2cmdline(command)


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def write_report(
    path: Path,
    *,
    config_path: Path,
    config: dict[str, Any],
    probe_command: list[str],
    metadata: dict[str, str],
    completed: subprocess.CompletedProcess[str],
    summary: dict[str, Any],
    probe_path: Path,
    label_path: Path,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    status = "passed" if summary["passed"] and completed.returncode == 0 else "failed"
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Phase4D LAU Update-Rule Probe Label Report\n\n")
        handle.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S %z')}\n")
        handle.write(f"Status: {status}\n\n")

        handle.write("## Scope\n\n")
        handle.write(
            "Phase4D runs short-budget counterfactual probes for fixed update rules "
            "and builds checkpoint-level best-rule labels. It does not train a model, "
            "modify `cpp/ntm`, or implement learned restart.\n\n"
        )

        handle.write("## Code State\n\n")
        handle.write(f"- branch: `{metadata['branch']}`\n")
        handle.write(f"- commit: `{metadata['commit']}`\n")
        handle.write(f"- dirty: `{metadata['dirty']}`\n")
        handle.write(f"- config: `{config_path.relative_to(ROOT)}`\n\n")

        probe = config.get("probe", {})
        handle.write("## Smoke Run\n\n")
        handle.write(f"- map: `{config['map_name']}`\n")
        handle.write(f"- agents: {config['agents']}\n")
        handle.write(f"- seed: {config['seed']}\n")
        handle.write(f"- base time_limit_sec: {config['time_limit_sec']}\n")
        handle.write(f"- max_iterations: {config['max_iterations']}\n")
        handle.write(f"- short_budget_sec: {probe.get('short_budget_sec')}\n")
        handle.write(f"- max_checkpoints_per_run: {probe.get('max_checkpoints_per_run')}\n")
        handle.write(f"- rules: `{','.join(probe.get('rule_set', []))}`\n")
        handle.write(f"- probe exit code: {completed.returncode}\n\n")

        handle.write("## Command\n\n")
        handle.write("```powershell\n")
        handle.write("powershell -ExecutionPolicy Bypass -File scripts\\build_phase4_laur_probe.ps1\n")
        handle.write(command_string(probe_command) + "\n")
        handle.write("```\n\n")

        handle.write("## Outputs\n\n")
        handle.write(f"- probe JSONL: `{probe_path.relative_to(ROOT)}` ({file_size(probe_path)} bytes)\n")
        handle.write(f"- best-rule labels: `{label_path.relative_to(ROOT)}` ({file_size(label_path)} bytes)\n")
        if config.get("probe_summary_json"):
            summary_path = resolve_repo_path(config["probe_summary_json"])
            handle.write(f"- summary JSON: `{summary_path.relative_to(ROOT)}` ({file_size(summary_path)} bytes)\n")
        handle.write("\n")

        handle.write("## Audit Result\n\n")
        handle.write(f"- probe rows: {summary['probe_rows']}\n")
        handle.write(f"- checkpoint count: {summary['checkpoint_count']}\n")
        handle.write(f"- best-label rows: {summary['best_label_rows']}\n")
        handle.write(f"- schema errors: {summary['probe_schema_error_count']}\n")
        handle.write(f"- grouping errors: {summary['grouping_error_count']}\n")
        handle.write(f"- non-neutral checkpoints: {summary['non_neutral_checkpoint_count']}\n")
        handle.write(f"- harmful update rows: {summary['harmful_update_count']}\n")
        handle.write(f"- label distribution: `{summary['label_distribution']}`\n")
        handle.write(f"- best-rule histogram: `{summary['best_rule_histogram']}`\n")
        handle.write(f"- audit passed: {summary['passed']}\n\n")

        handle.write("## Probe Stdout\n\n")
        handle.write("```text\n")
        handle.write(completed.stdout.strip() + "\n")
        handle.write("```\n\n")
        if completed.stderr.strip():
            handle.write("## Probe Stderr\n\n")
            handle.write("```text\n")
            handle.write(completed.stderr.strip() + "\n")
            handle.write("```\n")


def run(config_path: Path, overwrite: bool) -> int:
    config = load_config(config_path)
    if config.get("schema_version") != "phase4_laur_config_v1":
        raise ValueError("config schema_version must be phase4_laur_config_v1")

    probe_config = config.get("probe", {})
    if not probe_config.get("enabled", True):
        raise ValueError("Phase4D probe config is disabled")

    binary = resolve_repo_path(config["probe_binary"])
    probe_path = resolve_repo_path(config["probe_output_jsonl"])
    label_path = resolve_repo_path(config["update_label_jsonl"])
    summary_path = resolve_repo_path(config["probe_summary_json"])
    report_path = resolve_repo_path(config["probe_report_md"])

    if overwrite:
        for path in (probe_path, label_path, summary_path, report_path):
            remove_file_if_exists(path)
    elif probe_path.exists() or label_path.exists():
        raise FileExistsError("Phase4D outputs already exist; pass --overwrite")

    if not binary.exists():
        raise FileNotFoundError(f"missing Phase4D probe binary: {binary}")

    metadata = {
        "branch": git_value(["branch", "--show-current"]),
        "commit": git_value(["rev-parse", "--short", "HEAD"]),
        "dirty": dirty_state(),
    }
    run_id = config.get("run_id") or default_run_id(config)
    rule_set = probe_config.get("rule_set", [])
    probe_command = [
        str(binary),
        "--map",
        str(resolve_repo_path(config["map"])),
        "--scen",
        str(resolve_repo_path(config["scen"])),
        "--map-name",
        str(config["map_name"]),
        "--split",
        str(config.get("split", "train")),
        "--agents",
        str(config["agents"]),
        "--seed",
        str(config["seed"]),
        "--time-limit-sec",
        str(config["time_limit_sec"]),
        "--max-iterations",
        str(config["max_iterations"]),
        "--run-id",
        str(run_id),
        "--probe-output-jsonl",
        str(probe_path),
        "--probe-short-budget-sec",
        str(probe_config.get("short_budget_sec", 1.0)),
        "--max-checkpoints-per-run",
        str(probe_config.get("max_checkpoints_per_run", 8)),
        "--checkpoint-topk-edges",
        str(config.get("checkpoint_topk_edges", 16)),
        "--harmful-delta-ratio-threshold",
        str(probe_config.get("harmful_delta_ratio_threshold", -0.02)),
        "--rule-set",
        ",".join(str(rule) for rule in rule_set),
        "--branch",
        metadata["branch"],
        "--commit",
        metadata["commit"],
        "--dirty",
        metadata["dirty"],
    ]
    completed = subprocess.run(probe_command, cwd=ROOT, text=True, capture_output=True)
    if completed.returncode != 0:
        raise RuntimeError(
            "Phase4D probe command failed "
            f"exit={completed.returncode}\nstdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )

    min_delta = float(probe_config.get("min_delta_ratio_for_label", 0.005))
    probe_rows = list(read_probe_jsonl(probe_path))
    best_labels = build_best_rule_labels(probe_rows, min_delta_ratio=min_delta)
    write_jsonl(label_path, best_labels)

    summary = audit_probe_labels(probe_path, min_delta_ratio=min_delta)
    summary["label_jsonl"] = str(label_path)
    summary["label_rows"] = len(best_labels)
    summary["written_label_distribution"] = dict(Counter(row["label_rule_id"] for row in best_labels))
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    if not summary["passed"]:
        raise ValueError("Phase4D probe audit failed:\n" + json.dumps(summary, indent=2))

    write_report(
        report_path,
        config_path=config_path,
        config=config,
        probe_command=probe_command,
        metadata=metadata,
        completed=completed,
        summary=summary,
        probe_path=probe_path,
        label_path=label_path,
    )
    print(
        "phase4_laur_probe_pipeline "
        f"probe_rows={summary['probe_rows']} "
        f"label_rows={len(best_labels)} report={report_path}"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path("configs/phase4/laur_ltm.yaml"))
    parser.add_argument("--mode", choices=["smoke"], default="smoke")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(argv)
    config_path = resolve_repo_path(args.config)
    return run(config_path, args.overwrite)


if __name__ == "__main__":
    raise SystemExit(main())
