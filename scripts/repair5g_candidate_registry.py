"""Repair5G candidate registry and UpdateParams hash dump.

This file mirrors the project-owned C++ mapping in ``cpp/tools/phase1a_batch.cpp``
for the Repair5G candidates used by G5.2 diagnostics. It intentionally keeps the
registry small and explicit: unsupported candidates must be visible in audits
instead of silently drifting to additive behavior.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g3_common import load_json, repo_root, resolve, write_json  # noqa: E402


DEFAULT_FROZEN_SPEC = "outputs/reports/phase5p5_repair5g2_frozen_selector_spec.json"
DEFAULT_SELECTOR_SPEC = (
    "artifacts/models/laur_ltm/repair5g5_contextual_flow_shield_selector/"
    "selector_spec.json"
)
DEFAULT_CSV = "outputs/tables/phase5p5_repair5g_candidate_registry.csv"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g_candidate_registry_summary.json"

REGISTRY_FIELDS = [
    "method_name",
    "canonical_candidate_id",
    "component",
    "enable_dual_channel",
    "alpha_cong_commit_progress",
    "alpha_cong_commit_nonprogress",
    "alpha_cong_block",
    "alpha_cong_wait_progress",
    "alpha_cong_wait_nonprogress",
    "alpha_flow_commit_progress",
    "alpha_flow_wait_progress",
    "rho_cong_decay",
    "rho_flow_decay",
    "lambda_cong",
    "lambda_flow",
    "min_edge_cost",
    "max_edge_cost",
    "goal_projection_mode",
    "flow_shield_beta",
    "max_flow_shield",
    "fallback_behavior",
    "is_alias",
    "alias_target",
    "updateparams_hash",
]


@dataclass(frozen=True)
class RegistryRow:
    method_name: str
    canonical_candidate_id: str
    component: str
    enable_dual_channel: bool
    alpha_cong_commit_progress: float
    alpha_cong_commit_nonprogress: float
    alpha_cong_block: float
    alpha_cong_wait_progress: float
    alpha_cong_wait_nonprogress: float
    alpha_flow_commit_progress: float
    alpha_flow_wait_progress: float
    rho_cong_decay: float
    rho_flow_decay: float
    lambda_cong: float
    lambda_flow: float
    min_edge_cost: float
    max_edge_cost: float
    goal_projection_mode: str
    flow_shield_beta: float
    max_flow_shield: float
    fallback_behavior: str = ""
    is_alias: bool = False
    alias_target: str = ""

    @property
    def updateparams_hash(self) -> str:
        return updateparams_hash(asdict(self))

    def to_csv_row(self) -> dict[str, Any]:
        row = asdict(self)
        row["updateparams_hash"] = self.updateparams_hash
        return row


def updateparams_hash(row: dict[str, Any]) -> str:
    payload = {
        key: row[key]
        for key in REGISTRY_FIELDS
        if key not in {"method_name", "canonical_candidate_id", "component", "fallback_behavior", "is_alias", "alias_target", "updateparams_hash"}
        and key in row
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def additive_row(method_name: str, *, component: str = "control") -> RegistryRow:
    return RegistryRow(
        method_name=method_name,
        canonical_candidate_id=method_name,
        component=component,
        enable_dual_channel=False,
        alpha_cong_commit_progress=0.0,
        alpha_cong_commit_nonprogress=1.0,
        alpha_cong_block=1.0,
        alpha_cong_wait_progress=1.0,
        alpha_cong_wait_nonprogress=1.0,
        alpha_flow_commit_progress=0.0,
        alpha_flow_wait_progress=0.0,
        rho_cong_decay=1.0,
        rho_flow_decay=1.0,
        lambda_cong=1.0,
        lambda_flow=0.0,
        min_edge_cost=0.25,
        max_edge_cost=11.0,
        goal_projection_mode="none",
        flow_shield_beta=0.0,
        max_flow_shield=0.0,
        fallback_behavior="canonical_additive_ltm",
    )


def parse_decimal_token(token: str) -> float:
    return float(token.replace("p", "."))


def parse_scalar_rule(rule_id: str) -> tuple[float, float, float, float] | None:
    if rule_id == "additive":
        return (1.0, 1.0, 1.0, 1.0)
    match = re.fullmatch(r"c(\d{3})_b(\d{3})_w(\d{3})_d(\d{3})", rule_id)
    if not match:
        return None
    return tuple(float(group) / 100.0 for group in match.groups())  # type: ignore[return-value]


def c_equiv_row(method_name: str, rule_id: str, *, component: str = "c_equiv_baseline") -> RegistryRow | None:
    scalar = parse_scalar_rule(rule_id)
    if scalar is None:
        return None
    alpha_commit, alpha_block, alpha_wait, rho_decay = scalar
    return RegistryRow(
        method_name=method_name,
        canonical_candidate_id=method_name,
        component=component,
        enable_dual_channel=True,
        alpha_cong_commit_progress=alpha_commit,
        alpha_cong_commit_nonprogress=alpha_commit,
        alpha_cong_block=alpha_block,
        alpha_cong_wait_progress=alpha_wait,
        alpha_cong_wait_nonprogress=alpha_wait,
        alpha_flow_commit_progress=0.0,
        alpha_flow_wait_progress=0.0,
        rho_cong_decay=rho_decay,
        rho_flow_decay=1.0,
        lambda_cong=1.0,
        lambda_flow=0.0,
        min_edge_cost=0.25,
        max_edge_cost=11.0,
        goal_projection_mode="none",
        flow_shield_beta=0.0,
        max_flow_shield=0.0,
    )


def flow_shield_row(method_name: str) -> RegistryRow | None:
    prefix = "repair5g1_shield_"
    if not method_name.startswith(prefix):
        return None
    match = re.fullmatch(r"repair5g1_shield_(.+)_beta([^_]+)_max(.+)", method_name)
    if not match:
        return None
    scalar = parse_scalar_rule(match.group(1))
    if scalar is None:
        return None
    alpha_commit, alpha_block, alpha_wait, rho_decay = scalar
    return RegistryRow(
        method_name=method_name,
        canonical_candidate_id=method_name,
        component="flow_shield",
        enable_dual_channel=True,
        alpha_cong_commit_progress=alpha_commit,
        alpha_cong_commit_nonprogress=alpha_commit,
        alpha_cong_block=alpha_block,
        alpha_cong_wait_progress=alpha_wait,
        alpha_cong_wait_nonprogress=alpha_wait,
        alpha_flow_commit_progress=1.0,
        alpha_flow_wait_progress=0.0,
        rho_cong_decay=rho_decay,
        rho_flow_decay=1.0,
        lambda_cong=1.0,
        lambda_flow=0.0,
        min_edge_cost=1.0,
        max_edge_cost=11.0,
        goal_projection_mode="flow_shield",
        flow_shield_beta=parse_decimal_token(match.group(2)),
        max_flow_shield=parse_decimal_token(match.group(3)),
    )


def direct_candidate_row(method_name: str) -> RegistryRow | None:
    if method_name in {
        "additive_ltm",
        "always_additive_defer",
        "repair5f_candidate_additive_ltm",
        "laur_disable",
        "laur_force_additive_direct",
        "repair5g_dual_additive_parity",
        "repair5g_dual_c_equiv_additive",
        "repair5g52_runtime_force_additive_exact",
        "repair5g52_runtime_disable_exact",
    }:
        return additive_row(method_name)
    if method_name.startswith("repair5g_dual_c_equiv_"):
        return c_equiv_row(method_name, method_name.removeprefix("repair5g_dual_c_equiv_"))
    return flow_shield_row(method_name)


def alias_row(method_name: str, target: str, target_row: RegistryRow | None, *, component: str) -> RegistryRow:
    if target_row is None:
        return RegistryRow(
            method_name=method_name,
            canonical_candidate_id=target,
            component=component,
            enable_dual_channel=False,
            alpha_cong_commit_progress=0.0,
            alpha_cong_commit_nonprogress=1.0,
            alpha_cong_block=1.0,
            alpha_cong_wait_progress=1.0,
            alpha_cong_wait_nonprogress=1.0,
            alpha_flow_commit_progress=0.0,
            alpha_flow_wait_progress=0.0,
            rho_cong_decay=1.0,
            rho_flow_decay=1.0,
            lambda_cong=1.0,
            lambda_flow=0.0,
            min_edge_cost=0.25,
            max_edge_cost=11.0,
            goal_projection_mode="none",
            flow_shield_beta=0.0,
            max_flow_shield=0.0,
            fallback_behavior="unsupported_alias_target_requires_logged_fallback",
            is_alias=True,
            alias_target=target,
        )
    data = asdict(target_row)
    data.update(
        {
            "method_name": method_name,
            "canonical_candidate_id": target,
            "component": component,
            "fallback_behavior": "alias_resolved",
            "is_alias": True,
            "alias_target": target,
        }
    )
    return RegistryRow(**{key: data[key] for key in RegistryRow.__dataclass_fields__})


def candidate_names_from_specs(frozen_spec: dict[str, Any], selector_spec: dict[str, Any]) -> list[str]:
    names: list[str] = [
        "additive_ltm",
        "always_additive_defer",
        "repair5f_candidate_additive_ltm",
        "laur_disable",
        "laur_force_additive_direct",
        "repair5g_dual_additive_parity",
        "repair5g_dual_c_equiv_additive",
        "repair5g_dual_c_equiv_c100_b100_w075_d090",
        "repair5g_dual_c_equiv_c100_b100_w075_d095",
        "repair5g_dual_c_equiv_c100_b100_w075_d100",
        "repair5g_dual_c_equiv_c100_b100_w100_d090",
        "repair5g_dual_c_equiv_c100_b125_w075_d100",
        "repair5g_dual_c_equiv_c125_b125_w075_d095",
    ]
    for key in [
        "selected_static_candidate",
        "selected_group_selector_default_candidate",
        "selected_c_equiv_baseline",
        "g1_top_diagnostic_candidate",
    ]:
        if frozen_spec.get(key):
            names.append(str(frozen_spec[key]))
    for rule in frozen_spec.get("group_rules", []):
        if rule.get("candidate"):
            names.append(str(rule["candidate"]))
    names.extend(str(value) for value in selector_spec.get("candidate_set", []))
    aliases = selector_spec.get("candidate_aliases", {})
    names.extend(str(value) for value in aliases.values())
    return list(dict.fromkeys(name for name in names if name))


def build_registry(frozen_spec: dict[str, Any] | None = None, selector_spec: dict[str, Any] | None = None) -> list[RegistryRow]:
    frozen_spec = frozen_spec or {}
    selector_spec = selector_spec or {}
    by_name: dict[str, RegistryRow] = {}
    for name in candidate_names_from_specs(frozen_spec, selector_spec):
        row = direct_candidate_row(name)
        if row is not None:
            by_name[name] = row

    static_target = str(
        frozen_spec.get("selected_static_candidate")
        or selector_spec.get("candidate_aliases", {}).get("repair5g2_best_frozen_static_candidate")
        or "repair5g1_shield_c125_b125_w075_d095_beta0p35_max0p75"
    )
    c_equiv_target = str(
        frozen_spec.get("selected_c_equiv_baseline")
        or selector_spec.get("candidate_aliases", {}).get("repair5g2_c_equiv_best_frozen_baseline")
        or "repair5g_dual_c_equiv_c100_b100_w075_d100"
    )
    g1_target = str(frozen_spec.get("g1_top_diagnostic_candidate") or static_target)
    for target in [static_target, c_equiv_target, g1_target]:
        if target not in by_name:
            direct = direct_candidate_row(target)
            if direct is not None:
                by_name[target] = direct

    for alias, target, component in [
        ("repair5g2_best_frozen_static_candidate", static_target, "frozen_static_alias"),
        ("repair5g2_g1_top_diagnostic_candidate", g1_target, "g1_top_alias"),
        ("repair5g2_c_equiv_best_frozen_baseline", c_equiv_target, "c_equiv_alias"),
    ]:
        by_name[alias] = alias_row(alias, target, by_name.get(target) or direct_candidate_row(target), component=component)

    group_default = str(frozen_spec.get("selected_group_selector_default_candidate") or static_target)
    by_name["repair5g2_frozen_static_or_selector"] = alias_row(
        "repair5g2_frozen_static_or_selector",
        group_default,
        by_name.get(group_default) or direct_candidate_row(group_default),
        component="map_agent_group_selector_alias",
    )
    object.__setattr__(
        by_name["repair5g2_frozen_static_or_selector"],
        "fallback_behavior",
        "map_agent_group_selector; see frozen spec group_rules",
    )

    return [by_name[name] for name in sorted(by_name)]


def write_csv(path: Path, rows: list[RegistryRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=REGISTRY_FIELDS, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(row.to_csv_row())


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frozen-selector-spec-json", type=Path, default=Path(DEFAULT_FROZEN_SPEC))
    parser.add_argument("--selector-spec-json", type=Path, default=Path(DEFAULT_SELECTOR_SPEC))
    parser.add_argument("--output-csv", type=Path, default=Path(DEFAULT_CSV))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    frozen_spec = load_json(resolve(args.frozen_selector_spec_json, root))
    selector_spec = load_json(resolve(args.selector_spec_json, root))
    rows = build_registry(frozen_spec, selector_spec)
    write_csv(resolve(args.output_csv, root), rows)
    summary = {
        "schema_version": "phase5p5_repair5g_candidate_registry_summary_v1",
        "candidate_rows": len(rows),
        "alias_rows": sum(1 for row in rows if row.is_alias),
        "unsupported_alias_targets": [
            row.method_name
            for row in rows
            if row.is_alias and row.fallback_behavior.startswith("unsupported")
        ],
        "registry_csv": str(resolve(args.output_csv, root)),
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "aaai_ready": False,
    }
    write_json(resolve(args.summary_json, root), summary)
    print(json.dumps({"candidate_rows": len(rows), "alias_rows": summary["alias_rows"]}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
