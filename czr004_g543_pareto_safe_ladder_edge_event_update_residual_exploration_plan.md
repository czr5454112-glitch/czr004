# G5.43 Pareto-Safe Static Lattice and Edge/Event Residual Plan

## Intent

G5.43 follows the G5.42 evidence without treating it as a simple residual
failure.  The first question is whether the two `static_flow` regressions in
the targeted probe were caused by the deployable static ladder itself.  Only
after that autopsy does this round judge edge/event-conditioned UpdateLTM
residuals.

## Stages

1. Verify all required G5.42 summaries and tables and reproduce the P2/P3
   static-flow contradiction.
2. Classify each P2/P3 static-flow regression as static-ladder caused,
   overlay caused, materialization mismatch, or ambiguous.
3. Build and score twelve static lattice variants with success-regression
   safety before quality ranking.  If no all-baseline zero-regression lattice is
   supported, freeze the conservative static-flow baseline and continue.
4. Audit edge/event feature coverage in existing logs and project-owned
   checkpoint exporters.
5. Create symbolic edge/event UpdateLTM residual aliases that map to existing
   bounded dual-channel `UpdateParams` grammar.
6. Run a fresh-seed successive-halving stage-1 real solver probe with checkpoint
   resume behavior from the existing G5.40/G5.42 materialization path.
7. Run refinement, abstaining policy, frozen policy, and blind replay only if
   the earlier gates warrant them.
8. Write the final G5.43 decision summary with all Phase5.5, Phase6, runtime,
   learned-runtime, and AAAI claims closed.

## Guardrails

- No `external/lacam2/lacam2/**` edits.
- No LaCAM*/PIBT/search/restart/h-value/candidate-action semantic changes.
- No reserved IDs `166..205`.
- No posthoc oracle static baseline as a deployable rule.
- No runtime, Phase5.5, Phase6, learned runtime, or AAAI readiness claim.

## Primary Commands

```powershell
python scripts\verify_repair5g543_g542_artifacts.py
python scripts\audit_repair5g543_g542_staticflow_regression_sources.py
python scripts\create_repair5g543_pareto_safe_static_lattice.py
python scripts\analyze_repair5g543_static_lattice_safety_frontier.py
python scripts\audit_repair5g543_trace_edge_event_feature_coverage.py
python scripts\create_repair5g543_edge_event_candidate_family.py
python scripts\verify_repair5g543_edge_event_adapter_static.py
python scripts\create_repair5g543_successive_halving_probe_plan.py
python scripts\run_repair5g543_edge_event_probe_stage1.py --overwrite --max-workers 1
python scripts\analyze_repair5g543_edge_event_probe_stage1.py
python scripts\create_repair5g543_refinement_probe_plan.py
python scripts\run_repair5g543_edge_event_refinement_probe.py --overwrite --max-workers 1
python scripts\analyze_repair5g543_edge_event_refinement.py
python scripts\train_eval_repair5g543_abstaining_policy_if_warranted.py --bootstrap-samples 300
python scripts\create_repair5g543_frozen_policy_if_warranted.py
python scripts\run_repair5g543_frozen_policy_blind_replay_if_warranted.py --overwrite --max-workers 1
python scripts\analyze_repair5g543_blind_evidence.py
python scripts\write_repair5g543_decision.py
```
