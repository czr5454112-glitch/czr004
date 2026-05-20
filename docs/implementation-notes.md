# Implementation Notes

This file records implementation decisions where the local code cannot be directly checked against an official LTM implementation.

## 2026-05-20 - initial constraints

- LTM public source is not available in the local materials.
- The project will describe its LTM implementation as `paper-faithful reimplementation`.
- The local PDF states the LTM experimental edge-weight range as `[0,10]`; this is the default until contradicted by a primary source.
- LaCAM* is the only solver base for this project.
- Any deviation from the PDF algorithm must be recorded here before it is used in experiments.

## Open Items

- Confirm exact LaCAM* upstream commit after cloning `Kei18/lacam2`.
- Build a line-by-line checklist for LTM Algorithm 1 and Section 4.1 before editing solver code.
- Define quantitative parity tolerance after the first reproducible LTM smoke.
