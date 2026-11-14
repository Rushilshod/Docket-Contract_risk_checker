"""
Tests for the jurisdiction-isolation guard (Section 4/9). This is the
automated half of the manual check in Section 7, item 4 — it should catch
regressions in CI, but does not replace the manual spot-check with a real
contract that Section 7 asks you to do by hand.
"""
import networkx as nx
import pytest

from app.graph.schema import GraphEdge
from app.graph.validation import JurisdictionIsolationError, validate_edge_jurisdiction


def test_rejects_cross_jurisdiction_invokes_edge():
    graph = nx.MultiDiGraph()
    bad_edge = GraphEdge(
        source_id="clause:1",
        target_id="statute:uk_crs_2015_sch2",
        type="INVOKES",
        jurisdiction="uk",
    )
    with pytest.raises(JurisdictionIsolationError):
        validate_edge_jurisdiction(graph, bad_edge, expected_jurisdiction="india")


def test_accepts_matching_jurisdiction_edge():
    graph = nx.MultiDiGraph()
    good_edge = GraphEdge(
        source_id="clause:1",
        target_id="statute:india_ica_1872_s74",
        type="INVOKES",
        jurisdiction="india",
    )
    # Should not raise.
    validate_edge_jurisdiction(graph, good_edge, expected_jurisdiction="india")


def test_edge_construction_requires_jurisdiction_on_sensitive_types():
    with pytest.raises(ValueError):
        GraphEdge(source_id="a", target_id="b", type="REQUIRES", jurisdiction=None)


def test_propose_requires_edges_returns_jurisdictional_candidate_edges():
    from app.graph.build_static_graph import propose_requires_edges

    sections = [
        {
            "node_id": "india:ICA:27",
            "title": "Agreement in restraint of trade",
            "text": "An agreement by which a person restrains exercise of a lawful profession is void.",
            "jurisdiction": "india",
        },
        {
            "node_id": "india:DPDP:5",
            "title": "Processing of personal data",
            "text": "A data fiduciary shall process personal data only for a lawful purpose.",
            "jurisdiction": "india",
        },
    ]

    edges = propose_requires_edges("india", sections)

    assert edges
    assert all(edge.type == "REQUIRES" for edge in edges)
    assert all(edge.jurisdiction == "india" for edge in edges)
    assert any(edge.target_id == "india:ICA:27" for edge in edges)
    assert any(edge.target_id == "india:DPDP:5" for edge in edges)


# TODO(human): add an end-to-end version of this test using a real sample
# contract per Section 7, item 4 — feed an Indian contract through the
# full pipeline and assert zero UK/US statute citations appear anywhere
# in the output, including low-confidence flags. That test needs the real
# pipeline wired up (app.pipeline.run_pipeline), so it belongs here once
# that stops raising NotImplementedError.
