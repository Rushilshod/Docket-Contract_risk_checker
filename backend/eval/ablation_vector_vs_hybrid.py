"""
Ablation test (Section 6): vector-only retrieval vs. hybrid GraphRAG
retrieval on the same held-out test set, to justify (or not) the added
complexity of the knowledge-graph layer.
"""
from app.retrieval.hybrid_retriever import retrieve_grounding, retrieve_vector_only


def run_ablation(test_set: list[dict]) -> dict:
    """
    TODO(engineer): for each test contract's clauses, run both
    retrieve_vector_only and retrieve_grounding, score each against the
    ground-truth "correct statute section" label, and report the two
    accuracy/precision numbers side by side. Report this in the writeup
    (Section 7) as evidence for or against keeping the graph layer.
    """
    raise NotImplementedError


if __name__ == "__main__":
    raise NotImplementedError
