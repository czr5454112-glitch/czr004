# G5.41 Deep Exploration Prompt: Balanced Per-Stratum Static-Flow Safe-Region Mining

Project: `czr004`
Target branch: `codex/g531-slice-pilot`
Starting commit: `8ec7f9c3643434ffbb585cc7d52d632cbdd8be99` (`eval: add G5.40 full-scale static-flow parameter optimization`)
Round name: `Repair5G.5.41 balanced per-stratum static-flow safe-region mining`
Suggested plan file: `czr004_g541_balanced_per_stratum_static_flow_safe_region_mining_plan.md`

## 0. Why G5.41 exists

G5.40 was a high-quality negative/diagnostic result, not a quick failure. It fixed the G5.39 underpowering problem enough to show that the first full parameter-search attempt did not produce globally supported safe regions:

```text
Stage 1:
  candidate coverage = 128 / 128
  new_solver_rows = 3168
  contexts = 24
  unsafe_candidate_count = 14
  safe_candidate_count = 114

Stage 2:
  top_k candidates = 32
  new_solver_rows = 6120
  contexts = 170
  safe_region_count = 0
  useful_safe_region_count = 0
  unsafe_region_count = 28
  boundary_region_count = 4

Final:
  decision = g540_no_supported_safe_param_region_continue_design
  stage3 / generator / blind replay not warranted
```

However, G5.40 also exposed two important design issues:

```text
1. Stage 2 support was judged at global candidate level.
   A candidate can be unsafe globally but safe and useful in a specific map/budget/agent stratum.

2. The Stage 2 context sampler likely did not provide enough seed-block diversity.
   Boundary candidates had enough total pairs but only one seed-block support in the committed boundary table.
```

Therefore G5.41 must not simply rerun G5.40. It must shift from:

```text
global candidate -> safe / unsafe
```

to:

```text
candidate × map_family × agents × budget × stage/final -> safe / unsafe / useful
```

The key question for G5.41:

```text
Are there per-stratum static-flow-relative parameter regions that are safe and useful
after balanced seed-block support,
even though no global candidate is safe/useful?
```

This is still the same strategic direction:

```text
learn safe UpdateParams residuals around static_flow,
not stale candidate-ID selection.
```

But it corrects the granularity.

## 1. Required strategy update

Before experiments, append a G5.41 note to:

```text
deep-research-report.md
phase4_6_laur_ltm_codex_execution_plan.md
docs/goal_aware_dual_channel_ltm_research_strategy.md
```

Add section:

```markdown
## 2026-06-12 - G5.41 strategic update: safe regions are per-stratum, not global candidates
```

Required content:

```text
G5.40 showed that no parameter candidate was globally supported safe/useful under the initial thresholds.
This does not prove the absence of learnable parameter regions.
Static-flow residuals may be safe only in specific strata:
  map family
  agent count
  budget
  iteration/final behavior
Therefore G5.41 changes the safe-region unit from candidate-level to candidate-stratum-level.
Learning target becomes:
  context/trace -> safe parameter region or static fallback
rather than:
  one global parameter candidate.
```

Also include this exact strategic statement:

```text
From G5.41 onward, a static-flow parameter region is evaluated at the deployable stratum level. A candidate that is unsafe globally may still be valuable if a frozen pre-replay policy can restrict it to strata where it has zero regression and nontrivial static-relative gain.
```

## 2. Non-negotiable guardrails

Do not modify:

```text
external/lacam2/lacam2/**
PIBT conflict semantics
candidate domain
agent actions
agent priorities
h-values
candidate deletion
LaCAM* high-level search
OPEN / EXPLORED / rewrite / incumbent pruning
restart semantics
```

Do not claim:

```text
phase5p5_allowed=true
phase6_allowed=true
runtime_claim_allowed=true
learned_runtime_policy_validated=true
aaai_ready=true
```

All summaries must keep:

```json
{
  "phase5p5_allowed": false,
  "phase6_allowed": false,
  "runtime_claim_allowed": false,
  "learned_runtime_policy_validated": false,
  "aaai_ready": false
}
```

Do not use reserved IDs `166..205`.

Do not use posthoc oracle static as deployable baseline. Keep:

```text
deployable baselines:
  additive_ltm
  static_flow_shield
  best_fixed_static_goal_aware
  frozen_family_static_goal_aware

diagnostic only:
  posthoc oracle static
```

Do not train a generator or selector unless per-stratum safe regions pass support thresholds.

## 3. Required worklog entry before code

Append to `docs/codex-worklog.md`:

```markdown
## 2026-06-12 - Repair5G.5.41 balanced per-stratum static-flow safe-region mining

- Request:
  Continue after G5.40 commit 8ec7f9c. G5.40 covered all 128 parameter candidates and ran a larger Stage 2, but no globally supported safe/useful region was found. The next hypothesis is that useful static-flow parameter regions are per-stratum, not global: a candidate may be unsafe overall but safe in specific map/budget/agent strata. G5.41 must reclassify G5.40 evidence at candidate-stratum level, fix seed-block support, extend boundary and near-miss candidates with balanced seeds, and only then decide whether per-stratum parameter learning is viable.
- Planned files:
  - czr004_g541_balanced_per_stratum_static_flow_safe_region_mining_plan.md
  - scripts/repair5g541_common.py
  - scripts/verify_repair5g541_g540_artifacts.py
  - scripts/audit_repair5g541_g540_global_vs_stratum_regions.py
  - scripts/update_repair5g541_strategy_docs.py
  - scripts/create_repair5g541_per_stratum_region_labels.py
  - scripts/create_repair5g541_balanced_support_extension_plan.py
  - scripts/run_repair5g541_balanced_support_extension.py
  - scripts/analyze_repair5g541_balanced_per_stratum_regions.py
  - scripts/create_repair5g541_stratum_local_refinement_space.py
  - scripts/run_repair5g541_stratum_local_refinement.py
  - scripts/analyze_repair5g541_final_stratum_regions.py
  - scripts/train_eval_repair5g541_region_predictor_if_warranted.py
  - scripts/create_repair5g541_frozen_stratum_policy.py
  - scripts/run_repair5g541_frozen_stratum_blind_replay.py
  - scripts/analyze_repair5g541_frozen_stratum_blind_evidence.py
  - scripts/write_repair5g541_decision.py
  - outputs/reports/phase5p5_repair5g541_*
  - outputs/tables/phase5p5_repair5g541_*
  - outputs/logs/phase5p5_repair5g541_* local/ignored raw logs
  - artifacts/models/laur_ltm/repair5g541_* manifest files only
- Constraints:
  No external/lacam2/lacam2 edits, no solver semantic changes, no action/priority/search/restart/candidate deletion/h-value target, no reserved IDs 166..205, no Phase5.5/Phase6/runtime/AAAI claims.
- Pre-experiment statement:
  G5.41 does not search for one globally safe parameter candidate. It searches for frozen deployable per-stratum safe parameter regions and static fallback rules.
```

## 4. Stage A — Verify G5.40 and audit global-vs-stratum issue

Create:

```text
scripts/verify_repair5g541_g540_artifacts.py
scripts/audit_repair5g541_g540_global_vs_stratum_regions.py
```

Outputs:

```text
outputs/reports/phase5p5_repair5g541_g540_verification.md
outputs/reports/phase5p5_repair5g541_g540_verification_summary.json
outputs/reports/phase5p5_repair5g541_g540_global_vs_stratum_audit.md
outputs/reports/phase5p5_repair5g541_g540_global_vs_stratum_audit_summary.json
outputs/tables/phase5p5_repair5g541_g540_table_materialization_audit.csv
outputs/tables/phase5p5_repair5g541_g540_global_region_audit.csv
outputs/tables/phase5p5_repair5g541_g540_candidate_stratum_reclassification.csv
outputs/tables/phase5p5_repair5g541_g540_seed_block_support_audit.csv
outputs/tables/phase5p5_repair5g541_g540_near_miss_candidate_audit.csv
```

### A.1 Required G5.40 artifacts

Verify:

```text
outputs/reports/phase5p5_repair5g540_decision_summary.json
outputs/reports/phase5p5_repair5g540_stage1_param_coverage_summary.json
outputs/reports/phase5p5_repair5g540_stage2_safe_regions_summary.json
outputs/reports/phase5p5_repair5g540_final_safe_regions_summary.json
outputs/reports/phase5p5_repair5g540_param_generator_summary.json
outputs/reports/phase5p5_repair5g540_frozen_region_policy_summary.json
outputs/tables/phase5p5_repair5g540_stage1_param_search_results.csv
outputs/tables/phase5p5_repair5g540_stage1_candidate_leaderboard.csv
outputs/tables/phase5p5_repair5g540_stage2_topk_results.csv
outputs/tables/phase5p5_repair5g540_stage2_safe_regions.csv
outputs/tables/phase5p5_repair5g540_stage2_unsafe_regions.csv
outputs/tables/phase5p5_repair5g540_stage2_boundary_regions.csv
outputs/tables/phase5p5_repair5g540_param_search_stage2_plan.csv
scripts/repair5g540_common.py
```

### A.2 Audit questions

Answer explicitly:

```text
How many G5.40 Stage 2 candidates were unsafe globally but safe in at least one stratum?
How many were useful in at least one stratum?
How many boundary candidates failed only because seed_block_support < 2?
Was Stage 2 context sampling balanced across seed blocks?
How many candidate-stratum pairs had:
  0 success regression vs static_flow
  0 success regression vs family_static
  quality_only_mean_delta < 0
  better_count >= worse_count
but failed global aggregation?
```

### A.3 Expected finding to test

Likely finding:

```text
G5.40's global candidate-level safe-region criterion is too coarse.
There may be per-stratum safe/useful regions hidden inside globally unsafe or boundary candidates.
```

Stage A decisions:

```text
g540_global_no_region_but_stratum_regions_exist_continue_g541
g540_no_stratum_signal_continue_candidate_design
g540_artifact_blocker_stop
```

## 5. Stage B — Create per-stratum region labels

Create:

```text
scripts/create_repair5g541_per_stratum_region_labels.py
```

Outputs:

```text
outputs/tables/phase5p5_repair5g541_candidate_stratum_region_labels.csv
outputs/tables/phase5p5_repair5g541_candidate_stratum_pairwise.csv
outputs/tables/phase5p5_repair5g541_candidate_stratum_safe_regions.csv
outputs/tables/phase5p5_repair5g541_candidate_stratum_unsafe_regions.csv
outputs/tables/phase5p5_repair5g541_candidate_stratum_boundary_regions.csv
outputs/reports/phase5p5_repair5g541_per_stratum_region_labels.md
outputs/reports/phase5p5_repair5g541_per_stratum_region_labels_summary.json
```

### B.1 Region unit

Define region key as:

```text
candidate_id
map_family
agents
budget_ms
iteration_bucket
```

Use:

```text
iteration_bucket = final_only / iteration0 / iteration1 / any
```

If a policy cannot change per iteration at runtime, keep iteration-specific labels diagnostic and create run-level equivalents:

```text
run_level_stratum = candidate_id + map_family + agents + budget_ms
```

### B.2 Deployable safety labels

For each region, compute vs:

```text
static_flow_shield
frozen_family_static_goal_aware
best_fixed_static_goal_aware
additive_ltm floor
```

Region labels:

```text
safe_vs_static_flow
safe_vs_family_static
useful_vs_static_flow
quality_delta_vs_static_flow
better/equal/worse
success_regression_count
success_gain_count
support_pairs
seed_block_support
context_support
```

### B.3 Region thresholds

Initial diagnostic thresholds:

```text
support_pairs >= 20
seed_block_support >= 1
context_support >= 5
```

Strong support thresholds:

```text
support_pairs >= 60
seed_block_support >= 2
context_support >= 20
map_budget_agent_support = 1 exact stratum
```

For final deployable region:

```text
support_pairs >= 80
seed_block_support >= 3
success_regression_vs_static_flow = 0
success_regression_vs_family_static = 0
quality_only_mean_delta_vs_static_flow <= 0
better_count >= worse_count or safe_high_margin_count > 0
```

Do not require a candidate to be safe globally.

## 6. Stage C — Balanced support extension plan

Create:

```text
scripts/create_repair5g541_balanced_support_extension_plan.py
```

Outputs:

```text
outputs/tables/phase5p5_repair5g541_balanced_support_extension_plan.csv
outputs/reports/phase5p5_repair5g541_balanced_support_extension_plan.md
outputs/reports/phase5p5_repair5g541_balanced_support_extension_plan_summary.json
```

### C.1 Candidate-stratum selection

Select candidate-stratum pairs from:

```text
1. G5.40 boundary candidates:
   repair5g539_s2_110
   repair5g539_s1_026
   repair5g539_s2_089
   repair5g539_s1_000

2. G5.40 unsafe-but-near-useful candidates:
   candidates with low success_regression_count and negative/near-zero delta in at least one stratum

3. G5.40 Stage 1 top candidates that were filtered out globally but have per-stratum positives

4. Static anchors:
   static_flow_shield
   best_fixed_static_goal_aware
   frozen_family_static_goal_aware
   additive_ltm
```

Maximum candidate-stratum hypotheses:

```text
target = 24..48 candidate-stratum pairs
hard cap = 72 candidate-stratum pairs
```

### C.2 Balanced seed blocks

Use fresh seeds and force at least three seed blocks:

```text
support_extension_seeds:
  826..905
```

Split into blocks:

```text
826..845
846..865
866..885
886..905 optional stress
```

For each candidate-stratum pair, select contexts across at least three seed blocks.

### C.3 Size target

```text
minimum_solver_rows = 6000
target_solver_rows = 12000..30000
minimum_candidate_stratum_pairs = 24
minimum_seed_blocks_per_pair = 3 for priority pairs
minimum_contexts_per_pair = 20
```

If runtime is constrained, reduce candidate-stratum pairs, not seed-block diversity.

## 7. Stage D — Run balanced support extension

Create:

```text
scripts/run_repair5g541_balanced_support_extension.py
scripts/analyze_repair5g541_balanced_per_stratum_regions.py
```

Outputs:

```text
outputs/logs/phase5p5_repair5g541_balanced_support_extension/*.jsonl
outputs/tables/phase5p5_repair5g541_balanced_support_extension_results.csv
outputs/tables/phase5p5_repair5g541_balanced_candidate_stratum_leaderboard.csv
outputs/tables/phase5p5_repair5g541_balanced_supported_safe_regions.csv
outputs/tables/phase5p5_repair5g541_balanced_supported_unsafe_regions.csv
outputs/tables/phase5p5_repair5g541_balanced_supported_boundary_regions.csv
outputs/reports/phase5p5_repair5g541_balanced_support_extension.md
outputs/reports/phase5p5_repair5g541_balanced_per_stratum_regions_summary.json
```

### D.1 Required metrics

For each candidate-stratum pair:

```text
support_pairs
seed_block_support
context_support
success_regression_vs_static_flow
success_regression_vs_family_static
quality_only_mean_delta_vs_static_flow
better/equal/worse
safe_high_margin_count
fallback static baseline
```

### D.2 Supported region decision

A supported safe/useful region requires:

```text
success_regression_vs_static_flow = 0
success_regression_vs_family_static = 0
support_pairs >= 80
seed_block_support >= 3
context_support >= 20
quality_only_mean_delta_vs_static_flow <= 0
better_count >= worse_count or safe_high_margin_count > 0
```

If no supported per-stratum regions exist after this stage, do not train a generator. Decision path should go to candidate-design redesign.

## 8. Stage E — Local refinement around supported strata

Only if Stage D finds supported safe/useful regions.

Create:

```text
scripts/create_repair5g541_stratum_local_refinement_space.py
scripts/run_repair5g541_stratum_local_refinement.py
scripts/analyze_repair5g541_final_stratum_regions.py
```

Outputs:

```text
outputs/tables/phase5p5_repair5g541_stratum_local_refinement_space.csv
outputs/logs/phase5p5_repair5g541_stratum_local_refinement/*.jsonl
outputs/tables/phase5p5_repair5g541_stratum_local_refinement_results.csv
outputs/tables/phase5p5_repair5g541_final_supported_stratum_regions.csv
outputs/tables/phase5p5_repair5g541_final_stratum_policy_candidates.csv
outputs/reports/phase5p5_repair5g541_final_stratum_regions.md
outputs/reports/phase5p5_repair5g541_final_stratum_regions_summary.json
```

### E.1 Refinement perturbations

Around each supported region, perturb:

```text
flow_shield_beta ± 0.05 / ± 0.10
max_flow_shield ± 0.25
rho_flow ± 0.02 / ± 0.05
alpha_wait_or_nonprogress ± 0.10
alpha_cong_blocked ± 0.10 / ± 0.15
alpha_cong_committed ± 0.10
```

Hard cap:

```text
refinement_candidates <= 64
```

### E.2 Final support

A final stratum region must have:

```text
support_pairs >= 120
seed_block_support >= 3
success_regression_vs_static_flow = 0
success_regression_vs_family_static = 0
quality_only_mean_delta_vs_static_flow < 0
better_count_vs_static_flow >= worse_count_vs_static_flow
```

## 9. Stage F — Train region predictor only if warranted

Create:

```text
scripts/train_eval_repair5g541_region_predictor_if_warranted.py
```

Outputs:

```text
outputs/tables/phase5p5_repair5g541_region_predictor_eval.csv
outputs/tables/phase5p5_repair5g541_region_predictor_predictions.csv
outputs/tables/phase5p5_repair5g541_region_predictor_negative_controls.csv
outputs/reports/phase5p5_repair5g541_region_predictor.md
outputs/reports/phase5p5_repair5g541_region_predictor_summary.json
artifacts/models/laur_ltm/repair5g541_region_predictor_manifest.json
```

If final regions are absent:

```text
decision = region_predictor_skipped_no_supported_stratum_regions
```

If present, train diagnostic model to predict:

```text
safe_region_id
fallback_static_region
risk of success regression
expected static-relative utility
```

Inputs:

```text
map_family
agents
budget
context/static features
exact goal-distance features if available
failure-audit features if available
candidate parameter vector
```

Do not claim runtime.

## 10. Stage G — Frozen stratum policy and blind replay

Only if Stage E finds final supported regions.

Create:

```text
scripts/create_repair5g541_frozen_stratum_policy.py
scripts/run_repair5g541_frozen_stratum_blind_replay.py
scripts/analyze_repair5g541_frozen_stratum_blind_evidence.py
```

Outputs:

```text
outputs/tables/phase5p5_repair5g541_frozen_stratum_policy.csv
outputs/reports/phase5p5_repair5g541_frozen_stratum_policy.md
outputs/reports/phase5p5_repair5g541_frozen_stratum_policy_summary.json

outputs/logs/phase5p5_repair5g541_frozen_stratum_blind_replay/*.jsonl
outputs/tables/phase5p5_repair5g541_frozen_stratum_blind_replay_results.csv
outputs/tables/phase5p5_repair5g541_frozen_stratum_selected_vs_static_flow.csv
outputs/tables/phase5p5_repair5g541_frozen_stratum_selected_vs_family_static.csv
outputs/tables/phase5p5_repair5g541_frozen_stratum_failure_cases.csv
outputs/reports/phase5p5_repair5g541_frozen_stratum_blind_replay.md
outputs/reports/phase5p5_repair5g541_frozen_stratum_blind_evidence.md
outputs/reports/phase5p5_repair5g541_frozen_stratum_blind_evidence_summary.json
```

Blind seeds:

```text
906..985
optional 986..1025 if runtime acceptable
```

Targets:

```text
minimum_solver_rows = 6000
target_solver_rows = 12000..30000
minimum_pairs_vs_static_flow = 1000
minimum_contexts = 240
```

Blind success requires:

```text
success_regression_vs_static_flow = 0
success_regression_vs_family_static = 0
quality_only_mean_delta_vs_static_flow < 0
better_count_vs_static_flow > worse_count_vs_static_flow
non_static_selection_rate > 0.05
```

If no supported policy exists, blind replay is not warranted and should be skipped with explicit summary.

## 11. Decision policy

Create:

```text
scripts/write_repair5g541_decision.py
```

Outputs:

```text
outputs/reports/phase5p5_repair5g541_decision.md
outputs/reports/phase5p5_repair5g541_decision_summary.json
```

Possible decisions:

```text
g541_per_stratum_param_regions_blind_positive_continue_runtime_preflight_later
g541_supported_stratum_regions_found_continue_refinement
g541_no_supported_stratum_regions_continue_candidate_design
g541_global_negative_but_stratum_signal_continue_sampling
g541_underpowered_continue_runs
g541_success_regression_blocks_stratum_policy
g541_artifact_or_solver_blocker
```

Strong positive requires:

```text
G5.40 global-vs-stratum audit completed
balanced support extension executed
final supported stratum regions exist
blind replay executed
blind pairs_vs_static_flow >= 1000
success_regression_vs_static_flow = 0
success_regression_vs_family_static = 0
quality_only_mean_delta_vs_static_flow < 0
better_count_vs_static_flow > worse_count_vs_static_flow
all claims closed
external/lacam2 clean
reserved IDs untouched
```

Medium positive:

```text
balanced support extension finds supported stratum regions,
but final refinement or blind replay is not warranted/underpowered.
```

Negative but informative:

```text
no supported per-stratum regions after balanced seed-block support.
```

This should lead to candidate-design redesign, not selector training.

## 12. Validation commands

Run and record:

```powershell
git status --short
python -m py_compile scripts\repair5g541_common.py scripts\verify_repair5g541_g540_artifacts.py scripts\audit_repair5g541_g540_global_vs_stratum_regions.py scripts\update_repair5g541_strategy_docs.py scripts\create_repair5g541_per_stratum_region_labels.py scripts\create_repair5g541_balanced_support_extension_plan.py scripts\run_repair5g541_balanced_support_extension.py scripts\analyze_repair5g541_balanced_per_stratum_regions.py scripts\create_repair5g541_stratum_local_refinement_space.py scripts\run_repair5g541_stratum_local_refinement.py scripts\analyze_repair5g541_final_stratum_regions.py scripts\train_eval_repair5g541_region_predictor_if_warranted.py scripts\create_repair5g541_frozen_stratum_policy.py scripts\run_repair5g541_frozen_stratum_blind_replay.py scripts\analyze_repair5g541_frozen_stratum_blind_evidence.py scripts\write_repair5g541_decision.py
C:\Users\38908\.conda\envs\czr004\python.exe -m py_compile scripts\repair5g541_common.py scripts\train_eval_repair5g541_region_predictor_if_warranted.py
python scripts\verify_repair5g541_g540_artifacts.py
python scripts\audit_repair5g541_g540_global_vs_stratum_regions.py
python scripts\update_repair5g541_strategy_docs.py
python scripts\create_repair5g541_per_stratum_region_labels.py
python scripts\create_repair5g541_balanced_support_extension_plan.py
powershell -ExecutionPolicy Bypass -File scripts\build_phase1a_batch.ps1
python scripts\run_repair5g541_balanced_support_extension.py --max-workers 1
python scripts\analyze_repair5g541_balanced_per_stratum_regions.py
python scripts\create_repair5g541_stratum_local_refinement_space.py
python scripts\run_repair5g541_stratum_local_refinement.py --max-workers 1
python scripts\analyze_repair5g541_final_stratum_regions.py
C:\Users\38908\.conda\envs\czr004\python.exe scripts\train_eval_repair5g541_region_predictor_if_warranted.py --epochs 80 --bootstrap-samples 300
python scripts\create_repair5g541_frozen_stratum_policy.py
python scripts\run_repair5g541_frozen_stratum_blind_replay.py --max-workers 1
python scripts\analyze_repair5g541_frozen_stratum_blind_evidence.py
python scripts\write_repair5g541_decision.py
python - <<'PY'
import json, glob
for path in glob.glob('outputs/reports/phase5p5_repair5g541_*summary.json'):
    with open(path, encoding='utf-8') as f:
        json.load(f)
print('G5.41 JSON summaries parse')
PY
git diff --check
git status --short -- external/lacam2/lacam2
```

If pytest is available:

```powershell
C:\Users\38908\.conda\envs\czr004\python.exe -m pytest tests\test_repair5g_dual_channel_ltm.py tests\test_repair5g5_runtime_selector_policy.py tests\test_repair5g5_contextual_selector_export.py tests\test_repair5g5_aaai_quality_gates.py tests\test_repair5g52_checkpoint_schema.py
```

## 13. Commit and push

At the end:

```powershell
git status --short
git add czr004_g541_balanced_per_stratum_static_flow_safe_region_mining_plan.md docs/codex-worklog.md deep-research-report.md phase4_6_laur_ltm_codex_execution_plan.md docs/goal_aware_dual_channel_ltm_research_strategy.md scripts/repair5g541_*.py outputs/reports/phase5p5_repair5g541_* outputs/tables/phase5p5_repair5g541_* outputs/datasets/phase5p5_repair5g541_* artifacts/models/laur_ltm/repair5g541_*_manifest.json cpp/tools/phase1a_batch.cpp
git commit -m "eval: add G5.41 per-stratum static-flow safe-region mining"
git push origin codex/g531-slice-pilot
```

Only include `cpp/tools/phase1a_batch.cpp` if project-owned alias support is added. Never include `external/lacam2/lacam2/**`.

## 14. Short prompt for Codex

```text
Continue czr004 after G5.40 commit 8ec7f9c on codex/g531-slice-pilot. Implement Repair5G.5.41 as balanced per-stratum static-flow safe-region mining. G5.40 was a high-quality negative result at global candidate level: Stage 1 covered 128/128 candidates and Stage 2 ran 6120 rows over 170 contexts, but no globally supported safe/useful region was found. However, this does not rule out per-stratum safe parameter regions. Stage 2 boundary candidates such as repair5g539_s2_110 had 0 regressions and negative quality delta but failed support because seed_block_support was only 1; globally unsafe candidates may still be safe/useful in specific map/budget/agent strata.

First verify G5.40 and audit global-vs-stratum evidence: reclassify Stage1/Stage2 results at candidate × map_family × agents × budget × iteration_bucket, audit seed-block support, identify boundary and near-miss regions. Update strategy docs to record that safe regions are per-stratum, not global candidates. Create per-stratum region labels and a balanced support-extension plan that targets 24-48 promising candidate-stratum pairs, including G5.40 boundary candidates and unsafe-but-near-useful candidates. Use fresh seeds 826..905 and force at least three seed blocks per priority pair. Run real solver support extension, then analyze supported safe/useful regions with zero regression vs static_flow/family_static and enough seed/context support. If supported regions exist, locally refine around those strata and optionally train a region predictor; then freeze a stratum policy and run blind replay. If no supported per-stratum regions exist after balanced seed-block support, do not train a fake selector—return candidate-design redesign. Keep all Phase5.5/Phase6/runtime/learned-runtime/AAAI claims closed and do not touch external/lacam2/lacam2.
```
