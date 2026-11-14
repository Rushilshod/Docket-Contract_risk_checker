"""
Missing-clause detection (Section 3/4): compare classified clauses against
a jurisdiction x domain checklist.
"""
import json

from app.config import CHECKLISTS_DIR, canonical_domain, canonical_jurisdiction


def load_checklist(jurisdiction: str, domain: str) -> list[str]:
    """
    Checklists live at data/checklists/<jurisdiction>__<domain>.json as a
    flat list of required clause types.

    TODO(human): these checklists need the same legal review as the graph
    edges (Section 7, item 1) before they're trustworthy — a starter/
    placeholder checklist ships in data/checklists/, but treat it as a
    draft, not a source of truth.
    """
    normalized_jurisdiction = canonical_jurisdiction(jurisdiction)
    normalized_domain = canonical_domain(domain)
    path = CHECKLISTS_DIR / f"{normalized_jurisdiction}__{normalized_domain}.json"
    with open(path) as f:
        return json.load(f)["required_clause_types"]


def find_missing_clauses(jurisdiction: str, domain: str, present_clause_types: set[str]) -> list[str]:
    required = load_checklist(jurisdiction, domain)
    return [c for c in required if c not in present_clause_types]
