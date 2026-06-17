# Repair5G.5.56 Transformer/Retrieval Fixed StaticFlow Execution Plan

This is the canonical ASCII execution plan for G5.56. The user-supplied source plan is `czr004_g556_transformer_retrieval_aaai_fixed_staticflow_plan (2).md`.

## Decision

G5.56 continues the fixed-global staticflow coefficient route. The candidate object is exactly one deterministic global fixed UpdateParams theta vector shared across all maps, agent counts, seeds, budgets, horizons, checkpoints, and runtime states.

The neural model is training-time only. It may propose fixed candidate vectors, but it is not a runtime policy, contextual selector, checkpoint policy, abstention policy, per-context theta generator, or dynamic learned UpdateLTM policy.

## Primary Baseline

After G5.55, `g554_c00051` is the primary fixed global staticflow baseline for this route. The old hand `repair5g59_static_flow_shield` is a beaten diagnostic reference. `additive_ltm` remains the paper/parity floor.

Any G5.56 candidate must beat `g554_c00051` by paired solver validation and, if warranted, blind replay with zero success regressions before it can become a stronger fixed baseline candidate.

## Architecture

The primary offline surrogate is FixedTheta Retrieval-Set Transformer (FTRST):

- row-level theta/context feature-token Transformer
- retrieval memory over historical solver-facing theta/context/outcome rows
- candidate-set aggregation over a canonical evaluation panel
- multi-head risk, gain, quality, and uncertainty outputs
- constrained candidate generation around `g554_c00051`

Required controls include FT-Transformer, SAINT/AMFormer diagnostics, TabM/MLP controls, GBDT controls, and derivative-free heuristic optimizers.

## Server Policy

Run experiments on the KCS/Paratera server under `tmux`.

Use:

```bash
export REMOTE_ARTIFACT_ROOT=/root/shared-nvme/czr004_g556_remote_artifacts
export TMPDIR=/root/shared-nvme/tmp
mkdir -p "$REMOTE_ARTIFACT_ROOT" "$TMPDIR"
```

Fresh workdir:

```text
/root/shared-nvme/czr004_g556_9e083eb
```

Large raw inputs, generated datasets, checkpoints, solver plans, and solver results stay under `/root/shared-nvme`. Git only receives compact summaries, leaderboards, manifests, small previews, and reports.

## Required Execution Order

```bash
python scripts/verify_repair5g556_g555_artifacts.py
python scripts/audit_repair5g556_promoted_baseline.py
python scripts/create_repair5g556_literature_model_audit.py
python scripts/create_repair5g556_unified_fixedtheta_dataset_manifest.py
python scripts/create_repair5g556_surrogate_dataset.py
python scripts/train_eval_repair5g556_ftrst_surrogate.py --device cuda --gpus 2 --epochs 80 --batch-size auto
python scripts/train_eval_repair5g556_ft_transformer_baseline.py --device cuda --gpus 2
python scripts/train_eval_repair5g556_saint_amformer_diagnostics.py --device cuda --gpus 2
python scripts/train_eval_repair5g556_tabm_and_mlp_controls.py --device cuda --gpus 2
python scripts/train_eval_repair5g556_gbdt_controls.py
python scripts/generate_repair5g556_surrogate_candidates.py --candidate-count 100000 --selected-count 3000
python scripts/create_repair5g556_stage1_solver_screen_plan.py
python scripts/run_repair5g556_stage1_solver_screen.py --row-limit 300000 --max-workers 24
python scripts/analyze_repair5g556_stage1_solver_screen.py
python scripts/create_repair5g556_stage2_elite_validation_plan.py
python scripts/run_repair5g556_stage2_elite_validation.py --row-limit 240000 --max-workers 24
python scripts/analyze_repair5g556_stage2_elite_validation.py
python scripts/create_repair5g556_blind_if_warranted.py
python scripts/run_repair5g556_blind_if_warranted.py --row-limit 240000 --max-workers 24
python scripts/analyze_repair5g556_blind_if_warranted.py
python scripts/write_repair5g556_decision.py
```

## Claim Ledger

Closed throughout G5.56:

```json
{
  "phase5p5_allowed": false,
  "phase6_allowed": false,
  "runtime_claim_allowed": false,
  "learned_runtime_policy_validated": false,
  "aaai_ready": false
}
```

## Success Interpretation

Positive result:

```text
FTRST or ensemble proposes a fixed global theta vector that passes Stage2 and blind replay against g554_c00051 with zero success regression, nonnegative success-rate delta, negative mean quality delta, CI upper <= 0, fingerprint=1, candidate recognized, finite costs, and all claims closed.
```

Useful negative:

```text
No candidate beats g554_c00051 under real paired replay. Then g554_c00051 remains a strong fixed-global Pareto baseline, and future progress likely requires per-family diagnostics or a later return to dynamic learned policy.
```

## Final Outcome

The G5.56 server run completed under `tmux` on the KCS RTX4090 instance. Final decision: `g556_transformer_fixed_global_candidate_blind_passed_keep_claims_closed`.

Evidence:

- unified usable row-level examples: `1,001,437`
- surrogate training rows: `968,362`
- candidate vectors generated: `100,000`
- Stage1 solver rows: `304,500`
- Stage2 solver rows: `430,000`
- blind solver rows: `360,000`
- promoted fixed candidate: `g556_c063174`
- prior fixed baseline: `g554_c00051`
- blind success regressions versus `g554_c00051`: `0`
- blind quality delta versus `g554_c00051`: `-0.0032705119799`
- blind CI upper: `-0.00305603582661`
- materialization/fingerprint: pass

The fixed global baseline ladder advances to `g556_c063174`. FTRST did not pass the offline learned-SafeGate gate, so learned SafeGate, runtime learned policy, dynamic UpdateParams, Phase5.5, Phase6, and AAAI claims remain closed.
