import asyncio
import io

from fastapi import UploadFile

from app.api.routes_check import check_contract
from app.api.routes_draft import DraftRequest, draft_contract


def test_check_route_returns_frontend_compatible_report():
    upload = UploadFile(filename="sample.txt", file=io.BytesIO(b"Confidential information must be kept secret. The governing law is India."))

    body = asyncio.run(check_contract("india", "nda_service", upload))

    assert body["jurisdiction"] == "india"
    assert body["domain"] == "nda_service"
    assert set(body.keys()) >= {"jurisdiction", "domain", "generatedAt", "summary", "stages"}
    assert set(body["stages"].keys()) >= {"Signing", "Performance", "Termination"}


def test_draft_route_returns_draft_text_and_report():
    req = DraftRequest(
        jurisdiction="india",
        domain="nda_service",
        answers={
            "party_a": "Acme",
            "party_b": "Beta",
            "term_months": "12",
            "auto_renew": "No",
            "scope": "Software development services",
        },
    )

    body = asyncio.run(draft_contract(req))

    assert "draftText" in body
    assert body["report"]["jurisdiction"] == "india"
    assert body["report"]["domain"] == "nda_service"


def test_check_route_exposes_explanation_in_each_flag():
    upload = UploadFile(filename="sample.txt", file=io.BytesIO(b"Confidential information must be kept secret. The governing law is India."))

    body = asyncio.run(check_contract("india", "nda_service", upload))

    flags = [flag for stage in body["stages"].values() for flag in stage]
    assert flags
    assert all("explanation" in flag for flag in flags)
    assert any(flag["explanation"] for flag in flags)
