"""
Stage 2b — Deal-type classification (NDA/Service vs. Rental/Tenancy).

Section 3: "lightweight classifier or zero-shot prompt for deal type."
Given there are only 2 domains in scope, a zero-shot LLM prompt is
probably the pragmatic starting point; a scikit-learn baseline (Section 5)
is worth comparing against once you have a handful of labeled examples.
"""
import json
import re

from app.config import DOMAINS
from app.llm.gemini_client import generate_json


def _fallback_domain(full_contract_text: str) -> str:
    text = (full_contract_text or "").lower()
    if any(token in text for token in ["confidential", "non-disclosure", "nda", "trade secret", "service agreement", "services"]):
        return "nda_service"
    if any(token in text for token in ["lease", "rental", "tenancy", "landlord", "tenant", "rent"]):
        return "rental_tenancy"
    return "nda_service"


def classify_deal_type(full_contract_text: str) -> tuple[str, float]:
    """Classify the contract into one of the supported domains.

    The function prefers Gemini when a valid API key is configured, but falls back
    to a conservative keyword-based heuristic if the key is absent or the call fails.
    """
    prompt = (
        "Classify this contract as one of the following exact values only: "
        + ", ".join(DOMAINS)
        + ". Return valid JSON with fields: {'domain': '...', 'confidence': 0.0-1.0}.\n\n"
        + str(full_contract_text[:8000])
    )

    result = generate_json(
        prompt,
        system_prompt=(
            "You are a contract classification assistant. Only output strict JSON, no markdown, "
            "no commentary, and choose one of the allowed domains exactly."
        ),
    )
    if result:
        domain = str(result.get("domain", "")).strip().lower()
        if domain in DOMAINS:
            return domain, float(result.get("confidence", 0.8))

    fallback_domain = _fallback_domain(full_contract_text)
    fallback_confidence = 0.7
    return fallback_domain, fallback_confidence
