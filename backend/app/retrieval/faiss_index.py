"""
Per-jurisdiction FAISS retrieval (Section 4/5). One index per jurisdiction,
never one merged index with metadata filtering — same isolation-by-
construction reasoning as the graph layer.
"""
import importlib
import json
import os
from pathlib import Path

try:
    import faiss  # type: ignore
except Exception:  # pragma: no cover - optional dependency in local fallback mode
    faiss = None

try:
    import numpy as np  # type: ignore
except Exception:  # pragma: no cover - fallback mode does not require it
    np = None

SentenceTransformer = None

from app.config import FAISS_DIR, JURISDICTIONS, SENTENCE_EMBEDDING_MODEL
from app.graph.build_static_graph import load_statute_text

_MODEL_CACHE: dict[str, SentenceTransformer] = {}


def _get_model():
    global SentenceTransformer
    if os.environ.get("Docket_ENABLE_EMBEDDINGS", "0").lower() not in {"1", "true", "yes", "on"}:
        return None

    if SentenceTransformer is None:
        try:
            module = importlib.import_module("sentence_transformers")
            SentenceTransformer = getattr(module, "SentenceTransformer", None)
        except Exception:
            SentenceTransformer = None
    if SentenceTransformer is None:
        return None
    try:
        model = _MODEL_CACHE.get(SENTENCE_EMBEDDING_MODEL)
        if model is None:
            model = SentenceTransformer(SENTENCE_EMBEDDING_MODEL)
            _MODEL_CACHE[SENTENCE_EMBEDDING_MODEL] = model
        return model
    except Exception:
        return None


def _lexical_similarity(query: str, text: str) -> float:
    q_terms = {t for t in query.lower().split() if len(t) > 2}
    if not q_terms:
        return 0.0
    t_terms = {t for t in text.lower().split() if len(t) > 2}
    if not t_terms:
        return 0.0
    overlap = len(q_terms & t_terms)
    return overlap / max(len(q_terms), 1)


def build_index_for_jurisdiction(jurisdiction: str, statute_sections: list[dict]) -> Path:
    """Build a per-jurisdiction FAISS index and a matching metadata sidecar."""
    FAISS_DIR.mkdir(parents=True, exist_ok=True)
    index_path = FAISS_DIR / f"{jurisdiction}.index"
    metadata_path = FAISS_DIR / f"{jurisdiction}.metadata.json"

    sections = [
        section for section in statute_sections if section.get("jurisdiction") == jurisdiction
    ]
    if not sections:
        return index_path

    metadata = []
    texts: list[str] = []
    for section in sections:
        text_blob = " ".join(
            [
                str(section.get("title", "")),
                str(section.get("text", "")),
                str(section.get("text_clean", "")),
            ]
        ).strip()
        if not text_blob:
            continue
        metadata.append(
            {
                "node_id": section.get("node_id") or section.get("section_id"),
                "section_id": section.get("section_id") or section.get("node_id"),
                "title": section.get("title"),
                "text": text_blob,
                "jurisdiction": jurisdiction,
            }
        )
        texts.append(text_blob)

    if not texts:
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump([], f)
        return index_path

    model = _get_model()
    if model is not None and faiss is not None and np is not None:
        embeddings = model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
        embeddings = np.asarray(embeddings, dtype="float32")
        index = faiss.IndexFlatIP(embeddings.shape[1])
        index.add(embeddings)
        faiss.write_index(index, str(index_path))
    else:
        # Keep the metadata sidecar even when the embedding model is unavailable;
        # the search function can still do a deterministic lexical fallback.
        index_path.touch(exist_ok=True)

    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f)

    return index_path


def load_index_for_jurisdiction(jurisdiction: str):
    """Load the index and metadata for one jurisdiction only."""
    if jurisdiction not in JURISDICTIONS:
        return None, []

    index_path = FAISS_DIR / f"{jurisdiction}.index"
    metadata_path = FAISS_DIR / f"{jurisdiction}.metadata.json"

    if metadata_path.exists():
        with open(metadata_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)
        if not index_path.exists():
            return None, metadata
    else:
        try:
            sections = load_statute_text(jurisdiction)
        except FileNotFoundError:
            return None, []
        build_index_for_jurisdiction(jurisdiction, sections)
        with open(metadata_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)

    if faiss is None:
        return None, metadata

    try:
        index = faiss.read_index(str(index_path))
    except Exception:
        index = None

    return index, metadata


def search(jurisdiction: str, query_text: str, top_k: int = 5) -> list[dict]:
    """Embed the query and return the top-k matches for this jurisdiction."""
    if not query_text or jurisdiction not in JURISDICTIONS:
        return []

    index, metadata = load_index_for_jurisdiction(jurisdiction)
    if not metadata:
        return []

    model = _get_model()
    if model is not None and index is not None and faiss is not None and np is not None:
        query_vector = model.encode([query_text], convert_to_numpy=True, normalize_embeddings=True)
        query_vector = np.asarray(query_vector, dtype="float32")
        k = min(top_k, len(metadata))
        scores, indices = index.search(query_vector, k)
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or idx >= len(metadata):
                continue
            item = dict(metadata[int(idx)])
            item["score"] = float(score)
            item.setdefault("jurisdiction", jurisdiction)
            results.append(item)
        return results

    ranked = []
    for item in metadata:
        score = _lexical_similarity(query_text, item.get("title", "") + " " + item.get("text", ""))
        if score <= 0:
            continue
        ranked.append({**item, "score": float(score), "jurisdiction": jurisdiction})
    ranked.sort(key=lambda hit: hit["score"], reverse=True)
    return ranked[:top_k]
