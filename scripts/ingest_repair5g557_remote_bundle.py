"""Safely ingest a compact Repair5G.5.57 remote result bundle.

The server-side pack watcher writes a tarball containing only compact
G5.57 reports, tables, and small model manifests.  This script unpacks that
bundle into the repository with a strict path allowlist and then validates the
final decision summary guardrails before the artifacts are staged for GitHub.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import tarfile
from pathlib import Path, PurePosixPath
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g557_remote_bundle_ingest_summary.json"
MAX_MEMBER_BYTES = 50 * 1024 * 1024
PRIMARY_BASELINE = "g556_c063174"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True, help="Path to czr004_g557_compact_results_*.tar.gz")
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    parser.add_argument("--max-member-bytes", type=int, default=MAX_MEMBER_BYTES)
    parser.add_argument("--allow-missing-decision", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args(argv)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_member_name(name: str) -> str:
    name = name.replace("\\", "/")
    while name.startswith("./"):
        name = name[2:]
    pure = PurePosixPath(name)
    if pure.is_absolute() or not pure.parts:
        raise ValueError(f"unsafe tar member path: {name!r}")
    if any(part in {"", ".", ".."} for part in pure.parts):
        raise ValueError(f"unsafe tar member path: {name!r}")
    if pure.parts[0].endswith(":"):
        raise ValueError(f"unsafe tar member path: {name!r}")
    return pure.as_posix()


def allowed_member(rel: str) -> bool:
    return (
        rel.startswith("outputs/reports/phase5p5_repair5g557")
        or rel.startswith("outputs/tables/phase5p5_repair5g557")
        or rel.startswith("artifacts/models/laur_ltm/repair5g557")
    )


def target_path(root: Path, rel: str) -> Path:
    parts = PurePosixPath(rel).parts
    target = (root.joinpath(*parts)).resolve()
    root_resolved = root.resolve()
    if target != root_resolved and root_resolved not in target.parents:
        raise ValueError(f"tar member escapes repository root: {rel}")
    return target


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"expected JSON object in {path}")
    return data


def validate_decision(root: Path, allow_missing: bool) -> dict[str, Any]:
    decision_path = root / "outputs/reports/phase5p5_repair5g557_decision_summary.json"
    if not decision_path.exists():
        if allow_missing:
            return {"decision_summary_present": False}
        raise FileNotFoundError(f"missing required final decision summary: {decision_path}")

    decision = load_json(decision_path)
    errors: list[str] = []
    if decision.get("primary_baseline") != PRIMARY_BASELINE:
        errors.append(f"primary_baseline is {decision.get('primary_baseline')!r}, expected {PRIMARY_BASELINE!r}")
    if decision.get("dynamic_policy") is not False:
        errors.append("dynamic_policy must be false for G5.57 static-theta claims")
    if decision.get("checkpoint_policy") is not False:
        errors.append("checkpoint_policy must be false for G5.57 static-theta claims")
    if decision.get("runtime_claim_allowed") is not False:
        errors.append("runtime_claim_allowed must remain false")
    if decision.get("learned_runtime_policy_validated") is not False:
        errors.append("learned_runtime_policy_validated must remain false")
    if decision.get("phase6_allowed") is not False:
        errors.append("phase6_allowed must remain false")
    if decision.get("aaai_ready") is not False:
        errors.append("aaai_ready must remain false until a separate AAAI readiness gate")
    if errors:
        raise ValueError("; ".join(errors))
    return {
        "decision_summary_present": True,
        "decision": decision.get("decision"),
        "primary_baseline": decision.get("primary_baseline"),
        "strict_blind_passed": decision.get("strict_blind_passed"),
        "phase5p5_allowed": decision.get("phase5p5_allowed"),
        "phase6_allowed": decision.get("phase6_allowed"),
        "aaai_ready": decision.get("aaai_ready"),
    }


def parse_extracted_summaries(root: Path, extracted: list[str]) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for rel in extracted:
        if rel.startswith("outputs/reports/phase5p5_repair5g557") and rel.endswith("_summary.json"):
            path = root.joinpath(*PurePosixPath(rel).parts)
            data = load_json(path)
            parsed[rel] = str(data.get("decision", data.get("schema_version", "json_object")))
    return parsed


def inspect_bundle(bundle: Path, max_member_bytes: int) -> list[tarfile.TarInfo]:
    members: list[tarfile.TarInfo] = []
    with tarfile.open(bundle, "r:gz") as tar:
        for member in tar.getmembers():
            rel = normalize_member_name(member.name)
            member.name = rel
            if member.isdir():
                continue
            if not member.isfile():
                raise ValueError(f"refusing non-regular tar member: {rel}")
            if not allowed_member(rel):
                raise ValueError(f"refusing unexpected tar member: {rel}")
            if member.size > max_member_bytes:
                raise ValueError(f"refusing oversized tar member: {rel} size={member.size}")
            members.append(member)
    return members


def extract_members(bundle: Path, members: list[tarfile.TarInfo], root: Path) -> list[str]:
    extracted: list[str] = []
    with tarfile.open(bundle, "r:gz") as tar:
        by_name = {normalize_member_name(member.name): member for member in tar.getmembers()}
        for member in members:
            rel = member.name
            source = by_name[rel]
            target = target_path(root, rel)
            target.parent.mkdir(parents=True, exist_ok=True)
            handle = tar.extractfile(source)
            if handle is None:
                raise ValueError(f"could not read tar member: {rel}")
            with handle, target.open("wb") as out:
                shutil.copyfileobj(handle, out)
            extracted.append(rel)
    return extracted


def write_summary(path: Path, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    bundle = args.bundle.resolve()
    if not bundle.exists():
        raise FileNotFoundError(bundle)

    members = inspect_bundle(bundle, args.max_member_bytes)
    extracted = [] if args.dry_run else extract_members(bundle, members, ROOT)
    parsed = {} if args.dry_run else parse_extracted_summaries(ROOT, extracted)
    decision = {"decision_summary_present": False} if args.dry_run else validate_decision(ROOT, args.allow_missing_decision)

    summary = {
        "schema_version": "phase5p5_repair5g557_remote_bundle_ingest_summary_v1",
        "bundle": str(bundle),
        "bundle_sha256": sha256(bundle),
        "dry_run": bool(args.dry_run),
        "inspected_member_count": len(members),
        "inspected_bytes": sum(member.size for member in members),
        "extracted_member_count": len(extracted),
        "extracted_members": extracted,
        "parsed_summaries": parsed,
        "decision_validation": decision,
    }
    if not args.dry_run:
        write_summary(ROOT / args.summary_json, summary)
    print(json.dumps({"decision": decision.get("decision"), "members": len(members), "dry_run": args.dry_run}, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
