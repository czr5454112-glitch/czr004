# Phase5.5 Repair5G.5.9 Counterfactual Probe Run

- decision: `counterfactual_probe_not_run_server_required`
- planned_contexts: `60`
- planned_candidates: `14`
- planned_rows: `2520`
- observed_ids_only: `True`
- ids_166_205_untouched: `True`

The local Python layer can design the expanded lattice, but the current C++/probe harness does not expose these new G5.9 lattice candidates as executable UpdateLTM runtime candidates without a dedicated server run.
