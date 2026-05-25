"""Generate Phase3 NTM teacher-data manifest, edge labels, and audit report."""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
import zipfile
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from czr004_teacher.schema import (  # noqa: E402
    EDGE_LABEL_SCHEMA_VERSION,
    MANIFEST_SCHEMA_VERSION,
    PRIMARY_SUPERVISION,
    TRACE_SCHEMA_VERSION,
    count_jsonl_rows,
    run_id_for,
    sha256_file,
    validate_edge_label,
    validate_manifest_row,
)
from czr004_teacher.splits import audit_no_leakage, split_for, validate_split_maps  # noqa: E402


def read_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSONL") from exc
    return rows


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row.get(name) for name in fieldnames})


def load_config(path: Path) -> dict:
    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError("PyYAML is required to read Phase3 teacher config") from exc
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


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


def split_maps_from_config(config: dict) -> dict[str, tuple[str, ...]]:
    rule = config["split_rule"]
    split_maps = {
        "train": tuple(rule["train"]),
        "validation": tuple(rule["validation"]),
        "test": tuple(rule["test"]),
    }
    errors = validate_split_maps(split_maps)
    if errors:
        raise ValueError("invalid split map config:\n" + "\n".join(errors))
    return split_maps


def ensure_scenario_file(record: dict, instance_id: int, generated_root: Path) -> Path:
    relative = Path(record["scen_template"].format(instance=instance_id))
    scenario_path = generated_root / relative
    if scenario_path.exists():
        return scenario_path

    archive_path = ROOT / record["scen_archive"]
    if not archive_path.exists():
        raise FileNotFoundError(f"missing scenario file {scenario_path} and archive {archive_path}")
    generated_root.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive_path) as archive:
        try:
            archive.extract(relative.as_posix(), generated_root)
        except KeyError as exc:
            raise FileNotFoundError(f"{archive_path} does not contain {relative.as_posix()}") from exc
    return scenario_path


def select_jobs(config: dict, split_maps: dict[str, tuple[str, ...]]) -> list[dict]:
    manifest_path = ROOT / config["source_manifest"]
    generated_root = ROOT / config["generated_scenarios_root"]
    records = read_jsonl(manifest_path)
    sample_instances = {int(value) for value in config["sample_instances"]}
    jobs: list[dict] = []

    for record in records:
        map_name = record["map"]
        split = split_for(map_name, split_maps)
        agent_counts = [int(value) for value in record["agent_counts"]]
        agent_policy = config.get("agent_policy", "min_per_map")
        if agent_policy == "min_per_map":
            agents = min(agent_counts)
        elif agent_policy == "fixed":
            agents = int(config["agent_count"])
            max_agents = max(agent_counts)
            if agents > max_agents:
                raise ValueError(f"{map_name}: fixed agent_count={agents} exceeds scenario capacity {max_agents}")
        else:
            raise ValueError("agent_policy must be min_per_map or fixed")

        for instance_id in [int(value) for value in record["instances"]]:
            if instance_id not in sample_instances:
                continue
            scen_path = ensure_scenario_file(record, instance_id, generated_root)
            scen_id = Path(record["scen_template"].format(instance=instance_id)).as_posix()
            run_id = run_id_for(
                map_name=map_name,
                scen=scen_id,
                agents=agents,
                seed=instance_id,
                time_limit_sec=float(config["time_limit_sec"]),
                source_manifest=config["source_manifest"],
            )
            jobs.append(
                {
                    "run_id": run_id,
                    "split": split,
                    "map": map_name,
                    "map_path": str(ROOT / record["map_path"]),
                    "scen": scen_id,
                    "scen_path": str(scen_path),
                    "agents": agents,
                    "seed": instance_id,
                    "source_manifest": config["source_manifest"],
                    "source_scen_archive": record["scen_archive"],
                }
            )

    return sorted(jobs, key=lambda row: (row["split"], row["map"], row["agents"], row["seed"]))


def validate_label_file(path: Path) -> list[str]:
    errors: list[str] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                errors.append(f"{path}:{line_no}: invalid JSON")
                continue
            errors.extend(f"{path}:{line_no}: {error}" for error in validate_edge_label(row))
            if len(errors) >= 20:
                break
    return errors


def run_job(config: dict, job: dict, metadata: dict[str, str], overwrite: bool) -> dict:
    binary = ROOT / config["binary"]
    if not binary.exists():
        raise FileNotFoundError(f"missing Phase1a batch binary: {binary}")

    label_path = ROOT / config["label_root"] / job["split"] / f"{job['run_id']}.edge_labels.jsonl"
    if label_path.exists():
        if not overwrite:
            raise FileExistsError(f"{label_path} exists; pass --overwrite")
        label_path.unlink()

    run_log = ROOT / config["run_log_jsonl"]
    cmd = [
        str(binary),
        "--method",
        "lacam_star_ltm",
        "--map",
        job["map_path"],
        "--scen",
        job["scen_path"],
        "--map-name",
        job["map"],
        "--scen-id",
        job["scen"],
        "--agents",
        str(job["agents"]),
        "--seed",
        str(job["seed"]),
        "--time-limit-sec",
        str(config["time_limit_sec"]),
        "--ltm-max-iterations",
        str(config["ltm_max_iterations"]),
        "--output-jsonl",
        str(run_log),
        "--manifest",
        config["source_manifest"],
        "--project-commit",
        metadata["git_commit"],
        "--external-commit",
        metadata["external_lacam2_commit"],
        "--branch",
        metadata["branch"],
        "--dirty",
        metadata["dirty"],
        "--platform",
        "Windows phase3 teacher-data generator",
        "--traffic-map-jsonl",
        str(label_path),
        "--traffic-map-run-id",
        job["run_id"],
        "--traffic-map-edge-filter",
        config["edge_filter"],
    ]
    completed = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)
    if completed.returncode not in {0, 2}:
        raise RuntimeError(
            "teacher job failed "
            f"run_id={job['run_id']} exit={completed.returncode}\n"
            f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )
    if not label_path.exists():
        raise FileNotFoundError(f"teacher job did not create {label_path}")

    label_errors = validate_label_file(label_path)
    if label_errors:
        raise ValueError("edge label validation failed:\n" + "\n".join(label_errors))

    run_rows = read_jsonl(run_log)
    run_row = run_rows[-1]
    label_rows = count_jsonl_rows(label_path)
    return {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "run_id": job["run_id"],
        "split": job["split"],
        "primary_supervision": PRIMARY_SUPERVISION,
        "warm_start_target": "ltm_normalized_edge_weight",
        "edge_label_schema_version": EDGE_LABEL_SCHEMA_VERSION,
        "trace_schema_version": TRACE_SCHEMA_VERSION,
        "label_path": str(label_path.relative_to(ROOT)).replace("\\", "/"),
        "label_sha256": sha256_file(label_path),
        "label_rows": label_rows,
        "method": "lacam_star_ltm",
        "map": job["map"],
        "map_path": str(Path(job["map_path"]).relative_to(ROOT)).replace("\\", "/"),
        "scen": job["scen"],
        "agents": job["agents"],
        "seed": job["seed"],
        "time_limit_sec": float(config["time_limit_sec"]),
        "objective": "sum_of_loss",
        "success": bool(run_row.get("success")),
        "feasible": bool(run_row.get("feasible")),
        "sum_of_loss": run_row.get("sum_of_loss"),
        "lower_bound": run_row.get("lower_bound"),
        "sum_of_loss_ratio": run_row.get("sum_of_loss_ratio"),
        "runtime_ms": run_row.get("runtime_ms"),
        "ltm_iterations": run_row.get("ltm_iterations"),
        "committed_events": run_row.get("committed_events"),
        "blocked_events": run_row.get("blocked_events"),
        "nonzero_ltm_edges": run_row.get("nonzero_ltm_edges"),
        "git_commit": metadata["git_commit"],
        "external_lacam2_commit": metadata["external_lacam2_commit"],
        "branch": metadata["branch"],
        "dirty": metadata["dirty"],
        "source_manifest": job["source_manifest"],
        "source_scen_archive": job["source_scen_archive"],
    }


def split_audit_rows(manifest_rows: list[dict]) -> list[dict]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in manifest_rows:
        grouped[row["split"]].append(row)

    out: list[dict] = []
    for split in ("train", "validation", "test"):
        rows = grouped.get(split, [])
        out.append(
            {
                "split": split,
                "runs": len(rows),
                "maps": len({row["map"] for row in rows}),
                "label_rows": sum(int(row["label_rows"]) for row in rows),
                "successes": sum(1 for row in rows if row["success"]),
                "feasible": sum(1 for row in rows if row["feasible"]),
                "map_names": ";".join(sorted({row["map"] for row in rows})),
            }
        )
    return out


def dataset_summary_rows(manifest_rows: list[dict]) -> list[dict]:
    return [
        {
            "split": row["split"],
            "map": row["map"],
            "agents": row["agents"],
            "seed": row["seed"],
            "success": row["success"],
            "feasible": row["feasible"],
            "sum_of_loss_ratio": row.get("sum_of_loss_ratio"),
            "runtime_ms": row.get("runtime_ms"),
            "ltm_iterations": row.get("ltm_iterations"),
            "committed_events": row.get("committed_events"),
            "blocked_events": row.get("blocked_events"),
            "nonzero_ltm_edges": row.get("nonzero_ltm_edges"),
            "label_rows": row["label_rows"],
            "label_path": row["label_path"],
            "label_sha256": row["label_sha256"],
        }
        for row in manifest_rows
    ]


def write_report(
    path: Path,
    *,
    config_path: Path,
    config: dict,
    manifest_rows: list[dict],
    split_rows: list[dict],
    dataset_csv: Path,
    split_csv: Path,
    manifest_path: Path,
    leakage_errors: list[str],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    total_labels = sum(int(row["label_rows"]) for row in manifest_rows)
    successes = sum(1 for row in manifest_rows if row["success"])
    feasible = sum(1 for row in manifest_rows if row["feasible"])
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Phase3 Teacher Data Report\n\n")
        handle.write(f"Date: {date.today().isoformat()}\n")
        handle.write("Status: Phase3 teacher-data gate complete\n\n")

        handle.write("## Gate Result\n\n")
        handle.write(f"- teacher manifest: `{manifest_path.relative_to(ROOT)}`\n")
        handle.write(f"- edge-label schema: `{EDGE_LABEL_SCHEMA_VERSION}`\n")
        handle.write(f"- PIBT trace schema: `{TRACE_SCHEMA_VERSION}`\n")
        handle.write(f"- runs generated: {len(manifest_rows)}\n")
        handle.write(f"- edge-label rows generated: {total_labels}\n")
        handle.write(
            f"- sample policy: `{config.get('agent_policy')}` agents={config.get('agent_count', 'min_per_map')}, "
            f"instances={config.get('sample_instances')}, time_limit_sec={config.get('time_limit_sec')}\n"
        )
        handle.write(f"- successful runs: {successes} / {len(manifest_rows)}\n")
        handle.write(f"- feasible runs: {feasible} / {len(manifest_rows)}\n")
        handle.write(f"- split leakage audit: {'passed' if not leakage_errors else 'failed'}\n\n")

        handle.write("## Supervision Route\n\n")
        handle.write(
            "Primary route is `online_residual`: future NTM inference should start from "
            "`w_ntm = clamp(w_ltm + delta, 0, 10)` and remain safely comparable to LTM. "
            "The exported `ltm_normalized_weight` is a warm-start teacher target, not the final "
            "solver-facing claim. Pure edge regression is therefore diagnostic/pretraining only.\n\n"
        )

        handle.write("## Split Rule\n\n")
        handle.write("The split is map-holdout: a map appears in exactly one split, so generated seeds and scenarios for that map cannot cross train/validation/test.\n\n")
        for row in split_rows:
            handle.write(
                f"- {row['split']}: runs={row['runs']}, maps={row['maps']}, "
                f"label_rows={row['label_rows']}, map_names=`{row['map_names']}`\n"
            )
        handle.write("\n")

        handle.write("## Edge Label Rows\n\n")
        handle.write(
            "Each label row is one directed graph edge after a LaCAM*+LTM run. "
            "Core fields are `run_id`, map/scenario metadata, `from_id`, `to_id`, grid coordinates, "
            "`ltm_raw_count`, `ltm_normalized_weight`, `warm_start_target_weight`, "
            "`residual_reference_weight`, `residual_delta_target`, and `traversal_cost`.\n\n"
        )

        handle.write("## PIBT Trace Schema\n\n")
        handle.write(
            "Raw PIBT trace events use schema `phase3_pibt_trace_v1`: `run_id`, `iteration`, "
            "`event_index`, `kind` (`committed` or `blocked`), `agent_id`, `from_id`, `to_id`, "
            "`at_goal`, plus map/scenario/agent/seed metadata. Phase3 stores derived edge labels "
            "by default; raw traces belong under ignored `artifacts/teacher/traces/` when enabled.\n\n"
        )

        handle.write("## Outputs\n\n")
        handle.write(f"- config: `{config_path.relative_to(ROOT)}`\n")
        handle.write(f"- manifest: `{manifest_path.relative_to(ROOT)}`\n")
        handle.write(f"- dataset summary CSV: `{dataset_csv.relative_to(ROOT)}`\n")
        handle.write(f"- split audit CSV: `{split_csv.relative_to(ROOT)}`\n")
        handle.write(f"- ignored edge labels root: `{config['label_root']}`\n\n")

        handle.write("## Repro Commands\n\n")
        handle.write("```powershell\n")
        handle.write("powershell -ExecutionPolicy Bypass -File scripts\\build_phase1a_batch.ps1\n")
        handle.write(
            "& 'C:\\PROGRAMING\\anaconda\\Scripts\\conda.exe' run -n czr004 "
            "python scripts\\generate_phase1a_scenarios.py --manifest configs\\phase1a\\manifest_plus_3000.jsonl --overwrite\n"
        )
        handle.write(
            "& 'C:\\PROGRAMING\\anaconda\\Scripts\\conda.exe' run -n czr004 "
            f"python scripts\\run_phase3_teacher_data.py --config {config_path.relative_to(ROOT)} --overwrite\n"
        )
        handle.write("```\n\n")

        handle.write("## Validation\n\n")
        handle.write("- every generated edge-label row passed schema validation\n")
        handle.write("- every manifest row passed schema validation\n")
        handle.write("- map/map-seed/run-id leakage audit passed\n" if not leakage_errors else "- leakage errors:\n")
        for error in leakage_errors:
            handle.write(f"  - {error}\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path("configs/phase3/teacher_data.yaml"))
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(argv)

    config_path = (ROOT / args.config).resolve() if not args.config.is_absolute() else args.config
    config = load_config(config_path)
    split_maps = split_maps_from_config(config)

    run_log = ROOT / config["run_log_jsonl"]
    manifest_path = ROOT / config["output_manifest"]
    if args.overwrite:
        if run_log.exists():
            run_log.unlink()
        if manifest_path.exists():
            manifest_path.unlink()
    elif run_log.exists() or manifest_path.exists():
        raise FileExistsError("Phase3 outputs already exist; pass --overwrite")

    external_root = ROOT / "external/lacam2"
    metadata = {
        "git_commit": git_value(["rev-parse", "HEAD"]),
        "external_lacam2_commit": git_value(["rev-parse", "HEAD"], cwd=external_root)
        if (external_root / ".git").exists()
        else "",
        "branch": git_value(["branch", "--show-current"]),
        "dirty": dirty_state(),
    }

    jobs = select_jobs(config, split_maps)
    manifest_rows = [run_job(config, job, metadata, args.overwrite) for job in jobs]

    manifest_errors: list[str] = []
    for index, row in enumerate(manifest_rows, 1):
        manifest_errors.extend(f"row {index}: {error}" for error in validate_manifest_row(row))
    if manifest_errors:
        raise ValueError("manifest validation failed:\n" + "\n".join(manifest_errors[:20]))

    leakage_errors = audit_no_leakage(manifest_rows)
    if leakage_errors:
        raise ValueError("split leakage audit failed:\n" + "\n".join(leakage_errors))

    write_jsonl(manifest_path, manifest_rows)

    dataset_csv = ROOT / config["dataset_summary_csv"]
    split_csv = ROOT / config["split_audit_csv"]
    summary_rows = dataset_summary_rows(manifest_rows)
    audit_rows = split_audit_rows(manifest_rows)
    write_csv(
        dataset_csv,
        summary_rows,
        [
            "split",
            "map",
            "agents",
            "seed",
            "success",
            "feasible",
            "sum_of_loss_ratio",
            "runtime_ms",
            "ltm_iterations",
            "committed_events",
            "blocked_events",
            "nonzero_ltm_edges",
            "label_rows",
            "label_path",
            "label_sha256",
        ],
    )
    write_csv(split_csv, audit_rows, ["split", "runs", "maps", "label_rows", "successes", "feasible", "map_names"])

    write_report(
        ROOT / config["report_md"],
        config_path=config_path,
        config=config,
        manifest_rows=manifest_rows,
        split_rows=audit_rows,
        dataset_csv=dataset_csv,
        split_csv=split_csv,
        manifest_path=manifest_path,
        leakage_errors=leakage_errors,
    )

    print(
        "phase3_teacher_data "
        f"runs={len(manifest_rows)} labels={sum(row['label_rows'] for row in manifest_rows)} "
        f"manifest={manifest_path}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
