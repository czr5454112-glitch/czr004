"""Verify G5.17 C++ adapter recognition for the G5.16 repair lattice."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g517_common import (  # noqa: E402
    DEFAULT_CPP_ADAPTER,
    DEFAULT_G516_LATTICE,
    G517_ADAPTER_REPORT,
    G517_ADAPTER_SUMMARY,
    G517_CLOSED_CLAIMS,
    lattice_param_tuple,
    lattice_rows,
    params_close,
    repo_root,
    resolve,
    write_json,
    write_text,
)


ADAPTER_PATTERN = re.compile(
    r'method\s*==\s*"(?P<name>repair5g516_[^"]+)"\s*\)\s*\{(?P<body>.*?)set_g510_lattice\s*\((?P<args>.*?)\)\s*;',
    re.DOTALL,
)


def parse_g510_args(raw: str) -> tuple[float, float, float, float, float, float, float, float, bool, str]:
    parts = [part.strip() for part in raw.replace("\n", " ").split(",")]
    if len(parts) < 10:
        raise ValueError(f"expected at least 10 set_g510_lattice args, got {len(parts)}: {raw}")
    numeric = tuple(float(parts[index]) for index in range(8))
    c_only_text = parts[8].strip().lower()
    if c_only_text not in {"true", "false"}:
        raise ValueError(f"invalid c_only arg: {parts[8]}")
    mode = parts[9].strip().strip('"')
    return (*numeric, c_only_text == "true", mode)


def adapter_mappings(source: str) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for match in ADAPTER_PATTERN.finditer(source):
        name = match.group("name")
        parsed = parse_g510_args(match.group("args"))
        out[name] = {
            "params": parsed[:9],
            "update_mode": parsed[9],
            "comment_block_present": "Repair5G.5.17 targeted update-parameter adapter recognition only" in match.group("body"),
        }
    return out


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cpp", type=Path, default=Path(DEFAULT_CPP_ADAPTER))
    parser.add_argument("--lattice-csv", type=Path, default=Path(DEFAULT_G516_LATTICE))
    parser.add_argument("--summary-json", type=Path, default=Path(G517_ADAPTER_SUMMARY))
    parser.add_argument("--report", type=Path, default=Path(G517_ADAPTER_REPORT))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    cpp_path = resolve(args.cpp, root)
    source = cpp_path.read_text(encoding="utf-8")
    mappings = adapter_mappings(source)
    expected_rows = lattice_rows(resolve(args.lattice_csv, root))
    expected = {str(row["candidate_id"]): lattice_param_tuple(row) for row in expected_rows}
    records = []
    missing = []
    mismatched = []
    for candidate, expected_tuple in expected.items():
        actual = mappings.get(candidate)
        actual_tuple = actual["params"] if actual else None
        exact = actual_tuple is not None and params_close(actual_tuple, expected_tuple)
        if actual is None:
            missing.append(candidate)
        elif not exact:
            mismatched.append(candidate)
        records.append(
            {
                "candidate_id": candidate,
                "recognized_in_adapter": actual is not None,
                "exact_parameter_tuple": exact,
                "expected_tuple": list(expected_tuple),
                "adapter_tuple": list(actual_tuple) if actual_tuple is not None else None,
                "adapter_update_mode": actual.get("update_mode", "") if actual else "",
                "comment_block_present": bool(actual.get("comment_block_present")) if actual else False,
            }
        )
    extra = sorted(name for name in mappings if name not in expected)
    comment_block_present = any(row["comment_block_present"] for row in records)
    gates = {
        "candidate_count_eq_10": len(expected) == 10,
        "all_candidates_present": not missing,
        "all_parameter_tuples_exact": not mismatched,
        "no_extra_repair5g516_adapter_candidates": not extra,
        "comment_block_present": comment_block_present,
    }
    passed = all(gates.values())
    decision = "adapter_recognition_passed_continue_local_probe" if passed else "adapter_recognition_failed_no_solver_run"
    summary = {
        "schema_version": "phase5p5_repair5g517_adapter_recognition_summary_v1",
        "decision": decision,
        "candidate_count": len(expected),
        "recognized_candidate_count": sum(1 for row in records if row["recognized_in_adapter"]),
        "exact_parameter_tuple_count": sum(1 for row in records if row["exact_parameter_tuple"]),
        "missing_candidates": missing,
        "mismatched_candidates": mismatched,
        "extra_repair5g516_adapter_candidates": extra,
        "candidate_mappings": records,
        "gates": gates,
        **G517_CLOSED_CLAIMS,
    }
    write_json(resolve(args.summary_json, root), summary)
    mapping_lines = "\n".join(
        f"- `{row['candidate_id']}`: recognized=`{row['recognized_in_adapter']}`, exact=`{row['exact_parameter_tuple']}`"
        for row in records
    )
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.17 Adapter Recognition\n\n"
        f"- decision: `{decision}`\n"
        f"- candidate_count: `{len(expected)}`\n"
        f"- recognized_candidate_count: `{summary['recognized_candidate_count']}`\n"
        f"- exact_parameter_tuple_count: `{summary['exact_parameter_tuple_count']}`\n"
        f"- gates: `{gates}`\n\n"
        "## Candidate Mappings\n\n"
        f"{mapping_lines}\n\n"
        "This check only verifies project-owned adapter recognition in `cpp/tools/phase1a_batch.cpp`; it does not modify or inspect reserved scenario IDs.\n",
    )
    print(json.dumps({"decision": decision, "recognized_candidate_count": summary["recognized_candidate_count"]}))
    return 0 if passed else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
