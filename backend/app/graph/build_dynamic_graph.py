"""
Phase B — dynamic per-contract graph, built at runtime (Section 4).
"""
import pickle

import networkx as nx

from app.config import GRAPHS_DIR
from app.graph.schema import GraphEdge
from app.graph.validation import validate_edge_jurisdiction


def load_static_subgraph(jurisdiction: str) -> nx.MultiDiGraph:
    path = GRAPHS_DIR / f"{jurisdiction}.gpickle"
    if not path.exists():
        raise FileNotFoundError(
            f"No static graph for jurisdiction={jurisdiction}. "
            "Run scripts/build_static_graphs.py first (and complete the "
            "human review step in build_static_graph.py before that)."
        )
    with open(path, "rb") as f:
        return pickle.load(f)


def merge_contract_clauses(graph: nx.MultiDiGraph, classified_clauses: list) -> nx.MultiDiGraph:
    """Add one Clause node per classified clause and link it to its ClauseType node."""
    for clause in classified_clauses:
        clause_id = f"clause:{clause.index}"
        clause_type_id = f"clause_type:{clause.clause_type.lower().replace(' ', '_')}"
        graph.add_node(
            clause_id,
            id=clause_id,
            type="Clause",
            jurisdiction="",
            attrs={"text": clause.text, "clause_type": clause.clause_type},
        )
        graph.add_node(
            clause_type_id,
            id=clause_type_id,
            type="ClauseType",
            jurisdiction="",
            attrs={"title": clause.clause_type},
        )
        graph.add_edge(clause_id, clause_type_id, type="HAS_STAGE", jurisdiction="", clause_type=clause.clause_type)
    return graph


def extract_dynamic_edges(contract_text: str, jurisdiction: str) -> list[GraphEdge]:
    """Default to no dynamic contract edges unless a future model extracts them."""
    return []


def commit_edges(graph: nx.MultiDiGraph, edges: list[GraphEdge], expected_jurisdiction: str | None = None) -> nx.MultiDiGraph:
    """Validate jurisdiction-sensitive edges before adding them to the runtime graph."""
    for edge in edges:
        expected = expected_jurisdiction or edge.jurisdiction
        if expected is not None:
            validate_edge_jurisdiction(graph, edge, expected_jurisdiction=expected)
        graph.add_edge(edge.source_id, edge.target_id, type=edge.type, jurisdiction=edge.jurisdiction, **edge.attrs)
    return graph
