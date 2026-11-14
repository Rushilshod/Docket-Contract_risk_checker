"""
Statute PDF -> clean per-section JSON (v2, multi-Act).

Why v2: v1 guessed section boundaries from number sequence and broke on every
new PDF. v2 uses the Act's OWN "Arrangement of Sections" as a whitelist of
valid section numbers and requires numbers to increase, which removes the
footnote-number / illustration-number collisions that caused v1's cascades.

What it does NOT do: decide what a section means or which clause type it
governs. That is the human-reviewed step (Section 7, item 1 of the brief).

Usage (batch, recommended):
    python extract_statute_sections.py --manifest ../data/statutes/sources_india.json \
        --pdf-dir /path/to/pdfs --out-dir ../data/statutes/india
"""
import argparse
import collections
import datetime
import hashlib
import json
import re
import statistics
import sys
from pathlib import Path

try:
    import pymupdf as fitz
except ImportError:  # older PyMuPDF
    import fitz

NOISE_RES = [re.compile(p) for p in (
    r"^IndiaCode\d*$", r"^\d{1,4}$", r"^SECTIONS?\s*:?$", r"^Clauses\s*:?$",
    r"^_{3,}$", r"^[\*\s]+$",
)]
CAND_RE = re.compile(r"^(?:\d*\s?\[)?(?P<id>\d{1,3}(?:-?[A-Z]{1,2})?)\.\s*(?P<rest>.*)$")
FOOTNOTE_LEAD_RE = re.compile(
    r"^(\d{1,2}\.\s*(Subs\.|Ins\.|Rep\.|Inserted|Substituted|Omitted|Added|Re-?numbered|Deemed|"
    r"Repealed|Amended|The words|The Sub|Sub-section|See\b|Cf\.|Vide|Now\b))")
# A bare "12." on its own line is a footnote number in the inline-footnote layout, but in a
# Schedule TABLE it is the Article number sitting alone in its cell -> inline mode only.
FOOTNOTE_BARE_RE = re.compile(r"^\d{1,2}\.$")
CHAPTER_RE = re.compile(r"^\[?(CHAPTER|PART)\b\s*[-–—]?\s*[IVXLCDM0-9]+[A-Z]?\b")
SCHEDULE_RE = re.compile(
    r"^(?:\d*\s?\[)?\s*(THE\s+)?((FIRST|SECOND|THIRD|FOURTH|FIFTH|SIXTH|SEVENTH|EIGHTH|NINTH|TENTH)\s+)?SCHEDULE\b")
SCHEDULE_TC_RE = re.compile(r"^(First|Second|Third|Fourth|Fifth|Sixth|Seventh|Eighth)\s+Schedule\s*$")
FORM_RE = re.compile(r"^FORM[-–\s]+[IVX0-9A-Z]+\b")
REPEAL_RE = re.compile(
    r"\[\s*(Repealed|Omitted)|Rep\.\s*by|Omitted by|^\s*\*\s*\*\s*\*|\[?\s*X\s+X\s+X\b", re.I)


FOOTNOTE_STRONG_RE = re.compile(
    r"^\d{1,2}\.\s+.*(?:\bby Act\b|\bw\.e\.f\.|\bAct \d+ of \d{4}|\bibid\b|Order, \d{4})")


def _key(sid: str):
    m = re.match(r"(\d+)([A-Z]*)", sid)
    return (int(m.group(1)), m.group(2))


# ----------------------------------------------------------------- extraction
def extract_lines(pdf_path: str, footnote_mode: str, extractor: str = "pymupdf"):
    """Return (body_lines, notes_by_page, page_count). Skips rotated watermarks."""
    if extractor == "pdftotext":      # for PDFs whose fonts lack a Unicode map in PyMuPDF
        import subprocess
        txt = subprocess.run(["pdftotext", pdf_path, "-"], capture_output=True, text=True).stdout
        pages = txt.split("\f")
        # a page break can glue the next section onto the previous line:
        # "...commencement of this Act69. Transfer of pending cases.- On the..."
        glue = re.compile(r"(?<=[a-z\)])(\d{1,3}[A-Z]?)\.\s+(?=[A-Z][^.\n]{2,120}\.\s*[-\u2014\u2013])")
        out = [{"page": n, "x0": 0, "y0": 0, "size": 11.0, "text": part.rstrip(), "note": False}
               for n, pt in enumerate(pages, 1) for ln in pt.split("\n") if ln.strip()
               for part in glue.sub(lambda m: "\n" + m.group(1) + ". ", ln).split("\n") if part.strip()]
        return out, collections.defaultdict(list), len(pages)
    doc = fitz.open(pdf_path)
    body, notes = [], collections.defaultdict(list)
    # Body font = most common size across the WHOLE document. Per-page is wrong:
    # a footnote-heavy page has footnote text as its dominant size.
    doc_chars = collections.Counter()
    for page in doc:
        for b in page.get_text("dict")["blocks"]:
            for l in b.get("lines", []):
                if abs(l["dir"][0] - 1.0) <= 0.01:
                    for sp in l["spans"]:
                        if sp["size"] < 25:
                            doc_chars[round(sp["size"], 1)] += len(sp["text"])
    dominant = doc_chars.most_common(1)[0][0]
    for pno, page in enumerate(doc, start=1):
        lines = []
        for b in page.get_text("dict")["blocks"]:
            for l in b.get("lines", []):
                if abs(l["dir"][0] - 1.0) > 0.01:      # rotated watermark
                    continue
                spans = l["spans"]
                text = "".join(s["text"] for s in spans).rstrip()
                if not text.strip() or max(s["size"] for s in spans) >= 25:
                    continue
                lines.append({"page": pno, "x0": l["bbox"][0], "y0": l["bbox"][1],
                              "size": round(max(x["size"] for x in spans), 1), "text": text})
        if not lines:
            continue
        cut = None
        if footnote_mode in ("rule", "inline"):
            cut = _rule_cut(page, lines, dominant)
        for l in lines:
            l["note"] = cut is not None and l["y0"] >= cut
        in_note = False
        for l in lines:
            small = l["size"] <= dominant - 0.4
            t = l["text"].strip()
            if l["note"]:
                in_note = True
            elif (FOOTNOTE_STRONG_RE.match(t) or (small and FOOTNOTE_LEAD_RE.match(t))
                  or (footnote_mode == "inline" and small and FOOTNOTE_BARE_RE.match(t))):
                # "N. ... by Act NN of YYYY / w.e.f." is specific enough to trust at ANY font size
                # (Karnataka Stamp Act prints footnotes at body size). The weaker lead-word
                # signature still needs the smaller font.
                l["note"], in_note = True, True
            elif (footnote_mode == "inline" and in_note and not CAND_RE.match(t)
                  and (small or (len(t) < 110 and re.search(r"w\.e\.f\.|\bAct\b.*\d{4}|\d{1,2}\.\d{1,2}\.\d{4}", t)))):
                l["note"] = True          # wrapped continuation of an inline footnote
            else:
                in_note = False
        if footnote_mode == "tail":
            for l in reversed(lines):
                if l["size"] <= dominant - 1.5 and l["y0"] > page.rect.height * 0.5:
                    l["note"] = True
                else:
                    break
        for l in lines:
            if l["note"]:
                notes[pno].append(l["text"].strip())
            else:
                body.append(l)
    return body, notes, len(doc)


def _rule_cut(page, lines, dominant):
    """Y of the footnote separator rule, or None. Requires: thin rule at the left
    margin, text below it smaller than body text, and first line below looking
    like a footnote ('1. ...' or '*'). The last two checks stop table borders
    (e.g. a Schedule) from being mistaken for footnote rules."""
    left = sorted(l["x0"] for l in lines)[len(lines) // 10]
    ys = sorted(d["rect"].y0 for d in page.get_drawings()
                if d["rect"].height < 2 and 100 <= d["rect"].width <= 260 and d["rect"].x0 <= left + 8)
    for y in ys:
        below = sorted((l for l in lines if l["y0"] >= y), key=lambda l: l["y0"])
        if (below and statistics.median(l["size"] for l in below) < dominant - 0.4
                and re.match(r"^(\d{1,2}[\.\s]|\*)", below[0]["text"].strip())):
            return y
    return None


def clean_lines(body):
    freq = collections.Counter(l["text"].strip() for l in body)
    pages = len({l["page"] for l in body}) or 1
    out = []
    for l in body:
        s = l["text"].strip()
        if any(p.match(s) for p in NOISE_RES):
            continue
        # running page headers, e.g. "THE CONSUMER PROTECTION ACT, 2019"
        if s == s.upper() and len(s) < 90 and freq[s] >= max(4, 0.2 * pages) \
                and not SCHEDULE_RE.match(s) and not CHAPTER_RE.match(s):
            continue
        out.append({**l, "text": s})
    return out


# ------------------------------------------------------------------- structure
def find_body_start(lines):
    for i, l in enumerate(lines):
        if re.search(r"may be called", l["text"]):
            for j in range(i, max(-1, i - 6), -1):
                if re.match(r"^(?:\d*\s?\[)?1\.", lines[j]["text"]):
                    return j
            return i
    return 0


def parse_toc_ids(toc_lines):
    ids, repealed = set(), set()
    for i, l in enumerate(toc_lines):
        m = CAND_RE.match(l["text"])
        if m:
            ids.add(m.group("id").replace("-", ""))
            probe = m.group("rest")
            if not probe.strip() and i + 1 < len(toc_lines):     # "12." alone, title on next line
                probe = toc_lines[i + 1]["text"]
            if re.search(r"Repealed|Omitted|Rep\.\s*by", probe, re.I):
                repealed.add(m.group("id").replace("-", ""))
    return ids, repealed


def split_title(head):
    m = re.search(r"\.\s*[—–\-]{1,3}\s*", head) or re.search(r"[—–]{1,3}\s*", head)
    if not m:
        return None, head
    return head[:m.start()].strip(" ."), head[m.end():]


def split_sections(lines, toc_ids, max_jump):
    items, cur, last = [], None, (0, "")

    def close():
        nonlocal cur
        if cur:
            if cur["kind"] == "section" and not cur["title_done"]:
                cur["title"], cur["lines"] = cur["head"][:160], [cur["head"]]
            items.append(cur)
        cur = None

    for idx, l in enumerate(lines):
        s = l["text"]
        in_sched = cur is not None and cur["kind"] == "schedule"
        if CHAPTER_RE.match(s):
            if in_sched:                      # "PART I" headings inside a Schedule are structure, not a boundary
                cur["lines"].append(s); continue
            close(); continue
        # Title-case headings ("Second Schedule") also occur as ordinary words in wrapped text, so
        # only accept them when the next line is the usual "[See section ...]" marker.
        tc_heading = bool(SCHEDULE_TC_RE.match(s)) and idx + 1 < len(lines) \
            and lines[idx + 1]["text"].lstrip().startswith("[See")
        if SCHEDULE_RE.match(s) or tc_heading or FORM_RE.match(s):
            sid = re.sub(r"\s+", " ", re.sub(r"^\d*\s?\[", "", s)).strip("[] .").upper()
            if in_sched and cur["id"] == sid:  # running page header repeated on every page of the table
                cur["pages"].add(l["page"]); continue
            close()
            cur = {"kind": "schedule", "id": sid, "title": s,
                   "lines": [], "pages": {l["page"]}, "title_done": True}
            continue
        picked, best = None, None
        cands = [(m.group("id").replace("-", ""), m.group("rest")) for m in [CAND_RE.match(s)] if m]
        if s[:1].isdigit():
            m2 = CAND_RE.match(s[1:])
            if m2:
                cands.append((m2.group("id").replace("-", ""), m2.group("rest")))
        for cid, rest in cands:
            if toc_ids and cid not in toc_ids:
                continue
            k = _key(cid)
            jump = k[0] - last[0]
            if k > last and jump <= max_jump and (best is None or jump < best):
                picked, best = (cid, rest), jump
        if picked and not (cur and cur["kind"] == "schedule"):
            close()
            cid, rest = picked
            last = _key(cid)
            title, body = split_title(rest)
            cur = {"kind": "section", "id": cid, "title": title, "head": rest,
                   "lines": [body] if title is not None else [], "pages": {l["page"]},
                   "title_done": title is not None}
            continue
        if not in_sched and re.fullmatch(r"\d{1,2}\.", s):
            continue                      # stray footnote number (but inside a Schedule it is an Article number)
        if cur:
            cur["pages"].add(l["page"])
            if cur["kind"] == "section" and not cur["title_done"]:
                cur["head"] += " " + s
                title, body = split_title(cur["head"])
                if title is not None:
                    cur["title"], cur["title_done"], cur["lines"] = title, True, [body]
                    continue
                if len(cur["head"]) > 400:      # no dash found: give up on title
                    cur["title"], cur["title_done"], cur["lines"] = cur["head"][:120], True, [cur["head"]]
                continue
            cur["lines"].append(s)
    close()
    return items


FOOT_VERB_RE = re.compile(r"^\s*(Inserted|Substituted|Omitted|Added|Subs\.|Ins\.|Renumbered|Re-numbered)\b", re.I)


ART_RE = re.compile(r"^(?:\d*\s?\[)?(\d{1,3}[A-Z]?)\.\s*(.*)$")


def split_articles(items):
    """Split a Schedule that is a table of numbered Articles (Limitation Act, stamp-duty
    Schedules) into one entry per Article. Articles must increase (max jump 3, allowing
    omitted ones). Falls back to the whole Schedule if fewer than 5 Articles are found."""
    out = []
    for it in items:
        if it["kind"] != "schedule" or not re.match(r"^(THE )?(\w+ )?SCHEDULE", it["id"]):
            out.append(it); continue
        arts, cur, last = [], None, (0, "")
        for ln in it["lines"]:
            m = ART_RE.match(ln)
            if m:
                k = _key(m.group(1))
                if k > last and k[0] - last[0] <= 3:
                    if cur:
                        arts.append(cur)
                    last = k
                    cur = {"kind": "schedule_article", "id": f"{it['id']} - Article {m.group(1)}",
                           "title": m.group(2)[:110], "lines": [m.group(2)],
                           "pages": set(it["pages"]), "title_done": True}
                    continue
            if cur:
                cur["lines"].append(ln)
        if cur:
            arts.append(cur)
        out.extend(arts if len(arts) >= 5 else [it])
    return out


def to_entries(items, notes, meta, source_file):
    out, dropped = [], set()
    for it in items:
        body = "\n".join(x for x in it["lines"] if x).strip()
        title = (it["title"] or "").strip()
        probe = (title + " " + body[:80])
        title = re.sub(r"(?<![\w.])\d{1,2}\s?\[", "", title).replace("[", "").replace("]", "").strip()
        if REPEAL_RE.search(probe) or (it["kind"] != "section" and len(body) < 60):
            dropped.add(it["id"])
            continue
        sid = it["id"]
        heading = f"{sid}. {title}" if it["kind"] == "section" else sid
        text = (heading + ".\u2014" + body if it["kind"] == "section" else body).strip()
        pages = sorted(it["pages"])
        page_notes, seen = [], set()
        for p in range(pages[0], pages[-1] + 1):
            for n in notes.get(p, []):
                if n not in seen:
                    seen.add(n); page_notes.append(n)
        clean = re.sub(r"(?<![\w.])\d{1,2}\s?\[", "", text).replace("[", "").replace("]", "")
        out.append({
            "node_id": f"{meta['jurisdiction']}:{meta.get('short') or meta['act']}:{sid}",
            "act": meta["act"], "act_short": meta.get("short"), "year": meta.get("year"),
            "jurisdiction": meta["jurisdiction"], "level": meta.get("level", "central"),
            "status": meta.get("status", "in_force"), "kind": it["kind"],
            "section_id": sid, "title": title, "text": text, "text_clean": clean,
            "pages": [pages[0], pages[-1]], "page_notes": page_notes[:12],
            "source_file": source_file, "domain": None,
            "oversized": it["kind"] == "schedule" and len(text) > 40000,
        })
    return out, dropped


def build(pdf_path: Path, meta: dict):
    body, notes, npages = extract_lines(str(pdf_path), meta.get("footnote_mode", "rule"),
                                        meta.get("extractor", "pymupdf"))
    body = clean_lines(body)
    start = find_body_start(body)
    toc_ids, toc_rep = parse_toc_ids(body[:start])
    items = split_sections(body[start:], toc_ids, meta.get("max_jump", 15))
    if meta.get("split_articles"):
        items = split_articles(items)
    entries, dropped = to_entries(items, notes, meta, pdf_path.name)
    got = {e["section_id"] for e in entries if e["kind"] == "section"}
    expected = toc_ids - toc_rep
    # A matching COUNT does not prove correct TEXT (footnotes numbered like real
    # sections once passed the count check), so also flag suspicious bodies.
    suspect = []
    for e in entries:
        if e["kind"] != "section":
            continue
        body = e["text"].split("\u2014", 1)[-1]
        if FOOT_VERB_RE.match(body) or len(body.strip()) < 40:
            suspect.append(e["section_id"])
    report = {"pages": npages, "toc_ids": len(toc_ids), "expected_live": len(expected),
              "suspect": suspect[:15], "omitted_in_body": sorted((d for d in dropped - toc_rep if d[:1].isdigit()), key=_key)[:15],
              "extracted": len(got), "missing": sorted(expected - got - dropped, key=_key),
              "extra": sorted(got - expected, key=_key) if toc_ids else [],
              "schedules": sum(e["kind"] == "schedule" for e in entries)}
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
        meta["processed_on"] = datetime.date.today().isoformat()
        json.dump(manifest, open(a.manifest, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
        print(f"{meta['file']:42s} sections={rep['extracted']:4d} expected={rep['expected_live']:4d} "
              f"sched={rep['schedules']:2d} missing={rep['missing'][:12]} extra={rep['extra'][:12]} suspect={rep['suspect']}")


if __name__ == "__main__":
    main()
