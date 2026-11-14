"""
Stage 2c — Jurisdiction detection.

Section 3: detect from the governing-law clause; if absent, ask the user
directly rather than guessing. Guessing wrong here is dangerous — it's
exactly the failure mode the jurisdiction-isolation guard (Section 4,
Phase B) exists to prevent, so this function must be conservative about
returning None rather than a low-confidence guess.
"""
from typing import Optional

from app.config import JURISDICTIONS

GOVERNING_LAW_PATTERNS = {
    "india": ["laws of india", "india", "indian law"],
    "uk": ["laws of england and wales", "uk", "united kingdom", "england and wales"],
    "us": ["state of delaware", "laws of the state of", "us law", "united states"],
}


def detect_jurisdiction_from_text(full_contract_text: str) -> Optional[str]:
    """Return a jurisdiction when there is a strong lexical indicator; else None."""
    lowered = (full_contract_text or "").lower()
    for jurisdiction, patterns in GOVERNING_LAW_PATTERNS.items():
        if any(pattern in lowered for pattern in patterns):
            return jurisdiction
    return None


def validate_jurisdiction(value: str) -> str:
    if value not in JURISDICTIONS:
        raise ValueError(f"Unknown jurisdiction: {value}")
    return value
