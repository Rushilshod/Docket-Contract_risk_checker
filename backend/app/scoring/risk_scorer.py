"""
Risk scoring + explanation (Section 3). Two distinct LLM call sites with
different reasoning-mode settings — keep them separate functions so it's
never ambiguous which one a given call site is.
"""
from dataclasses import dataclass

from app.llm.gemini_client import generate_text


@dataclass
class RiskFlag:
    clause_index: int
    severity: str  # "high" | "medium" | "missing"
    title: str
    body: str
    confidence: float
    risk_allocation_standard: str | None  # control / foreseeability / reliance
    disadvantaged_party: str | None
    citation: dict | None  # {"section_id", "text", "jurisdiction"}


def score_clause_risk(clause_text: str, clause_type: str, grounding: list[dict]) -> RiskFlag:
    """Use conservative keyword triggers so the pipeline behaves deterministically without a model."""
    text = (clause_text or "").lower()
    if any(token in text for token in ["confidential", "non-disclosure", "trade secret", "secret"]):
        severity = "high"
        standard = "reliance"
        disadvantaged = "receiving party"
    elif any(token in text for token in ["indemn", "liability", "termination", "renew"]):
        severity = "medium"
        standard = "foreseeability"
        disadvantaged = "counterparty"
    else:
        severity = "missing"
        standard = "control"
        disadvantaged = "counterparty"

    citation = grounding[0] if grounding else None
    title = f"{clause_type} risk"
    body = f"The {clause_type.lower()} clause contains contract language that can materially affect legal risk for the counterparty."
    confidence = 0.72 if severity == "high" else 0.6 if severity == "medium" else 0.5
    return RiskFlag(
        clause_index=0,
        severity=severity,
        title=title,
        body=body,
        confidence=confidence,
        risk_allocation_standard=standard,
        disadvantaged_party=disadvantaged,
        citation=citation,
    )


def _grounding_context(grounding: list[dict] | None) -> str:
    if not grounding:
        return "No statute grounding was available for this clause."

    snippets: list[str] = []
    for item in grounding[:3]:
        title = item.get("title") or item.get("section_id") or "Relevant legal source"
        text = item.get("text") or ""
        snippet = (text[:280] + "...") if len(text) > 280 else text
        snippets.append(f"- {title}: {snippet}")
    return "\n".join(snippets)


def generate_plain_english_explanation(risk_flag: RiskFlag, grounding: list[dict] | None = None) -> str:
    """Explain the structured score in plain English in one paragraph, grounded in the legal snippets retrieved for the clause."""
    fallback = None
    if risk_flag.severity == "missing":
        fallback = "This clause does not currently trigger a clear legal risk signal from the available grounding, so it is treated as low concern for the moment."
    else:
        citation = ""
        if risk_flag.citation:
            citation = f" It cites {risk_flag.citation.get('title') or risk_flag.citation.get('node_id')}."
        fallback = (
            f"This {risk_flag.title.lower()} is flagged as {risk_flag.severity} risk. "
            f"The issue is most relevant to the {risk_flag.disadvantaged_party or 'counterparty'} under a "
            f"{risk_flag.risk_allocation_standard or 'balanced'} allocation standard.{citation}"
        )

    grounding_text = _grounding_context(grounding)
    model_text = generate_text(
        (
            "Explain this contract risk in one short paragraph for a business user. "
            f"Severity: {risk_flag.severity}. Title: {risk_flag.title}. "
            f"Disadvantaged party: {risk_flag.disadvantaged_party}. "
            f"Risk allocation standard: {risk_flag.risk_allocation_standard}. "
            f"Body: {risk_flag.body}.\n\nLegal grounding context:\n{grounding_text}"
        ),
        system_prompt=(
            "You are a legal-analysis assistant operating in a RAG workflow. Use the provided "
            "grounding snippets as the source of truth. Give a concise plain-English explanation, "
            "no markdown, no legal disclaimer, and no extra sections."
        ),
    )
    if model_text and model_text.strip():
        return model_text.strip()
    return fallback
