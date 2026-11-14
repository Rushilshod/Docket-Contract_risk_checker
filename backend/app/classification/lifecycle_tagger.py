"""
Stage 2d — Lifecycle-stage tagging (signing / performance / termination).

Section 3: "rule-based lookup plus LLM fallback."
"""
from typing import Literal

Stage = Literal["signing", "performance", "termination"]

RULE_BASED_STAGE_MAP: dict[str, Stage] = {
    "Signature Block": "signing",
    "Effective Date": "signing",
    "Termination": "termination",
    "Auto-Renewal": "termination",
    "Governing Law": "signing",
    "Confidentiality": "performance",
    "Indemnification": "performance",
    "Data Protection": "performance",
}


def tag_lifecycle_stage(clause_type: str, clause_text: str) -> Stage:
    """Use the rule-based classification first; fall back to a conservative default when unknown."""
    if clause_type in RULE_BASED_STAGE_MAP:
        return RULE_BASED_STAGE_MAP[clause_type]
    lowered = (clause_text or "").lower()
    if any(token in lowered for token in ["termination", "expire", "renew"]):
        return "termination"
    if any(token in lowered for token in ["effective date", "signature", "governing law"]):
        return "signing"
    return "performance"
