"""Run Phase4 LAU-LTM pilot/full batches end to end.

This orchestrator is designed for server tmux usage. It builds the C++ Phase4
record/probe binaries, runs many checkpoint/probe jobs, joins the dataset, then
launches Phase4F training and offline eval with fixed output paths.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PHASE4F_GATE_THRESHOLDS = {
    "validation_non_neutral_checkpoints": 50,
    "rule_top1_accuracy": 0.35,
    "rule_top3_accuracy": 0.70,
    "harmful_update_recall": 0.80,
    "harmful_update_precision": 0.30,
    "predicted_rule_validation_mean_delta_ratio": 0.0,
}
sys.path.insert(0, str(ROOT / "src"))

from czr004_teacher.update_sequences import (  # noqa: E402
    audit_checkpoint_trace_join,
    audit_probe_labels,
    audit_update_dataset_rows,
    build_best_rule_labels,
    build_update_dataset_rows,
    read_checkpoint_jsonl,
    read_probe_jsonl,
    read_trace_jsonl,
    write_jsonl,
    write_update_dataset_summary_csv,
)


def load_config(path: Path) -> dict[str, Any]:
    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError("PyYAML is required to read Phase4 LAUR config") from exc
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    return data or {}


def resolve_repo_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def ensure_within_root(path: Path) -> Path:
    resolved = path.resolve()
    root = ROOT.resolve()
    if resolved != root and root not in resolved.parents:
        raise ValueError(f"refusing to modify path outside repository: {resolved}")
    return resolved


def remove_file_if_exists(path: Path) -> None:
    resolved = ensure_within_root(path)
    if resolved.exists():
        if resolved.is_dir():
            raise IsADirectoryError(resolved)
        resolved.unlink()


def remove_tree_if_exists(path: Path) -> None:
    resolved = ensure_within_root(path)
    if resolved.exists():
        if not resolved.is_dir():
            raise NotADirectoryError(resolved)
        shutil.rmtree(resolved)


def git_value(args: list[str], cwd: Path = ROOT) -> str:
    try:
        return subprocess.check_output(["git", *args], cwd=cwd, text=True).strip()
    except (FileNotFoundError, subprocess.CalledProcessError):
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


def command_string(command: list[str]) -> str:
    return subprocess.list2cmdline(command)


def display_path(path: str | Path) -> str:
    value = Path(path)
    try:
        return str(value.relative_to(ROOT))
    except ValueError:
        return str(value)


def write_json(path: str | Path, payload: dict[str, Any]) -> None:
    output = resolve_repo_path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def append_log(log_dir: Path, name: str, completed: subprocess.CompletedProcess[str]) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    (log_dir / f"{name}.stdout.log").write_text(completed.stdout, encoding="utf-8")
    (log_dir / f"{name}.stderr.log").write_text(completed.stderr, encoding="utf-8")


def run_command(
    command: list[str],
    *,
    log_dir: Path,
    log_name: str,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
    append_log(log_dir, log_name, completed)
    if check and completed.returncode != 0:
        raise RuntimeError(
            f"command failed ({log_name}) exit={completed.returncode}\n"
            f"command: {command_string(command)}\n"
            f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )
    return completed


def maybe_exe(path: Path) -> Path:
    if path.exists():
        return path
    if platform.system().lower().startswith("win"):
        exe = path.with_suffix(path.suffix + ".exe") if path.suffix else Path(str(path) + ".exe")
        if exe.exists():
            return exe
    return path


def build_binaries(config: dict[str, Any], log_dir: Path) -> list[list[str]]:
    build_dir = resolve_repo_path(config.get("build_dir", "build/phase4-laur-ltm"))
    commands = [
        ["cmake", "-S", str(ROOT / "cpp" / "ltm"), "-B", str(build_dir), "-G", "Ninja"],
        [
            "cmake",
            "--build",
            str(build_dir),
            "--config",
            "Release",
            "--target",
            "phase4_laur_record",
            "phase4_laur_probe",
            "--parallel",
            "1",
        ],
    ]
    for index, command in enumerate(commands, 1):
        run_command(command, log_dir=log_dir, log_name=f"build_{index:02d}")
    return commands


def prepare_scenarios(config: dict[str, Any], log_dir: Path, overwrite: bool) -> list[str]:
    output_zip = resolve_repo_path(config["scenario_output_zip"])
    output_dir = resolve_repo_path(config["scenario_output_dir"])
    if output_zip.exists() and output_dir.exists() and not overwrite:
        return []
    command = [
        sys.executable,
        str(ROOT / "scripts" / "generate_phase1a_scenarios.py"),
        "--manifest",
        str(config.get("scenario_manifest", "configs/phase1a/manifest.jsonl")),
        "--output-dir",
        str(config["scenario_output_dir"]),
        "--output-zip",
        str(config["scenario_output_zip"]),
        "--metadata",
        str(config.get("scenario_metadata", "outputs/reports/phase1a_generated_scenarios_manifest.json")),
    ]
    if overwrite:
        command.append("--overwrite")
    run_command(command, log_dir=log_dir, log_name="prepare_scenarios")
    return command


def expanded_runs(config: dict[str, Any]) -> list[dict[str, Any]]:
    runs: list[dict[str, Any]] = []
    instances = [int(value) for value in config.get("instances", [1])]
    if "agent_counts" in config:
        agent_counts = [int(value) for value in config["agent_counts"]]
    elif "agents" in config:
        agent_counts = [int(config["agents"])]
    else:
        raise ValueError("batch config requires agent_counts or agents")
    scen_template = str(config["scen_template"])
    for map_record in config["maps"]:
        map_name = str(map_record["map_name"])
        for instance in instances:
            scen = scen_template.format(map_name=map_name, instance=instance)
            for agents in agent_counts:
                run_id = (
                    f"{map_name}__a{agents}__i{instance}"
                    f"__phase4_{config.get('mode', 'pilot')}"
                )
                runs.append(
                    {
                        "run_id": run_id,
                        "map_name": map_name,
                        "map_path": str(map_record["map_path"]),
                        "scen_path": scen,
                        "split": str(map_record.get("split", "train")),
                        "agents": agents,
                        "seed": int(map_record.get("seed", instance)),
                        "instance": instance,
                    }
                )
    return runs


def clear_outputs(config: dict[str, Any]) -> None:
    for key in (
        "checkpoint_jsonl",
        "trace_jsonl",
        "probe_output_jsonl",
        "update_label_jsonl",
        "dataset_jsonl",
        "dataset_summary_csv",
        "dataset_summary_json",
        "offline_eval_summary_csv",
        "offline_eval_summary_json",
        "batch_summary_json",
        "batch_report_md",
        "train_report_md",
        "offline_eval_report_md",
    ):
        if config.get(key):
            remove_file_if_exists(resolve_repo_path(config[key]))
    for key in ("traffic_snapshot_root", "model_output_dir", "log_dir"):
        if config.get(key):
            remove_tree_if_exists(resolve_repo_path(config[key]))


def metadata() -> dict[str, str]:
    return {
        "branch": git_value(["branch", "--show-current"]),
        "commit": git_value(["rev-parse", "--short", "HEAD"]),
        "dirty": dirty_state(),
        "platform": platform.platform(),
        "python": sys.version.replace("\n", " "),
    }


def record_command(config: dict[str, Any], run: dict[str, Any], meta: dict[str, str]) -> list[str]:
    return [
        str(maybe_exe(resolve_repo_path(config["binary"]))),
        "--map",
        str(resolve_repo_path(run["map_path"])),
        "--scen",
        str(resolve_repo_path(run["scen_path"])),
        "--map-name",
        run["map_name"],
        "--split",
        run["split"],
        "--agents",
        str(run["agents"]),
        "--seed",
        str(run["seed"]),
        "--time-limit-sec",
        str(config["time_limit_sec"]),
        "--max-iterations",
        str(config["max_iterations"]),
        "--run-id",
        run["run_id"],
        "--checkpoint-jsonl",
        str(resolve_repo_path(config["checkpoint_jsonl"])),
        "--trace-jsonl",
        str(resolve_repo_path(config["trace_jsonl"])),
        "--traffic-snapshot-root",
        str(resolve_repo_path(config["traffic_snapshot_root"])),
        "--checkpoint-topk-edges",
        str(config.get("checkpoint_topk_edges", 16)),
        "--branch",
        meta["branch"],
        "--commit",
        meta["commit"],
        "--dirty",
        meta["dirty"],
        "--export-raw-trace",
        "--export-checkpoints",
        "--force-additive",
    ]


def probe_command(config: dict[str, Any], run: dict[str, Any], meta: dict[str, str]) -> list[str]:
    probe_config = config.get("probe", {})
    return [
        str(maybe_exe(resolve_repo_path(config["probe_binary"]))),
        "--map",
        str(resolve_repo_path(run["map_path"])),
        "--scen",
        str(resolve_repo_path(run["scen_path"])),
        "--map-name",
        run["map_name"],
        "--split",
        run["split"],
        "--agents",
        str(run["agents"]),
        "--seed",
        str(run["seed"]),
        "--time-limit-sec",
        str(config["time_limit_sec"]),
        "--max-iterations",
        str(config["max_iterations"]),
        "--run-id",
        run["run_id"],
        "--probe-output-jsonl",
        str(resolve_repo_path(config["probe_output_jsonl"])),
        "--probe-short-budget-sec",
        str(probe_config.get("short_budget_sec", 1.0)),
        "--max-checkpoints-per-run",
        str(probe_config.get("max_checkpoints_per_run", config["max_iterations"])),
        "--checkpoint-topk-edges",
        str(config.get("checkpoint_topk_edges", 16)),
        "--harmful-delta-ratio-threshold",
        str(probe_config.get("harmful_delta_ratio_threshold", -0.02)),
        "--rule-set",
        ",".join(str(rule) for rule in probe_config.get("rule_set", [])),
        "--branch",
        meta["branch"],
        "--commit",
        meta["commit"],
        "--dirty",
        meta["dirty"],
    ]


def run_record_stage(config: dict[str, Any], runs: list[dict[str, Any]], meta: dict[str, str], log_dir: Path) -> dict[str, Any]:
    completed = 0
    for index, run in enumerate(runs, 1):
        run_command(
            record_command(config, run, meta),
            log_dir=log_dir,
            log_name=f"record_{index:04d}_{run['run_id']}",
        )
        completed += 1
    audit = audit_checkpoint_trace_join(
        resolve_repo_path(config["checkpoint_jsonl"]),
        resolve_repo_path(config["trace_jsonl"]),
    )
    if not audit["passed"]:
        raise ValueError("checkpoint/trace audit failed:\n" + json.dumps(audit, indent=2))
    return {"run_count": completed, "audit": audit}


def run_probe_stage(config: dict[str, Any], runs: list[dict[str, Any]], meta: dict[str, str], log_dir: Path) -> dict[str, Any]:
    completed = 0
    for index, run in enumerate(runs, 1):
        run_command(
            probe_command(config, run, meta),
            log_dir=log_dir,
            log_name=f"probe_{index:04d}_{run['run_id']}",
        )
        completed += 1

    probe_rows = list(read_probe_jsonl(resolve_repo_path(config["probe_output_jsonl"])))
    min_delta = float(config.get("probe", {}).get("min_delta_ratio_for_label", 0.005))
    labels = build_best_rule_labels(probe_rows, min_delta_ratio=min_delta)
    write_jsonl(resolve_repo_path(config["update_label_jsonl"]), labels)
    audit = audit_probe_labels(resolve_repo_path(config["probe_output_jsonl"]), min_delta_ratio=min_delta)
    if not audit["passed"]:
        raise ValueError("probe audit failed:\n" + json.dumps(audit, indent=2))
    return {
        "run_count": completed,
        "label_count": len(labels),
        "label_distribution": dict(sorted(Counter(label["label_rule_id"] for label in labels).items())),
        "audit": audit,
    }


def run_dataset_stage(config: dict[str, Any]) -> dict[str, Any]:
    checkpoints = list(read_checkpoint_jsonl(resolve_repo_path(config["checkpoint_jsonl"])))
    traces = list(read_trace_jsonl(resolve_repo_path(config["trace_jsonl"])))
    probes = list(read_probe_jsonl(resolve_repo_path(config["probe_output_jsonl"])))
    min_delta = float(config.get("probe", {}).get("min_delta_ratio_for_label", 0.005))
    rows = build_update_dataset_rows(
        checkpoints,
        traces,
        probes,
        config=config,
        repo_root=ROOT,
        min_delta_ratio=min_delta,
    )
    audit = audit_update_dataset_rows(rows, expected_checkpoint_rows=len(checkpoints))
    if not audit["passed"]:
        raise ValueError("dataset audit failed:\n" + json.dumps(audit, indent=2))
    write_jsonl(resolve_repo_path(config["dataset_jsonl"]), rows)
    write_update_dataset_summary_csv(resolve_repo_path(config["dataset_summary_csv"]), rows)
    write_json(config["dataset_summary_json"], audit)
    return {"row_count": len(rows), "audit": audit}


def run_train_stage(config: dict[str, Any], log_dir: Path) -> dict[str, Any]:
    command = [
        sys.executable,
        str(ROOT / "src" / "train" / "train_laur_ltm.py"),
        "--config",
        str(resolve_repo_path(config_path_for_summary(config))),
        "--dataset",
        str(resolve_repo_path(config["dataset_jsonl"])),
        "--output-dir",
        str(resolve_repo_path(config["model_output_dir"])),
        "--report",
        str(resolve_repo_path(config["train_report_md"])),
    ]
    completed = run_command(command, log_dir=log_dir, log_name="train")
    summary_path = resolve_repo_path(config["model_output_dir"]) / "laur_mlp_v1_train_summary.json"
    return {"command": command, "stdout": completed.stdout.strip(), "summary_json": str(summary_path)}


def run_eval_stage(config: dict[str, Any], log_dir: Path) -> dict[str, Any]:
    model_path = resolve_repo_path(config["model_output_dir"]) / "laur_mlp_v1_weights.json"
    summary_path = resolve_repo_path(config["offline_eval_summary_json"])
    command = [
        sys.executable,
        str(ROOT / "src" / "eval" / "eval_laur_offline.py"),
        "--config",
        str(resolve_repo_path(config_path_for_summary(config))),
        "--dataset",
        str(resolve_repo_path(config["dataset_jsonl"])),
        "--model",
        str(model_path),
        "--probe-jsonl",
        str(resolve_repo_path(config["probe_output_jsonl"])),
        "--report",
        str(resolve_repo_path(config["offline_eval_report_md"])),
        "--summary-csv",
        str(resolve_repo_path(config["offline_eval_summary_csv"])),
        "--summary-json",
        str(summary_path),
    ]
    completed = run_command(command, log_dir=log_dir, log_name="eval")
    summary = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.exists() else {}
    return {
        "command": command,
        "stdout": completed.stdout.strip(),
        "summary_json": str(summary_path),
        "summary": summary,
    }


def phase4f_performance_gate(
    eval_summary: dict[str, Any] | None,
    *,
    validation_non_neutral_checkpoints: int,
) -> dict[str, Any]:
    metrics_by_split = (eval_summary or {}).get("metrics_by_split", {})
    validation_metrics = metrics_by_split.get("validation", {}) if isinstance(metrics_by_split, dict) else {}

    def metric_value(key: str) -> float | None:
        value = validation_metrics.get(key)
        return float(value) if isinstance(value, (int, float)) else None

    def metric_passes(key: str) -> bool:
        value = metric_value(key)
        threshold = PHASE4F_GATE_THRESHOLDS[key]
        return value is not None and value >= threshold

    gate = {
        "validation_non_neutral_checkpoints": validation_non_neutral_checkpoints,
        "phase4f_validation_non_neutral_min": PHASE4F_GATE_THRESHOLDS[
            "validation_non_neutral_checkpoints"
        ],
        "phase4f_validation_non_neutral_gate": (
            validation_non_neutral_checkpoints
            >= PHASE4F_GATE_THRESHOLDS["validation_non_neutral_checkpoints"]
        ),
        "phase4f_validation_rule_top1_accuracy": metric_value("rule_top1_accuracy"),
        "phase4f_validation_rule_top1_gate": metric_passes("rule_top1_accuracy"),
        "phase4f_validation_rule_top3_accuracy": metric_value("rule_top3_accuracy"),
        "phase4f_validation_rule_top3_gate": metric_passes("rule_top3_accuracy"),
        "phase4f_validation_harmful_update_recall": metric_value("harmful_update_recall"),
        "phase4f_harmful_update_recall_gate": metric_passes("harmful_update_recall"),
        "phase4f_validation_harmful_update_precision": metric_value("harmful_update_precision"),
        "phase4f_harmful_update_precision_gate": metric_passes("harmful_update_precision"),
        "phase4f_validation_predicted_rule_mean_delta_ratio": metric_value(
            "predicted_rule_validation_mean_delta_ratio"
        ),
        "phase4f_predicted_rule_mean_delta_gate": metric_passes(
            "predicted_rule_validation_mean_delta_ratio"
        ),
        "phase4f_validation_neutral_additive_rate": metric_value("neutral_additive_rate"),
        "phase4f_neutral_additive_documented": "neutral_additive_rate" in validation_metrics,
    }
    gate["phase4f_performance_gate_passed"] = all(
        bool(gate[key])
        for key in (
            "phase4f_validation_non_neutral_gate",
            "phase4f_validation_rule_top1_gate",
            "phase4f_validation_rule_top3_gate",
            "phase4f_harmful_update_recall_gate",
            "phase4f_harmful_update_precision_gate",
            "phase4f_predicted_rule_mean_delta_gate",
            "phase4f_neutral_additive_documented",
        )
    )
    return gate


def config_path_for_summary(config: dict[str, Any]) -> str:
    value = config.get("_config_path")
    if not value:
        raise ValueError("internal config path missing")
    return str(value)


def write_report(path: Path, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    status = "passed" if summary["gate"]["passed"] else "failed"
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Phase4 LAU-LTM Pilot Batch Report\n\n")
        handle.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S %z')}\n")
        handle.write(f"Status: {status}\n\n")
        handle.write("## Code State\n\n")
        meta = summary["metadata"]
        handle.write(f"- branch: `{meta['branch']}`\n")
        handle.write(f"- commit: `{meta['commit']}`\n")
        handle.write(f"- dirty: `{meta['dirty']}`\n")
        handle.write(f"- platform: `{meta['platform']}`\n\n")
        handle.write("## Scope\n\n")
        handle.write(f"- mode: `{summary['mode']}`\n")
        handle.write(f"- run_count: {summary['run_count']}\n")
        handle.write(f"- maps: `{summary['maps']}`\n")
        handle.write(f"- agent_counts: `{summary['agent_counts']}`\n")
        handle.write(f"- instances: `{summary['instances']}`\n\n")
        handle.write("## Outputs\n\n")
        for key, value in summary["outputs"].items():
            handle.write(f"- {key}: `{display_path(value)}`\n")
        handle.write("\n## Dataset\n\n")
        dataset = summary.get("dataset", {})
        audit = dataset.get("audit", {})
        handle.write(f"- rows: {dataset.get('row_count')}\n")
        handle.write(f"- non_neutral_checkpoints: {audit.get('non_neutral_checkpoint_count')}\n")
        handle.write(f"- harmful_update_count: {audit.get('harmful_update_count')}\n")
        handle.write(f"- label_distribution: `{audit.get('label_distribution')}`\n\n")
        handle.write("## Gate\n\n")
        for key, value in summary["gate"].items():
            handle.write(f"- {key}: `{value}`\n")
        handle.write("\n## Notes\n\n")
        handle.write(
            "Pilot/full evidence requires held-out validation rows and enough "
            "non-neutral checkpoints. Smoke success alone is not a Phase5 learned-runtime claim.\n"
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path("configs/phase4/laur_ltm_pilot.yaml"))
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--build", action="store_true")
    parser.add_argument("--prepare-scenarios", action="store_true")
    parser.add_argument(
        "--steps",
        default="record,probe,dataset,train,eval",
        help="comma-separated subset: record,probe,dataset,train,eval",
    )
    args = parser.parse_args(argv)

    config_path = resolve_repo_path(args.config)
    config = load_config(config_path)
    config["_config_path"] = str(config_path)
    if config.get("schema_version") != "phase4_laur_batch_config_v1":
        raise ValueError("config schema_version must be phase4_laur_batch_config_v1")

    log_dir = resolve_repo_path(config.get("log_dir", "outputs/logs/phase4_laur_batch"))
    if args.overwrite:
        clear_outputs(config)
    log_dir.mkdir(parents=True, exist_ok=True)

    build_commands: list[list[str]] = []
    scenario_command: list[str] = []
    if args.prepare_scenarios:
        scenario_command = prepare_scenarios(config, log_dir, overwrite=args.overwrite)
    if args.build:
        build_commands = build_binaries(config, log_dir)

    runs = expanded_runs(config)
    if not runs:
        raise ValueError("batch config expanded to zero runs")
    meta = metadata()
    steps = {step.strip() for step in args.steps.split(",") if step.strip()}

    record_summary: dict[str, Any] | None = None
    probe_summary: dict[str, Any] | None = None
    dataset_summary: dict[str, Any] | None = None
    train_summary: dict[str, Any] | None = None
    eval_summary: dict[str, Any] | None = None

    if "record" in steps:
        record_summary = run_record_stage(config, runs, meta, log_dir)
    if "probe" in steps:
        probe_summary = run_probe_stage(config, runs, meta, log_dir)
    if "dataset" in steps:
        dataset_summary = run_dataset_stage(config)
    if "train" in steps:
        train_summary = run_train_stage(config, log_dir)
    if "eval" in steps:
        eval_summary = run_eval_stage(config, log_dir)

    dataset_audit = dataset_summary["audit"] if dataset_summary else {}
    non_neutral = int(dataset_audit.get("non_neutral_checkpoint_count", 0))
    validation_rows = 0
    if resolve_repo_path(config["dataset_jsonl"]).exists():
        validation_rows = sum(
            1
            for row in _read_jsonl_for_gate(resolve_repo_path(config["dataset_jsonl"]))
            if row.get("split") == "validation" and not row.get("target", {}).get("neutral", True)
        )
    eval_metrics_summary = eval_summary.get("summary", {}) if eval_summary else None
    gate = {
        "batch_script_completed": True,
        "record_completed": record_summary is not None or "record" not in steps,
        "probe_completed": probe_summary is not None or "probe" not in steps,
        "dataset_completed": dataset_summary is not None or "dataset" not in steps,
        "train_completed": train_summary is not None or "train" not in steps,
        "eval_completed": eval_summary is not None or "eval" not in steps,
    }
    gate.update(
        phase4f_performance_gate(
            eval_metrics_summary,
            validation_non_neutral_checkpoints=validation_rows,
        )
    )
    gate["operational_gate_passed"] = all(
        bool(gate[key])
        for key in (
            "batch_script_completed",
            "record_completed",
            "probe_completed",
            "dataset_completed",
            "train_completed",
            "eval_completed",
        )
    )
    gate["passed"] = bool(gate["operational_gate_passed"]) and bool(
        gate["phase4f_performance_gate_passed"]
    )

    summary = {
        "schema_version": "phase4_laur_batch_summary_v1",
        "mode": config.get("mode", "pilot"),
        "config": str(config_path),
        "metadata": meta,
        "run_count": len(runs),
        "maps": sorted({run["map_name"] for run in runs}),
        "agent_counts": sorted({run["agents"] for run in runs}),
        "instances": sorted({run["instance"] for run in runs}),
        "scenario_command": scenario_command,
        "build_commands": build_commands,
        "record": record_summary,
        "probe": probe_summary,
        "dataset": dataset_summary,
        "train": train_summary,
        "eval": eval_summary,
        "outputs": {
            "checkpoint_jsonl": str(resolve_repo_path(config["checkpoint_jsonl"])),
            "trace_jsonl": str(resolve_repo_path(config["trace_jsonl"])),
            "probe_output_jsonl": str(resolve_repo_path(config["probe_output_jsonl"])),
            "dataset_jsonl": str(resolve_repo_path(config["dataset_jsonl"])),
            "model_output_dir": str(resolve_repo_path(config["model_output_dir"])),
            "batch_report_md": str(resolve_repo_path(config["batch_report_md"])),
            "batch_summary_json": str(resolve_repo_path(config["batch_summary_json"])),
            "log_dir": str(log_dir),
        },
        "gate": gate,
    }
    write_json(config["batch_summary_json"], summary)
    write_report(resolve_repo_path(config["batch_report_md"]), summary)
    print(json.dumps({"passed": gate["passed"], "summary": str(resolve_repo_path(config["batch_summary_json"]))}))
    return 0 if gate["passed"] else 1


def _read_jsonl_for_gate(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


if __name__ == "__main__":
    raise SystemExit(main())
