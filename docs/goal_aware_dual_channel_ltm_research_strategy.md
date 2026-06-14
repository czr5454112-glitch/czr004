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
