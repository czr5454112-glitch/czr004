"""Project-level contract for goal-aware dual-channel LTM actors."""

from __future__ import annotations

from dataclasses import dataclass


FLOOR_BEGIN = "<!-- GOAL_AWARE_DUAL_CHANNEL_LTM_REPRESENTATION_FLOOR_BEGIN -->"
FLOOR_END = "<!-- GOAL_AWARE_DUAL_CHANNEL_LTM_REPRESENTATION_FLOOR_END -->"

MINIMUM_INPUTS = [
    "physical graph topology",
    "actual paired starts/goals",
    "paired OD tokens",
    "directed C0 congestion prior",
    "directed F0 goal-progress prior",
    "solver budget",
    "LTM iteration budget",
]

FORBIDDEN_REGRESSIONS = [
    "agent action imitation",
    "DAgger or learner-state expert action aggregation",
    "learned priority ordering",
    "learned restart selection",
    "runtime-varying theta",
    "candidate-ID retrieval or codebook selection as the production method",
    "scalar-only primary actor",
]

REQUIRED_EVIDENCE = [
    "actual node tensor count and dimensions",
    "actual directed edge tensor count and dimensions",
    "actual paired OD token count",
    "actual C0 tensor nonzero rate",
    "actual F0 tensor nonzero rate",
    "forward-hook evidence for graph, OD, C, F, scalar, fusion, and theta heads",
    "nonzero graph, OD, C stream, F stream, fusion, and theta-head gradients",
    "batch-composition, node-order, and agent-order invariance",
    "paired-goal shuffle, C0, F0, topology, and scalar-shortcut interventions",
]


@dataclass(frozen=True)
class LiteratureSource:
    key: str
    title: str
    url: str
    version: str
    inspected_source: str
    adopted_lesson: str
    rejected_direction: str


LITERATURE_SOURCES = [
    LiteratureSource(
        key="aaai2024_tfo_lmapf",
        title="Traffic Flow Optimisation for Lifelong Multi-Agent Path Finding",
        url="https://arxiv.org/abs/2308.11234",
        version="arXiv:2308.11234v5, last revised 2024-01-31",
        inspected_source="arXiv abstract/version page",
        adopted_lesson="Keep C0 congestion and F0 goal-progress separate; represent vertex/wait pressure and edge contraflow explicitly.",
        rejected_direction="Do not replace the run-static theta actor with a different MAPF action policy.",
    ),
    LiteratureSource(
        key="ijcai2024_ggo",
        title="Guidance Graph Optimization for Lifelong Multi-Agent Path Finding",
        url="https://arxiv.org/abs/2402.01446",
        version="arXiv:2402.01446v2, last revised 2024-05-09",
        inspected_source="arXiv abstract/version page plus official repository",
        adopted_lesson="Use exact solver replay as final truth; use bounded black-box teacher/control diagnostics only as training data sources.",
        rejected_direction="Do not deploy CMA-ES/CEM or stored guidance graph optimization at runtime.",
    ),
    LiteratureSource(
        key="icra2023_graph_transformer_mapf",
        title="Accelerating Multi-Agent Planning Using Graph Transformers with Bounded Suboptimality",
        url="https://arxiv.org/abs/2301.08451",
        version="arXiv:2301.08451v1, submitted 2023-01-20",
        inspected_source="arXiv abstract/version page",
        adopted_lesson="Graph attention can guide classical MAPF while preserving solver semantics; test size and density generalization.",
        rejected_direction="Do not change LaCAM*/PIBT feasibility semantics.",
    ),
    LiteratureSource(
        key="aaai2026_lagat",
        title="Graph Attention-Guided Search for Dense Multi-Agent Pathfinding",
        url="https://arxiv.org/abs/2510.17382",
        version="arXiv:2510.17382v1, submitted 2025-10-20",
        inspected_source="arXiv abstract/version page plus official repository",
        adopted_lesson="Use pretraining before real-label fine-tuning and an explicit safeguard/trust head for imperfect learned guidance.",
        rejected_direction="Do not copy the action-policy target.",
    ),
    LiteratureSource(
        key="qd_mapper",
        title="QD-MAPPER: A Quality Diversity Framework to Automatically Evaluate Multi-Agent Path Finding Algorithms in Diverse Maps",
        url="https://arxiv.org/abs/2409.06888",
        version="arXiv:2409.06888v5, last revised 2026-02-14",
        inspected_source="arXiv abstract/version page",
        adopted_lesson="Use morphology descriptors or targeted generated maps only as coverage diagnostics.",
        rejected_direction="Do not switch the main round to building a QD/NCA map generator.",
    ),
]


OFFICIAL_REPOS = [
    {
        "project": "Guidance Graph Optimization",
        "repo_url": "https://github.com/lunjohnzhang/ggo_public",
        "head_commit": "d8de695dbd95c912ee59e8e626d63e511da684a7",
        "source": "git ls-remote HEAD on 2026-06-20",
    },
    {
        "project": "LaGAT",
        "repo_url": "https://github.com/proroklab/lagat",
        "head_commit": "69e0611d10567daf76db37fe9ca6af92766df188",
        "source": "git ls-remote HEAD on 2026-06-20",
    },
]


def representation_floor_block() -> str:
    inputs = "\n".join(f"- {item}" for item in MINIMUM_INPUTS)
    forbidden = "\n".join(f"- {item}" for item in FORBIDDEN_REGRESSIONS)
    evidence = "\n".join(f"- {item}" for item in REQUIRED_EVIDENCE)
    return f"""{FLOOR_BEGIN}
## Goal-aware dual-channel LTM representation floor

This block is a project-level research contract. It is a minimum information
floor for any primary production actor in the goal-aware dual-channel LTM line,
not an architecture ceiling.

The primary production actor must consume, in its actual forward pass:

{inputs}

The primary output remains one continuous bounded solver-facing UpdateParams
theta per MAPF instance. That theta is fixed for the complete solver run while
the ordinary trace-driven C/F traffic maps continue to update online.

G5.62 is explicitly not DAgger. The project must not learn agent actions,
query an expert for learner-visited action labels, aggregate state-action
trajectories, learn priority ordering, learn restart selection, switch theta
during a run, or deploy a stored candidate/codebook selector.

Forbidden regressions:

{forbidden}

Allowed extensions include richer local/global graph attention, OD-to-graph or
OD-to-edge cross-attention, separate C and F streams, hierarchical graph/raster
fusion, field-group theta heads, safe residual subspaces, uncertainty/trust
heads, and self-supervised pretraining. Scalar features are supplemental
controls or auxiliary inputs only; a scalar-only model is never the primary
goal-aware dual-channel actor.

Every future round claiming a goal-aware graph actor must record:

{evidence}
{FLOOR_END}
"""


def contract_markers_present(text: str) -> bool:
    return FLOOR_BEGIN in text and FLOOR_END in text and text.index(FLOOR_BEGIN) < text.index(FLOOR_END)
