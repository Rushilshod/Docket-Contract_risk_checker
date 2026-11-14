"""
Phase A — static subgraph construction (Section 4). Built once per
jurisdiction, offline. This is curation work, not an ML pipeline step.

*** DO NOT wire this into the live API. It's a one-time (or occasionally
re-run) offline script, invoked deliberately via scripts/build_static_graphs.py. ***
"""
import pickle
from pathlib import Path

import networkx as nx
from app.config import GRAPHS_DIR, STATUTES_DIR
from app.graph.schema import GraphEdge, GraphNode


def load_statute_text(jurisdiction: str) -> list[dict]:
    """
    Load cleaned statute entries for one jurisdiction from
    data/statutes/<jurisdiction>/*.json (produced by
    scripts/extract_statute_sections.py from the source PDFs).

    Entry kinds: "section", "schedule", "schedule_article". Every entry has a
    globally unique "node_id" (section numbers repeat across Acts, so NEVER key
    on section_id alone).

    Deliberately NOT loaded:
      - model_not_in_force/ (Model Tenancy Act, draft state-rules template): the
        glob below is non-recursive on purpose, so a template can never be
        mistaken for law in force.
      - entries flagged "oversized" (raw Schedule blobs that need Article-level
        splitting, e.g. the central Stamp Act Schedule I with every state's
        amendments).
    The "domain" field is None here on purpose: which sections apply to
    NDA/Service vs Rental/Tenancy is a legal judgement, made in the
    human-reviewed mapping step (Section 7, item 1), not by a loader.

    Still TODO(engineer): US (US Code / eCFR). India and UK statute text is now
    present under data/statutes/india/ and data/statutes/uk/ respectively -- see
    their READMEs for what's covered and known limitations.
    """
    import json

    jurisdiction_dir = STATUTES_DIR / jurisdiction
    sections: list[dict] = []
    seen: set[str] = set()
    for path in sorted(jurisdiction_dir.glob("*.json")):
        with open(path, encoding="utf-8") as f:
            for entry in json.load(f):
                if entry.get("jurisdiction") != jurisdiction:
                    raise ValueError(
                        f"{path.name} contains an entry tagged "
                        f"'{entry.get('jurisdiction')}' inside the "
                        f"'{jurisdiction}' folder \u2014 refusing to load "
                        "(jurisdiction isolation, Section 4)."
                    )
                if entry.get("oversized") or entry.get("status", "in_force") != "in_force":
                    continue
                if entry["node_id"] in seen:
                    raise ValueError(f"duplicate node_id {entry['node_id']} in {path.name}")
                seen.add(entry["node_id"])
                sections.append(entry)
    if not sections:
        raise FileNotFoundError(f"No statute JSON found in {jurisdiction_dir}")
    return sections


def propose_requires_edges(jurisdiction: str, statute_sections: list[dict]) -> list[GraphEdge]:
    """
    Draft a small, human-reviewable set of candidate REQUIRES edges linking
    DealType/ClauseType nodes to StatuteSection nodes.

    This is intentionally conservative: the project expects a lawyer to later
    confirm each candidate. The function therefore only emits edges for terms
    that are clearly relevant to the jurisdiction's supported contract types and
    for which the statute text itself contains a strong lexical signal.
    """
    if not statute_sections:
        return []

    source_rules: list[tuple[str, str, list[str]]] = [
        (
            "deal_type:nda_service",
            "DealType",
            [
                "confidential",
                "non-disclosure",
                "non disclosure",
                "trade secret",
                "restraint of trade",
                "indemnity",
                "liability",
                "personal data",
                "data protection",
                "arbitration",
                "jurisdiction",
                "dispute resolution",
            ],
        ),
        (
            "deal_type:rental_tenancy",
            "DealType",
            [
                "rent",
                "tenant",
                "landlord",
                "lease",
                "tenancy",
                "eviction",
                "repair",
                "maintenance",
                "security deposit",
                "notice period",
            ],
        ),
        (
            "clause_type:confidentiality",
            "ClauseType",
            [
                "confidential",
                "trade secret",
                "proprietary information",
                "non-disclosure",
                "non disclosure",
            ],
        ),
        (
            "clause_type:governing_law",
            "ClauseType",
            [
                "governing law",
                "choice of law",
                "jurisdiction",
                "court having jurisdiction",
                "arbitration",
            ],
        ),
        (
            "clause_type:data_protection",
            "ClauseType",
            [
                "personal data",
                "data protection",
                "processing of personal data",
                "data fiduciary",
                "data principal",
            ],
        ),
    ]

    edges: list[GraphEdge] = []
    seen: set[tuple[str, str]] = set()

    for section in statute_sections:
        text_blob = " ".join(
            [
                str(section.get("title", "")),
                str(section.get("text", "")),
                str(section.get("text_clean", "")),
            ]
        ).lower()
        if not text_blob:
            continue

        for source_id, source_type, keywords in source_rules:
            if any(keyword in text_blob for keyword in keywords):
                key = (source_id, section["node_id"])
                if key in seen:
                    continue
                seen.add(key)
                edges.append(
                    GraphEdge(
                        source_id=source_id,
                        target_id=section["node_id"],
                        type="REQUIRES",
                        jurisdiction=jurisdiction,
                        attrs={
                            "source_type": source_type,
                            "match_keywords": [kw for kw in keywords if kw in text_blob],
                            "reason": f"Candidate {source_type.lower()} linkage from statute text for {section.get('title', 'untitled section')}",
                        },
                    )
                )

    return edges


def build_static_subgraph(
    jurisdiction: str, approved_edges: list[GraphEdge] | None = None
) -> nx.MultiDiGraph:
    """
    Assemble the human-approved nodes/edges for one jurisdiction into a graph.

    If `approved_edges` is not supplied, this builds the candidate set from the
    jurisdiction's statute corpus exactly as the offline static graph pipeline
    expects. The result is a minimal, jurisdiction-isolated graph we can use for
    graph retrieval and explanation.
    """
    sections = load_statute_text(jurisdiction)
    if approved_edges is None:
        approved_edges = propose_requires_edges(jurisdiction, sections)

    graph = nx.MultiDiGraph()

    # Add the statute section nodes first so every REQUIRES edge is grounded in a
    # real, jurisdiction-specific document section.
    for section in sections:
        node = GraphNode(
            id=section["node_id"],
            type="StatuteSection",
            jurisdiction=section.get("jurisdiction"),
            attrs={
                "title": section.get("title"),
                "act": section.get("act"),
                "act_short": section.get("act_short"),
                "kind": section.get("kind"),
                "section_id": section.get("section_id"),
                "source_file": section.get("source_file"),
                "status": section.get("status"),
            },
        )
        graph.add_node(node.id, **node.__dict__)

    # Add the source nodes that the approved edges point to.
    source_nodes: dict[str, GraphNode] = {}
    for edge in approved_edges:
        if edge.source_id not in source_nodes:
            source_type = "DealType" if edge.source_id.startswith("deal_type:") else "ClauseType"
            source_nodes[edge.source_id] = GraphNode(
                id=edge.source_id,
                type=source_type,
                jurisdiction=jurisdiction,
                attrs={"approved": True},
            )
        graph.add_node(source_nodes[edge.source_id].id, **source_nodes[edge.source_id].__dict__)

    # Add the approved edges to the graph.
    for edge in approved_edges:
        existing_edges = graph.number_of_edges(edge.source_id, edge.target_id)
        graph.add_edge(
            edge.source_id,
            edge.target_id,
            key=f"{edge.type}:{edge.source_id}:{edge.target_id}:{existing_edges}",
            type=edge.type,
            jurisdiction=edge.jurisdiction,
            **edge.attrs,
        )

    return graph


def save_jurisdiction_graph(jurisdiction: str, graph: nx.MultiDiGraph) -> Path:
    """
    Never merge jurisdictions into one graph file (Section 4) — this is
    part of the isolation-by-construction design, not just tidiness.
    """
    GRAPHS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = GRAPHS_DIR / f"{jurisdiction}.gpickle"
    with open(out_path, "wb") as f:
        pickle.dump(graph, f)
    return out_path
