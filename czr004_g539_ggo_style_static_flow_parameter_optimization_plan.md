# Repair5G.5.39 GGO-Style Static-Flow Parameter Optimization Plan

Date: 2026-06-12

## Scope

G5.39 shifts the LAU/LAUR learning target from selector-over-candidate-ID to static-flow-relative bounded UpdateParams generation. The round is offline and diagnostic. It keeps Phase5.5, Phase6, runtime, learned-runtime, and AAAI claim flags closed.

## Stages

1. Verify required G5.38 artifacts and audit why the globally selected residual candidate failed blind replay.
2. Update `deep-research-report.md`, `phase4_6_laur_ltm_codex_execution_plan.md`, and the strategy note with the G5.39 strategic shift.
3. Build a bounded 128-candidate parameter search space using existing `repair5g518_grid_*` grammar.
4. Run a local-PC real-solver optimizer probe with static baselines and selected G5.39 parameter candidates.
5. Analyze safe, unsafe, and boundary parameter regions against deployable static baselines.
6. Train only an offline diagnostic parameter generator if useful safe regions exist; otherwise skip model claims.
7. Freeze a static-fallback policy and run fresh-seed blind replay.
8. Write the decision summary with all claim flags closed and no `external/lacam2/lacam2` changes.

## Guardrails

- No edits to `external/lacam2/lacam2/**`.
- No PIBT, candidate domain, agent action, priority, h-value, candidate deletion, high-level search, restart, rewrite, or incumbent pruning semantic changes.
- No reserved IDs `166..205`.
- No success claim by beating additive alone.
- Posthoc/oracle static diagnostics are separated from deployable static baselines.

## Validation

The validation sequence follows the prompt commands:

```powershell
python -m py_compile scripts\repair5g539_common.py scripts\verify_repair5g539_g538_artifacts.py scripts\audit_repair5g539_g538_residual_failure.py scripts\update_repair5g539_project_strategy_docs.py scripts\create_repair5g539_static_flow_param_search_space.py scripts\run_repair5g539_static_flow_param_optimizer_probe.py scripts\analyze_repair5g539_param_safe_regions.py scripts\train_eval_repair5g539_param_generator.py scripts\create_repair5g539_frozen_param_policy.py scripts\run_repair5g539_frozen_param_blind_replay.py scripts\analyze_repair5g539_frozen_param_blind_evidence.py scripts\write_repair5g539_decision.py
python scripts\verify_repair5g539_g538_artifacts.py
python scripts\audit_repair5g539_g538_residual_failure.py
python scripts\update_repair5g539_project_strategy_docs.py
python scripts\create_repair5g539_static_flow_param_search_space.py
powershell -ExecutionPolicy Bypass -File scripts\build_phase1a_batch.ps1
python scripts\run_repair5g539_static_flow_param_optimizer_probe.py --max-workers 1
python scripts\analyze_repair5g539_param_safe_regions.py
C:\Users\38908\.conda\envs\czr004\python.exe scripts\train_eval_repair5g539_param_generator.py --epochs 80 --bootstrap-samples 300
python scripts\create_repair5g539_frozen_param_policy.py
python scripts\run_repair5g539_frozen_param_blind_replay.py --max-workers 1
python scripts\analyze_repair5g539_frozen_param_blind_evidence.py
python scripts\write_repair5g539_decision.py
git diff --check
git status --short -- external/lacam2/lacam2
```
