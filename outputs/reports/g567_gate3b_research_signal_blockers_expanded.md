# Gate-3B Research Signal Blockers Expanded

Blocker table: `outputs/tables/g567_gate3b_research_signal_blockers_expanded.csv`

Gate logic source: `scripts/run_repair5g567_gate3b_bounded_pilot.py::compute_research_signal`.

Primary pair count: `500`
Margin: `0.043`

Tier-A failed primarily because additive median relative improvement was `0.010034757202263999`, below the required `0.05`.

Tier-B failed because the static-flow median was exactly `0.0` rather than positive and the clustered lower bound was negative; q95 harmful delta was also above the configured margin.
