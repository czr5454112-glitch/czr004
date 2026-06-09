# Phase5.5 LAUR Diagnostic Preflight Plan

Date: 2026-05-31 12:14:34

## Boundary

This is a diagnostic preflight plan only. Phase5.5 runtime remains forbidden, and Phase6 remains forbidden until closed-loop learned benefit over additive LTM is shown.

- diagnostic preflight warranted: `True`
- Phase5.5 allowed: `False`
- Phase6 allowed: `False`

## Required Comparisons

- LaCAM*
- LaCAM*+LTM
- Repair3 safe runtime
- Repair5C composite/reranker diagnostic
- always-additive/defer
- oracle replay or teacher-forced update choices if feasible

## Stop Conditions

- offline candidate is worse than additive LTM on success or sum_of_loss_ratio
- non-additive rate collapses to zero
- strict safety mask blocks all learned choices
- oracle replay fails to transfer any measurable advantage
