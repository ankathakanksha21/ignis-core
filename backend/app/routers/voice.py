"""The voice guide: a spoken explanation of one page, which the listener can interrupt."""

import urllib.error
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, ValidationError

from .. import voice

router = APIRouter(prefix="/voice", tags=["voice"])


Kind = Literal["investigation", "compare", "rank", "gaps", "prediction", "lab", "similar"]


class ExplainRequest(BaseModel):
    kind: Kind
    # What the page is showing, in the same names the page's own request uses.
    params: dict = {}


class Turn(BaseModel):
    role: Literal["agent", "user"]
    text: str = Field(max_length=1200)


class AnswerRequest(ExplainRequest):
    question: str = Field(min_length=2, max_length=400)
    # What was said before, so "and the second one?" can be understood.
    history: list[Turn] = Field(default=[], max_length=12)


@router.post("/explain")
def explain(body: ExplainRequest) -> dict:
    try:
        return voice.explain(body.kind, body.params)
    except (KeyError, StopIteration) as error:
        raise HTTPException(404, f"Nothing to explain: {error}") from error
    except (ValueError, TypeError, ValidationError) as error:
        raise HTTPException(422, f"Cannot explain that: {error}") from error


@router.post("/answer")
def answer(body: AnswerRequest) -> dict:
    """A typed question about the page, answered from its facts and checked before it is read aloud."""
    try:
        return voice.answer(body.kind, body.params, body.question.strip(), [turn.model_dump() for turn in body.history])
    except (KeyError, StopIteration) as error:
        raise HTTPException(404, f"Nothing to explain: {error}") from error
    except RuntimeError as error:  # the key is not set
        raise HTTPException(503, f"The language model is not set up. {error}") from error
    except (urllib.error.URLError, TimeoutError) as error:
        raise HTTPException(502, "The language model did not answer. Try again.") from error
    except (ValueError, TypeError, ValidationError) as error:
        raise HTTPException(422, f"Cannot answer that: {error}") from error
