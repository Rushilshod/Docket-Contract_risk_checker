"""
Drafting flow (Section 3): fixed-form guided interview per domain ->
assemble from a hand-vetted clause bank -> run through the identical
Stage 2-5 check pipeline used for Check.
"""
import json

from app.config import CLAUSE_BANK_DIR, canonical_domain, canonical_jurisdiction

# Interview field schema per domain. Keep this in sync with
# frontend/src/data/mockData.js:INTERVIEW_FIELDS — the frontend currently
# hardcodes its own copy for the demo; a real build should serve this from
# one place (e.g. a GET /api/interview-schema/<domain> endpoint) so the
# two never drift apart.
INTERVIEW_SCHEMA = {
    "nda_service": ["party_a", "party_b", "term_months", "auto_renew", "scope"],
    "rental_tenancy": ["landlord", "tenant", "term_months", "deposit_amount", "renewal_notice_days"],
}


def load_clause_bank(jurisdiction: str, domain: str) -> dict:
    """
    Clause bank lives at data/clause_bank/<jurisdiction>__<domain>.json.

    TODO(human): every clause in the bank needs the same legal review as
    the graph edges (Section 7, item 1) — this is text that gets handed
    directly to a real person to sign, which is a higher real-world stake
    than a review flag (Section 7, item 6).
    """
    normalized_jurisdiction = canonical_jurisdiction(jurisdiction)
    normalized_domain = canonical_domain(domain)
    path = CLAUSE_BANK_DIR / f"{normalized_jurisdiction}__{normalized_domain}.json"
    with open(path) as f:
        return json.load(f)


def assemble_draft(jurisdiction: str, domain: str, answers: dict) -> str:
    """Build a simple deterministic draft from the interview answers when no clause bank file is available."""
    normalized_domain = canonical_domain(domain)
    if normalized_domain == "nda_service":
        clauses = [
            "CONFIDENTIALITY. The receiving party shall keep confidential information strictly confidential.",
            f"TERM. This agreement shall commence on the date of signing and continue for {answers.get('term_months', answers.get('term', '12'))} months.",
            f"GOVERNING LAW. This agreement shall be governed by the laws of {jurisdiction.title()}.",
            f"AUTO-RENEWAL. Auto-renewal is {answers.get('auto_renew', 'No')}.",
            f"SCOPE. The services relate to {answers.get('scope', 'the engagement described in the statement of work')}.",
        ]
    else:
        clauses = [
            "TENANCY. The landlord grants the tenant possession of the premises for the agreed term.",
            f"DEPOSIT. Security deposit is {answers.get('deposit_amount', answers.get('deposit', '0'))}.",
            f"RENEWAL NOTICE. Renewal notice shall be given {answers.get('renewal_notice_days', '30')} days in advance.",
            f"GOVERNING LAW. This agreement shall be governed by the laws of {jurisdiction.title()}.",
        ]
    return "\n\n".join(clauses)
