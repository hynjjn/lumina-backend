from typing import Annotated

from fastapi import APIRouter, Depends

from app.deps import current_user
from app.gemini import gloss_word
from app.models import User
from app.schemas import GlossIn, GlossOut

router = APIRouter(tags=["gloss"])


@router.post("/gloss", response_model=GlossOut)
async def gloss(
    body: GlossIn,
    user: Annotated[User, Depends(current_user)],  # noqa: ARG001 — auth gate
) -> GlossOut:
    """Look up an English word: returns learner-friendly EN definitions, a Korean
    translation, and example sentences. Optional `context` disambiguates words
    with multiple senses."""
    result = await gloss_word(body.word, body.context)
    return GlossOut(word=body.word, **result.model_dump())
