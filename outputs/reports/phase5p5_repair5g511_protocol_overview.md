# Phase5.5 Repair5G.5.11 Protocol Overview

## Scope

Run the G5.10 executable bounded UpdateLTM parameter lattice at full observed-ID server scale and re-ingest the artifacts under G5.11 names.

## Required Run

```text
maps = random-32-32-20, maze-32-32-4, warehouse-10-20-10-2-1
agents = 50, 100
instance_ids = 146..155
budgets_ms = 250, 500, 1000, 2000
candidates = 14
expected_rows = 3360
```

## Execution

The accepted run used:

```text
scripts/server_run_repair5g511_full_lattice.sh
max_workers = 1
```

The single-worker rerun was required because the initial four-worker server run completed all solver tasks but corrupted a shared JSONL append file.

## Gates

Integrity gate:

```text
results_rows >= 3360
candidate_count == 14
measured_contexts >= 60
primary_1000_2000_contexts >= 60
duplicate context/candidate/budget rows == 0
JSON/CSV parse clean
ids_166_205_untouched = true
```

Candidate-space gate:

```text
primary_1000_2000_stable_contexts >= 40
candidate_space_oracle_gap_vs_g58 < 0
oracle_beats_static_fraction > 0
oracle_beats_additive_fraction > 0
```

Confidence-target gate:

```text
measured_confidence_contexts >= 60
head_b_training_rows >= 40
stable_high_confidence_parameter_candidate >= 10
stable_static_or_abstain >= 10
no_solution_or_budget_abstain_count > 0
```

The run passes integrity and candidate-space gates, then stops at confidence v5.
