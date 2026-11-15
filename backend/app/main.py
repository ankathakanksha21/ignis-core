"""Application entry point.

Every feature has its own router file under routers/, registered here.

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
