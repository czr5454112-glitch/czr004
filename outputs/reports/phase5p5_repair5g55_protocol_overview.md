# Phase5.5 Repair5G.5.5 Protocol Overview

G5.5 scales same-context UpdateLTM labels over observed IDs only, with each label row produced by applying a candidate UpdateParams set to the same pre-update traffic snapshot and trace events, then measuring a short downstream probe.

Default scope:
- maps: `random-32-32-20`, `maze-32-32-4`, `warehouse-10-20-10-2-1`
- agents: `50`, `100`
- primary observed IDs: `146..165`; stratified smoke may use a smaller observed subset and must report missing target coverage
- candidates: the seven compact G5.4 candidates unless explicitly expanded after candidate-set audit
- primary short budget: `1000 ms`; stability diagnostics compare `250`, `500`, `1000`, and optional `2000 ms`

Current scaled context count: `60`. Smoke passed: `True`. Full 120-context target passed: `False`.

No final full-run outcomes are used as per-update labels. G6 training is not part of G5.5.
