"""6.5 Question answering over retrieved records, with a citation on every sentence."""

from fastapi import APIRouter

router = APIRouter(prefix="/qa", tags=["qa"])
