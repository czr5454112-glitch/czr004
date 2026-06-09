from __future__ import annotations

import csv
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ADDENDUM = ROOT / "czr004_learning_insertion_strategy_grand_plan_addendum.md"
TARGET_DOCS = [
    ROOT / "deep-research-report.md",
    ROOT / "phase4_6_laur_ltm_codex_execution_plan.md",
    ROOT / "docs" / "aaai_quality_requirements.md",
]
WORKLOG = ROOT / "docs" / "codex-worklog.md"
SUMMARY_JSON = (
    ROOT / "outputs" / "reports" / "phase5p5_repair5g_learning_insertion_strategy_summary.json"
)
STRATEGY_REPORT = (
    ROOT / "outputs" / "reports" / "phase5p5_repair5g_learning_insertion_strategy.md"
)
ROUTE_CSV = ROOT / "outputs" / "tables" / "phase5p5_repair5g_learning_route_comparison.csv"
STAGE_CSV = ROOT / "outputs" / "tables" / "phase5p5_repair5g_learning_stage_ladder.csv"

BEGIN = "## BEGIN VERBATIM GRAND-PLAN ADDENDUM"
END = "## END VERBATIM GRAND-PLAN ADDENDUM"
TITLE = "## 2026-06 Repair5G learning-insertion strategy for top-tier AI / MAPF venues"

REQUIRED_SUMMARY_VALUES = {
    "grand_plan_addendum_inserted": True,
    "learning_insertion_point": "UpdateLTM dynamics, not action policy",
    "preferred_top_venue_route": "safe learned bounded dual-channel parameter/residual policy",
    "selector_role": "safety bridge and fallback layer, not final paper method",
    "advanced_neural_stage": "only after counterfactual UpdateLTM labels and safe runtime bridge",
    "phase5p5_allowed": False,
    "phase6_allowed": False,
    "aaai_ready": False,
}

ROUTE_HEADERS = {
    "route",
    "description",
    "top_venue_attractiveness",
    "current_readiness",
    "main_risk",
    "project_decision",
}
STAGE_HEADERS = {
    "stage",
    "goal",
    "allowed_model_class",
    "required_inputs",
    "required_gates",
    "blocked_until",
}


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def read_text(path: Path) -> str:
    if not path.exists():
        raise AssertionError(f"missing required file: {rel(path)}")
    return path.read_text(encoding="utf-8")


def extract_addendum_block() -> str:
    text = read_text(ADDENDUM)
    if BEGIN not in text or END not in text:
        raise AssertionError("addendum source is missing verbatim markers")
    block = text.split(BEGIN, 1)[1].split(END, 1)[0].strip("\r\n")
    if not block.startswith(TITLE):
        raise AssertionError("verbatim block does not start with the required title")
    return block


def check_target_docs(block: str) -> None:
    for path in TARGET_DOCS:
        text = read_text(path)
        if TITLE not in text:
            raise AssertionError(f"{rel(path)} is missing the core addendum title")
        if block not in text:
            raise AssertionError(f"{rel(path)} does not contain the exact verbatim addendum block")


def check_summary() -> None:
    data = json.loads(read_text(SUMMARY_JSON))
    for key, expected in REQUIRED_SUMMARY_VALUES.items():
        actual = data.get(key)
        if actual != expected:
            raise AssertionError(
                f"{rel(SUMMARY_JSON)} has {key}={actual!r}, expected {expected!r}"
            )


def check_csv(path: Path, required_headers: set[str], min_rows: int) -> None:
    if not path.exists():
        raise AssertionError(f"missing required CSV: {rel(path)}")
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        headers = set(reader.fieldnames or [])
        missing = required_headers - headers
        if missing:
            raise AssertionError(f"{rel(path)} missing headers: {sorted(missing)}")
        rows = list(reader)
    if len(rows) < min_rows:
        raise AssertionError(f"{rel(path)} has {len(rows)} rows, expected at least {min_rows}")


def main() -> int:
    block = extract_addendum_block()
    check_target_docs(block)
    check_summary()
    check_csv(ROUTE_CSV, ROUTE_HEADERS, min_rows=8)
    check_csv(STAGE_CSV, STAGE_HEADERS, min_rows=4)
    read_text(STRATEGY_REPORT)
    worklog = read_text(WORKLOG)
    if "Repair5G learning insertion strategy grand-plan addendum" not in worklog:
        raise AssertionError("worklog is missing the learning insertion strategy entry")
    print("OK: Repair5G learning strategy docs are consistent.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
