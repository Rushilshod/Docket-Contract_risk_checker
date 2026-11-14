"""
Statute PDF -> clean per-section JSON, for legislation.gov.uk-generated PDFs (UK).

This is a SEPARATE extractor from extract_statute_sections.py (India), because the
legislation.gov.uk layout is structurally different, not just messier in the same way:

  - No table of contents / "Arrangement of Sections" page at the front, so there is
    no whitelist to validate against (unlike India Code). Validation here relies on
    strict monotonic section-number increase plus a small set of hand-checked spots.
  - A section's number and its title are two SEPARATE, ISOLATED bold text lines
    (e.g. line "1", then line "Removal of certain bars..."), not "1. Title.\u2014body"
    on one line. This is actually cleaner than India once recognised.
  - Every page repeats a "Changes to legislation: ..." / "Status: ..." / running
    "<Act> (c. NN)" footer block, ALWAYS at 8pt font in these PDFs -- a clean,
    reliable filter (India's watermark needed a frequency-based filter instead).
  - Marginal notes ("Textual Amendments", "Commencement Information", "Marginal
    Citations", etc.) are headed by a bold 10pt label and follow with "F1"/"C1"/
    "I1"/"M1"-style reference codes at 9pt -- letters, not digits, so they cannot
    collide with section numbers the way India's numeric footnotes did.
  - Newly-inserted sections/subsections carry an amendment marker glued directly
    onto the number with NO separator, e.g. "[F23" for inserted section "3"
    (marker "F2" + id "3") or "[F42A" for inserted section "2A" (marker "F4" +
    id "2A") -- the same "ambiguous glued digits" problem as India's "1151", solved
    the same way: try every split and keep the one consistent with the expected
    next section number.
  - A quoted section number belonging to the ACT BEING AMENDED can appear inside
    another section's body text (e.g. the Homes Act 2018 inserts new sections
    "9A"/"9B"/"9C" into the Landlord and Tenant Act 1985, printed inside section 1
    of the Homes Act itself). These are NOT new top-level sections of the source
    Act. They are reliably distinguished because a genuine section-number line is
    ISOLATED (nothing else on that line) and sits at the document's left margin;
    quoted nested numbers are indented and/or share their line with title text.

Usage:
    python extract_statute_sections_uk.py --manifest ../data/statutes/sources_uk.json \
        --pdf-dir /path/to/pdfs --out-dir ../data/statutes/uk
"""
import argparse
import collections
import hashlib
import json
import re
import sys
from datetime import date
from pathlib import Path

try:
    import pymupdf as fitz
except ImportError:
    import fitz

NOTE_HEADERS = {
    "Textual Amendments", "Commencement Information", "Marginal Citations",
    "Modifications etc. (not altering text)", "Extent Information",
    "Editorial Information", "Subordinate Legislation Made", "Status:",
}
PART_RE = re.compile(r"^(PART|CHAPTER)\b\s*[0-9IVXLCDM]*[A-Z]?\s*$")
SCHEDULE_RE = re.compile(r"^\[?F?\d*\s*SCHEDULES?\b")  # case-SENSITIVE: an actual heading is
# printed in caps ("SCHEDULE 1"); an ordinary body cross-reference ("Schedule 5 provides...")
# is not, and must not be treated as the start of a new Schedule block.
PURE_ID_RE = re.compile(r"^\[?(?:F(?P<amend>\d+))?(?P<id>\d{1,3}[A-Z]{0,2})\]?$")
DOTS_RE = re.compile(r"^[\.\s]{10,}")
NOTE_REF_RE = re.compile(r"^[A-Z]\d{1,3}$")


def _key(sid: str):
    m = re.match(r"(\d+)([A-Z]*)", sid)
    return (int(m.group(1)), m.group(2))


# ------------------------------------------------------------------ extraction
def extract_lines(pdf_path: str):
    """One dict per text line, across the whole document, in reading order.
    Drops the 8pt boilerplate footer/header and bare page numbers outright."""
    doc = fitz.open(pdf_path)
    out = []
    for pno, page in enumerate(doc, start=1):
        for b in page.get_text("dict")["blocks"]:
            for l in b.get("lines", []):
                spans = l["spans"]
                if not spans:
                    continue
                text = "".join(s["text"] for s in spans).strip()
                if not text:
                    continue
                size = round(spans[0]["size"], 1)
                if size >= 24 or size <= 8.0:          # title page / running boilerplate
                    continue
                bold = bool(spans[0]["flags"] & 2**4)
                if not bold and re.fullmatch(r"\d{1,4}", text):   # bare page number (never bold here)
                    continue
                italic = bool(spans[0]["flags"] & 2**1)
                out.append({"page": pno, "x0": round(l["bbox"][0]), "size": size,
                            "bold": bold, "italic": italic, "text": text})
    return out, len(doc)


def find_left_margin(lines):
    """x0 of genuine section-id lines: the mode of x0 among BODY-SIZE bold lines
    whose text is ONLY an id pattern. The size filter matters: bare reference codes
    in the "Textual Amendments" notes (e.g. "F1", "F23") are printed at 9pt and can
    ALSO match the id pattern (PURE_ID_RE's amendment-marker branch doesn't require
    brackets) -- a large Act can have far more of those than real sections, which
    silently drags the mode onto the notes column instead of the real margin."""
    body_size = collections.Counter(l["size"] for l in lines if not l["bold"]).most_common(1)[0][0]
    xs = collections.Counter(
        l["x0"] for l in lines
        if l["bold"] and l["size"] >= body_size - 0.6 and PURE_ID_RE.match(l["text"])
    )
    if xs:
        return xs.most_common(1)[0][0]
    bold_xs = [l["x0"] for l in lines if l["bold"] and l["size"] >= body_size - 0.6]
    return min(bold_xs) if bold_xs else 90


def resolve_amendment_split(raw_id: str, last: tuple):
    """'F23' or 'F42A': try every prefix-length split of the digits after 'F' into
    (amendment ref number, real section id), keep the split whose id's number is
    either the same as the last section seen (an inserted lettered sub-section,
    e.g. "20" then "20B") or one more than it. Iterates longest-id-first so a
    genuinely multi-digit amendment reference number doesn't win by accident when
    a shorter one also happens to satisfy the constraint.

    Returns None if NO split fits -- this matters: the token can be a plain
    footnote/amendment reference number with nothing to do with a section id at
    all (e.g. "F190" as an inline reference mark, sitting right before a real,
    unambiguous "19" section-id line of its own). Guessing a fallback here once
    produced the id "0" for what was actually section 19 of the Housing Act 1988.
    Returning None lets the caller treat the line as noise rather than commit to
    a wrong section boundary."""
    m = re.match(r"F(\d+)([A-Z]*)$", raw_id)
    if not m:
        return raw_id  # no amendment marker, id is already clean
    digits, letters = m.group(1), m.group(2)
    candidates = [str(int(digits[i:])) + letters for i in range(1, len(digits))]
    for cand in candidates:
        if _key(cand)[0] in (last[0], last[0] + 1):
            return cand
    return None


# --------------------------------------------------------------------- parsing
def split_sections(lines, left_margin, body_size):
    items, cur, last, mode = [], None, (0, ""), "scan"

    def close():
        nonlocal cur
        if cur:
            items.append(cur)
        cur = None

    for l in lines:
        t, x0, bold = l["text"], l["x0"], l["bold"]

        if bold and t in NOTE_HEADERS or t.startswith("Status:"):
            mode = "notes"
            if cur:
                cur.setdefault("notes", []).append(t)
            continue

        in_sched = cur is not None and cur["kind"] == "schedule"

        if bold and PART_RE.match(t):
            if in_sched:            # e.g. "PART 1" inside a Schedule is structure, not a boundary
                cur["lines"].append(t); continue
            close(); mode = "scan"; continue
        if SCHEDULE_RE.match(t) and l["size"] >= body_size - 0.6:
            # Unlike section headings, a genuine Schedule heading is not always bold in
            # these PDFs -- what distinguishes it from an ordinary in-body cross-reference
            # ("Schedule 5 (application to bread) is amended...") is that the real heading
            # is printed in caps ("SCHEDULE 1") and the cross-reference is not (checked by
            # SCHEDULE_RE being case-sensitive), not boldness.
            close()
            cur = {"kind": "schedule", "id": t, "title": t, "lines": [],
                   "pages": {l["page"]}, "stage": "body"}
            mode = "body"
            continue

        is_id_line = (not in_sched and bold and l["size"] >= body_size - 0.6
                      and abs(x0 - left_margin) <= 4 and PURE_ID_RE.match(t))
        if is_id_line:
            m = PURE_ID_RE.match(t)
            if m.group("amend"):
                real_id = resolve_amendment_split("F" + m.group("amend") + m.group("id"), last)
            else:
                real_id = m.group("id")
            if real_id is None or (_key(real_id) <= last and not m.group("amend")):
                pass  # noise (e.g. a bare footnote ref like "F190"), or a non-increasing plain id
            else:
                close()
                last = _key(real_id)
                cur = {"kind": "section", "id": real_id, "title_lines": [], "lines": [],
                       "pages": {l["page"]}, "stage": "title", "notes": []}
                mode = "body"
                continue

        if cur is None:
            continue
        cur["pages"].add(l["page"])

        if mode == "notes":
            if l["size"] >= body_size - 0.6:
                # Font size back to body size (11pt) and this isn't itself a note
                # header (already handled above) -- the notes block has ended and
                # real body text has resumed. Without this check, mode stayed
                # "notes" for the rest of the section/schedule once a single
                # Commencement Information/Textual Amendments block appeared
                # anywhere mid-body, silently dropping everything after it from
                # "text" -- this truncated most Schedules to a few hundred
                # characters (e.g. Consumer Rights Act Sch. 4 down from several
                # thousand) even though section/schedule BOUNDARIES were still
                # detected correctly, so the bug was invisible in id/title counts.
                mode = "body"
            else:
                cur.setdefault("notes", []).append(t)
                continue

        if cur["kind"] == "section" and cur["stage"] == "title":
            if t in ("[", "]"):
                continue  # stray bracket from an amendment marker, not title or body
            if bold and not DOTS_RE.match(t):
                cur["title_lines"].append(t)
                continue
            cur["stage"] = "body"
            # fall through: this line is already body content

        cur["lines"].append(t)

    close()
    return items


def to_entries(items, meta, source_file):
    out = []
    for it in items:
        if it["kind"] == "schedule":
            text = "\n".join(it["lines"]).strip()
            if len(text) < 40:
                continue
            out.append({"node_id": f"{meta['jurisdiction']}:{meta['short']}:{it['id']}",
                        "act": meta["act"], "act_short": meta["short"], "year": meta.get("year"),
                        "jurisdiction": meta["jurisdiction"], "level": meta.get("level", "central"),
                        "status": meta.get("status", "in_force"), "kind": "schedule",
                        "section_id": it["id"], "title": it["id"], "text": text,
                        "pages": [min(it["pages"]), max(it["pages"])], "page_notes": [],
                        "source_file": source_file, "domain": None,
                        "oversized": len(text) > 40000})
            continue

        title = " ".join(it["title_lines"]).strip()
        if DOTS_RE.match(title) or not title:
            continue  # wholly repealed/omitted section (e.g. Misrepresentation Act s.4)
        body = "\n".join(it["lines"]).strip()
        if not body:
            continue  # title stub survives but the substantive text has been repealed away
                       # entirely (no dots shown), e.g. Housing Act 1988 s.55 -- confirmed by
                       # its own "Textual Amendments" note explaining the repeal
        heading = f"{it['id']} {title.rstrip('.')}"
        text = f"{heading}.\u2014{body}" if body else heading + "."
        clean = re.sub(r"\[?F\d+", "", text).replace("[", "").replace("]", "")
        clean = re.sub(r"\.\s\.(\s\.){8,}", "[text omitted]", clean)
        seen, notes = set(), []
        for n in it.get("notes", []):
            if n not in seen:
                seen.add(n); notes.append(n)
        out.append({"node_id": f"{meta['jurisdiction']}:{meta['short']}:{it['id']}",
                    "act": meta["act"], "act_short": meta["short"], "year": meta.get("year"),
                    "jurisdiction": meta["jurisdiction"], "level": meta.get("level", "central"),
                    "status": meta.get("status", "in_force"), "kind": "section",
                    "section_id": it["id"], "title": title, "text": text, "text_clean": clean,
                    "pages": [min(it["pages"]), max(it["pages"])], "page_notes": notes[:12],
                    "source_file": source_file, "domain": None})
    return out


def build(pdf_path: Path, meta: dict):
    lines, npages = extract_lines(str(pdf_path))
    left_margin = find_left_margin(lines)
    body_size = collections.Counter(l["size"] for l in lines if not l["bold"]).most_common(1)[0][0]
    items = split_sections(lines, left_margin, body_size)
    entries = to_entries(items, meta, pdf_path.name)
    ids = [_key(e["section_id"]) for e in entries if e["kind"] == "section"]
    non_monotonic = [i for i in range(1, len(ids)) if ids[i] <= ids[i - 1]]
    gaps = [(ids[i - 1], ids[i]) for i in range(1, len(ids)) if ids[i][0] - ids[i - 1][0] > 5]
    report = {"pages": npages, "left_margin_x0": left_margin,
              "sections": sum(e["kind"] == "section" for e in entries),
              "schedules": sum(e["kind"] == "schedule" for e in entries),
              "non_monotonic_at": non_monotonic, "large_gaps": gaps[:8]}
    return entries, report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--pdf-dir", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--only", help="substring of file name to process")
    a = ap.parse_args()
    manifest = json.load(open(a.manifest, encoding="utf-8"))
    for meta in manifest["files"]:
        if a.only and a.only not in meta["file"]:
            continue
        pdf = Path(a.pdf_dir) / meta["file"]
        entries, rep = build(pdf, {**meta, "jurisdiction": manifest["jurisdiction"]})
        out = Path(a.out_dir) / meta.get("out_subdir", "") / meta["out"]
        out.parent.mkdir(parents=True, exist_ok=True)
        json.dump(entries, open(out, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
        meta["sha256"] = hashlib.sha256(pdf.read_bytes()).hexdigest()
        meta["processed_on"] = date.today().isoformat()
        json.dump(manifest, open(a.manifest, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
        flag = " !!" if rep["non_monotonic_at"] or rep["large_gaps"] else ""
        print(f"{meta['file']:32s} pages={rep['pages']:4d} sections={rep['sections']:4d} "
              f"sched={rep['schedules']:2d} margin_x0={rep['left_margin_x0']:4d} "
              f"gaps={rep['large_gaps']}{flag}")


if __name__ == "__main__":
    main()
