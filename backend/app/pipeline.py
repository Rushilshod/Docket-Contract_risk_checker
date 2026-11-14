"""
Pipeline orchestration (Section 3): the exact same Stage 2-5 sequence is
used for both Check and Draft, so it lives in one place and both API
routes call it.
"""
from dataclasses import dataclass

from app.classification.clause_classifier import ClauseClassifier
from app.classification.lifecycle_tagger import tag_lifecycle_stage
from app.config import canonical_domain, canonical_jurisdiction, is_supported
from app.graph.build_dynamic_graph import (
    commit_edges, extract_dynamic_edges, load_static_subgraph, merge_contract_clauses,
)
from app.ingestion.segmenter import segment_into_clauses
from app.retrieval.hybrid_retriever import retrieve_grounding
from app.scoring.missing_clause_checker import find_missing_clauses
from app.scoring.risk_scorer import generate_plain_english_explanation, score_clause_risk


@dataclass
class PipelineResult:
    jurisdiction: str
    domain: str
    flags: list
    missing_clauses: list[str]


_classifier = ClauseClassifier()


def run_pipeline(contract_text: str, jurisdiction: str, domain: str) -> PipelineResult:
    """Run the minimal contract pipeline with rule-based fallbacks for unimplemented ML stubs."""
    jurisdiction = canonical_jurisdiction(jurisdiction)
    domain = canonical_domain(domain)

    if not is_supported(jurisdiction, domain):
        raise ValueError(f"Unsupported jurisdiction/domain combination: {jurisdiction}/{domain}")

    clauses = segment_into_clauses(contract_text)
    if not clauses:
        clauses = [type("C", (), {"index": 0, "heading": None, "text": contract_text, "start_char": 0, "end_char": len(contract_text)})()]

    classified = _classifier.classify(clauses)
    present_types = {entry.clause_type for entry in classified}

    graph = load_static_subgraph(jurisdiction)
    graph = merge_contract_clauses(graph, classified)

    dynamic_edges = extract_dynamic_edges(contract_text, jurisdiction)
    if dynamic_edges:
        graph = commit_edges(graph, dynamic_edges, expected_jurisdiction=jurisdiction)

    missing_clauses = find_missing_clauses(jurisdiction, domain, present_types)

    flags = []
    for clause in classified:
        clause_type_id = clause.clause_type
        stage = tag_lifecycle_stage(clause.clause_type, clause.text)
        grounding = retrieve_grounding(graph, jurisdiction, clause.text, clause_type_id, top_k=3)
        risk_flag = score_clause_risk(clause.text, clause.clause_type, grounding)
        explanation = generate_plain_english_explanation(risk_flag, grounding)
        flags.append(
            {
                "clause_index": risk_flag.clause_index,
                "severity": risk_flag.severity,
                "title": risk_flag.title,
                "body": risk_flag.body,
                "confidence": risk_flag.confidence,
                "risk_allocation_standard": risk_flag.risk_allocation_standard,
                "disadvantaged_party": risk_flag.disadvantaged_party,
                "citation": risk_flag.citation,
                "lifecycle_stage": stage,
                "explanation": explanation,
                "recommendation": explanation,
            }
        )

    return PipelineResult(
        jurisdiction=jurisdiction,
        domain=domain,
        flags=flags,
        missing_clauses=missing_clauses,
    )
