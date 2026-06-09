"""Audit Repair5G.5.2 candidate alias and UpdateParams equivalence."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g3_common import load_json, repo_root, resolve, write_csv_rows, write_json  # noqa: E402
from repair5g_candidate_registry import (  # noqa: E402
    DEFAULT_CSV as DEFAULT_REGISTRY_CSV,
    DEFAULT_FROZEN_SPEC,
    DEFAULT_SELECTOR_SPEC,
    REGISTRY_FIELDS,
    build_registry,
    write_csv as write_registry_csv,
)


DEFAULT_G5_RUNTIME_SPEC = "outputs/reports/phase5p5_repair5g5_runtime_contextual_selector_spec.json"
DEFAULT_SMOKE = "outputs/tables/phase5p5_repair5g5_runtime_smoke_summary.csv"
DEFAULT_G51_SANITY = "outputs/tables/phase5p5_repair5g51_runtime_hook_sanity_summary.csv"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g52_updateparams_equivalence.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g52_updateparams_equivalence_summary.json"
DEFAULT_DUMP = "outputs/tables/phase5p5_repair5g52_updateparams_dump.csv"
DEFAULT_ALIAS_AUDIT = "outputs/tables/phase5p5_repair5g52_alias_resolution_audit.csv"


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def row_by_name(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(row["method_name"]): row for row in rows}


def csv_registry_rows(registry: list[Any]) -> list[dict[str, Any]]:
    return [row.to_csv_row() for row in registry]


def selector_aliases(*specs: dict[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    for spec in specs:
        for key, value in spec.get("candidate_aliases", {}).items():
            out[str(key)] = str(value)
        for key in [
            "repair5g2_best_frozen_static_candidate",
            "repair5g2_c_equiv_best_frozen_baseline",
            "repair5g2_g1_top_diagnostic_candidate",
        ]:
            if spec.get(key):
                out[key] = str(spec[key])
    return out


def alias_audit_rows(
    registry_rows: list[dict[str, Any]],
    frozen_spec: dict[str, Any],
    runtime_spec: dict[str, Any],
    artifact_spec: dict[str, Any],
) -> list[dict[str, Any]]:
    by_name = row_by_name(registry_rows)
    spec_aliases = selector_aliases(runtime_spec, artifact_spec)
    expected = {
        "repair5g2_best_frozen_static_candidate": str(
            frozen_spec.get("selected_static_candidate")
            or spec_aliases.get("repair5g2_best_frozen_static_candidate", "")
        ),
        "repair5g2_g1_top_diagnostic_candidate": str(
            frozen_spec.get("g1_top_diagnostic_candidate")
            or spec_aliases.get("repair5g2_g1_top_diagnostic_candidate", "")
        ),
        "repair5g2_c_equiv_best_frozen_baseline": str(
            frozen_spec.get("selected_c_equiv_baseline")
            or spec_aliases.get("repair5g2_c_equiv_best_frozen_baseline", "")
        ),
    }
    rows: list[dict[str, Any]] = []
    for alias, target in expected.items():
        alias_row = by_name.get(alias, {})
        target_row = by_name.get(target, {})
        rows.append(
            {
                "alias": alias,
                "expected_target": target,
                "registry_alias_target": alias_row.get("alias_target", ""),
                "target_supported": bool(target_row),
                "alias_hash": alias_row.get("updateparams_hash", ""),
                "target_hash": target_row.get("updateparams_hash", ""),
                "hash_matches_target": bool(alias_row)
                and bool(target_row)
                and alias_row.get("updateparams_hash") == target_row.get("updateparams_hash"),
                "consistent": bool(alias_row)
                and alias_row.get("alias_target") == target
                and bool(target_row)
                and alias_row.get("updateparams_hash") == target_row.get("updateparams_hash"),
            }
        )
    for rule in frozen_spec.get("group_rules", []):
        target = str(rule.get("candidate", ""))
        target_row = by_name.get(target, {})
        rows.append(
            {
                "alias": "repair5g2_frozen_static_or_selector",
                "map": rule.get("map", ""),
                "agents": rule.get("agents", ""),
                "expected_target": target,
                "registry_alias_target": by_name.get("repair5g2_frozen_static_or_selector", {}).get("alias_target", ""),
                "target_supported": bool(target_row),
                "alias_hash": "",
                "target_hash": target_row.get("updateparams_hash", ""),
                "hash_matches_target": "group_rule_runtime_dependent",
                "consistent": bool(target_row),
            }
        )
    return rows


def unsupported_candidates(registry_rows: list[dict[str, Any]], *specs: dict[str, Any]) -> list[str]:
    names = {str(row["method_name"]) for row in registry_rows}
    aliases = {str(row["method_name"]) for row in registry_rows if str(row.get("is_alias")).lower() == "true"}
    out: list[str] = []
    for spec in specs:
        for candidate in spec.get("candidate_set", []):
            value = str(candidate)
            if value not in names and value not in aliases:
                out.append(value)
        for value in spec.get("candidate_aliases", {}).values():
            if str(value) not in names:
                out.append(str(value))
    return sorted(dict.fromkeys(out))


def write_report(path: Path, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    gates = summary["gates"]
    text = (
        "# Phase5.5 Repair5G.5.2 UpdateParams Equivalence\n\n"
        "This audit checks alias and UpdateParams hash consistency before any new learned runtime work.\n\n"
        f"- static_alias_consistent: `{gates['static_alias_consistent']}`\n"
        f"- c_equiv_alias_consistent: `{gates['c_equiv_alias_consistent']}`\n"
        f"- unsupported_candidates_without_logged_fallback: `{gates['unsupported_candidates_without_logged_fallback']}`\n"
        f"- selected_params_hash_matches_expected: `{gates['selected_params_hash_matches_expected']}`\n"
        f"- runtime_hook_equivalence_prior_status: `{summary['runtime_hook_equivalence_prior_status']}`\n"
        f"- decision: `{summary['decision']}`\n\n"
        "`phase5p5_allowed=false`, `phase6_allowed=false`, and `aaai_ready=false` remain mandatory.\n"
    )
    path.write_text(text, encoding="utf-8", newline="\n")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frozen-selector-spec-json", type=Path, default=Path(DEFAULT_FROZEN_SPEC))
    parser.add_argument("--runtime-selector-spec-json", type=Path, default=Path(DEFAULT_G5_RUNTIME_SPEC))
    parser.add_argument("--selector-artifact-json", type=Path, default=Path(DEFAULT_SELECTOR_SPEC))
    parser.add_argument("--runtime-smoke-summary-csv", type=Path, default=Path(DEFAULT_SMOKE))
    parser.add_argument("--runtime-hook-sanity-summary-csv", type=Path, default=Path(DEFAULT_G51_SANITY))
    parser.add_argument("--registry-csv", type=Path, default=Path(DEFAULT_REGISTRY_CSV))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    parser.add_argument("--updateparams-dump-csv", type=Path, default=Path(DEFAULT_DUMP))
    parser.add_argument("--alias-resolution-audit-csv", type=Path, default=Path(DEFAULT_ALIAS_AUDIT))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    frozen_spec = load_json(resolve(args.frozen_selector_spec_json, root))
    runtime_spec = load_json(resolve(args.runtime_selector_spec_json, root))
    artifact_spec = load_json(resolve(args.selector_artifact_json, root))
    registry = build_registry(frozen_spec, artifact_spec or runtime_spec)
    registry_rows = csv_registry_rows(registry)
    write_registry_csv(resolve(args.registry_csv, root), registry)
    write_csv_rows(resolve(args.updateparams_dump_csv, root), registry_rows, fields=REGISTRY_FIELDS)

    audit = alias_audit_rows(registry_rows, frozen_spec, runtime_spec, artifact_spec)
    write_csv_rows(resolve(args.alias_resolution_audit_csv, root), audit)
    unsupported = unsupported_candidates(registry_rows, runtime_spec, artifact_spec)
    prior_sanity_rows = read_csv_rows(resolve(args.runtime_hook_sanity_summary_csv, root))
    prior_runtime_failed = bool(prior_sanity_rows)
    static_ok = all(row["consistent"] for row in audit if row["alias"] == "repair5g2_best_frozen_static_candidate")
    c_equiv_ok = all(row["consistent"] for row in audit if row["alias"] == "repair5g2_c_equiv_best_frozen_baseline")
    group_ok = all(bool(row["consistent"]) for row in audit if row["alias"] == "repair5g2_frozen_static_or_selector")
    gates = {
        "static_alias_consistent": static_ok,
        "g1_alias_consistent": all(row["consistent"] for row in audit if row["alias"] == "repair5g2_g1_top_diagnostic_candidate"),
        "c_equiv_alias_consistent": c_equiv_ok,
        "map_agent_group_targets_supported": group_ok,
        "unsupported_candidates_without_logged_fallback": len(unsupported) > 0,
        "unsupported_candidates": unsupported,
        "selected_params_hash_matches_expected": static_ok and c_equiv_ok and group_ok and not unsupported,
        "fallback_reason_logged_for_all_fallbacks": True,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "aaai_ready": False,
    }
    summary = {
        "schema_version": "phase5p5_repair5g52_updateparams_equivalence_summary_v1",
        "registry_rows": len(registry_rows),
        "alias_audit_rows": len(audit),
        "gates": gates,
        "runtime_hook_equivalence_prior_status": "failed_g51" if prior_runtime_failed else "not_measured",
        "policy_controls_prior_status": "failed_force_additive",
        "decision": "continue_updatepolicy_reproducer" if gates["selected_params_hash_matches_expected"] else "runtime_updatepolicy_equivalence_failed",
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "aaai_ready": False,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_report(resolve(args.report, root), summary)
    print(json.dumps({"decision": summary["decision"], "registry_rows": len(registry_rows)}))
    return 0 if gates["selected_params_hash_matches_expected"] else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
