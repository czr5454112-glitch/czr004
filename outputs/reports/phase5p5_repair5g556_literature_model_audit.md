# G5.56 Literature And Model Audit

G5.56 chooses FixedTheta Retrieval-Set Transformer as the primary offline surrogate because the fixed-theta task is both row-level and candidate-set-level. The row encoder models theta/context interactions; retrieval memory supplies local empirical neighborhoods; candidate-set aggregation estimates global fixed-vector risk and utility. This matches the solver-facing lesson from guidance-optimization and learning-MAPF shield work: neural outputs may propose candidates, but only real paired solver replay can promote them.

- primary model family: `FixedTheta Retrieval-Set Transformer`
- required controls: `TabM`, `FT-Transformer`, `GBDT`, heuristic optimizers
- promotion baseline: `g554_c00051`
- runtime learned policy claim: `closed`
