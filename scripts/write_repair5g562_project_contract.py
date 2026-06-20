from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gcst.representation_contract import (  # noqa: E402
    FLOOR_BEGIN,
    FLOOR_END,
    FORBIDDEN_REGRESSIONS,
    LITERATURE_SOURCES,
    MINIMUM_INPUTS,
    OFFICIAL_REPOS,
    REQUIRED_EVIDENCE,
    contract_markers_present,
    representation_floor_block,
)


ROUND = "phase5p5_repair5g562"
CONTRACT_REPORT = Path(f"outputs/reports/{ROUND}_project_contract_update.md")
LITERATURE_REPORT = Path(f"outputs/reports/{ROUND}_literature_method_audit.md")
LITERATURE_DECISIONS = Path(f"outputs/tables/{ROUND}_literature_design_decisions.csv")
REPO_MANIFEST = Path(f"outputs/tables/{ROUND}_official_repo_commit_manifest.csv")
CONTRACT_DOC = Path("docs/goal_aware_dual_channel_ltm_research_contract.md")
OUTLINE_PATHS = [
    Path("deep-research-report.md"),
    Path("phase4_6_laur_ltm_codex_execution_plan.md"),
]


def claims() -> dict[str, bool]:
    return {
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "runtime_claim_allowed": False,
        "learned_runtime_policy_validated": False,
        "aaai_ready": False,
    }


def resolve(path: str | Path) -> Path:
    p = Path(path)
    return p if p.is_absolute() else ROOT / p


def write_rows(path: str | Path, rows: list[dict[str, Any]]) -> None:
    p = resolve(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with p.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: str | Path, data: dict[str, Any]) -> None:
    p = resolve(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def replace_or_insert_block(text: str, block: str) -> str:
    if FLOOR_BEGIN in text and FLOOR_END in text:
        before, rest = text.split(FLOOR_BEGIN, 1)
        _old, after = rest.split(FLOOR_END, 1)
        return before.rstrip() + "\n\n" + block.rstrip() + "\n" + after.lstrip("\n")
    return block.rstrip() + "\n\n" + text


def update_outline(path: Path, block: str) -> dict[str, Any]:
    p = resolve(path)
    old = p.read_text(encoding="utf-8") if p.exists() else ""
    new = replace_or_insert_block(old, block)
    p.write_text(new, encoding="utf-8")
    return {
        "path": str(path).replace("\\", "/"),
        "markers_present": contract_markers_present(new),
        "minimum_inputs_recorded": all(item in new for item in MINIMUM_INPUTS),
        "forbidden_regressions_recorded": all(item in new for item in FORBIDDEN_REGRESSIONS),
        **claims(),
    }


def write_contract_doc(block: str) -> dict[str, Any]:
    text = (
        "# Goal-Aware Dual-Channel LTM Research Contract\n\n"
        "This document is the permanent project-level contract for the G5.62 "
        "real-label goal-aware graph actor line.\n\n"
        + block
    )
    path = resolve(CONTRACT_DOC)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return {
        "path": str(CONTRACT_DOC).replace("\\", "/"),
        "markers_present": contract_markers_present(text),
        "non_dagger_contract_recorded": "G5.62 is explicitly not DAgger" in text,
        **claims(),
    }


def write_literature_artifacts() -> None:
    decision_rows = []
    for source in LITERATURE_SOURCES:
        decision_rows.append(
            {
                "source_key": source.key,
                "title": source.title,
                "url": source.url,
                "version": source.version,
                "inspected_source": source.inspected_source,
                "adopted_lesson": source.adopted_lesson,
                "rejected_direction": source.rejected_direction,
                "decision": "adopt_representation_training_or_design_lesson_only",
                **claims(),
            }
        )
    write_rows(LITERATURE_DECISIONS, decision_rows)
    write_rows(REPO_MANIFEST, [{**row, **claims()} for row in OFFICIAL_REPOS])
    lines = [
        "# Repair5G.5.62 Literature and Source Audit",
        "",
        "The audit uses primary arXiv pages and official GitHub repositories. It improves representation, training, safeguards, and experimental design while keeping the project on one run-static continuous theta per instance.",
        "",
    ]
    for row in decision_rows:
        lines.extend(
            [
                f"## {row['source_key']}",
                "",
                f"- title: `{row['title']}`",
                f"- source: {row['url']}",
                f"- version: `{row['version']}`",
                f"- adopted: {row['adopted_lesson']}",
                f"- rejected: {row['rejected_direction']}",
                "",
            ]
        )
    lines.extend(
        [
            "## Official Repository Heads",
            "",
        ]
    )
    for repo in OFFICIAL_REPOS:
        lines.append(f"- `{repo['project']}`: `{repo['head_commit']}` from {repo['repo_url']}")
    lines.extend(
        [
            "",
            "No action imitation, DAgger, priority-order policy, restart policy, deployed optimizer, runtime-varying theta policy, or codebook selector is adopted.",
            "",
            "All Phase5.5, Phase6, runtime, learned-policy, and AAAI claims remain closed.",
        ]
    )
    path = resolve(LITERATURE_REPORT)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    block = representation_floor_block()
    outline_rows = [update_outline(path, block) for path in OUTLINE_PATHS]
    outline_rows.append(write_contract_doc(block))
    write_literature_artifacts()
    report = {
        "schema_version": f"{ROUND}_project_contract_update_v1",
        "decision": "g562_project_representation_floor_and_non_dagger_contract_recorded",
        "updated_paths": [row["path"] for row in outline_rows],
        "all_markers_present": all(bool(row["markers_present"]) for row in outline_rows),
        "minimum_inputs": MINIMUM_INPUTS,
        "forbidden_regressions": FORBIDDEN_REGRESSIONS,
        "required_evidence": REQUIRED_EVIDENCE,
        "literature_sources": [source.key for source in LITERATURE_SOURCES],
        **claims(),
    }
    lines = [
        "# Repair5G.5.62 Project Contract Update",
        "",
        f"- decision: `{report['decision']}`",
        f"- all markers present: `{report['all_markers_present']}`",
        f"- updated paths: `{', '.join(report['updated_paths'])}`",
        "",
        "G5.62 records the representation floor as a minimum input contract and explicitly forbids DAgger/action-label reinterpretations. Claims remain closed.",
    ]
    resolve(CONTRACT_REPORT).parent.mkdir(parents=True, exist_ok=True)
    resolve(CONTRACT_REPORT).write_text("\n".join(lines) + "\n", encoding="utf-8")
    write_json(Path(f"outputs/reports/{ROUND}_project_contract_update_summary.json"), report)
    print(json.dumps({"decision": report["decision"], "paths": report["updated_paths"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
