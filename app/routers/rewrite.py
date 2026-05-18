from typing import Annotated

from fastapi import APIRouter, Depends

from app.deps import current_user
from app.models import User
from app.schemas import RewriteIn, RewriteOut

router = APIRouter(tags=["rewrite"])


@router.post("/rewrite", response_model=RewriteOut)
async def rewrite(
    body: RewriteIn,
    user: Annotated[User, Depends(current_user)],  # noqa: ARG001 — auth gate
) -> RewriteOut:
    # TODO: call Gemini 3 Flash with a level-parameterized prompt built from the rubric.
    return RewriteOut(rewritten=body.text, level=body.level)
