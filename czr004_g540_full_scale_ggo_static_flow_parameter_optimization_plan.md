# Repair5G.5.40 Full-Scale GGO-Style Static-Flow Parameter Optimization Plan

Date: 2026-06-12

## Scope

G5.40 treats G5.39 as an underpowered pilot, not as positive or negative scientific evidence. The round keeps the G5.39 strategic shift to static-flow-relative bounded `UpdateParams`, but requires staged coverage before any model, frozen policy, runtime, Phase5.5, Phase6, or AAAI claim.

## Stages

1. Verify required G5.39 artifacts and audit why the G5.39 parameter probe and blind replay were underpowered.
2. Update `deep-research-report.md`, `phase4_6_laur_ltm_codex_execution_plan.md`, and `docs/goal_aware_dual_channel_ltm_research_strategy.md` with the G5.40 underpowering policy.
3. Create a successive-halving parameter search plan from the 128 G5.39 parameter candidates:
   Stage 1 all-candidate coarse coverage, Stage 2 top-k expansion, and Stage 3 local refinement.
4. Run Stage 1 with all 128 candidates on a stratified fresh context set, then analyze candidate, stratum, seed-block, and safe-region coverage.
5. Run Stage 2 only on top safe candidates from Stage 1, then classify supported safe, unsafe, and boundary regions with the G5.40 support thresholds.
6. Create and run Stage 3 local refinement only if Stage 2 produces supported safe regions.
7. Train a parameter generator only if final safe-region support is met; otherwise emit an explicit skipped decision.
8. Freeze a static-fallback region policy and run blind replay only if a non-static supported policy exists.
9. Write the final G5.40 decision. Any shortfall in coverage or row targets returns `g540_underpowered_continue_runs`.

## Guardrails

- No edits to `external/lacam2/lacam2/**`.
- No PIBT, candidate domain, agent action, priority, h-value, candidate deletion, high-level search, restart, rewrite, or incumbent pruning semantic changes.
- No reserved IDs `166..205`.
- No positive or final negative scientific conclusion from an underpowered run.
- All summaries keep `phase5p5_allowed=false`, `phase6_allowed=false`, `runtime_claim_allowed=false`, `learned_runtime_policy_validated=false`, and `aaai_ready=false`.

## Validation

The validation sequence follows the G5.40 prompt commands:

```powershell
python -m py_compile scripts\repair5g540_common.py scripts\verify_repair5g540_g539_artifacts.py scripts\audit_repair5g540_g539_underpowering.py scripts\update_repair5g540_strategy_docs.py scripts\create_repair5g540_successive_halving_param_plan.py scripts\run_repair5g540_param_search_stage1.py scripts\analyze_repair5g540_stage1_param_coverage.py scripts\run_repair5g540_param_search_stage2_topk.py scripts\analyze_repair5g540_stage2_safe_regions.py scripts\create_repair5g540_local_refinement_space.py scripts\run_repair5g540_param_search_stage3_refine.py scripts\analyze_repair5g540_final_safe_regions.py scripts\train_eval_repair5g540_param_generator_if_warranted.py scripts\create_repair5g540_frozen_region_policy.py scripts\run_repair5g540_frozen_region_blind_replay.py scripts\analyze_repair5g540_blind_region_evidence.py scripts\write_repair5g540_decision.py
C:\Users\38908\.conda\envs\czr004\python.exe -m py_compile scripts\repair5g540_common.py scripts\train_eval_repair5g540_param_generator_if_warranted.py
python scripts\verify_repair5g540_g539_artifacts.py
python scripts\audit_repair5g540_g539_underpowering.py
python scripts\update_repair5g540_strategy_docs.py
python scripts\create_repair5g540_successive_halving_param_plan.py
powershell -ExecutionPolicy Bypass -File scripts\build_phase1a_batch.ps1
python scripts\run_repair5g540_param_search_stage1.py --max-workers 1
python scripts\analyze_repair5g540_stage1_param_coverage.py
python scripts\run_repair5g540_param_search_stage2_topk.py --max-workers 1
python scripts\analyze_repair5g540_stage2_safe_regions.py
python scripts\create_repair5g540_local_refinement_space.py
python scripts\run_repair5g540_param_search_stage3_refine.py --max-workers 1
python scripts\analyze_repair5g540_final_safe_regions.py
C:\Users\38908\.conda\envs\czr004\python.exe scripts\train_eval_repair5g540_param_generator_if_warranted.py --epochs 80 --bootstrap-samples 300
python scripts\create_repair5g540_frozen_region_policy.py
python scripts\run_repair5g540_frozen_region_blind_replay.py --max-workers 1
python scripts\analyze_repair5g540_blind_region_evidence.py
python scripts\write_repair5g540_decision.py
git diff --check
git status --short -- external/lacam2/lacam2
```
