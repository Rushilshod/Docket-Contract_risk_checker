"""
Regression tests for UK statute data. legislation.gov.uk PDFs have no table of
contents to validate against (unlike India Code), so these tests lock in: (a) a
baseline section count per Act, reconciled by hand against the extractor's own
report output, and (b) specific bugs that were found and fixed while building
this data, so a future change to extract_statute_sections_uk.py can't silently
reintroduce them. Re-run after any change to that script or after re-extracting.
"""
import re

import pytest

from app.graph.build_static_graph import load_statute_text

EXPECTED_SECTIONS = {
    "MA": 5, "HFHHA": 2, "LPCDIA": 19, "PIDA": 15, "SGSA": 27, "UCTA": 20,
    "PEA": 16, "LTA": 60, "TFA": 37, "HA1988": 137, "HA2004": 270,
    "RRA": 130, "CRA": 101, "DMCC": 313,
}


@pytest.fixture(scope="module")
def uk():
    return load_statute_text("uk")


def by(uk, short, sid):
    return next(e for e in uk if e["act_short"] == short and e["section_id"] == sid
                and e["kind"] == "section")


@pytest.mark.parametrize("short,count", EXPECTED_SECTIONS.items())
def test_section_counts_match_baseline(uk, short, count):
    assert sum(e["act_short"] == short and e["kind"] == "section" for e in uk) == count


def test_trade_secrets_regulations_known_unextracted(uk):
    # Statutory-Instrument layout (id+title combined on one bold line, no isolated
    # id line) is not supported by this extractor yet -- see sources_uk.json note.
    assert "TSR" not in {e["act_short"] for e in uk}


def test_node_ids_unique(uk):
    ids = [e["node_id"] for e in uk]
    assert len(ids) == len(set(ids))


def test_all_entries_tagged_uk(uk):
    assert all(e["jurisdiction"] == "uk" for e in uk)


def test_no_oversized_schedules_loaded(uk):
    assert not any(e.get("oversized") for e in uk)


@pytest.mark.parametrize("short,sid", [
    ("HFHHA", "1"), ("HFHHA", "2"),           # the two real top-level sections;
    # the Act's own quoted insertions (9A/9B/9C, into the ACT IT AMENDS) must not
    # appear as top-level sections of this Act
    ("MA", "1"), ("MA", "2"), ("MA", "3"), ("MA", "5"), ("MA", "6"),
    ("LTA", "3A"), ("LTA", "9A"), ("LTA", "9B"), ("LTA", "9C"),
    ("LTA", "20B"), ("LTA", "20E"), ("LTA", "20F"), ("LTA", "20J"), ("LTA", "20K"),
    ("CRA", "62"), ("CRA", "64"),               # core unfair-terms provisions
    ("HA1988", "18"), ("HA1988", "21"),          # core assured shorthold provisions
])
def test_sections_that_were_hard_to_extract_are_present(uk, short, sid):
    assert by(uk, short, sid)


def test_homes_act_does_not_contain_quoted_sections_as_top_level(uk):
    homes_ids = {e["section_id"] for e in uk if e["act_short"] == "HFHHA" and e["kind"] == "section"}
    assert homes_ids == {"1", "2"}
    # but the quoted text must still be present, inside section 1's own body
    assert "9A" in by(uk, "HFHHA", "1")["text"]


def test_misrepresentation_act_section_4_correctly_dropped_as_repealed(uk):
    ma_ids = {e["section_id"] for e in uk if e["act_short"] == "MA" and e["kind"] == "section"}
    assert "4" not in ma_ids  # wholly repealed (shown as a run of dots in the source)


def test_no_note_header_leakage_into_section_text(uk):
    leak = re.compile(r"\bTextual Amendments\b|\bMarginal Citations\b|\bCommencement Information\b")
    bad = [e["node_id"] for e in uk if e["kind"] == "section" and leak.search(e["text"])]
    assert not bad, bad


def test_no_part_or_chapter_heading_bleed(uk):
    # Only a problem for "section" entries -- a PART heading legitimately belongs
    # inside a Schedule's own body as retained structure (e.g. Consumer Rights Act
    # Schedule 2's "PART 1 / LIST OF TERMS"), which is intentional, not a bug.
    for e in uk:
        if e["kind"] != "section":
            continue
        assert not re.search(r"^(PART|CHAPTER)\b\s*[0-9IVXLCDM]", e["text"], re.M), e["node_id"]


def test_no_empty_or_near_empty_sections(uk):
    tiny = [e["node_id"] for e in uk if e["kind"] == "section" and len(e["text"]) < 30]
    assert not tiny, tiny


def test_notes_block_does_not_swallow_later_body_text(uk):
    # Regression for the biggest bug found: once a Commencement Information /
    # Textual Amendments block appeared mid-section or mid-schedule, everything
    # after it used to be silently diverted into page_notes instead of text.
    s62 = by(uk, "CRA", "62")
    assert "section 65" in s62["text"]  # the real closing cross-reference, after s.62's own notes
    sch4 = next(e for e in uk if e["node_id"] == "uk:CRA:SCHEDULE 4")
    assert len(sch4["text"]) > 5000  # was truncated to ~480 chars before the fix


def test_known_genuine_numbering_gaps_are_not_extraction_misses(uk):
    # Confirmed by direct inspection of the source PDFs: no candidate heading line
    # exists at all in these ranges, i.e. the consolidated in-force text itself
    # skips these numbers (sections repealed and fully removed, not just stubbed).
    ha1988_ids = {e["section_id"] for e in uk if e["act_short"] == "HA1988" and e["kind"] == "section"}
    assert ha1988_ids.isdisjoint({"46", "47", "48", "49", "51"})
    assert {"45", "52"}.issubset(ha1988_ids)


def test_known_extraction_gap_housing_act_1988_s19_s20(uk):
    # NOT a genuine numbering gap (unlike the test above) -- confirmed by direct
    # inspection that sections 19 and 20 DO exist in the source PDF with real
    # content (s.20 is the well-known "assured shorthold tenancy" provision), but
    # a rare PDF text-run merge around an inline footnote marker near s.19
    # ("F190") prevents both from being recognised as separate section-id lines
    # with the current heuristic. This test exists so a future fix is noticed
    # (it will start failing) rather than the gap being silently reintroduced
    # if someone "fixes" extraction without checking here. TODO(engineer): once
    # fixed, flip this assertion and add s.20 back to the "hard to extract" list
    # above.
    ha1988_ids = {e["section_id"] for e in uk if e["act_short"] == "HA1988" and e["kind"] == "section"}
    assert {"19", "20"}.isdisjoint(ha1988_ids)
