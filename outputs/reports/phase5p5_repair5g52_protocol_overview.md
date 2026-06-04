# Phase5.5 Repair5G.5.2 Protocol Overview

Repair5G.5.2 is a diagnostic and infrastructure phase, not a learned-method promotion.

- Scope: runtime UpdatePolicy equivalence, force-additive/disable closure, replayable UpdateLTM checkpoint export, and counterfactual label readiness.
- Allowed IDs: observed IDs only, preferably 146..165 for new smoke.
- Reserved IDs: 166..205 remain untouched until runtime equivalence, policy controls, and safe observed-ID smoke pass.
- Allowed C++ changes: project-owned runtime logging/checkpoint hooks in `cpp/tools/phase1a_batch.cpp` and `cpp/ltm`.
- Forbidden changes: no LaCAM*/PIBT semantic changes, no action prediction, no learned restart, no candidate deletion, no larger neural selector training.
- Required status while gates are open: `phase5p5_allowed=false`, `phase6_allowed=false`, `aaai_ready=false`.

Gate order:

1. Candidate registry and UpdateParams hash equivalence.
2. Runtime always-static/map-agent/shadow-static reproducer.
3. Force-additive and disable policy closure.
4. Replayable `traffic_before` + trace checkpoint export only if gates 1-3 pass.
5. Counterfactual UpdateLTM short-probe labels only if checkpoint replayability passes.
6. Safe mixture/residual G6 design only if true contextual labels exist.
