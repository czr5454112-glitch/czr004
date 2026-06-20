from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ROUND = "phase5p5_repair5g562"
REPORTS = ROOT / "outputs/reports"
TABLES = ROOT / "outputs/tables"
FAILURE_MD = REPORTS / f"{ROUND}_failure_attribution.md"
DECISION_MD = REPORTS / f"{ROUND}_decision.md"
DECISION_JSON = REPORTS / f"{ROUND}_decision_summary.json"
MANIFEST_JSON = REPORTS / f"{ROUND}_artifact_manifest.json"
CHECKSUMS = TABLES / f"{ROUND}_checksums.sha256"


def claims() -> dict[str, bool]:
    return {
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "runtime_claim_allowed": False,
        "learned_runtime_policy_validated": False,
        "aaai_ready": False,
    }


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def read_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def number(value: Any, default: float = 0.0) -> float:
    try:
        out = float(value)
    except Exception:
        return default
    return out if math.isfinite(out) else default


def boolish(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def manifest_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for root in [REPORTS, TABLES, ROOT / "artifacts/models/gcst"]:
        if not root.exists():
            continue
        for path in sorted(root.glob(f"{ROUND}*")):
            if not path.is_file():
                continue
            rows.append(
                {
                    "path": str(path.relative_to(ROOT)).replace("\\", "/"),
                    "bytes": path.stat().st_size,
                    "sha256": sha256_file(path),
                }
            )
        if root.name == "gcst":
            for path in sorted(root.glob("g562_*")):
                if path.is_file():
                    rows.append(
                        {
                            "path": str(path.relative_to(ROOT)).replace("\\", "/"),
                            "bytes": path.stat().st_size,
                            "sha256": sha256_file(path),
                        }
                    )
    dedup: dict[str, dict[str, Any]] = {}
    for row in rows:
        dedup[row["path"]] = row
    return list(dedup.values())


def cycle_summaries() -> list[dict[str, Any]]:
    return [
        load_json(REPORTS / f"{ROUND}_cycle1_summary.json"),
        load_json(REPORTS / f"{ROUND}_cycle2_summary.json"),
        load_json(REPORTS / f"{ROUND}_cycle3_summary.json"),
    ]


def best_method_from_cycle3() -> dict[str, Any]:
    cycle3 = load_json(REPORTS / f"{ROUND}_cycle3_summary.json")
    methods = cycle3.get("by_method", []) if isinstance(cycle3.get("by_method"), list) else []
    if not methods:
        methods = read_rows(TABLES / f"{ROUND}_replay_by_method.csv")
    if not methods:
        return {}
    return min(
        methods,
        key=lambda row: (
            int(number(row.get("success_regressions"), 10**9)),
            number(row.get("mean_quality_delta_vs_g556"), 10**9),
            -int(number(row.get("better_count_vs_g556"), 0)),
            str(row.get("method", "")),
        ),
    )


def promotion_gate(method: dict[str, Any]) -> bool:
    if not method:
        return False
    return (
        int(number(method.get("success_regressions"), 1)) == 0
        and number(method.get("mean_quality_delta_vs_g556"), 1.0) < 0.0
        and number(method.get("quality_delta_ci_upper_vs_g556"), 1.0) <= 0.0
        and int(number(method.get("better_count_vs_g556"), 0)) > int(number(method.get("worse_count_vs_g556"), 0))
    )


def main() -> int:
    dataset = load_json(REPORTS / f"{ROUND}_real_graph_dataset_summary.json")
    actor = load_json(REPORTS / f"{ROUND}_actor_training_summary.json")
    critic = load_json(REPORTS / f"{ROUND}_critic_training_summary.json")
    oracle = load_json(REPORTS / f"{ROUND}_valid_oracle_summary.json")
    alpha = load_json(REPORTS / f"{ROUND}_alpha_response_summary.json")
    teacher = load_json(REPORTS / f"{ROUND}_optimizer_teacher_summary.json")
    cycles = cycle_summaries()
    exact_rows = sum(int(number(cycle.get("new_exact_materialized_candidate_rows"), 0)) for cycle in cycles)
    exact_contexts = max([int(number(cycle.get("unique_valid_contexts"), 0)) for cycle in cycles] or [0])
    best = best_method_from_cycle3()
    gate = promotion_gate(best)
    required_evidence_present = all(
        [
            dataset.get("decision") == "g562_real_graph_dataset_ready",
            actor.get("decision") == "g562_real_safe_set_actor_training_completed",
            critic.get("decision") == "g562_real_graph_critic_calibrated",
            len([cycle for cycle in cycles if cycle.get("decision") == "g562_cycle_replay_completed_exact_materialization"]) >= 2,
            exact_rows >= 12000,
            exact_contexts >= 800,
        ]
    )
    if gate and required_evidence_present:
        decision = "g562_direct_graph_actor_promotion_candidate_keep_claims_closed"
    elif required_evidence_present:
        decision = "g562_rich_actor_no_supported_gain_continue_representation_or_label_repair"
    else:
        decision = "g562_incomplete_evidence_continue"

    summary = {
        "schema_version": f"{ROUND}_decision_summary_v1",
        "decision": decision,
        "primary_baseline": "g556_c063174",
        "paper_faithful_floor": "LaCAM* + additive LTM",
        "dataset_contexts": dataset.get("contexts"),
        "positive_contexts": dataset.get("positive_contexts"),
        "valid_oracle_decision": oracle.get("decision"),
        "actor_rows": actor.get("rows"),
        "three_seed_top_rich_complete": actor.get("three_seed_top_rich_complete"),
        "critic_decision": critic.get("decision"),
        "alpha_response_decision": alpha.get("decision"),
        "optimizer_teacher_decision": teacher.get("decision"),
        "exact_materialized_candidate_rows": exact_rows,
        "max_exact_contexts": exact_contexts,
        "best_cycle3_method": best,
        "promotion_gate_passed": gate,
        "required_evidence_present": required_evidence_present,
        **claims(),
    }
    DECISION_JSON.parent.mkdir(parents=True, exist_ok=True)
    DECISION_JSON.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    FAILURE_MD.write_text(
        "# G5.62 Failure Attribution\n\n"
        f"- decision: `{decision}`\n"
        f"- exact materialized candidate rows: `{exact_rows}`\n"
        f"- max exact contexts: `{exact_contexts}`\n"
        f"- best cycle3 method: `{best.get('method', '')}`\n"
        f"- best mean quality delta vs g556: `{best.get('mean_quality_delta_vs_g556', '')}`\n"
        f"- best success regressions: `{best.get('success_regressions', '')}`\n\n"
        "If the promotion gate is not met, the failure is attributed only to exact solver evidence: success regression, mean/CI quality, better/worse balance, or incomplete materialization. It is not inferred from offline loss, critic score, or checkpoint existence.\n",
        encoding="utf-8",
    )
    DECISION_MD.write_text(
        "# G5.62 Decision\n\n"
        f"- decision: `{decision}`\n"
        f"- primary baseline: `g556_c063174`\n"
        f"- dataset contexts: `{summary['dataset_contexts']}`\n"
        f"- positive contexts: `{summary['positive_contexts']}`\n"
        f"- actor rows: `{summary['actor_rows']}`\n"
        f"- critic decision: `{summary['critic_decision']}`\n"
        f"- exact materialized candidate rows: `{exact_rows}`\n"
        f"- promotion gate passed: `{gate}`\n\n"
        "Phase5.5, Phase6, runtime, learned-runtime-policy, and AAAI claims remain closed.\n",
        encoding="utf-8",
    )
    manifest = manifest_rows()
    MANIFEST_JSON.write_text(json.dumps({"schema_version": f"{ROUND}_artifact_manifest_v1", "artifacts": manifest}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    CHECKSUMS.parent.mkdir(parents=True, exist_ok=True)
    CHECKSUMS.write_text("".join(f"{row['sha256']}  {row['path']}\n" for row in manifest), encoding="utf-8")
    print(json.dumps({"decision": decision, "exact_rows": exact_rows, "promotion_gate_passed": gate}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
