import ast
from pathlib import Path

import numpy as np
import pytest

from gcst.actor_losses import anchor_loss, safe_set_softmin_loss
from gcst.direct_actor import ACTOR_FEATURE_SCHEMA, DirectGCSTActor, actor_features
from gcst.generated_theta_audit import generated_theta_uid
from gcst.label_v4 import BASELINE_G556, THETA_NUMERIC_COLUMNS


def test_direct_actor_outputs_continuous_theta():
    torch = pytest.importorskip("torch")
    actor = DirectGCSTActor(len(ACTOR_FEATURE_SCHEMA), hidden_dim=16).module()
    x = torch.zeros((2, len(ACTOR_FEATURE_SCHEMA)), dtype=torch.float32)
    theta = actor(x)
    assert theta.shape == (2, len(THETA_NUMERIC_COLUMNS))
    assert torch.isfinite(theta).all()
    assert not theta.dtype.is_floating_point is False


def test_direct_actor_does_not_load_codebook():
    source = (Path(__file__).resolve().parents[1] / "src" / "gcst" / "direct_actor_inference.py").read_text(encoding="utf-8").lower()
    assert "theta_codebook" not in source
    assert "nearest_neighbor" not in source
    assert "retrieval" not in source


def test_direct_actor_does_not_use_candidate_id():
    source = (Path(__file__).resolve().parents[1] / "src" / "gcst" / "direct_actor.py").read_text(encoding="utf-8").lower()
    assert "candidate_id" not in source


@pytest.mark.skipif(__import__("importlib").util.find_spec("torch") is None, reason="torch unavailable")
def test_export_bundle_excludes_critic(tmp_path):
    import torch

    from gcst.actor_critic_training import export_actor_bundle

    actor = DirectGCSTActor(len(ACTOR_FEATURE_SCHEMA), hidden_dim=16).module()
    source = tmp_path / "source.pt"
    torch.save(
        {
            "artifact_type": "g560_direct_actor_only",
            "variant": "unit",
            "actor_state_dict": actor.state_dict(),
            "feature_schema": ACTOR_FEATURE_SCHEMA,
            "feature_mean": np.zeros(len(ACTOR_FEATURE_SCHEMA), dtype=np.float32),
            "feature_std": np.ones(len(ACTOR_FEATURE_SCHEMA), dtype=np.float32),
            "theta_columns": THETA_NUMERIC_COLUMNS,
            "theta_anchor_g556": BASELINE_G556,
            "hidden_dim": 16,
            "residual_scale": 0.35,
            "auxiliary_state_dict": {"forbidden": True},
        },
        source,
    )
    manifest = export_actor_bundle(tmp_path, str(source), "artifacts/models/gcst/export.pt")
    exported = torch.load(tmp_path / "artifacts/models/gcst/export.pt", map_location="cpu", weights_only=False)
    assert "auxiliary_state_dict" not in exported
    assert not manifest["contains_auxiliary_critic"]


def test_export_bundle_excludes_codebook():
    source = (Path(__file__).resolve().parents[1] / "src" / "gcst" / "actor_critic_training.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    fn = next(node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == "export_actor_bundle")
    text = ast.get_source_segment(source, fn)
    assert "theta_codebook" not in text
    assert "selector_table" not in text or "contains_selector_table" in text


def test_no_safe_improvement_shrinks_to_g556():
    torch = pytest.importorskip("torch")
    theta = torch.tensor(BASELINE_G556, dtype=torch.float32).view(1, -1)
    assert float(anchor_loss(theta)) == pytest.approx(0.0)
    assert float(safe_set_softmin_loss(theta[0], torch.zeros((0, len(THETA_NUMERIC_COLUMNS))))) == pytest.approx(0.0)


def test_safe_set_softmin_is_mode_seeking():
    torch = pytest.importorskip("torch")
    left = torch.tensor(BASELINE_G556 - 0.2, dtype=torch.float32)
    right = torch.tensor(BASELINE_G556 + 0.2, dtype=torch.float32)
    midpoint = torch.tensor(BASELINE_G556, dtype=torch.float32)
    safe = torch.stack([left, right])
    assert float(safe_set_softmin_loss(left, safe)) < float(safe_set_softmin_loss(midpoint, safe))


def test_actor_loss_uses_real_safe_set():
    torch = pytest.importorskip("torch")
    theta = torch.tensor(BASELINE_G556 + 0.1, dtype=torch.float32)
    safe = torch.tensor(np.stack([BASELINE_G556 + 0.1, BASELINE_G556 + 0.4]), dtype=torch.float32)
    weights = torch.tensor([2.0, 0.1])
    assert float(safe_set_softmin_loss(theta, safe, weights)) < 0.02


def test_critic_quality_masks_noncomparable_rows():
    source = (Path(__file__).resolve().parents[1] / "src" / "gcst" / "actor_critic_training.py").read_text(encoding="utf-8")
    assert "labelv51_comparable_quality" in source
    assert "mask.sum().clamp_min(1.0)" in source


def test_actor_inference_single_forward_pass():
    source = (Path(__file__).resolve().parents[1] / "src" / "gcst" / "direct_actor_inference.py").read_text(encoding="utf-8")
    assert source.count("model(") == 1


def test_actor_theta_fixed_for_run():
    torch = pytest.importorskip("torch")
    actor = DirectGCSTActor(len(ACTOR_FEATURE_SCHEMA), hidden_dim=16).module().eval()
    x = torch.ones((1, len(ACTOR_FEATURE_SCHEMA)), dtype=torch.float32)
    with torch.no_grad():
        assert torch.allclose(actor(x), actor(x), atol=1e-8)


def test_pairing_shuffle_changes_theta_when_flow_changes():
    base = {"agent_count": "8", "nominal_budget_ms": "500", "represented_flow_mass": "8", "nonzero_flow": "True"}
    changed = dict(base)
    changed["represented_flow_mass"] = "13"
    assert not np.allclose(actor_features(base), actor_features(changed))


def test_solver_seed_does_not_change_theta():
    base = {"agent_count": "8", "nominal_budget_ms": "500", "seed": "1", "nonzero_flow": "True"}
    changed = dict(base)
    changed["seed"] = "999"
    assert np.allclose(actor_features(base), actor_features(changed))


def test_generated_theta_uid_depends_on_values():
    a = generated_theta_uid("m.pt", "i", BASELINE_G556)
    b = generated_theta_uid("m.pt", "i", BASELINE_G556 + 0.001)
    assert a != b


def test_generated_theta_materialization():
    uid = generated_theta_uid("model", "instance", BASELINE_G556)
    row = {"generated_theta_uid": uid, **{col: float(v) for col, v in zip(THETA_NUMERIC_COLUMNS, BASELINE_G556)}}
    assert row["generated_theta_uid"] == uid
    assert "candidate_id" not in row
