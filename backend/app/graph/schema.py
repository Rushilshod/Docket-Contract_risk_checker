"""
Knowledge graph schema (Section 4). Shared across all jurisdictions, but
graphs themselves are never merged across jurisdictions — see
build_static_graph.py and validation.py for why.
"""
from dataclasses import dataclass, field
from typing import Literal

NodeType = Literal[
    "Clause", "ClauseType", "StatuteSection", "DealType",
    "Party", "RiskAllocationStandard", "LifecycleStage",
]

EdgeType = Literal[
    "INVOKES", "AMENDED_BY", "REQUIRES", "CONFLICTS_WITH",
    "DISADVANTAGES", "HAS_STAGE",
]

JURISDICTION_SENSITIVE_EDGES = {"REQUIRES", "INVOKES", "AMENDED_BY"}


@dataclass
class GraphNode:
    id: str
    type: NodeType
    jurisdiction: str | None = None  # required for StatuteSection nodes
    attrs: dict = field(default_factory=dict)


@dataclass
class GraphEdge:
    source_id: str
    target_id: str
    type: EdgeType
    jurisdiction: str | None = None  # REQUIRED if type in JURISDICTION_SENSITIVE_EDGES
    attrs: dict = field(default_factory=dict)

    def __post_init__(self):
        if self.type in JURISDICTION_SENSITIVE_EDGES and not self.jurisdiction:
            raise ValueError(
                f"{self.type} edges must carry a jurisdiction property (Section 4)"
            )
