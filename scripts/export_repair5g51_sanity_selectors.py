"""Export Repair5G.5.1 runtime hook sanity selector specs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g51_common import (  # noqa: E402
    DEFAULT_SANITY_SELECTOR_DIR,
    G51_ALWAYS_ADDITIVE,
    G51_ALWAYS_MAP_AGENT,
    G51_ALWAYS_STATIC,
    G51_BAD_G5_STUMP,
    load_json,
    rel,
    repo_root,
    resolve,
    sanity_selector_paths,
    selector_spec_payload,
    sha256_file,
    write_json,
    write_selector_artifact,
    write_text,
)


DEFAULT_G5_SPEC = "outputs/reports/phase5p5_repair5g5_runtime_contextual_selector_spec.json"
DEFAULT_FROZEN = "outputs/reports/phase5p5_repair5g2_frozen_selector_spec.json"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g51_sanity_selector_export_report.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g51_sanity_selector_export_summary.json"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--g5-selector-spec-json", type=Path, default=Path(DEFAULT_G5_SPEC))
    parser.add_argument("--frozen-selector-spec-json", type=Path, default=Path(DEFAULT_FROZEN))
    parser.add_argument("--selector-dir", type=Path, default=Path(DEFAULT_SANITY_SELECTOR_DIR))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    return parser.parse_args(argv)


def write_report(path: Path, summary: dict) -> None:
    lines = [
        "# Phase5.5 Repair5G.5.1 Sanity Selector Export Report",
        "",
        "The exported selectors validate that the runtime hook can execute known safe policies before any new learning claim.",
        "",
    ]
    for alias, info in sorted(summary["selectors"].items()):
        lines.append(f"- `{alias}`: `{info['selector_spec']}`")
    lines.extend(
        [
            "",
            "`phase5p5_allowed=false`, `phase6_allowed=false`, and `aaai_ready=false` remain closed.",
            "",
        ]
    )
    write_text(path, "\n".join(lines))


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    selector_dir = resolve(args.selector_dir, root)
    paths = sanity_selector_paths(root)
    g5_spec_path = resolve(args.g5_selector_spec_json, root)
    g5_spec = load_json(g5_spec_path)
    frozen = load_json(resolve(args.frozen_selector_spec_json, root))
    if not g5_spec:
        raise SystemExit("missing G5 selector spec")
    static_candidate = str(
        frozen.get("selected_static_candidate", "repair5g1_shield_c125_b125_w075_d095_beta0p35_max0p75")
    )
    c_equiv_candidate = str(
        frozen.get("selected_c_equiv_baseline", "repair5g_dual_c_equiv_c100_b100_w075_d100")
    )

    manifests = {}
    specs = {
        G51_ALWAYS_STATIC: selector_spec_payload(
            selector_name="repair5g51_always_static_flow_shield",
            left_method="repair5g2_best_frozen_static_candidate",
            right_method="repair5g2_best_frozen_static_candidate",
            fallback_static="repair5g2_best_frozen_static_candidate",
            policy_note="Always execute the validated G2/G4 static flow-shield candidate.",
            static_candidate=static_candidate,
            c_equiv_candidate=c_equiv_candidate,
        ),
        G51_ALWAYS_MAP_AGENT: selector_spec_payload(
            selector_name="repair5g51_always_map_agent_selector",
            left_method="repair5g2_frozen_static_or_selector",
            right_method="repair5g2_frozen_static_or_selector",
            fallback_static="repair5g2_frozen_static_or_selector",
            policy_note="Always execute the validated frozen map-agent flow-shield selector.",
            static_candidate=static_candidate,
            c_equiv_candidate=c_equiv_candidate,
        ),
        G51_ALWAYS_ADDITIVE: selector_spec_payload(
            selector_name="repair5g51_always_additive",
            left_method="additive_ltm",
            right_method="additive_ltm",
            fallback_static="additive_ltm",
            policy_note="Always defer to canonical additive UpdateLTM.",
            static_candidate=static_candidate,
            c_equiv_candidate=c_equiv_candidate,
        ),
    }
    for alias, payload in specs.items():
        manifests[alias] = write_selector_artifact(root, paths[alias].parent, payload)

    bad_dir = paths[G51_BAD_G5_STUMP].parent
    bad_dir.mkdir(parents=True, exist_ok=True)
    write_json(paths[G51_BAD_G5_STUMP], g5_spec)
    bad_manifest = {
        "schema_version": "phase5p5_repair5g51_selector_manifest_v1",
        "selector_spec": rel(paths[G51_BAD_G5_STUMP], root),
        "selector_spec_hash": sha256_file(paths[G51_BAD_G5_STUMP]),
        "source": rel(g5_spec_path, root),
        "negative_control": True,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "aaai_ready": False,
    }
    write_json(bad_dir / "export_manifest.json", bad_manifest)
    manifests[G51_BAD_G5_STUMP] = bad_manifest

    summary = {
        "schema_version": "phase5p5_repair5g51_sanity_selector_export_summary_v1",
        "selector_dir": rel(selector_dir, root),
        "selectors": {
            alias: {
                "selector_spec": rel(paths[alias], root),
                "selector_spec_hash": manifest["selector_spec_hash"],
            }
            for alias, manifest in sorted(manifests.items())
        },
        "diagnostic_only": True,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "aaai_ready": False,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_report(resolve(args.report, root), summary)
    print(json.dumps({"selectors": len(summary["selectors"])}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
