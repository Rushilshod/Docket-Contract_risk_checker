# Docket backend

This backend implements the legal-risk workflow described in the project brief but with the engineering foundation now materially in place. The important change is that the project is no longer just a collection of stubs: the core graph, retrieval, and pipeline mechanics are now functionally wired up with safety checks and deterministic runtime fallbacks.

## Run

```bash
pip install -r requirements.txt
cd backend
PYTHONPATH=. uvicorn app.main:app --reload
```

## Module map and current state

```text
data/statutes/india/README.md and data/statutes/uk/README.md document the extracted law texts and their legal caveats.

app/
  config.py                    locked-scope constants, model names, and paths
  ingestion/
    parser.py                   PDF/DOCX/OCR parser stub for future production use
    segmenter.py                 working minimal clause splitter with safe fallback
  classification/
    clause_classifier.py         keyword-based classifier fallback until the fine-tuned model exists
    deal_type_classifier.py       future classification hook for NDA vs tenancy domain logic
    jurisdiction_detector.py      conservative jurisdiction pattern matcher
    lifecycle_tagger.py           rule-based lifecycle assignment with safe defaults
  graph/
    schema.py                    node/edge types and jurisdiction-sensitive edge rules
    build_static_graph.py         offline static graph builder with real `REQUIRES` mapping and approval flow
    build_dynamic_graph.py        runtime graph merge for contract clauses and dynamic edges
    validation.py                 jurisdiction isolation validation guard
  retrieval/
    faiss_index.py                per-jurisdiction index builder and safe lexical fallback
    hybrid_retriever.py           graph-first + vector retrieval with de-duping and jurisdiction checks
  scoring/
    missing_clause_checker.py     checklist-based missing clause detection
    risk_scorer.py                 deterministic risk scoring and plain-English explanation fallback
  drafting/
    clause_bank.py                 future drafting templates and bank logic
  api/
    routes_check.py               check endpoint hook
    routes_draft.py                draft endpoint hook
  pipeline.py                    working minimal pipeline orchestration
  main.py                        FastAPI app

data/
  statutes/<jurisdiction>/        extracted law corpora for the supported jurisdictions
  checklists/                     reviewable jurisdiction x domain checklists
  clause_bank/                    drafting templates and reusable clause records
  graphs/                         generated per-jurisdiction `.gpickle` files
  faiss_indexes/                  generated per-jurisdiction indexes

eval/
  run_eval.py                    future precision/recall and laziness tests
  ablation_vector_vs_hybrid.py    future vector-vs-hybrid comparison

scripts/
  build_static_graphs.py         offline static graph build with human review gate

tests/
  test_jurisdiction_isolation.py  automated guardrail tests
  test_pipeline_and_faiss.py      focused runtime regression for the implemented path
```

## What changed in engineering terms

### 1) The static graph is now real and reviewable
The static graph step was a critical missing foundation. It now loads actual statute JSON, builds per-jurisdiction `StatuteSection` nodes, creates source nodes for the approved clause/deal types, and adds edges with explicit jurisdiction metadata.

This was required because the legal system depends on citeable source material that is always scoped to the correct jurisdiction.

### 2) Cross-jurisdiction leakage is now blocked by design
The graph schema and validation layer enforce strict jurisdiction checks for sensitive edge types: `REQUIRES`, `INVOKES`, and `AMENDED_BY`.

This was a safety fix, not just a cleanup: if the graph can silently cite Indian law in a UK contract, the tool becomes unsafe.

### 3) Retrieval is graph-first instead of vector-only
The hybrid retriever now prefers direct graph edges out of a clause type before considering vector results. This matters because legal grounding should be traceable to a statute section, not just a similarity score.

### 4) FAISS is now per-jurisdiction and safe in constrained environments
The FAISS index builder/store was implemented so each jurisdiction gets its own index and metadata sidecar. When the embedding model is unavailable, the system falls back to lexical similarity rather than crashing.

This gives the project a practical local execution path without sacrificing the legal isolation requirement.

### 5) The pipeline runs with deterministic fallback logic
The orchestration layer is now implemented at a minimal but working level. It sequences clause segmentation, classification, lifecycle tagging, grounding, and scoring in the same flow the API is meant to use.

This gives product teams a runnable architecture even before the fully trained legal model stack is available.

## TODO engineer status matrix

| Area | Original task | Status | Reason |
|---|---|---|---|
| `app/graph/build_static_graph.py` | Fill `propose_requires_edges()` and `build_static_subgraph()` | Completed | The legal graph is now materially assembled from the statute corpus and type-safe edges. |
| `scripts/build_static_graphs.py` | Add human-review signoff and jurisdiction-safe build process | Completed | The build is gated and remains scoped to the supported corpora instead of running on unsupported or merged jurisdictions. |
| `app/retrieval/hybrid_retriever.py` | Implement graph-first retrieval | Completed | This path is now the actual grounding engine the project was missing. |
| `app/retrieval/faiss_index.py` | Build/load/search logic for per-jurisdiction indexes | Completed with safe fallback | It adds a real retrieval path and remains safe when no embedding model is present. |
| `app/pipeline.py` | Wire the backend stages together | Completed as minimal runnable pipeline | It now orchestrates the intended stage flow without pretending that the full model stack is already trained. |
| `app/ingestion/segmenter.py` | Implement clause segmentation | Completed as minimal splitter | It is enough for local execution while the full NLP parser is still future work. |
| `app/classification/clause_classifier.py` | Real clause classification | Completed as conservative fallback | A proper fine-tuned model is still future work; the program now has a safe placeholder strategy. |
| `app/classification/lifecycle_tagger.py` | Rule + LLM fallback | Completed as rule-based version | This keeps lifecycle assignment deterministic and avoids making unsupported LLM assumptions. |
| `app/classification/jurisdiction_detector.py` | Conservative jurisdiction detection | Completed as lexical-only detector | It avoids silently guessing jurisdiction and enforces a safer user-review fallback. |
| `app/graph/build_dynamic_graph.py` | Runtime contract graph assembly | Completed as minimal implementation | It adds runtime node/edge assembly without claiming to have full contract-graph extraction from an LLM. |
| `app/scoring/risk_scorer.py` | Real risk scoring and explanation | Completed as deterministic fallback | This keeps the app runnable and explainable while the full LLM-based scoring layer is still future work. |

## TODO human vs TODO engineer distinction

- `TODO(engineer)` means code implementation work. Most of the core engineering gaps are now addressed.
- `TODO(human)` means legal review or judgment that cannot be delegated to a model or script.

The critical `TODO(human)` items remain:

- verifying the statute-to-clause mappings and legal interpretation,
- review of checklists and clause-bank content,
- signing off on the real legal policies behind each requirement,
- confirming that jurisdictional assumptions align with the relevant law.

This separation matters because the brief specifically requires legal subject-matter review before treating any mapping as authoritative.

## Suggested next build priorities

1. replace the conservative classifier with a trained CUAD-backed clause model,
2. replace the minimal risk scoring fallback with a real model-driven scoring pipeline,
3. finish the real API response shape for the frontend,
4. run a formal jurisdiction-isolation and legal-evidence review before production deployment.

At this stage, the project has crossed the threshold from “just stubs” into a real legal-graph backend foundation with a functioning local execution path.
