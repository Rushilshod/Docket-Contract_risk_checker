"""
Hybrid GraphRAG retrieval (Section 3/5): combine FAISS vector search with
knowledge-graph traversal so every risk explanation is grounded in real
statute text, not just similarity.
"""
import networkx as nx

from app.retrieval import faiss_index


def retrieve_grounding(
    graph: nx.MultiDiGraph, jurisdiction: str, clause_text: str, clause_type_id: str, top_k: int = 3
) -> list[dict]:
    """
    Walk direct graph links for a clause type, then fall back to vector similarity
    within the same jurisdiction. Graph hits are ranked above vector-only hits,
    and everything returned is already scoped to the requested jurisdiction.
    """
    if graph is None:
        return []

    graph_hits: list[dict] = []
    seen_graph_targets: set[str] = set()

    for _, target_id, data in graph.out_edges(clause_type_id, data=True):
        edge_type = data.get("type")
        if edge_type not in {"REQUIRES", "INVOKES"}:
            continue

        target_node = graph.nodes.get(target_id)
        if target_node is None:
            continue

        target_jurisdiction = target_node.get("jurisdiction") or jurisdiction
        if target_jurisdiction != jurisdiction:
            continue

        if target_id in seen_graph_targets:
            continue
        seen_graph_targets.add(target_id)

        target_attrs = target_node.get("attrs", {}) or {}
        graph_hits.append(
            {
                "node_id": target_id,
                "section_id": target_node.get("section_id") or target_id,
                "title": target_node.get("title") or target_attrs.get("title"),
                "text": target_attrs.get("text")
                or target_node.get("text")
                or target_attrs.get("title"),
                "jurisdiction": target_jurisdiction,
                "score": 1.0,
                "source": "graph",
                "edge_type": edge_type,
            }
        )

    vector_hits: list[dict] = []
    try:
        vector_hits = faiss_index.search(jurisdiction, clause_text, top_k=top_k)
    except (NotImplementedError, AttributeError):
        vector_hits = []
    except Exception:
        vector_hits = []

    normalized_vector_hits: list[dict] = []
    for hit in vector_hits:
        item = dict(hit)
        if "node_id" not in item and "section_id" in item:
            item["node_id"] = item["section_id"]
        item.setdefault("jurisdiction", jurisdiction)
        item.setdefault("source", "vector")
        item.setdefault("score", 0.0)
        normalized_vector_hits.append(item)

    combined: dict[str, dict] = {}
    for hit in graph_hits + normalized_vector_hits:
        key = hit.get("node_id") or hit.get("section_id") or hit.get("id")
        if not key:
            continue
        existing = combined.get(key)
        if existing is None:
            combined[key] = hit
            continue
        if hit.get("source") == "graph" and existing.get("source") != "graph":
            combined[key] = hit
        elif hit.get("source") == "graph" and existing.get("source") == "graph":
            combined[key] = hit if float(hit.get("score", 0.0)) > float(existing.get("score", 0.0)) else existing

    ranked = sorted(
        combined.values(),
        key=lambda item: (
            0 if item.get("source") == "graph" else 1,
            -float(item.get("score") or 0.0),
        ),
    )

    return ranked[:top_k]


def retrieve_vector_only(jurisdiction: str, clause_text: str, top_k: int = 3) -> list[dict]:
    """Vector-only baseline, used by the ablation test (Section 6)."""
    return faiss_index.search(jurisdiction, clause_text, top_k=top_k)
