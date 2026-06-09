from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from czr004_teacher.attention_native_labels_laur import (  # noqa: E402
    build_attention_native_rows,
    compute_attention_native_target,
)
from czr004_teacher.attention_native_schema_laur import (  # noqa: E402
    audit_attention_native_rows,
    validate_attention_native_row,
)
from czr004_teacher.attention_native_union_laur import combine_attention_native_datasets  # noqa: E402
from czr004_teacher.stable_attention_dataset_laur import write_jsonl  # noqa: E402
from czr004_teacher.stable_attention_tokens_laur import EXECUTABLE_RULE_IDS  # noqa: E402


def _checkpoint() -> dict:
    return {
        "schema_version": "phase4_laur_checkpoint_v1",
        "run_id": "run-1",
        "checkpoint_id": "run-1__iter0",
        "split": "validation",
        "map_name": "empty-16-16",
        "map_path": "external/lacam2/scripts/map/empty-16-16.map",
        "agents": 50,
        "seed": 1,
        "time_limit_sec": 3,
        "max_iterations": 4,
        "iteration": 0,
        "solution_found_this_iteration": True,
        "sum_of_loss_this_iteration": 120,
        "sum_of_loss_ratio_this_iteration": 1.2,
        "trace_event_count": 15,
        "committed_count": 10,
        "blocked_count": 5,
        "wait_event_count": 2,
        "goal_wait_ignored_count": 1,
        "traffic_before_nonzero_edges": 2,
        "traffic_before_max_raw": 4,
        "raw_before_topk": [{"from_id": 1, "to_id": 2, "raw": 4}],
        "raw_after_topk": [{"from_id": 1, "to_id": 2, "raw": 7}],
        "normalized_after_topk": [{"from_id": 1, "to_id": 2, "weight": 10}],
    }


def _probe(rule_id: str, delta: float, harmful: bool = False, solution_found: bool = True) -> dict:
    return {
        "schema_version": "phase4_laur_update_label_v1",
        "run_id": "run-1",
        "checkpoint_id": "run-1__iter0",
        "rule_id": rule_id,
        "delta_ratio_vs_additive": delta,
        "harmful": harmful,
        "solution_found": solution_found,
        "feasible": solution_found,
    }


def _probes() -> list[dict]:
    return [
        _probe("additive_ltm", 0.0),
        _probe("commit_heavy", 0.030),
        _probe("block_heavy", 0.200, harmful=True),
        _probe("block_light", 0.005),
        _probe("wait_light", 0.0),
        _probe("wait_heavy", -0.001),
        _probe("decay_095", 0.0),
        _probe("decay_090", 0.0),
    ]


def _probes_for(run_id: str, checkpoint_id: str) -> list[dict]:
    return [{**row, "run_id": run_id, "checkpoint_id": checkpoint_id} for row in _probes()]


def test_attention_native_target_prefers_safe_nonadditive_over_harmful_high_delta() -> None:
    target = compute_attention_native_target(_probes())

    assert target["decision_target"] == "use_nonadditive"
    assert target["target_rule"] == "commit_heavy"
    assert target["has_nonadditive_opportunity"] is True
    assert target["has_high_margin_nonadditive_opportunity"] is True
    assert target["anti_escape_candidate_mask"][EXECUTABLE_RULE_IDS.index("commit_heavy")] == 1
    assert target["safe_rule_mask"][EXECUTABLE_RULE_IDS.index("block_heavy")] == 0


def test_attention_native_dataset_schema_keeps_defer_out_of_executable_vocab() -> None:
    rows = build_attention_native_rows(
        [_checkpoint()],
        _probes(),
        repo_root_path=ROOT,
        max_edge_tokens=4,
        max_trace_tokens=4,
    )
    row = rows[0]

    assert validate_attention_native_row(row) == []
    assert row["schema_version"] == "phase4_laur_attention_native_label_dataset_v1"
    assert row["rule_ids"] == EXECUTABLE_RULE_IDS
    assert "defer_ltm" not in row["rule_ids"]
    assert row["target"]["attention_target_rule"] == "commit_heavy"


def test_attention_native_defer_label_is_meta_decision_not_additive_top1() -> None:
    probes = [
        _probe("additive_ltm", 0.0),
        _probe("commit_heavy", 0.001),
        _probe("block_heavy", -0.010, harmful=True),
        _probe("block_light", 0.0),
        _probe("wait_light", 0.0),
        _probe("wait_heavy", -0.001),
        _probe("decay_095", 0.0),
        _probe("decay_090", 0.0),
    ]

    row = build_attention_native_rows(
        [_checkpoint()],
        probes,
        repo_root_path=ROOT,
        max_edge_tokens=4,
        max_trace_tokens=4,
    )[0]

    assert validate_attention_native_row(row) == []
    assert row["decision_target"] == "defer_ltm"
    assert row["target"]["attention_target_rule"] is None
    assert row["target"]["target_rule_index"] >= 0


def test_attention_native_audit_reports_opportunity_counts_and_no_leakage() -> None:
    rows = build_attention_native_rows(
        [_checkpoint()],
        _probes(),
        repo_root_path=ROOT,
        max_edge_tokens=4,
        max_trace_tokens=4,
    )
    audit = audit_attention_native_rows(rows)

    assert audit["passed"] is True
    assert audit["validation_high_margin_opportunity_count"] == 1
    assert audit["split_diagnostics"]["validation"]["sample_count"] == 1
    assert audit["split_diagnostics"]["validation"]["decision_distribution"] == {"use_nonadditive": 1}
    assert audit["split_diagnostics"]["validation"]["target_rule_distribution"] == {"commit_heavy": 1}
    assert audit["split_diagnostics"]["validation"]["high_margin_nonadditive_opportunity_count"] == 1
    assert audit["schema_error_count"] == 0
    assert audit["split_leakage_error_count"] == 0


def test_attention_native_union_combines_compatible_datasets(tmp_path: Path) -> None:
    checkpoint_a = _checkpoint()
    checkpoint_b = {**_checkpoint(), "run_id": "run-2", "checkpoint_id": "run-2__iter0", "seed": 2}
    rows_a = build_attention_native_rows(
        [checkpoint_a],
        _probes_for("run-1", "run-1__iter0"),
        repo_root_path=ROOT,
        max_edge_tokens=4,
        max_trace_tokens=4,
    )
    rows_b = build_attention_native_rows(
        [checkpoint_b],
        _probes_for("run-2", "run-2__iter0"),
        repo_root_path=ROOT,
        max_edge_tokens=4,
        max_trace_tokens=4,
    )
    path_a = tmp_path / "a.jsonl"
    path_b = tmp_path / "b.jsonl"
    write_jsonl(path_a, rows_a)
    write_jsonl(path_b, rows_b)

    rows, summary = combine_attention_native_datasets([path_a, path_b])

    assert len(rows) == 2
    assert {row["checkpoint_id"] for row in rows} == {"run-1__iter0", "run-2__iter0"}
    assert {row["union_source"] for row in rows} == {"input1:a", "input2:b"}
    assert summary["passed"] is True
    assert summary["validation_high_margin_opportunity_count"] == 2
    assert summary["duplicate_checkpoint_count"] == 0


def test_attention_native_union_rejects_duplicate_checkpoint_by_default(tmp_path: Path) -> None:
    rows = build_attention_native_rows([_checkpoint()], _probes(), repo_root_path=ROOT, max_edge_tokens=4, max_trace_tokens=4)
    path_a = tmp_path / "a.jsonl"
    path_b = tmp_path / "b.jsonl"
    write_jsonl(path_a, rows)
    write_jsonl(path_b, rows)

    try:
        combine_attention_native_datasets([path_a, path_b])
    except ValueError as exc:
        assert "duplicate checkpoint_id" in str(exc)
    else:
        raise AssertionError("expected duplicate checkpoint rejection")


def test_attention_native_union_rejects_token_shape_mismatch(tmp_path: Path) -> None:
    checkpoint_a = _checkpoint()
    checkpoint_b = {**_checkpoint(), "run_id": "run-2", "checkpoint_id": "run-2__iter0", "seed": 2}
    rows_a = build_attention_native_rows(
        [checkpoint_a],
        _probes_for("run-1", "run-1__iter0"),
        repo_root_path=ROOT,
        max_edge_tokens=4,
        max_trace_tokens=4,
    )
    rows_b = build_attention_native_rows(
        [checkpoint_b],
        _probes_for("run-2", "run-2__iter0"),
        repo_root_path=ROOT,
        max_edge_tokens=4,
        max_trace_tokens=5,
    )
    path_a = tmp_path / "a.jsonl"
    path_b = tmp_path / "b.jsonl"
    write_jsonl(path_a, rows_a)
    write_jsonl(path_b, rows_b)

    try:
        combine_attention_native_datasets([path_a, path_b])
    except ValueError as exc:
        assert "incompatible attention-native token shape" in str(exc)
    else:
        raise AssertionError("expected token shape mismatch rejection")
