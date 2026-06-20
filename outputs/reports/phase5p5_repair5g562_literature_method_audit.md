# Repair5G.5.62 Literature and Source Audit

The audit uses primary arXiv pages and official GitHub repositories. It improves representation, training, safeguards, and experimental design while keeping the project on one run-static continuous theta per instance.

## aaai2024_tfo_lmapf

- title: `Traffic Flow Optimisation for Lifelong Multi-Agent Path Finding`
- source: https://arxiv.org/abs/2308.11234
- version: `arXiv:2308.11234v5, last revised 2024-01-31`
- adopted: Keep C0 congestion and F0 goal-progress separate; represent vertex/wait pressure and edge contraflow explicitly.
- rejected: Do not replace the run-static theta actor with a different MAPF action policy.

## ijcai2024_ggo

- title: `Guidance Graph Optimization for Lifelong Multi-Agent Path Finding`
- source: https://arxiv.org/abs/2402.01446
- version: `arXiv:2402.01446v2, last revised 2024-05-09`
- adopted: Use exact solver replay as final truth; use bounded black-box teacher/control diagnostics only as training data sources.
- rejected: Do not deploy CMA-ES/CEM or stored guidance graph optimization at runtime.

## icra2023_graph_transformer_mapf

- title: `Accelerating Multi-Agent Planning Using Graph Transformers with Bounded Suboptimality`
- source: https://arxiv.org/abs/2301.08451
- version: `arXiv:2301.08451v1, submitted 2023-01-20`
- adopted: Graph attention can guide classical MAPF while preserving solver semantics; test size and density generalization.
- rejected: Do not change LaCAM*/PIBT feasibility semantics.

## aaai2026_lagat

- title: `Graph Attention-Guided Search for Dense Multi-Agent Pathfinding`
- source: https://arxiv.org/abs/2510.17382
- version: `arXiv:2510.17382v1, submitted 2025-10-20`
- adopted: Use pretraining before real-label fine-tuning and an explicit safeguard/trust head for imperfect learned guidance.
- rejected: Do not copy the action-policy target.

## qd_mapper

- title: `QD-MAPPER: A Quality Diversity Framework to Automatically Evaluate Multi-Agent Path Finding Algorithms in Diverse Maps`
- source: https://arxiv.org/abs/2409.06888
- version: `arXiv:2409.06888v5, last revised 2026-02-14`
- adopted: Use morphology descriptors or targeted generated maps only as coverage diagnostics.
- rejected: Do not switch the main round to building a QD/NCA map generator.

## Official Repository Heads

- `Guidance Graph Optimization`: `d8de695dbd95c912ee59e8e626d63e511da684a7` from https://github.com/lunjohnzhang/ggo_public
- `LaGAT`: `69e0611d10567daf76db37fe9ca6af92766df188` from https://github.com/proroklab/lagat

No action imitation, DAgger, priority-order policy, restart policy, deployed optimizer, runtime-varying theta policy, or codebook selector is adopted.

All Phase5.5, Phase6, runtime, learned-policy, and AAAI claims remain closed.
