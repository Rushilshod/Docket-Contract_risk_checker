"""
Jurisdiction-isolation validation (Section 4). This is the single most
important safety mechanism in the whole graph layer: it's what makes the
acceptance criterion "zero cross-jurisdiction citations" (Section 9)
actually enforceable in code rather than hoped for.

Do not weaken, bypass, or "temporarily disable" this check, even during
debugging — a silently-disabled guard here is exactly how a wrong-country
statute ends up cited to a real user.
"""
import networkx as nx

from app.graph.schema import GraphEdge, JURISDICTION_SENSITIVE_EDGES


class JurisdictionIsolationError(ValueError):
    pass


def validate_edge_jurisdiction(
    graph: nx.MultiDiGraph, edge: GraphEdge, expected_jurisdiction: str
) -> None:
    if edge.type not in JURISDICTION_SENSITIVE_EDGES:
        return

    if edge.jurisdiction != expected_jurisdiction:
        raise JurisdictionIsolationError(
            f"Rejected {edge.type} edge: edge jurisdiction "
            f"'{edge.jurisdiction}' does not match contract jurisdiction "
            f"'{expected_jurisdiction}'."
        )

    # TODO(engineer): also confirm the target StatuteSection node's own
    # jurisdiction attribute matches — the edge's declared jurisdiction
    # and the node's actual jurisdiction should never disagree, and if
    # they do, that's a bug in graph construction, not just a bad edge.


def audit_graph_for_leaks(graph: nx.MultiDiGraph, expected_jurisdiction: str) -> list[str]:
    """
    TODO(engineer): full-graph sweep used by the manual test in Section 7,
    item 4 — feed a contract from one jurisdiction and confirm zero
    citations from the other two appear anywhere in the output, including
    low-confidence flags. Return a list of human-readable problems found
    (empty list = clean). Run this as an explicit step before showing any
    real contract's results to a real person.
    """
    raise NotImplementedError
