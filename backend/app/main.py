from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes_check import router as check_router
from app.api.routes_draft import router as draft_router

app = FastAPI(title="Docket — Contract Risk Checker API")

# TODO(engineer): lock this down before anything beyond local dev.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(check_router)
app.include_router(draft_router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
