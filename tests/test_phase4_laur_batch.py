from scripts.run_phase4_laur_batch import phase4f_performance_gate, record_command
from scripts.run_phase4_laur_batch import expanded_runs


def test_record_command_can_disable_raw_trace_export() -> None:
    config = {
        "binary": "phase4_laur_record",
        "checkpoint_jsonl": "checkpoints.jsonl",
        "trace_jsonl": "trace.jsonl",
        "traffic_snapshot_root": "snapshots",
        "time_limit_sec": 1,
        "max_iterations": 1,
        "checkpoint_topk_edges": 4,
        "export_raw_trace": False,
    }
    run = {
        "map_path": "map.map",
        "scen_path": "case.scen",
        "map_name": "map",
        "split": "train",
        "agents": 10,
        "seed": 1,
        "run_id": "run",
    }
    meta = {"branch": "b", "commit": "c", "dirty": "clean"}

    command = record_command(config, run, meta)

    raw_trace_index = command.index("--export-raw-trace")
    assert command[raw_trace_index + 1] == "0"


def test_expanded_runs_allows_map_specific_agent_counts() -> None:
    config = {
        "mode": "repair",
        "instances": [1],
        "agent_counts": [50, 100],
        "scen_template": "{map_name}-{instance}.scen",
        "maps": [
            {"map_name": "small", "map_path": "small.map", "split": "train", "agent_counts": [10]},
            {"map_name": "large", "map_path": "large.map", "split": "validation"},
        ],
    }

    runs = expanded_runs(config)

    assert [run["agents"] for run in runs] == [10, 50, 100]


def test_phase4f_performance_gate_rejects_weak_validation_metrics() -> None:
    eval_summary = {
        "metrics_by_split": {
            "validation": {
                "rule_top1_accuracy": 0.1375,
                "rule_top3_accuracy": 0.4875,
                "harmful_update_recall": 0.0714,
                "harmful_update_precision": 0.4,
                "predicted_rule_validation_mean_delta_ratio": 0.002,
                "neutral_additive_rate": 0.1125,
            }
        }
    }

    gate = phase4f_performance_gate(eval_summary, validation_non_neutral_checkpoints=58)

    assert gate["phase4f_validation_non_neutral_gate"]
    assert not gate["phase4f_validation_rule_top1_gate"]
    assert not gate["phase4f_validation_rule_top3_gate"]
    assert not gate["phase4f_harmful_update_recall_gate"]
    assert gate["phase4f_harmful_update_precision_gate"]
    assert not gate["phase4f_performance_gate_passed"]


def test_phase4f_performance_gate_accepts_threshold_metrics() -> None:
    eval_summary = {
        "metrics_by_split": {
            "validation": {
                "rule_top1_accuracy": 0.35,
                "rule_top3_accuracy": 0.70,
                "harmful_update_recall": 0.80,
                "harmful_update_precision": 0.30,
                "predicted_rule_validation_mean_delta_ratio": 0.0,
                "neutral_additive_rate": 0.2,
            }
        }
    }

    gate = phase4f_performance_gate(eval_summary, validation_non_neutral_checkpoints=50)

    assert gate["phase4f_performance_gate_passed"]
