"""
POST /api/check — upload a contract, run the pipeline, return a risk report.
Response shape must match what frontend/src/api/client.js expects, so the
mock and the real backend are interchangeable from the UI's point of view.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.config import canonical_domain, canonical_jurisdiction, is_supported
from app.ingestion.parser import parse_document
from app.pipeline import run_pipeline

router = APIRouter()


def _normalize_stage_name(stage: str) -> str:
    if stage == "signing":
        return "Signing"
    if stage == "performance":
        return "Performance"
    if stage == "termination":
        return "Termination"
    return stage.title()


def _to_report_json(result, jurisdiction: str, domain: str) -> dict:
    stages = {"Signing": [], "Performance": [], "Termination": []}
    for flag in result.flags:
        stage_name = _normalize_stage_name(flag.get("lifecycle_stage", "performance"))
        entry = {
            "id": f"{stage_name.lower()}-{flag['clause_index']}",
            "severity": flag["severity"],
            "title": flag["title"],
            "clauseType": flag["title"].split(" risk", 1)[0] if " risk" in flag["title"] else flag["title"],
            "body": flag["body"],
            "explanation": flag.get("explanation") or flag["body"],
            "recommendation": flag.get("recommendation") or flag.get("explanation") or flag["body"],
            "confidence": float(flag.get("confidence", 0.5)),
            "disadvantages": flag.get("disadvantaged_party"),
            "citationLabel": None,
            "citationText": None,
        }
        citation = flag.get("citation") or {}
        if citation:
            entry["citationLabel"] = citation.get("title") or citation.get("node_id")
            entry["citationText"] = citation.get("text")
        stages.setdefault(stage_name, []).append(entry)

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


@router.post("/api/check")
async def check_contract(
    jurisdiction: str = Form(...),
    domain: str = Form(...),
    file: UploadFile = File(...),
):
    jurisdiction = canonical_jurisdiction(jurisdiction)
    domain = canonical_domain(domain)

    if not is_supported(jurisdiction, domain):
        raise HTTPException(status_code=400, detail="UNSUPPORTED_COMBINATION")

    file_bytes = await file.read()
    parsed = parse_document(file.filename or "document.txt", file_bytes)
    if not parsed.raw_text.strip():
        raise HTTPException(status_code=400, detail="EMPTY_DOCUMENT")

    result = run_pipeline(parsed.raw_text, jurisdiction, domain)
    return _to_report_json(result, jurisdiction, domain)
