# UK statute sources (Section 4, Phase A)

All files below were extracted from legislation.gov.uk PDFs by
`scripts/extract_statute_sections_uk.py`, driven by `data/statutes/sources_uk.json`
(which also records each PDF's SHA-256 and the processing date).

| Act | Short | Year | Sections | Schedules | File |
|---|---|---|---|---|---|
| Consumer Rights Act 2015 | CRA | 2015 | 101 | 10 | `consumer_rights_act_2015.json` |
| Digital Markets, Competition and Consumers Act 2024 | DMCC | 2024 | 313 | 31 | `digital_markets_competition_consumers_act_2024.json` |
| Homes (Fitness for Human Habitation) Act 2018 | HFHHA | 2018 | 2 | 0 | `homes_fitness_for_human_habitation_act_2018.json` |
| Housing Act 1988 | HA1988 | 1988 | 137 | 17 | `housing_act_1988.json` |
| Housing Act 2004 | HA2004 | 2004 | 270 | 16 | `housing_act_2004.json` |
| Landlord and Tenant Act 1985 | LTA | 1985 | 60 | 1 | `landlord_and_tenant_act_1985.json` |
| Late Payment of Commercial Debts (Interest) Act 1998 | LPCDIA | 1998 | 19 | 0 | `late_payment_of_commercial_debts_interest_act_1998.json` |
| Misrepresentation Act 1967 | MA | 1967 | 5 | 0 | `misrepresentation_act_1967.json` |
| Protection from Eviction Act 1977 | PEA | 1977 | 16 | 4 | `protection_from_eviction_act_1977.json` |
| Public Interest Disclosure Act 1998 | PIDA | 1998 | 15 | 0 | `public_interest_disclosure_act_1998.json` |
| Renters' Rights Act 2025 | RRA | 2025 | 130 | 6 | `renters_rights_act_2025.json` |
| Supply of Goods and Services Act 1982 | SGSA | 1982 | 27 | 1 | `supply_of_goods_and_services_act_1982.json` |
| Tenant Fees Act 2019 | TFA | 2019 | 37 | 3 | `tenant_fees_act_2019.json` |
| (no sections extracted) |  |  | 0 | 0 | `trade_secrets_regulations_2018.json` |
| Unfair Contract Terms Act 1977 | UCTA | 1977 | 20 | 0 | `unfair_contract_terms_act_1977.json` |

## Why this is a separate extractor from India's

legislation.gov.uk PDFs are structurally different from India Code PDFs, not just
messier in the same way, so `extract_statute_sections.py` (India) was not reused:

- **No table of contents.** India Code prints an "Arrangement of Sections" that
  acted as a whitelist to validate extraction against. These PDFs have none, so
  validation here relies on strict monotonic section numbering plus the specific
  regression tests in `tests/test_statute_data_uk.py`, not a count-against-TOC check.
- **Id and title are separate, isolated bold lines** (e.g. a line containing only
  `"1"`, then a line containing only the title), not `"1. Title.\u2014body"` on one
  line. Cleaner once recognised, but a fundamentally different parse.
- **Every page repeats an 8pt "Changes to legislation" / status footer** &mdash; a
  reliable, simple filter (drop everything at exactly that font size).
- **Inserted sections/subsections carry a glued amendment marker** with no
  separator, e.g. `"[F23"` for inserted section "3" (marker "F2" + id "3"), or
  `"[F42A"` for inserted section "2A" (marker "F4" + id "2A"). Resolved the same way
  as India's "1151" glued-digit problem: try every split, keep the one consistent
  with the expected next section number.
- **A quoted section number belonging to the Act being amended can appear inside
  another section's body.** The Homes (Fitness for Human Habitation) Act 2018 has
  only 2 real sections; its section 1 quotes new sections "9A"/"9B"/"9C" that it
  inserts into the Landlord and Tenant Act 1985. These are reliably excluded because
  a genuine section-id line is isolated (nothing else on it) and sits at the
  document's left margin; the quoted ones are indented and share their line with
  title text.

## Bugs found and fixed while building this data (see tests for the regression coverage)

1. **Bare page numbers ate the section-id lines.** A section's id ("1", "2") is also
   just a bare digit, indistinguishable from a page number by text alone. Fixed by
   only filtering bare digits when NOT bold (page numbers are never bold here).
2. **Footnote reference codes falsely matched the id pattern.** "Textual Amendments"
   lists plain codes like `"F1"`, `"F23"` with no brackets, which the amendment-marker
   regex can also parse as a section id. A large Act can have far more of these than
   real sections, which silently dragged the left-margin detector onto the wrong
   column. Fixed by restricting margin detection (and id-line detection) to
   body-sized (11pt) text; the reference codes are printed at 9pt.
3. **Ambiguous glued markers were accepted even when no split fit**, producing wrong
   ids like `"0B"` for what was actually section `"20B"`, because the acceptance
   test only allowed "exactly next number", not "same number, new letter". Broadened
   to accept same-or-next major number, and made the resolver return `None` (treat
   as noise) rather than guess when truly nothing fits — this is what caught an
   inline footnote mark ("F190") that very nearly became a fake section "0".
4. **Schedule headings aren't always bold**, unlike section headings, so requiring
   boldness excluded genuine `"SCHEDULE 1"` headings in some Acts.
5. **The Schedule-heading regex was case-insensitive**, so it matched ordinary
   lowercase in-body cross-references ("Schedule 5 (application to bread) is
   amended...") as if they started a new Schedule, truncating real Schedules to a
   few hundred characters. Fixed by requiring the all-caps form.
6. **A `"PART 1"` heading inside a Schedule closed the Schedule early**, same class
   of bug as India's Chapter-heading bleed. Fixed by only treating Part/Chapter
   headings as boundaries when not already inside a Schedule.
7. **The worst one: once a "Commencement Information"/"Textual Amendments" notes
   block appeared anywhere mid-section or mid-schedule, the parser never switched
   back out of "notes" mode**, silently diverting all later real body text (for the
   rest of that section or schedule) into the discarded notes list instead of the
   returned text. This affected most multi-paragraph Schedules (e.g. Consumer
   Rights Act Schedule 4 was truncated to ~480 characters, actually ~10,500) and any
   section with notes before its final subsections. Fixed by resuming "body" mode
   as soon as body-sized (11pt) text reappears.

## Known limitations (read before relying on this data)

- **Not legally verified.** As with India, extraction quality is checked
  mechanically and spot-checked, not read end to end by a person. TODO(human):
  Section 7, item 1.
- **Trade Secrets (Enforcement, etc.) Regulations 2018 is not extracted at all**
  (`trade_secrets_regulations_2018.json` is an empty list). It's a Statutory
  Instrument with a different layout again (regulation number and title combined
  on one bold line, e.g. `"1.\u2014(1) These Regulations may be cited..."`), which
  this extractor doesn't yet handle. It's a short document (8 regulations); a
  human can transcribe it faster than it would take to write a third extractor.
- **Housing Act 1988 sections 19 and 20 are missing.** Confirmed to exist with real
  content in the source (s.20 is the well-known "assured shorthold tenancy"
  provision) but not recognised due to a rare PDF text-run merge around an inline
  footnote marker. See `test_known_extraction_gap_housing_act_1988_s19_s20`.
- **Large numbering gaps elsewhere are genuine, not extraction misses** &mdash;
  specifically checked by directly inspecting the source for Housing Act 1988
  (46-51), Renters' Rights Act 2025 (69-73), and the DMCC Act 2024 (259-266,
  268-276): no candidate heading exists at all in those ranges, meaning the
  consolidated in-force text itself has fully removed those repealed sections
  rather than leaving a "[Repealed]" stub the way India Code does.
- **Schedules are stored as one text blob per Schedule**, not split into numbered
  paragraphs the way India's Limitation Act Schedule was split into Articles.
  Several Schedules exceed 40,000 characters and are flagged `"oversized"` (the
  loader skips these by default): Consumer Rights Act Schedule 5
  (~104,500 characters), and large consequential-amendment schedules in the
  Housing Acts and DMCC Act.
- **A `"PART 1"` (etc.) heading inside a retained Schedule is kept as plain text**
  within that Schedule's body — it is not parsed into separate Part-level entries.
- **`uk-consumer-rights-2015.pdf` was a byte-identical duplicate** of
  `uk-consumer-rights.pdf` (confirmed by SHA-256) and was not processed separately.
- **Currency:** point-in-time PDFs. TODO(human): fill `date_downloaded` in the
  manifest and confirm each is the current consolidated text — the Renters' Rights
  Act 2025 in particular is recent and may already have further amendments.
- **`domain` is `null` everywhere.** Mapping sections to NDA/Service vs
  Rental/Tenancy is the human-reviewed step (Section 7, item 1).
