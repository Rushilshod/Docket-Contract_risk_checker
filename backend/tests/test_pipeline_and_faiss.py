from app.pipeline import run_pipeline
from app.retrieval import faiss_index


def test_faiss_search_returns_only_requested_jurisdiction_results():
    sections = [
        {
            "node_id": "india:ICA:27",
            "section_id": "27",
            "title": "Confidentiality obligations",
            "text": "confidential information must not be disclosed to third parties",
            "jurisdiction": "india",
        },
        {
            "node_id": "uk:CA:2",
            "section_id": "2",
            "title": "Unrelated section",
            "text": "this section is not about confidentiality",
            "jurisdiction": "uk",
        },
    ]

    faiss_index.build_index_for_jurisdiction("india", sections)
    results = faiss_index.search("india", "confidentiality obligations and non disclosure", top_k=3)

    assert results
    assert all(hit["jurisdiction"] == "india" for hit in results)
    assert any(hit["section_id"] == "27" for hit in results)


def test_run_pipeline_returns_result_for_supported_contract():
    result = run_pipeline(
        "The parties shall keep all confidential information secret. The governing law is India.",
        "india",
        "nda_service",
    )

    assert result.jurisdiction == "india"
    assert result.domain == "nda_service"
    assert isinstance(result.flags, list)
    assert isinstance(result.missing_clauses, list)
