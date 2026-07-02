# Gate-3B Failure Attribution

## H1: Label-v5.4 is too conservative

Evidence for: Label-v5.4 selected safe targets with zero unexcluded hard timeouts, but the one-primary actor only achieved weak additive uplift and no static-flow uplift. Mean target L1 distance to g556 is `0.018269681479323712` and to static-flow is `0.07872480399932148`; inspect `g567_gate3b_labelv54_by_context.csv` for zero/anchor-like target counts.

Evidence against: Label replay still contains positive candidates and a weak positive additive signal, so the label is not completely collapsed.

Probability: medium

## H2: Candidate pool lacks high-quality safe theta

Evidence for: Safe oracle median improvement vs static-flow is `None` on the label candidate pool. If this is small, the candidate pool itself does not provide enough static-flow headroom.

Evidence against: There are positive candidates in Label-v5.4, and safe oracle vs additive is `None`.

Probability: medium

## H3: Actor underfit or training too short

Evidence for: The final trained actor has development median vs additive `0.010034757202264051` and vs static-flow `0.0` despite 4 GPU-active hours; full per-epoch loss curves were not stored, limiting fit diagnosis.

Evidence against: Training completed two seeds, BF16, token batching, and nonzero gradient norms; there is no mechanical training failure.

Probability: medium

## H4: Public/official distribution shift

Evidence for: Development public fraction is `0.7`, official scenario fraction is `0.336`, and old G5.65 signal came from a different pooled discovery/evaluation setup.

Evidence against: Gate-3B label and development splits were both generated under the repaired public/synthetic mixture rules with zero parent leakage.

Probability: medium

## H5: Static-flow is too strong on this panel

Evidence for: Static-flow median relative improvement is `0.0`, static clustered LCB is `-0.024142784246652928`, and q95 harmful delta is `0.21588373910299968`.

Evidence against: A5 has some cases beating static-flow; see the case-study CSV.

Probability: high

## H6: A5 architecture bottleneck

Evidence for: The actor predictions remain relatively close to g556/static anchors: prediction L1 to g556 `0.002083667624829306`, to static-flow `0.08951411757578928`.

Evidence against: The 3000-agent memory contract passed with OD Perceiver and no quadratic OD self-attention collapse.

Probability: low-to-medium

## H7: Solver/timing noise

Evidence for: Some large/tail rows have high runtimes and no-solution equivalents.

Evidence against: Development replay finished 3000/3000 with zero hard timeouts and direct exact rows, so timing noise is unlikely to explain the research-signal failure.

Probability: low
