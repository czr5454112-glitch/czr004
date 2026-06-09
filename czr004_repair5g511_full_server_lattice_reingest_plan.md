# czr004 Repair5G.5.11 Full Server Lattice Re-ingest Plan

Date: 2026-06-07
Base: `44035e6 repair5g: finish g511 server lattice prompt`
Branch: `phase4f5p5-stable-attention-lau`

## Objective

Repair5G.5.11 takes the executable G5.10 bounded goal-aware dual-channel UpdateLTM lattice from a 2-context local smoke to the required full observed-ID server run:

```text
60 contexts x 14 candidates x 4 budgets = 3360 lattice probe rows
```

The goal is not to claim a learned runtime policy. The goal is to verify whether the bounded parameter lattice improves the oracle upper bound on the full observed confidence bank, then gate the next label/feature/policy step.

## Server Execution

Server used:

```text
instance = ackcs-00gjh3x3
resource = 2 x RTX4090, 22 vCPU, 120GB RAM
os = Ubuntu 24.04
framework = PyTorch 2.7.0 / PyTorch-25.03-py3
```

Execution notes:

```text
GitHub clone from the server failed due outbound network/TLS access.
A local source bundle from pushed commit 44035e6 was uploaded instead.
tmux was installed on the server.
The first max-workers=4 run completed solver tasks but produced corrupt shared JSONL from concurrent appends.
The accepted run used max-workers=1 and completed cleanly.
```

The committed launch script is:

```text
scripts/server_run_repair5g511_full_lattice.sh
```

It uses Linux binary path:

```text
build/phase1a-batch/phase1a_batch
```

and keeps Phase5.5/Phase6/runtime/AAAI claims closed.

## Re-ingest Artifacts

Raw server artifacts were pulled locally under:

```text
outputs/server/phase5p5_repair5g511_remote/
```

The 1.45GB checkpoint JSONL is retained there for local audit only and is intentionally not promoted to GitHub-tracked G5.11 outputs.

G5.11 tracked outputs are:

```text
outputs/tables/phase5p5_repair5g511_full_lattice_counterfactual_results.csv
outputs/tables/phase5p5_repair5g511_full_lattice_counterfactual_plan.csv
outputs/tables/phase5p5_repair5g511_lattice_oracle_by_context.csv
outputs/tables/phase5p5_repair5g511_lattice_candidate_distribution.csv
outputs/tables/phase5p5_repair5g511_lattice_by_map_agent.csv
outputs/tables/phase5p5_repair5g511_confidence_targets_v5.csv
outputs/reports/phase5p5_repair5g511_*.md
outputs/reports/phase5p5_repair5g511_*summary.json
```

## Gate Result

Candidate-space gate passed:

```text
results_rows = 3360
candidate_count = 14
measured_contexts = 60
primary_1000_2000_stable_contexts = 60
candidate_space_oracle_gap_vs_g58 = -0.028445334327249994
mean_oracle_gap_over_static = -0.035097435576500004
mean_oracle_gap_over_additive = -0.12287598200416668
oracle_beats_static_fraction = 0.8666666666666667
oracle_beats_additive_fraction = 1.0
ids_166_205_untouched = true
```

Confidence-target gate failed:

```text
stable_high_confidence_parameter_candidate = 52
stable_static = 8
stable_static_or_abstain = 8 < 10
no_solution_or_budget_abstain_count = 0
decision = confidence_targets_v5_failed_continue_label_design
```

Therefore feature v3 and abstention-aware policy training are not allowed in G5.11.
