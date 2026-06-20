from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ROUND = "phase5p5_repair5g563"
REPORTS = ROOT / "outputs/reports"
TABLES = ROOT / "outputs/tables"
DECISION_JSON = REPORTS / f"{ROUND}_decision_summary.json"
DECISION_MD = REPORTS / f"{ROUND}_decision.md"
MANIFEST_JSON = REPORTS / f"{ROUND}_artifact_manifest.json"
CHECKSUMS = TABLES / f"{ROUND}_checksums.sha256"


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def read_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def artifact_rows() -> list[dict[str, Any]]:
    rows = []
    excluded = {MANIFEST_JSON.resolve(), CHECKSUMS.resolve()}
    for root in [REPORTS, TABLES, ROOT / "artifacts/models/gcst"]:
        if not root.exists():
            continue
        for path in sorted(root.glob(f"{ROUND}*")):
            if not path.is_file():
                continue
            if path.resolve() in excluded:
                continue
            rows.append(
                {
                    "path": str(path.relative_to(ROOT)).replace("\\", "/"),
                    "bytes": path.stat().st_size,
                    "sha256": sha256_file(path),
                }
            )
    return rows


def main() -> int:
    dataset = load_json(REPORTS / f"{ROUND}_labelv52_set_dataset_summary.json")
    tiny = load_json(REPORTS / f"{ROUND}_tiny_overfit_summary.json")
    scaling = load_json(REPORTS / f"{ROUND}_scaling_study_summary.json")
    scaling_rows = read_rows(TABLES / f"{ROUND}_scaling_study_results.csv")
    code_truth = (
        dataset.get("decision") == "g563_labelv52_set_dataset_ready"
        and dataset.get("positive_set_is_not_averaged") is True
        and dataset.get("censored_rows_are_negative") is False
        and dataset.get("grouped_split_hashes_disjoint") is True
    )
    overfit_passed = tiny.get("decision") == "g563_tiny_overfit_passed"
    scaling_positive = scaling.get("decision") == "g563_validation_loss_scales_with_context_count"
    if code_truth and overfit_passed and scaling_positive:
        decision = "g563_feasibility_supported_continue_scaleup"
    elif code_truth and overfit_passed:
        decision = "g563_validation_loss_flat_label_or_representation_blocker"
    elif code_truth:
        decision = "g563_tiny_overfit_failed_repair_model_or_loss"
    else:
        decision = "g563_incomplete_code_truth"
    summary = {
        "schema_version": f"{ROUND}_decision_summary_v1",
        "decision": decision,
        "code_truth_gate": code_truth,
        "tiny_overfit_gate": overfit_passed,
        "scaling_gate": scaling_positive,
        "labelv52_dataset_decision": dataset.get("decision", ""),
        "tiny_overfit_decision": tiny.get("decision", ""),
        "scaling_decision": scaling.get("decision", ""),
        "contexts": dataset.get("contexts"),
        "candidate_rows": dataset.get("candidate_rows"),
        "tiny_initial_loss": tiny.get("initial_loss"),
        "tiny_final_loss": tiny.get("final_loss"),
        "scaling_sizes": scaling.get("sizes", []),
        "scaling_rows": len(scaling_rows),
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "runtime_claim_allowed": False,
        "learned_runtime_policy_validated": False,
        "aaai_ready": False,
    }
    DECISION_JSON.parent.mkdir(parents=True, exist_ok=True)
    DECISION_JSON.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    DECISION_MD.write_text(
        "# G5.63 Decision\n\n"
        f"- decision: `{decision}`\n"
        f"- Label-v5.2 dataset: `{summary['labelv52_dataset_decision']}`\n"
        f"- tiny overfit: `{summary['tiny_overfit_decision']}`; loss `{summary['tiny_initial_loss']}` -> `{summary['tiny_final_loss']}`\n"
        f"- scaling: `{summary['scaling_decision']}`; sizes `{summary['scaling_sizes']}`\n"
        f"- contexts: `{summary['contexts']}`; candidate rows: `{summary['candidate_rows']}`\n\n"
        "Claims remain closed unless the fixed solver replay gate is run and passes with zero success-regression evidence.\n",
        encoding="utf-8",
    )
    manifest = artifact_rows()
    MANIFEST_JSON.write_text(json.dumps({"schema_version": f"{ROUND}_artifact_manifest_v1", "artifacts": manifest}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    CHECKSUMS.parent.mkdir(parents=True, exist_ok=True)
    CHECKSUMS.write_text("".join(f"{row['sha256']}  {row['path']}\n" for row in manifest), encoding="utf-8")
    print(json.dumps({"decision": decision, "code_truth_gate": code_truth, "tiny_overfit_gate": overfit_passed, "scaling_gate": scaling_positive}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
