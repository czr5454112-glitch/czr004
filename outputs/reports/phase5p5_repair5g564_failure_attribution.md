# G5.64 Failure Attribution

- G5.63 scaling was invalid as primary evidence because label/outcome counts were used as scalar features.
- G5.63 tiny overfit did not test graph-actor memorization; it tested free per-context theta behavior.
- G5.64 loss geometry found `0` near-duplicate positive/harmful theta conflicts.
- G5.64 fixed solver transfer remains blocked until a fresh fixed panel is run with the selected leakage-free actor.
- Censored rows continue to be treated as unknown, not as negative/no-op supervision.
