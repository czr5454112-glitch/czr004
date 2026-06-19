import ast
import csv
import hashlib
from pathlib import Path

import pytest

from gcst.identity_recovery import recover_labelv51
from gcst.label_v5 import aggregate_replicates
from gcst.real_critic_training import TRAINING_ROWS_CSV, train_and_evaluate
from gcst.scenario_features import _sample
from gcst.scenario_validation import validate_scenarios
from gcst.schemas_v51 import identity_digest, legacy_context_key


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else []
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_identity_digest_roundtrip():
    row = {
        "g560_plan_row_uid": "p1",
        "g560_instance_uid": "sha-instance",
        "g560_evaluation_uid": "sha-eval",
        "g560_theta_id": "c1",
        "g560_physical_map_sha256": "map",
        "g560_start_goal_assignment_sha256": "assign",
        "g560_solver_scenario_sha256": "scen",
    }
    assert identity_digest(row) == identity_digest(dict(row))
    row["g560_theta_id"] = "c2"
    assert identity_digest(row) != identity_digest({**row, "g560_theta_id": "c1"})


def test_legacy_uid_crosswalk_unique_and_join_rate(tmp_path):
    root = tmp_path
    base = {
        "plan_row_id": "p0",
        "instance_uid": "sha-instance",
        "evaluation_uid": "sha-eval",
        "map": "m",
        "map_family": "f",
        "agents": "4",
        "agent_count": "4",
        "seed": "7",
        "budget_ms": "500",
        "nominal_budget_ms": "500",
        "horizon_id": "h",
        "physical_map_sha256": "mapsha",
        "start_goal_assignment_sha256": "assignsha",
        "solver_scenario_sha256": "scensha",
        "candidate_id": "g556_c063174",
        "theta_id": "g556_c063174",
    }
    cand = {**base, "plan_row_id": "p1", "candidate_id": "c1", "theta_id": "c1"}
    key = legacy_context_key(base)
    pair = {
        "instance_uid": key,
        "evaluation_uid": "7",
        "theta_id": "c1",
        "candidate_success": "True",
        "baseline_success": "True",
        "success_regression": "False",
        "success_gain": "False",
        "both_success": "True",
        "both_fail": "False",
        "quality_delta_vs_g556": "-0.1",
        "candidate_recognized": "True",
        "fingerprint_match": "True",
        "cost_finite": "True",
        "theta_in_bounds": "True",
        "runtime": "0.1",
        "row_weight": "1.0",
    }
    for col in [
        "theta_alpha_cong_commit_progress",
        "theta_alpha_cong_commit_nonprogress",
        "theta_alpha_cong_block",
        "theta_alpha_cong_wait_progress",
        "theta_alpha_cong_wait_nonprogress",
        "theta_alpha_flow_commit_progress",
        "theta_alpha_flow_wait_progress",
        "theta_rho_cong_decay",
        "theta_rho_flow_decay",
        "theta_lambda_cong",
        "theta_lambda_flow",
        "theta_flow_shield_beta",
        "theta_max_flow_shield",
        "theta_min_edge_cost",
        "theta_max_edge_cost",
    ]:
        base[col] = "1.0"
        cand[col] = "1.0"
        pair[col] = "1.0"
    write_csv(root / "outputs/tables/phase5p5_repair5g559_labelv5_pilot_plan.csv", [base, cand])
    write_csv(root / "outputs/tables/phase5p5_repair5g559_labelv5_pair_rows.csv", [pair])
    write_csv(root / "outputs/tables/phase5p5_repair5g559_real_learnability_split_manifest.csv", [{"instance_uid": "sha-instance", "split": "heldout"}])
    summary = recover_labelv51(root)
    assert summary["identity_join_rate"] == 1.0
    assert summary["baseline_pair_same_evaluation_rate"] == 1.0
    rows = list(csv.DictReader((root / "outputs/tables/phase5p5_repair5g560_labelv51_join_audit.csv").open()))
    assert rows[0]["g560_instance_uid"] == "sha-instance"
    assert rows[0]["legacy_instance_uid"] == key


def test_assignment_sampling_no_cycles():
    cells = [(0, 0), (1, 0), (2, 0)]
    sample = _sample(cells, __import__("random").Random(1), 5, cells)
    assert len(sample) == len(set(sample))
    assert len(sample) == 3


def test_replicates_are_not_overwritten():
    rows = [
        {"instance_uid": "i", "theta_id": "t", "quality_delta_vs_g556": -1.0, "success_regression": False, "success_gain": True},
        {"instance_uid": "i", "theta_id": "t", "quality_delta_vs_g556": 1.0, "success_regression": True, "success_gain": False},
    ]
    agg = aggregate_replicates(rows)
    assert agg[0]["replicate_count"] == 2
    assert agg[0]["success_regression_count"] == 1


def test_scenario_parser_validates_actual_files(tmp_path):
    root = tmp_path
    map_path = root / "contexts/maps/tiny.map"
    scen_path = root / "contexts/scenarios/tiny.scen"
    map_path.parent.mkdir(parents=True, exist_ok=True)
    scen_path.parent.mkdir(parents=True, exist_ok=True)
    map_path.write_text("type octile\nheight 3\nwidth 3\nmap\n...\n.@.\n...\n", encoding="utf-8")
    scen_path.write_text("version 1\n0 tiny.map 3 3 0 0 2 2 4\n1 tiny.map 3 3 2 0 0 2 4\n", encoding="utf-8")
    assign = hashlib.sha256("|".join(["(0, 0)->(2, 2)", "(2, 0)->(0, 2)"]).encode("utf-8")).hexdigest()
    write_csv(
        root / "outputs/tables/phase5p5_repair5g559_solver_map_manifest.csv",
        [{"map": "tiny", "map_family": "tiny", "solver_map_path": str(map_path), "solver_map_sha256": sha(map_path)}],
    )
    write_csv(
        root / "outputs/tables/phase5p5_repair5g559_solver_scenario_manifest.csv",
        [
            {
                "map": "tiny",
                "map_family": "tiny",
                "solver_seed": "1",
                "solver_scenario_path": str(scen_path),
                "solver_scenario_sha256": sha(scen_path),
                "solver_scenario_pair_count": "2",
                "start_goal_assignment_sha256": assign,
            }
        ],
    )
    summary = validate_scenarios(root)
    assert summary["valid_scenarios"] == 1
    assert summary["actual_file_validation_complete"]


def test_training_wrapper_calls_real_trainer():
    path = Path(__file__).resolve().parents[1] / "scripts" / "train_repair5g560_codebook_critic.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    assert "main_train_g560_codebook_critic" in names
    assert "main_eval_real_learnability" not in names


@pytest.mark.skipif(__import__("importlib").util.find_spec("torch") is None, reason="torch unavailable")
def test_training_script_writes_checkpoint(tmp_path):
    root = tmp_path
    rows = []
    for group, split, phys in [("g1", "train", "h1"), ("g2", "heldout", "h2")]:
        for idx, theta in enumerate(["g556_c063174", "c1", "c2"]):
            base = {
                "schema_version": "label_v5.1_identity_safe",
                "source_round": "phase5p5_repair5g559",
                "row_kind": "baseline_pseudo_candidate" if theta == "g556_c063174" else "candidate_pair",
                "g560_evaluation_uid": group,
                "g560_instance_uid": group + "i",
                "g560_physical_map_sha256": phys,
                "split": split,
                "theta_id": theta,
                "candidate_id": theta,
                "agent_count": "4",
                "nominal_budget_ms": "500",
                "requested_agent_count": "4",
                "physical_free_cell_count": "9",
                "agent_density": "0.4",
                "encoded_OD_token_count": "4",
                "represented_agent_mass": "4",
                "represented_flow_mass": "4",
                "path_found_rate": "1.0",
                "base_time_limit_sec": "0.5",
                "ltm_max_iterations": "2",
                "nonzero_flow": "True",
                "labelv51_target_utility": str(0.0 if theta == "g556_c063174" else (1.0 if idx == 1 else -1.0)),
                "labelv51_development_safe": "True" if idx != 2 else "False",
                "labelv51_success_gain": "True" if idx == 1 else "False",
                "labelv51_success_regression": "True" if idx == 2 else "False",
                "labelv51_comparable_quality": "True",
                "quality_delta_vs_g556": str(0.0 if theta == "g556_c063174" else (-0.2 if idx == 1 else 0.4)),
            }
            for col in [
                "theta_alpha_cong_commit_progress",
                "theta_alpha_cong_commit_nonprogress",
                "theta_alpha_cong_block",
                "theta_alpha_cong_wait_progress",
                "theta_alpha_cong_wait_nonprogress",
                "theta_alpha_flow_commit_progress",
                "theta_alpha_flow_wait_progress",
                "theta_rho_cong_decay",
                "theta_rho_flow_decay",
                "theta_lambda_cong",
                "theta_lambda_flow",
                "theta_flow_shield_beta",
                "theta_max_flow_shield",
                "theta_min_edge_cost",
                "theta_max_edge_cost",
            ]:
                base[col] = "1.0"
            rows.append(base)
    write_csv(root / TRAINING_ROWS_CSV, rows)
    summary = train_and_evaluate(root, seed=1, hidden_dim=16, steps=2, fold_steps=1, n_folds=2, batch_groups=1, device="cpu")
    assert summary["final_checkpoint_step"] == 2
    assert (root / summary["model_path"]).exists()
