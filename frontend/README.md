# Docket — Contract Risk Checker & Drafting Assistant (frontend)

This is the **React frontend** for the two-tab tool described in the project
brief: **Check** (upload → risk report) and **Draft** (guided interview →
generated draft → risk report on that draft).

## Run it

From this folder:

```powershell
npm install
npm run dev -- --host 0.0.0.0 --port 5174
```

Then open:

```text
http://localhost:5174
```

## Backend dependency

This frontend is wired to the live backend API in the repo. Start the backend first:

```powershell
cd ..\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:PYTHONPATH='.'
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

The frontend will call:

- POST http://127.0.0.1:8000/api/check
- POST http://127.0.0.1:8000/api/draft

## What this delivers

This build implements the live UI for the full contract-risk workflow and it is
wired to the backend API for both the Check and Draft flows.

The frontend does not contain fallback sample reports or mock data for the active
workflow. It calls the real FastAPI endpoints, validates supported
jurisdiction/domain combinations, and renders the backend-generated analysis.

The backend remains responsible for legal grounding, retrieval, and risk scoring;
this UI is only the interaction layer.

## File map

```
src/
  App.jsx                 tab shell (Check / Draft)
  index.css               design tokens + all styling
  api/client.js            real backend API client for check + draft
  data/realOptions.js      live supported jurisdictions/domain options
  components/
    CheckTab.jsx            upload + jurisdiction/domain picker
    DraftTab.jsx             guided interview + draft generation
    ResultView.jsx           shared risk report (used by both tabs)
    PipelineStatus.jsx       5-stage progress indicator
```

## Before any real person uses a live version of this

Per Section 7 of the brief: get statute-to-clause mappings verified by
someone with legal training, verify jurisdiction isolation manually, and
review all disclaimer language — the "have a lawyer review" prompt here
is wired up but its prominence should be user-tested, not assumed.
