# Repair5G.5.32 Real Solver Slice Dataset Scale-Up Plan

Date: 2026-06-10

## Objective

Promote the G5.31 slice pipeline from artifact-backed deterministic replay to a real C++ solver trace round. G5.32 audits G5.31 materialization, discovers executable trace runners, collects real UpdateLTM checkpoint traces, converts them to bounded slice tables, builds diagnostic residual/risk labels, validates against existing gold counterfactual rows, and writes a closed-claims scale-up decision.

## Guardrails

- Do not modify `external/lacam2/lacam2/**`.
- Do not change PIBT, LaCAM*, search, rewrite, incumbent, pruning, restart, candidate deletion, h-value, action, or priority semantics.
- Do not inspect or run reserved IDs `166..205`.
- Keep `phase5p5_allowed=false`, `phase6_allowed=false`, `runtime_claim_allowed=false`, `learned_runtime_policy_validated=false`, and `aaai_ready=false` in every G5.32 report/summary.
- Treat gold counterfactual rows as validation/calibration only, never as training targets or runtime claims.
- Keep raw logs local/ignored; commit manifests, row-count audits, samples, summaries, and small derived tables only.

## Execution Stages

1. Verify G5.31/G5.30 starting artifacts and closed-claim state.
2. Audit G5.31 materialization, row counts, hashes, and provenance.
3. Discover real project trace runners and required logging surfaces.
4. Build an executable context source from the original 60 gold anchors plus generated seeds `156..159` on the same map/agent panel.
5. Rebuild `phase1a_batch` if needed so the current checkpoint exporter includes exact failure audits.
6. Run real solver trace collection for budgets `1000` and `2000` ms across three UpdateParams configurations.
7. Convert real checkpoint logs to context, edge, event, failure, and update slices with `trace_backend=real_solver_trace`.
8. Create residual and risk/fallback labels with evidence-strength tags and no forbidden targets.
9. Run micro-counterfactual replay checks and join existing gold validation rows.
10. Train/evaluate residual, risk, and world-model diagnostics with CUDA if available or sklearn/numpy fallback otherwise.
11. Compare real G5.32 slices against synthetic/artifact-backed G5.31 distributions.
12. Write the final G5.32 decision and run the required validation commands.

## Expected Outputs

- `scripts/repair5g532_common.py` plus one wrapper script per stage.
- `outputs/reports/phase5p5_repair5g532_*`
- `outputs/tables/phase5p5_repair5g532_*`
- `outputs/datasets/phase5p5_repair5g532_*` manifest/sample files only where large data would otherwise be committed.
- `outputs/logs/phase5p5_repair5g532_*` raw local logs, not intended for commit.

## Decision Policy

Positive continuation requires audited G5.31 materialization, real-solver trace usage only, at least 300 real context slices, substantial edge/event slices beyond the 120-context-budget pilot, no forbidden targets/features, gold validation overlap, at least one residual or risk diagnostic beating baseline/control, and all claims still closed. Weak model signal should become a refine-labels decision, not a runtime or AAAI claim.
