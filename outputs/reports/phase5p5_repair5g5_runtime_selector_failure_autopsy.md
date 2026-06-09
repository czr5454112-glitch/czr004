# Phase5.5 Repair5G.5 Runtime Selector Failure Autopsy

G5 runtime selector integration is auditable, but the learned runtime selector failed observed-ID smoke. This autopsy preserves the result as a selector-transfer failure, not a flow-shield representation failure.

## Selector Rule

- feature: `ltm_iterations`
- threshold: `2.5`
- left_method: `repair5g_dual_c_equiv_c100_b100_w100_d090`
- right_method: `repair5g2_best_frozen_static_candidate`
- fallback_static: `repair5g2_best_frozen_static_candidate`

## Core Metrics

- runtime learned selector mean: `0.00350549546894118`
- static flow-shield mean: `-0.02232529495036001`
- map-agent flow-shield mean: `-0.026533959629559997`
- random-feature diagnostic mean: `-0.020724342164560004`
- shuffled-label diagnostic mean: `-0.020724342164560004`
- runtime better/equal/worse: `8/27/23`
- disable_policy_compliant_before_g51: `False`
- force_additive_policy_compliant_before_g51: `False`

## Diagnosis

The bad stump overused the weak C-equiv branch in early runtime iterations. Observed updates selecting the left C-equiv branch at iterations 0..2: `147`; later static-branch updates: `0`. That timing suppresses the early flow-shield updates that made G2/G4 strong on maze and random.

## Offline To Runtime Reconciliation

The offline stump mean was about `-0.025178`, but runtime smoke mean was `0.00350549546894118`. The offline rows are run-level candidate outcomes, while the runtime hook invokes the stump per UpdateLTM iteration. The same `ltm_iterations <= 2.5` rule therefore changes from a coarse run descriptor into an early-update switch, choosing C-equiv before the traffic map has accumulated the flow-shield context. That feature-granularity mismatch explains the sign flip without implicating the flow-shield representation.

## Random/Shuffled Interpretation

The random/shuffled diagnostics did not prove label learning. In this C++ diagnostic mode, the even-agent random-feature path and the shuffled-label path mostly route to the strong static flow-shield branch, while the learned stump routes early iterations through `repair5g_dual_c_equiv_c100_b100_w100_d090`. That is why random/shuffled mean `-0.020724342164560004`/`-0.020724342164560004` tracks the static mean `-0.02232529495036001`.

## Policy Controls

G5 strict smoke marked disable/force-additive noncompliant because individual short-budget rows were not exactly equal to LTM. G5.1 treats this as a required reproducer/classification task: if semantic mismatch count remains zero and group-level harm remains zero, classify as time-budget sensitivity rather than a C++ semantic mapping bug.

## Artifacts

- `outputs/tables/phase5p5_repair5g5_selector_decision_distribution.csv`
- `outputs/tables/phase5p5_repair5g5_selector_iteration_distribution.csv`
- `outputs/tables/phase5p5_repair5g5_selector_vs_static_regret_cases.csv`
- `outputs/tables/phase5p5_repair5g5_runtime_feature_drift.csv`
- `outputs/tables/phase5p5_repair5g5_control_policy_failures.csv`
- `outputs/tables/phase5p5_repair5g5_bad_stump_failure_cases.csv`

`phase5p5_allowed=false`, `phase6_allowed=false`, and `aaai_ready=false` remain closed.
