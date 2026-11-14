"""
Regression tests for extracted statute data. PDF extraction failed SILENTLY in many
different ways while building the India corpus (dropped sections, scrambled words,
next-chapter text bleeding into the previous section, and -- worst -- footnotes whose
numbers matched real section numbers, so the COUNT was right but the TEXT was wrong).
Re-run after any change to scripts/extract_statute_sections.py or after re-extracting.
"""
import re
from collections import Counter

import pytest

from app.graph.build_static_graph import load_statute_text

# live sections per Act, reconciled against each Act's own "Arrangement of Sections"
EXPECTED_SECTIONS = {
    "ICA": 192, "SRA": 46, "TPA": 135, "RA": 90, "ISA": 95, "LA": 30, "ACA": 106,
    "CPA": 107, "ITA": 109, "DPDP": 44, "KRA": 70, "KSA": 85,
}


@pytest.fixture(scope="module")
def india():
    return load_statute_text("india")


def by(india, short, sid):
    return next(e for e in india if e["act_short"] == short and e["section_id"] == sid
                and e["kind"] == "section")


@pytest.mark.parametrize("short,count", EXPECTED_SECTIONS.items())
def test_section_counts_match_table_of_contents(india, short, count):
    assert sum(e["act_short"] == short and e["kind"] == "section" for e in india) == count


def test_node_ids_unique(india):
    ids = [e["node_id"] for e in india]
    assert len(ids) == len(set(ids)), [k for k, v in Counter(ids).items() if v > 1][:5]


def test_model_and_template_documents_are_not_loaded(india):
    assert {e["act_short"] for e in india}.isdisjoint({"MTA", "MTR"})
    assert all(e.get("status", "in_force") == "in_force" for e in india)


def test_no_oversized_blobs_loaded(india):
    assert not any(e.get("oversized") for e in india)


def test_all_entries_tagged_india(india):
    assert all(e["jurisdiction"] == "india" for e in india)


@pytest.mark.parametrize("short,sid", [
    ("ICA", "16"), ("ICA", "19A"), ("ICA", "74"), ("ICA", "151"), ("ICA", "234"), ("ICA", "238"),
    ("TPA", "53A"), ("TPA", "63A"), ("TPA", "107"), ("KSA", "10A"), ("KSA", "52B"), ("KRA", "69"),
    ("ISA", "35"), ("KRA", "4"),
])
def test_sections_that_once_went_missing_are_present(india, short, sid):
    assert by(india, short, sid)


def test_footnote_numbers_did_not_become_sections(india):
    # Karnataka Stamp Act footnotes ("11. Inserted by Act 7 of 2016...") once became "sections" 10-18
    for sid in ("10", "11", "13", "14", "15", "16", "17", "18"):
        try:
            e = by(india, "KSA", sid)
        except StopIteration:
            continue  # 11 and 12 are genuinely omitted in the body
        body = e["text"].split("\u2014", 1)[-1]
        assert not re.match(r"\s*(Inserted|Substituted|Omitted)\b", body), sid


def test_omitted_sections_are_not_loaded(india):
    ksa = {e["section_id"] for e in india if e["act_short"] == "KSA" and e["kind"] == "section"}
    assert "60" not in ksa and "11" not in ksa and "12" not in ksa   # "[X X X]" in the body


def test_no_repealed_or_omitted_sections_leaked(india):
    for e in india:
        if e["kind"] == "section":
            assert not re.search(r"\[Repealed|Rep\.\s*by", e["text"][:120], re.I), e["node_id"]


def test_no_next_chapter_heading_bleed(india):
    for e in india:
        assert not re.search(r"^\[?CHAPTER\b", e["text"], re.M), e["node_id"]


def test_footnote_leakage_is_negligible(india):
    leak = re.compile(r"\b(Subs\.|Ins\.) by Act|\bby Act \d+ of \d{4}")
    bad = [e["node_id"] for e in india if e["kind"] == "section" and leak.search(e["text"])]
    assert len(bad) <= 2, bad


def test_no_scrambled_words_in_ica_74(india):
    text = by(india, "ICA", "74")["text"]
    assert "penalty" in text and "paenalty" not in text and "amiount" not in text


def test_limitation_article_for_breach_of_contract(india):
    art = next(e for e in india if e["node_id"].endswith("LA:THE SCHEDULE - Article 55"))
    assert "breach of" in art["text"] and "Three years" in art["text"]


def test_karnataka_stamp_lease_and_agreement_articles(india):
    lease = next(e for e in india if e["node_id"].endswith("KSA:SCHEDULE - Article 30"))
    agreement = next(e for e in india if e["node_id"].endswith("KSA:SCHEDULE - Article 5"))
    assert "Lease" in lease["text"] and "Agreement" in agreement["text"]


def test_karnataka_rent_act_scope_exclusions_present(india):
    s2 = by(india, "KRA", "2")["text"]
    assert "Nothing contained in this Act shall apply" in s2 and "rupees per month" in s2
