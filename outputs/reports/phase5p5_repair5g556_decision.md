# G5.56 Decision

- decision: `g556_transformer_fixed_global_candidate_blind_passed_keep_claims_closed`
- primary baseline: `g554_c00051`
- training rows: `968362`
- generated candidates: `100000`
- Stage1 rows: `304500`
- Stage2 rows: `430000`
- blind rows: `360000`
- optimized fixed candidate promoted: `True`

G5.56 keeps the neural model training-time only. It does not deploy a contextual selector, checkpoint policy, abstention gate, or runtime learned UpdateParams policy.
