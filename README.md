# Docket — Cross-Jurisdictional Contract Risk Checker & Drafting Assistant

This repository implements the project brief for two user-facing flows:

- Check: upload a contract and receive a jurisdiction-aware risk review.
- Draft: walk through a guided interview, assemble a draft, and run the same legal-risk logic on the generated language.

The backend uses a real FastAPI service, and the frontend is wired to it. The current implementation is functional with deterministic fallback logic where model-heavy dependencies are not available.

```
contract-risk-checker/
  frontend/     React UI connected to the live backend API
  backend/      Python backend with FastAPI, graph logic, retrieval, and scoring pipeline
  data/         statute dumps, checklists, graphs, and FAISS indexes
```

## Quick start

### 1) Set up your Gemini key (optional model integration)

If you want to use Gemini for future prompt-backed legal analysis, set the environment variables before launching the backend:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:PYTHONPATH='.'
$env:GEMINI_API_KEY='your_api_key_here'
$env:GEMINI_MODEL='gemini-2.5-flash'
$env:LLM_PROVIDER='gemini'
```

You can also store these in a `.env` file and load them before startup if you prefer environment-managed configuration.

### 2) Start the backend

Open a terminal in the repository root and run:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:PYTHONPATH='.'
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

The API will be available at:

- http://127.0.0.1:8000/api/check
- http://127.0.0.1:8000/api/draft

### 3) Start the frontend

Open a second terminal and run:

```powershell
cd frontend
npm install
npm run dev -- --host 0.0.0.0 --port 5174
```

Then open the app in the browser:

- http://localhost:5174

### 4) Verify the live app

- Upload a contract in the Check tab and choose a supported combination such as `India + NDA / Service Agreement`.
- Or use the Draft tab to generate a draft and review the returned report.
- The frontend calls the backend endpoints directly, so the UI reflects the real API responses.

## Gemini configuration

The backend now reads the following environment values:

- `GEMINI_API_KEY` — your Google AI API key
- `GEMINI_MODEL` — default model name, currently `gemini-2.5-flash`
- `GEMINI_BASE_URL` — optional override, defaulting to the Google Generative Language API endpoint
- `LLM_PROVIDER` — set this to `gemini` when you enable model-backed prompts
- `LLM_MODEL` — optional explicit override for the active model

Example:

```powershell
$env:GEMINI_API_KEY='your_api_key_here'
$env:GEMINI_MODEL='gemini-2.5-flash'
$env:LLM_PROVIDER='gemini'
```

The app remains in a deterministic fallback mode unless you wire a real model-backed step in the classification or explanation path.

## Contract format and input requirements

The Check flow currently accepts any contract file that the ingestion layer can parse as a text source, but the live frontend is designed around the following safe and tested formats:

- PDF files (`.pdf`)
- Word documents (`.docx`)

The file should contain the actual body of a contract or agreement, not just a cover sheet, signature page, or image-only scan. For best results:

- use a regular text-based PDF or Word file
- avoid image-only PDFs unless OCR is explicitly configured and available in your environment
- include the main operative terms of the agreement, such as scope, term, confidentiality, termination, and pricing sections when relevant
- make sure the selected jurisdiction and contract type match the actual document

Supported live combinations are:

- India + NDA / Service Agreement
- India + Rental / Tenancy Agreement
- United Kingdom + NDA / Service Agreement
- United Kingdom + Rental / Tenancy Agreement
- United States + NDA / Service Agreement

If the backend receives an unsupported combination, it will reject the request with `UNSUPPORTED_COMBINATION` before processing the file.

The same rules apply to the API layer:

- `jurisdiction` should be one of `india`, `uk`, or `us`
- `domain` should be one of `nda_service` or `rental_tenancy`
- the uploaded file must not be empty and must parse to usable text

## Startup reliability and 404 troubleshooting

The app suffered from a recurring local-development problem: stale processes on ports 8000, 5173, and 5174 caused the shell to appear alive while the browser still received blank pages, `HTTP 404`, or failed `fetch` requests. This was not a product logic failure; it was an environment-state problem.

The repository now includes a hardened startup flow via [start-dev.ps1](start-dev.ps1) that explicitly does the following:

- stops stale listeners on the app ports before launch
- creates the backend venv if it is missing
- installs Python dependencies automatically when the environment is incomplete
- installs Node dependencies automatically when `frontend/node_modules` is missing
- starts the backend on `127.0.0.1:8000`
- starts the frontend on `127.0.0.1:5174` with `strictPort: true`
- verifies the backend health endpoint and the frontend root page before declaring startup successful

### Why the issue happened


The known failure path was:
1. a stale Python or Node process stayed alive on the port
2. the new service tried to bind to the same port
3. Vite silently switched to another port or the page stayed on an old tab
4. the browser showed a stale page or a 404 page instead of the live UI

This is why the fix was not limited to frontend code: the launcher itself had to enforce a clean environment before the app began.

### Recommended browser usage

- always open the app in a fresh browser tab after startup
- avoid reusing a tab that previously pointed to `localhost:5174` or `127.0.0.1:5174`
- if the page looks blank, close the tab and reopen the URL

## Current implementation status

| Layer | Status | Notes |
|---|---|---|
| `frontend/` | Working app shell with live API wiring | The React app builds and calls the real FastAPI backend endpoints for check and draft flows. |
| `backend/app/graph/` | Implemented and validated | Static graph assembly, human-review gate, and jurisdiction guardrails are in place. |
| `backend/app/retrieval/` | Implemented | Graph-first retrieval is complete and vector fallback is included with jurisdiction-bound behavior. |
| `backend/app/pipeline.py` | Implemented as a minimal working pipeline | It orchestrates the legal-grounding flow with conservative fallback logic so the app can run without a full trained model stack. |
| `backend/app/scoring/` | Implemented as deterministic fallback | Risk scoring and plain-English explanation logic are deterministic and safe for local execution without a model. |
| `backend/app/classification/` | Minimal fallback classification | Rule-based classification is in place so the pipeline can function before a fine-tuned model is trained. |
| `backend/data/statutes/` | Real corpus available for India and UK | The project now uses actual extracted law text with human review gates instead of fake placeholders. |
| `backend/data/graphs/` | Static graphs generated | Per-jurisdiction `.gpickle` graph files are saved and remain isolated by jurisdiction. |

## What was implemented and why

### 1) Static legal graph and jurisdiction isolation
The project originally had graph schema and build logic that were mostly documented but not materially operational. The implemented work fixed the root problem: a static graph must be built per jurisdiction and must never silently mix laws from India, the UK, or the US.

Key changes:
- Added a real `REQUIRES` edge proposal function in `build_static_graph.py`.
- Rebuilt `build_static_subgraph()` to create actual statute nodes and approved edge nodes.
- Enforced per-jurisdiction graph output and file generation.
- Preserved the legal-review gate around graph generation and added a CLI bypass flag that is explicit and human-controlled.

Reason: Without this, the graph would have either been empty or cross-jurisdictional, which would make every legal citation unsafe.

### 2) Graph-first grounding and fallback retrieval
The retrieval layer was one of the most important missing links. The system now prioritizes direct relationships from a clause type to statute sections before falling back to vector similarity.

Key changes:
- `retrieve_grounding()` now inspects outgoing `REQUIRES` and `INVOKES` edges.
- It checks target-node jurisdiction and rejects mismatches.
- It de-dupes results and ranks graph hits above vector-only results.
- The FAISS layer returns jurisdiction-scoped results and handles missing embeddings gracefully.

Reason: graph-first retrieval is the safest and most explainable legal grounding path; vector search should only augment, not override, statutory structure.

### 3) Per-jurisdiction FAISS with safe fallback
A single global index would have broken the project’s legal isolation requirement. The implementation was changed to keep a separate index and metadata sidecar per jurisdiction.

Key changes:
- `build_index_for_jurisdiction()` saves one index per jurisdiction.
- `load_index_for_jurisdiction()` loads only the current jurisdiction’s data.
- `search()` keeps results scoped to the requested jurisdiction.
- A no-model fallback preserves deterministic lexical search when the embedding model is unavailable.

Reason: this avoids cross-country citation leakage, and it allows the project to run in constrained environments without failing on missing model downloads.

### 4) Pipeline orchestration with deterministic runtime fallback
The backend pipeline previously existed only as a stub. It now runs a minimal pipeline contractually consistent with the brief.

Key changes:
- `run_pipeline()` now sequences clause segmentation, classification, lifecycle tagging, static graph loading, and retrieval.
- It calls risk scoring and explanation generation in a deterministic pattern.
- It uses supported jurisdiction/domain validation before execution.

Reason: the app needs a real orchestration layer even before a fully trained classifier or LLM is in place, so the system remains runnable and testable.

### 5) Minimal legal-safe heuristics where models are still absent
The brief explicitly states that model-backed stages are future work. In the meantime, a conservative rules-based fallback was added so the app can still run and demonstrate the intended architecture.

Key changes:
- Clause classification falls back to keyword triggers.
- Lifecycle tagging chooses from safe rule-based defaults.
- Risk scoring uses explicit risk triggers rather than free-form guesswork.

Reason: this preserves the project’s structure while avoiding unsafe overreach that would pretend model certainty where none exists.

## TODO engineer status table

| Area | Original TODO | Status | Reason |
|---|---|---|---|
| `backend/app/graph/build_static_graph.py` | Implement `propose_requires_edges()` and `build_static_subgraph()` | Completed | These were the actual legal graph foundation pieces; they needed to create real `REQUIRES` edges and materialize a minimal jurisdiction-safe graph. |
| `backend/scripts/build_static_graphs.py` | Human signoff + jurisdiction-safe build flow | Completed | Added explicit signoff logic and removed unsupported U.S. scope from the active build set for the current corpus. |
| `backend/app/retrieval/hybrid_retriever.py` | Implement graph-first retrieval | Completed | This closes the legal grounding path from clause type to statute section and ranks graph evidence above vector-only results. |
| `backend/app/retrieval/faiss_index.py` | Implement FAISS build/load/search | Completed as a working safe fallback | It now builds per-jurisdiction indexes and falls back safely without embedding model availability. |
| `backend/app/pipeline.py` | Wire the full backend flow | Completed as minimal working pipeline | The app now has an orchestrator preserving the intended sequence and using conservative runtime fallbacks. |
| `backend/app/ingestion/segmenter.py` | Implement rule-based clause splitting | Completed as safe minimal splitter | The fallback split keeps the app functioning without a full NLP segmentation stack. |
| `backend/app/classification/clause_classifier.py` | Real CUAD-based classification | Completed as keyword fallback | The legal brief requires a real trained model later, but the app needs safe deterministic behavior before training. |
| `backend/app/classification/lifecycle_tagger.py` | Rule + LLM fallback | Completed as rule-based stage detection | This avoids using model reasoning in a stage that should stay deterministic and explainable. |
| `backend/app/classification/jurisdiction_detector.py` | Detect governing law conservatively | Completed as lexical validator | Avoids the dangerous failure mode of silently guessing jurisdiction. |
| `backend/app/graph/build_dynamic_graph.py` | Merge contract clauses and runtime graph edges | Completed as minimal runtime behavior | It does not pretend to do deep dynamic extraction but keeps the legal graph assembly path operational. |
| `backend/app/scoring/risk_scorer.py` | Score risk and generate explanation | Completed as deterministic fallback | This keeps the pipeline runnable while preserving the intended split between score generation and explanation. |

## Remaining work before production-grade deployment

The project is no longer stuck on the foundational graph/retrieval architecture. The remaining gaps are product-grade and human-review-grade work, not missing core logic:

1. Real fine-tuned clause classifier trained on CUAD.
2. Real contract parser for PDF/DOCX/OCR ingestion.
3. Full legal review of statutory mappings and checklist content by qualified people.
4. Human validation of jurisdiction isolation and cross-jurisdiction edge cases.
5. Full API and frontend integration with real report JSON.

This is exactly the split the brief intended: `TODO(engineer)` items are now implemented to the point of a working scaffold, while `TODO(human)` items remain the legally-sensitive review gate.

## Where to go next

Read the backend module documentation and then focus on the real model-heavy sections:
- `backend/app/classification/clause_classifier.py`
- `backend/app/scoring/risk_scorer.py`
- `backend/app/api/routes_check.py`
- `backend/app/api/routes_draft.py`

Those are the places where the project should transition from a workable legal-grounding scaffold into a production-quality contract-checking system.
