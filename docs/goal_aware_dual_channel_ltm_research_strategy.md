# Goal-Aware Dual-Channel LTM Research Strategy

## 2026-06-12 - G5.39 strategic update: from selector to static-flow parameter optimization

1. Additive LTM is now only a floor baseline.
2. The main baseline ladder is:
   additive_ltm
   static_flow_shield
   best_fixed_static_goal_aware
   frozen_family_static_goal_aware
   posthoc/oracle static diagnostic only
3. G5.37 showed old selector over old candidates does not beat static baselines.
4. G5.38 rebuilt direct labels and found residual opportunity, but one global residual candidate failed blind safety.
5. Therefore the next learning target is not candidate-ID selection.
6. The next learning target is static-flow-relative UpdateParams optimization:
   learn safe residual parameters around static_flow / best static.
7. A GGO-style workflow is adopted:
   search / optimize guidance parameters first,
   identify safe regions,
   then train a model to predict/generate those parameters.
8. Runtime / Phase5.5 / Phase6 / AAAI claims remain closed.

The learned component is not allowed to claim progress by merely selecting among stale hand-written candidates. From G5.39 onward, the learning target is static-flow-relative parameter/residual generation: use real solver outcomes to discover safe UpdateParams regions around static_flow and train models to predict those bounded residual parameters under zero-regression constraints.

## 2026-06-12 - G5.40 strategic update: underpowered parameter search is not evidence

G5.39 established the GGO-style direction but was underpowered: only 8 contexts and 8 parameter candidates were run in the optimizer probe. Therefore G5.40 requires staged, sufficiently powered parameter search before model training or frozen policy claims.

A safe region must have support across multiple seeds and at least one nontrivial map/budget/agent stratum. The project will treat underpowered runs as continuation artifacts, not positive or negative scientific conclusions.

From G5.40 onward, parameter optimization rounds must report:

- candidate coverage
- stratum coverage
- seed-block coverage
- safe-region support
- blind support
- whether the result is underpowered

No generator, frozen policy, runtime, Phase5.5, Phase6, or AAAI claim is allowed until the safe-region support thresholds are met.

## 2026-06-12 - G5.41 strategic update: safe regions are per-stratum, not global candidates

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

From G5.41 onward, a static-flow parameter region is evaluated at the deployable stratum level. A candidate that is unsafe globally may still be valuable if a frozen pre-replay policy can restrict it to strata where it has zero regression and nontrivial static-relative gain.

## 2026-06-12 - G5.42 strategic update: residual overlay must sit on a deployable static fallback ladder

G5.41 found per-stratum residual regions and achieved zero success regression versus static_flow in blind replay, but failed versus frozen_family_static.
This indicates that static_flow alone is not the correct fallback baseline in all strata.
From G5.42 onward, learned/static-flow residuals are evaluated as an overlay on a deployable static fallback ladder:
  additive_ltm
  static_flow_shield
  best_fixed_static_goal_aware
  frozen_family_static_goal_aware
Residual parameters are only allowed in supported strata where they beat the selected deployable static baseline with zero regression.

The learned residual component is not a replacement for the strongest deployable static baseline; it is a conditional overlay. The first decision is which deployable static baseline is safest for the stratum, and the second decision is whether a supported residual region can safely improve over that baseline.

## 2026-06-14 - G5.46 strategic update: real continuous-theta replay is mandatory

G5.45 built the neural continuous theta infrastructure but did not run new continuous-theta solver replay. From G5.46 onward, neural UpdateParams evidence requires real newly materialized continuous-theta solver rows. Retrospective rows may train diagnostic surrogates, but cannot satisfy generator or replay gates.

The active learning loop is now theta proposal, real solver-facing replay, calibrated risk/utility modeling, and then generated-theta replay if gates pass. Static selector gains remain diagnostic baselines, not LAUR progress.

## 2026-06-14 - G5.47 strategic update: SafeGate v2 for neural continuous UpdateParams

G5.46 evidence is now treated as materialization/evaluability-confounded unless full theta is executed and finite paired quality outcomes exist. The old selector-era zero-regression gate is no longer reused as a single blanket blocker for neural continuous theta exploration.

SafeGate v2 is layered:

- Tier I invariant safety gates are never relaxed: external solver code clean, reserved IDs untouched, candidate recognition, bounded finite UpdateParams, fulltheta fingerprint match, force-additive parity, cost bounds, and no solver semantic change.
- Tier E evaluability gates are required before positive or negative interpretation: finite ratio rate, finite paired rows, nontrivial primary baseline success, and paired baseline materialization.
- Tier X exploration gates intentionally allow unsafe theta as risk-model data. Unsafe exploration cannot support positive, blind, runtime, Phase5.5, Phase6, or AAAI claims.
- Tier R/P gates promote only supported regions or generated-theta policies against the declared primary baseline, currently `static_flow_shield`.
- Tier B blind/runtime/paper gates remain strict and are not relaxed in G5.47.

Strong static baselines such as `frozen_family_static_goal_aware`, `best_fixed_static_goal_aware`, and posthoc/oracle static variants are diagnostic stress tests unless a later experiment explicitly declares one as the primary baseline. During exploration, losing to every strong hand-written static variant is not by itself a learned UpdateLTM failure; static selector wins remain diagnostic, not LAUR progress.

## 2026-06-14 - G5.48 strategic update: static_flow primary and evaluable horizons

From G5.48 onward, `static_flow_shield` is the primary fixed baseline for neural continuous `UpdateParams`. The gate asks whether learned/fulltheta UpdateLTM can safely improve over this hand-designed static-flow LTM variant. Additive LTM is a paper-faithful floor. Strong family/static variants are diagnostic baselines, not the primary target and not selector actions.

G5.48 also establishes that a declared calibration grid is not evidence. Real solver-facing horizon calibration must report materialized rows, context-horizons, static_flow rows, finite-ratio rows, both-success pairs versus static_flow, and no-probe/no-solution diagnostic rows separately. Underpowered calibration is a continuation result, not an algorithmic negative.

The G5.48 local calibration produced real rows and found some evaluable stratum-horizons, but it did not reach the finite-row gate required for fulltheta replay. Therefore fulltheta replay, generator training, targeted replay, blind replay, runtime, Phase5.5, Phase6, and AAAI claims remain closed.

## 2026-06-14 - G5.49 strategic update: calibrated-core fulltheta signal, generator still gated

G5.49 completed the local calibrated-core evaluability stage and ran a static_flow-primary fulltheta replay. The round produced `8220` new calibration rows, `9780` cumulative finite-ratio rows, `30282` fulltheta replay rows, `18514` both-success pairs versus `static_flow_shield`, and `10` true safe-gain fulltheta regions. The positive regions are real solver-facing development evidence against the declared primary baseline.

This does not broaden the claim scope. The unique evaluable stratum count is `4`, while selected evaluable horizon rows are a separate metric. Warehouse remains non-evaluable on local budget. SafeGate v2 therefore keeps this as `calibrated_core_subset_development_only`: useful for generator design and server-scale replay, not for runtime, Phase5.5, Phase6, or AAAI claims.

The baseline policy is unchanged: `static_flow_shield` remains the primary baseline for learned/fulltheta continuous `UpdateParams`; `additive_ltm` remains the paper-faithful floor; `frozen_family_static_goal_aware` and `best_fixed_static_goal_aware` remain diagnostics unless explicitly promoted in a later round. The generator/targeted/blind path stays closed until a learned generated-theta policy, not replay-region hindsight, passes the offline risk/utility gate.

## 2026-06-14 - G5.50 strategic update: region-to-policy still gated

G5.50 audits the G5.49 true safe-gain regions and treats them as concentrated development signal, not as a deployable learned policy. The baseline policy is unchanged: `static_flow_shield` remains the primary baseline for learned/fulltheta continuous `UpdateParams`; `additive_ltm` remains the paper-faithful floor; strong static variants remain diagnostics.

SafeGate v2 is not relaxed. Replay-region hindsight must first become a runtime-available bounded `UpdateParams` generator, residual policy, or safe expert mixture with abstention and then survive fresh replay. In the completed local G5.50 pass, expansion (`68570` rows) did not replicate the G5.49 core true-gain regions, active theta search mapped `50065` rows, and the safe expert-mixture policy passed offline. Fresh targeted replay then failed the safety gate with `216` success regressions versus `static_flow_shield`, so blind replay and all runtime/Phase5.5/Phase6/AAAI claims stay closed. The decision label is `g550_iteration_counterfactual_labels_needed_before_generator`.

## 2026-06-15 - G5.51 strategic update: iteration/checkpoint labels before promotion

G5.51 keeps static_flow_shield as the primary baseline and tightens SafeGate after
G5.50 targeted replay failures. Offline generator success is no longer sufficient
for promotion. A learned bounded UpdateParams policy must pass fresh targeted
replay with zero success regressions versus static_flow_shield before blind replay
or runtime claims. The next valid learning signal is iteration/checkpoint-level
counterfactual labels, not final full-run hindsight alone.
