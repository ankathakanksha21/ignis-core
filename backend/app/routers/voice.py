"""The voice guide: a spoken explanation of one page, which the listener can interrupt."""

from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ValidationError

from .. import voice

router = APIRouter(prefix="/voice", tags=["voice"])


class ExplainRequest(BaseModel):
    kind: Literal["investigation", "compare", "rank", "gaps", "prediction", "lab", "similar"]
    # What the page is showing, in the same names the page's own request uses.
    params: dict = {}


@router.post("/explain")
def explain(body: ExplainRequest) -> dict:
    try:
        return voice.explain(body.kind, body.params)
    except (KeyError, StopIteration) as error:
        raise HTTPException(404, f"Nothing to explain: {error}") from error
    except (ValueError, TypeError, ValidationError) as error:
        raise HTTPException(422, f"Cannot explain that: {error}") from error
