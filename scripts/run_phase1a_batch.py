"""Cross-platform Phase1a batch driver.

The PowerShell runner remains the Windows entrypoint. This Python driver is
used by Linux servers and keeps the same manifest and JSONL contract.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def git_value(root: Path, args: list[str], cwd: Path | None = None) -> str:
    try:
        return subprocess.check_output(["git", *args], cwd=cwd or root, text=True).strip()
    except subprocess.CalledProcessError:
        return ""


def dirty_state(root: Path) -> str:
    tracked = git_value(root, ["status", "--porcelain", "--untracked-files=no"])
    untracked = git_value(root, ["status", "--porcelain", "--untracked-files=normal"])
    has_untracked = any(line.startswith("??") for line in untracked.splitlines())
    if tracked:
        return "tracked-dirty"
    if has_untracked:
        return "tracked-clean_untracked-present"
    return "clean"


def run_task(
    binary: Path,
    output_jsonl: Path,
    manifest: Path,
    method: str,
    map_name: str,
    map_path: Path,
    scen_path: Path,
    scen_id: str,
    agents: int,
    seed: int,
    time_limit_sec: float,
    ltm_max_iterations: int,
    metadata: dict[str, str],
) -> None:
    cmd = [
        str(binary),
        "--method",
        method,
        "--map",
        str(map_path),
        "--scen",
        str(scen_path),
        "--agents",
        str(agents),
        "--seed",
        str(seed),
        "--time-limit-sec",
        str(time_limit_sec),
        "--output-jsonl",
        str(output_jsonl),
        "--map-name",
        map_name,
        "--scen-id",
        scen_id,
        "--manifest",
        str(manifest),
        "--project-commit",
        metadata["project_commit"],
        "--external-commit",
        metadata["external_commit"],
        "--branch",
        metadata["branch"],
        "--dirty",
        metadata["dirty"],
        "--platform",
        metadata["platform"],
        "--ltm-max-iterations",
        str(ltm_max_iterations),
    ]
    completed = subprocess.run(cmd, check=False)
    if completed.returncode not in (0, 2):
        completed.check_returncode()


def archive_top_dir(archive: Path) -> str | None:
    with zipfile.ZipFile(archive) as zf:
        for name in zf.namelist():
            parts = Path(name).parts
            if not parts or parts[0] == "__MACOSX":
                continue
            return parts[0]
    return None


def ensure_scen_cache(root: Path, records: list[dict] | None = None) -> Path:
    cache = root / "outputs/tmp/phase1a/scen"
    archive_names = {
        record.get("scen_archive", "external/lacam2/scripts/scen/scen-random.zip")
        for record in records or []
    }
    if not archive_names:
        archive_names = {"external/lacam2/scripts/scen/scen-random.zip"}

    cache.mkdir(parents=True, exist_ok=True)
    for archive_name in sorted(archive_names):
        archive = root / archive_name
        if not archive.exists():
            raise FileNotFoundError(
                f"missing scenario archive: {archive}; "
                "run scripts/generate_phase1a_scenarios.py if this manifest uses generated scenarios"
            )
        top_dir = archive_top_dir(archive)
        if top_dir:
            target = cache / top_dir
            if target.exists():
                shutil.rmtree(target)
        with zipfile.ZipFile(archive) as zf:
            zf.extractall(cache)
    return cache


def parse_int_set(values: list[str]) -> set[int]:
    out: set[int] = set()
    for value in values:
        for part in value.split(","):
            part = part.strip()
            if part:
                out.add(int(part))
    return out


def selected_values(record: dict, agent_subset: set[int], instance_subset: set[int]) -> tuple[list[int], list[int]]:
    agents = [int(value) for value in record["agent_counts"]]
    if agent_subset:
        agents = [value for value in agents if value in agent_subset]
    instances = [int(value) for value in record["instances"]]
    if instance_subset:
        instances = [value for value in instances if value in instance_subset]
    return agents, instances


def scen_capacity(path: Path) -> int:
    with path.open("r", encoding="utf-8") as handle:
        nonempty = sum(1 for line in handle if line.strip())
    return max(0, nonempty - 1)


def preflight(
    root: Path,
    records: list[dict],
    scen_cache: Path,
    map_subset: set[str],
    agent_subset: set[int],
    instance_subset: set[int],
) -> int:
    issues: list[str] = []
    task_count = 0

    for record in records:
        map_name = record["map"]
        if map_subset and map_name not in map_subset:
            continue

        map_path = root / record["map_path"]
        if not map_path.exists():
            issues.append(f"{map_name}: missing map {map_path}")

        agents, instances = selected_values(record, agent_subset, instance_subset)
        if not agents:
            issues.append(f"{map_name}: no selected agent counts")
            continue
        if not instances:
            issues.append(f"{map_name}: no selected instances")
            continue

        max_agents = max(agents)
        for instance_id in instances:
            scen_id = record["scen_template"].replace("{instance}", str(instance_id))
            scen_path = scen_cache / scen_id
            if not scen_path.exists():
                issues.append(f"{map_name} instance {instance_id}: missing scenario {scen_path}")
                continue
            capacity = scen_capacity(scen_path)
            if capacity < max_agents:
                issues.append(
                    f"{map_name} instance {instance_id}: scenario has {capacity} pairs, "
                    f"but selected max agent count is {max_agents}"
                )
        task_count += len(agents) * len(instances) * 2

    if issues:
        preview = "\n".join(f"- {issue}" for issue in issues[:20])
        extra = "" if len(issues) <= 20 else f"\n- ... {len(issues) - 20} more issues"
        raise ValueError(f"Phase1a preflight failed:\n{preview}{extra}")

    print(f"Phase1a preflight passed. Tasks={task_count}")
    return task_count


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--full", action="store_true")
    parser.add_argument("--append", action="store_true")
    parser.add_argument("--build-dir", default="build/phase1a-batch")
    parser.add_argument("--manifest", default="configs/phase1a/manifest.jsonl")
    parser.add_argument("--output-jsonl", default="outputs/logs/phase1a/phase1a_runs.jsonl")
    parser.add_argument("--time-limit-sec", type=float, default=30.0)
    parser.add_argument("--dry-run-time-limit-sec", type=float, default=5.0)
    parser.add_argument("--map-subset", action="append", default=[])
    parser.add_argument("--agent-subset", action="append", default=[])
    parser.add_argument("--instance-subset", action="append", default=[])
    parser.add_argument("--max-tasks", type=int, default=0)
    parser.add_argument("--ltm-max-iterations", type=int, default=100000)
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--skip-preflight", action="store_true")
    args = parser.parse_args()

    root = project_root()
    binary = root / args.build_dir / "phase1a_batch"
    if os.name == "nt":
        binary = binary.with_suffix(".exe")
    if not binary.exists():
        raise FileNotFoundError(f"missing {binary}; build first")

    manifest = root / args.manifest
    output_jsonl = root / args.output_jsonl
    output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    if output_jsonl.exists() and not args.append:
        output_jsonl.unlink()

    metadata = {
        "project_commit": os.environ.get("PHASE1A_PROJECT_COMMIT")
        or git_value(root, ["rev-parse", "HEAD"]),
        "external_commit": os.environ.get("PHASE1A_EXTERNAL_LACAM2_COMMIT")
        or os.environ.get("PHASE1A_EXTERNAL_COMMIT")
        or git_value(root, ["rev-parse", "HEAD"], root / "external/lacam2"),
        "branch": os.environ.get("PHASE1A_BRANCH")
        or git_value(root, ["branch", "--show-current"]),
        "dirty": os.environ.get("PHASE1A_DIRTY") or dirty_state(root),
        "platform": os.environ.get("PHASE1A_PLATFORM")
        or "Linux/Windows Python Phase1a driver",
    }

    if args.dry_run:
        lacam_root = root / "external/lacam2"
        for method in ("lacam_star", "lacam_star_ltm"):
            run_task(
                binary,
                output_jsonl,
                manifest,
                method,
                "loop-dry-run",
                lacam_root / "assets/loop.map",
                lacam_root / "assets/loop.scen",
                "loop.scen",
                3,
                1,
                args.dry_run_time_limit_sec,
                args.ltm_max_iterations,
                metadata,
            )
        print(f"Phase1a dry-run JSONL: {output_jsonl}")
        return 0

    if not args.full and not args.preflight and not any(
        [args.map_subset, args.agent_subset, args.instance_subset, args.max_tasks]
    ):
        raise ValueError("choose --dry-run, --full, or an explicit subset")

    with manifest.open("r", encoding="utf-8") as handle:
        records = [json.loads(line) for line in handle if line.strip()]

    scen_cache = ensure_scen_cache(root, records)
    map_subset = set(args.map_subset)
    agent_subset = parse_int_set(args.agent_subset)
    instance_subset = parse_int_set(args.instance_subset)

    if args.preflight or not args.skip_preflight:
        preflight(root, records, scen_cache, map_subset, agent_subset, instance_subset)
        if args.preflight:
            return 0

    task_count = 0

    for record in records:
        map_name = record["map"]
        if map_subset and map_name not in map_subset:
            continue

        agents, instances = selected_values(record, agent_subset, instance_subset)

        for n_agents in agents:
            for instance_id in instances:
                scen_id = record["scen_template"].replace("{instance}", str(instance_id))
                scen_path = scen_cache / scen_id
                if not scen_path.exists():
                    raise FileNotFoundError(f"missing scenario after extraction: {scen_path}")
                for method in ("lacam_star", "lacam_star_ltm"):
                    run_task(
                        binary,
                        output_jsonl,
                        manifest,
                        method,
                        map_name,
                        root / record["map_path"],
                        scen_path,
                        scen_id,
                        n_agents,
                        instance_id,
                        args.time_limit_sec,
                        args.ltm_max_iterations,
                        metadata,
                    )
                    task_count += 1
                    if args.max_tasks > 0 and task_count >= args.max_tasks:
                        print(f"Stopped after max_tasks={args.max_tasks}. JSONL: {output_jsonl}")
                        return 0

    print(f"Phase1a batch complete. Tasks={task_count} JSONL: {output_jsonl}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
