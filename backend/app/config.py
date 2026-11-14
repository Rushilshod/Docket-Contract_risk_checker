"""
Central configuration for the pipeline. Keeping this in one place makes the
"locked scope" in Section 2 of the brief enforceable in code, not just docs.
"""
import os
import re
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BACKEND_DIR / ".env", override=False)

# --- Locked scope (Section 2) -----------------------------------------
# Only jurisdictions with extracted statute data should be built here.
# The US corpus is intentionally absent for now; if a US statute set is added,
# it can be re-enabled in the same place.
JURISDICTIONS = ["india", "uk"]

DOMAINS = ["nda_service", "rental_tenancy"]

# Which domain is actually supported per jurisdiction. US has no Rental
# coverage because CUAD does not include residential leases (Section 2).
SUPPORTED_COMBOS = {
    "india": ["nda_service", "rental_tenancy"],
    "uk": ["nda_service", "rental_tenancy"],
    "us": ["nda_service"],
}


def _normalize_jurisdiction(value: str) -> str:
    normalized = (value or "").strip().lower().replace(" ", "_").replace("-", "_")
    aliases = {
        "india": "india",
        "uk": "uk",
        "united_kingdom": "uk",
        "united_states": "us",
        "us": "us",
    }
    return aliases.get(normalized, normalized)


def _normalize_domain(value: str) -> str:
    normalized = (value or "").strip().lower()
    normalized = normalized.replace("/", "_").replace("-", "_").replace(" ", "_")
    normalized = re.sub(r"_+", "_", normalized)

    aliases = {
        "nda_service_agreement": "nda_service",
        "nda_service": "nda_service",
        "rental_tenancy_agreement": "rental_tenancy",
        "rental_tenancy": "rental_tenancy",
    }
    return aliases.get(normalized, normalized)


def is_supported(jurisdiction: str, domain: str) -> bool:
    normalized_jurisdiction = _normalize_jurisdiction(jurisdiction)
    normalized_domain = _normalize_domain(domain)
    return normalized_domain in SUPPORTED_COMBOS.get(normalized_jurisdiction, [])


def canonical_jurisdiction(jurisdiction: str) -> str:
    return _normalize_jurisdiction(jurisdiction)


def canonical_domain(domain: str) -> str:
    return _normalize_domain(domain)


# --- Paths --------------------------------------------------------------
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
STATUTES_DIR = DATA_DIR / "statutes"
CHECKLISTS_DIR = DATA_DIR / "checklists"
CLAUSE_BANK_DIR = DATA_DIR / "clause_bank"
GRAPHS_DIR = DATA_DIR / "graphs"
FAISS_DIR = DATA_DIR / "faiss_indexes"

# --- Models (Section 5) --------------------------------------------------
CLAUSE_CLASSIFIER_BASE_MODEL = "nlpaueb/legal-bert-base-uncased"
SENTENCE_EMBEDDING_MODEL = "sentence-transformers/all-mpnet-base-v2"  # TODO(human): confirm this is
# the embedding model you actually want; the brief doesn't pin one down.

# Gemini configuration. The project remains deterministic by default; these
# values become active only when you explicitly wire a model-backed step.
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "REPLACE_ME")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", GEMINI_API_KEY)
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
GEMINI_BASE_URL = os.getenv("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com")

# Generic LLM config used by any future prompt-backed pipeline stage.
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini").lower()
LLM_MODEL = os.getenv("LLM_MODEL", GEMINI_MODEL if LLM_PROVIDER == "gemini" else "REPLACE_ME")
LLM_REASONING_ALLOWED_STEPS = {"explanation"}


def get_gemini_config() -> dict[str, str]:
    """Return the currently configured Gemini connection values."""
    return {
        "api_key": GEMINI_API_KEY,
        "model": GEMINI_MODEL,
        "base_url": GEMINI_BASE_URL,
    }
