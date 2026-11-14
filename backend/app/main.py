"""Application entry point.

Every feature's router is already registered here, so feature work happens
inside the feature's own router file and this file should not need editing.

    uvicorn app.main:app --reload --port 8000      (run from backend/)
"""

from fastapi import FastAPI

from ignis_ml import CONTRACT_VERSION

from .routers import atmospheres, investigations, lab, predict, qa

app = FastAPI(title="Flame in Freefall", version="0.1.0")


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "contract_version": CONTRACT_VERSION}


for module in (investigations, atmospheres, predict, lab, qa):
    app.include_router(module.router, prefix="/api")
