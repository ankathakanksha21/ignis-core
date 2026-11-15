"""6.5 Question answering over retrieved records, with a citation on every sentence."""

import urllib.error

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .. import qa

router = APIRouter(prefix="/qa", tags=["qa"])


class Question(BaseModel):
    question: str = Field(min_length=3, max_length=400)


@router.post("/ask")
def ask(body: Question) -> dict:
    try:
        return qa.ask(body.question.strip())
    except RuntimeError as error:  # the key is not set
        raise HTTPException(503, f"The language model is not set up. {error}") from error
    except (urllib.error.URLError, TimeoutError) as error:
        raise HTTPException(502, "The language model did not answer. Try again.") from error
