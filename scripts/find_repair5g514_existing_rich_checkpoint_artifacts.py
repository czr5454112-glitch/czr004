"""Find existing rich checkpoint JSONL artifacts before any G5.14 solver run."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g512_common import repo_root, resolve, write_csv_rows, write_json, write_text  # noqa: E402
from repair5g514_common import (  # noqa: E402
    DEFAULT_CHECKPOINT_ARTIFACT_CSV,
    DEFAULT_CHECKPOINT_ARTIFACT_SUMMARY,
    G514_CLOSED_CLAIMS,
    checkpoint_context_key,
    checkpoint_record_has_required_fields,
    default_search_roots,
    load_jsonl_records,
    observed_flags_for_seeds,
)


DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g514_existing_rich_checkpoint_artifacts.md"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-csv", type=Path, default=Path(DEFAULT_CHECKPOINT_ARTIFACT_CSV))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_CHECKPOINT_ARTIFACT_SUMMARY))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--max-lines-per-file", type=int, default=0, help="0 means scan the whole file.")
    return parser.parse_args(argv)


def jsonl_files(root: Path) -> list[Path]:
    seen: set[Path] = set()
    files: list[Path] = []
    for search_root in default_search_roots(root):
        if not search_root.exists():
            continue
        for path in search_root.rglob("*.jsonl"):
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            files.append(path)
    return sorted(files, key=lambda path: str(path).lower())


def inspect_file(path: Path, root: Path, max_lines: int) -> dict[str, object]:
    usable_records = 0
    parse_errors = 0
    contexts: set[str] = set()
    seeds: set[int] = set()
    schemas: set[str] = set()
    first_line = ""
    first_method = ""
    required_literal_hits = False
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line_number, line in enumerate(handle, start=1):
            if max_lines and line_number > max_lines:
                break
            if not all(token in line for token in ['"feature_names"', '"feature_values"', '"traffic_before_hash_full"']):
                continue
            required_literal_hits = True
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                parse_errors += 1
                continue
            if not checkpoint_record_has_required_fields(record):
                continue
            usable_records += 1
            contexts.add(checkpoint_context_key(record))
            try:
                seed = int(record.get("seed"))
                seeds.add(seed)
            except (TypeError, ValueError):
                pass
            schemas.add(str(record.get("schema_version", "")))
            first_line = first_line or str(line_number)
            first_method = first_method or str(record.get("method", ""))
    flags = observed_flags_for_seeds(seeds) if seeds else {"observed_ids_only": True, "ids_166_205_untouched": True}
    return {
        "checkpoint_path": str(path.relative_to(root)),
        "absolute_checkpoint_path": str(path.resolve()),
        "literal_required_fields_seen": required_literal_hits,
        "usable_records": usable_records,
        "usable_contexts": len(contexts),
        "seed_min": min(seeds) if seeds else "",
        "seed_max": max(seeds) if seeds else "",
        "schema_versions": ",".join(sorted(schemas)),
        "first_usable_line": first_line,
        "first_method": first_method,
        "parse_errors": parse_errors,
        **flags,
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    rows = [inspect_file(path, root, args.max_lines_per_file) for path in jsonl_files(root)]
    usable = [row for row in rows if int(row["usable_records"]) > 0 and row["ids_166_205_untouched"]]
    usable_contexts = sum(int(row["usable_contexts"]) for row in usable)
    decision = (
        "existing_rich_checkpoint_artifacts_found_parse_without_solver"
        if usable
        else "no_existing_rich_checkpoint_artifacts_found_continue_local_probe"
    )
    write_csv_rows(resolve(args.output_csv, root), rows)
    summary = {
        "schema_version": "phase5p5_repair5g514_existing_rich_checkpoint_artifacts_summary_v1",
        "decision": decision,
        "jsonl_files_scanned": len(rows),
        "usable_files": len(usable),
        "usable_records": sum(int(row["usable_records"]) for row in usable),
        "usable_contexts_sum_across_files": usable_contexts,
        "usable_checkpoint_paths": [row["checkpoint_path"] for row in usable],
        "artifact_csv": str(resolve(args.output_csv, root)),
        **G514_CLOSED_CLAIMS,
    }
    write_json(resolve(args.summary_json, root), summary)
    usable_lines = "\n".join(
        f"- `{row['checkpoint_path']}`: records={row['usable_records']}, contexts={row['usable_contexts']}, seeds={row['seed_min']}..{row['seed_max']}"
        for row in usable[:20]
    )
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.14 Existing Rich Checkpoint Artifact Search\n\n"
        f"- decision: `{decision}`\n"
        f"- jsonl_files_scanned: `{len(rows)}`\n"
        f"- usable_files: `{len(usable)}`\n"
        f"- usable_records: `{summary['usable_records']}`\n"
        f"- usable_contexts_sum_across_files: `{usable_contexts}`\n"
        "- solver_rerun_required: `false` when usable files are present\n"
        "- runtime_claim_allowed: `false`\n\n"
        "## Usable Files\n\n"
        f"{usable_lines or '- none'}\n",
    )
    print(json.dumps({"decision": decision, "usable_files": len(usable), "usable_records": summary["usable_records"]}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
