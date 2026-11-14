# India statute sources (Section 4, Phase A)

All files below were extracted from the source PDFs by
`scripts/extract_statute_sections.py`, driven by `data/statutes/sources_india.json`
(which also records each PDF's SHA-256 and the processing date).

| Act | Level | Status | Sections | Schedule Articles | Other schedules | File |
|---|---|---|---|---|---|---|
| Arbitration and Conciliation Act, 1996 | central | in_force | 106 | 0 | 7 | `arbitration_conciliation_act_1996.json` |
| Consumer Protection Act, 2019 | central | in_force | 107 | 0 | 0 | `consumer_protection_act_2019.json` |
| Digital Personal Data Protection Act, 2023 | central | in_force | 44 | 0 | 1 | `dpdp_act_2023.json` |
| Indian Contract Act, 1872 | central | in_force | 192 | 0 | 0 | `indian_contract_act_1872.json` |
| Indian Stamp Act, 1899 | central | in_force | 95 | 0 | 4 | `indian_stamp_act_1899.json` |
| Information Technology Act, 2000 | central | in_force | 109 | 0 | 2 | `information_technology_act_2000.json` |
| Karnataka Rent Act, 1999 | state:karnataka | in_force | 70 | 0 | 4 | `karnataka_rent_act_1999.json` |
| Karnataka Stamp Act, 1957 | state:karnataka | in_force | 85 | 52 | 0 | `karnataka_stamp_act_1957.json` |
| Limitation Act, 1963 | central | in_force | 30 | 136 | 0 | `limitation_act_1963.json` |
| Registration Act, 1908 | central | in_force | 90 | 0 | 0 | `registration_act_1908.json` |
| Specific Relief Act, 1963 | central | in_force | 46 | 0 | 1 | `specific_relief_act_1963.json` |
| Transfer of Property Act, 1882 | central | in_force | 135 | 0 | 1 | `transfer_of_property_act_1882.json` |
| Model Tenancy Act, 2021 | central_model | model_act | 47 | 0 | 2 | `model_not_in_force/model_tenancy_act_2021.json` |
| Model Tenancy Rules (state template, placeholders) | central_model | model_template | 14 | 0 | 7 | `model_not_in_force/model_tenancy_rules_template.json` |

Sections are reconciled against each Act's own "Arrangement of Sections". Files in
`model_not_in_force/` are templates or model laws, **not** law in force, and the loader
(`app.graph.build_static_graph.load_statute_text`) deliberately does not load them.

## Re-running / adding an Act

1. Add an entry to `sources_india.json` (act name, short code, level, `footnote_mode`).
2. `python scripts/extract_statute_sections.py --manifest data/statutes/sources_india.json --pdf-dir <pdfs> --out-dir data/statutes/india`
3. Read the printed report: `missing`, `extra` and `suspect` must all be empty (or explained).
4. `pytest tests/test_statute_data.py`. A matching section COUNT is not enough: on the
   Karnataka Stamp Act, footnotes such as "11. Inserted by Act 7 of 2016" were once accepted
   as sections 10-18, so the count matched while the text was wrong.

`footnote_mode`: `rule` (India Code PDFs: footnotes under a short separator line), `inline`
(Karnataka Stamp Act: footnotes printed between sections), `none`. `extractor: pdftotext` is
used for the Karnataka Rent Act because PyMuPDF cannot decode that PDF's fonts.

## Known limitations (read before relying on the data)

- **Not legally verified.** Extraction quality is checked mechanically. Section wording was
  spot-checked, not read end to end. TODO(human): have someone with legal training read a sample.
- **Karnataka Stamp Act:** sections 11, 12 and 60 are `[X X X]` (omitted) in the body and are
  intentionally absent.
- **Oversized Schedules are not loaded:** the central Indian Stamp Act's Schedule I (with every
  state's amendments, ~500k characters) is stored but flagged `oversized`. Use the Karnataka
  Stamp Act Articles (e.g. Article 30 lease, Article 5 agreement) for Karnataka.
- **Schedule tables are text, not structured:** each Article keeps its description, rate and
  starting-point text, but columns are not parsed and an Article can end with the next page's
  table header ("Description of suit ...").
- **Karnataka Rent Act:** the Second and Third Schedules are merged into one entry.
- **`page_notes`** hold the footnotes (amendment history) of the *pages* a section spans, not of
  the section alone. They are raw material for AMENDED_BY edges and must be reviewed by a human.
- **State amendments** (e.g. Uttar Pradesh) appear inline in the central Acts. Decide whether
  they belong in a national graph.
- **Currency:** these are point-in-time PDFs. TODO(human): fill `date_downloaded` in the manifest and
  confirm each is the current consolidated text (the Karnataka Rent Act copy carries a 2001 gazette
  note and may not include later amendments).
- **`model_tenancy_rules_template.json`** comes from a scanned PDF with OCR errors (e.g. the form
  "FORM-IB" is read as "FORM-18"). It is a state-rules template with placeholders.
- **`domain` is `null` everywhere.** Mapping sections to NDA/Service vs Rental/Tenancy is the
  human-reviewed step (Section 7, item 1).
