"""
POST /api/draft — guided-interview answers in, assembled draft + risk
report out. The report shape matches /api/check exactly, since it runs
through the identical pipeline (Section 3).
"""
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import canonical_domain, canonical_jurisdiction, is_supported
from app.drafting.clause_bank import assemble_draft
from app.pipeline import run_pipeline

router = APIRouter()


class DraftRequest(BaseModel):
    jurisdiction: str
    domain: str
    answers: dict


def _to_report_json(result, jurisdiction: str, domain: str) -> dict:
    stages = {"Signing": [], "Performance": [], "Termination": []}
    for flag in result.flags:
        stage_name = flag.get("lifecycle_stage", "performance")
        stage_label = {"signing": "Signing", "performance": "Performance", "termination": "Termination"}.get(stage_name, stage_name.title())
        entry = {
            "id": f"{stage_label.lower()}-{flag['clause_index']}",
            "severity": flag["severity"],
            "title": flag["title"],
            "clauseType": flag["title"].split(" risk", 1)[0] if " risk" in flag["title"] else flag["title"],
            "body": flag["body"],
            "explanation": flag.get("explanation") or flag["body"],
            "confidence": float(flag.get("confidence", 0.5)),
            "disadvantages": flag.get("disadvantaged_party"),
            "citationLabel": None,
            "citationText": None,
        }
        citation = flag.get("citation") or {}
        if citation:
            entry["citationLabel"] = citation.get("title") or citation.get("node_id")
            entry["citationText"] = citation.get("text")
        stages.setdefault(stage_label, []).append(entry)

    high = sum(1 for flags in stages.values() for flag in flags if flag["severity"] == "high")
    medium = sum(1 for flags in stages.values() for flag in flags if flag["severity"] == "medium")
    missing = sum(1 for flags in stages.values() for flag in flags if flag["severity"] == "missing")
    ok = max(0, 3 - (high + medium + missing))

    return {
        "jurisdiction": jurisdiction,
        "domain": domain,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "summary": {"high": high, "medium": medium, "missing": missing, "ok": ok},
        "stages": stages,
    }


@router.post("/api/draft")
async def draft_contract(req: DraftRequest):
    jurisdiction = canonical_jurisdiction(req.jurisdiction)
    domain = canonical_domain(req.domain)

    if not is_supported(jurisdiction, domain):
        raise HTTPException(status_code=400, detail="UNSUPPORTED_COMBINATION")

    draft_text = assemble_draft(jurisdiction, domain, req.answers)
    result = run_pipeline(draft_text, jurisdiction, domain)
    report = _to_report_json(result, jurisdiction, domain)
    return {"draftText": draft_text, "report": report}
