from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import current_user
from app.models import Article, User, WordbookEntry
from app.schemas import WordbookEntryIn, WordbookEntryOut

router = APIRouter(prefix="/wordbook", tags=["wordbook"])


async def _owned(
    entry_id: str, user: User, session: AsyncSession
) -> WordbookEntry:
    entry = await session.get(WordbookEntry, entry_id)
    if entry is None or entry.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Wordbook entry not found")
    return entry


@router.post("", response_model=WordbookEntryOut, status_code=status.HTTP_201_CREATED)
async def create_entry(
    body: WordbookEntryIn,
    user: Annotated[User, Depends(current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> WordbookEntryOut:
    if body.article_id is not None:
        article = await session.get(Article, body.article_id)
        if article is None or article.user_id != user.id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "article_id does not belong to user")

    entry = WordbookEntry(
        user_id=user.id,
        article_id=body.article_id,
        word=body.word,
        context=body.context,
        definition_en=body.definition_en,
        definition_ko=body.definition_ko,
    )
    session.add(entry)
    await session.commit()
    await session.refresh(entry)
    return WordbookEntryOut.model_validate(entry)


@router.get("", response_model=list[WordbookEntryOut])
async def list_entries(
    user: Annotated[User, Depends(current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[WordbookEntryOut]:
    rows = await session.scalars(
        select(WordbookEntry)
        .where(WordbookEntry.user_id == user.id)
        .order_by(WordbookEntry.created_at.desc())
    )
    return [WordbookEntryOut.model_validate(e) for e in rows]


@router.get("/{entry_id}", response_model=WordbookEntryOut)
async def get_entry(
    entry_id: str,
    user: Annotated[User, Depends(current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> WordbookEntryOut:
    return WordbookEntryOut.model_validate(await _owned(entry_id, user, session))


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_entry(
    entry_id: str,
    user: Annotated[User, Depends(current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> None:
    entry = await _owned(entry_id, user, session)
    await session.delete(entry)
    await session.commit()
