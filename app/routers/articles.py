from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import current_user
from app.extract import fetch_and_extract
from app.models import Article, User
from app.schemas import ArticleImportIn, ArticleIn, ArticleOut

router = APIRouter(prefix="/articles", tags=["articles"])


async def _owned(
    article_id: str, user: User, session: AsyncSession
) -> Article:
    article = await session.get(Article, article_id)
    if article is None or article.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Article not found")
    return article


@router.post("", response_model=ArticleOut, status_code=status.HTTP_201_CREATED)
async def create_article(
    body: ArticleIn,
    user: Annotated[User, Depends(current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ArticleOut:
    article = Article(
        user_id=user.id,
        title=body.title,
        source_url=body.source_url,
        content=body.content,
    )
    session.add(article)
    await session.commit()
    await session.refresh(article)
    return ArticleOut.model_validate(article)


@router.post("/import", response_model=ArticleOut, status_code=status.HTTP_201_CREATED)
async def import_article(
    body: ArticleImportIn,
    user: Annotated[User, Depends(current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ArticleOut:
    """Fetch a URL, extract main content via trafilatura, save to reading list."""
    url = str(body.url)
    title, content = await fetch_and_extract(url)
    article = Article(user_id=user.id, title=title, source_url=url, content=content)
    session.add(article)
    await session.commit()
    await session.refresh(article)
    return ArticleOut.model_validate(article)


@router.get("", response_model=list[ArticleOut])
async def list_articles(
    user: Annotated[User, Depends(current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[ArticleOut]:
    rows = await session.scalars(
        select(Article)
        .where(Article.user_id == user.id)
        .order_by(Article.created_at.desc())
    )
    return [ArticleOut.model_validate(a) for a in rows]


@router.get("/{article_id}", response_model=ArticleOut)
async def get_article(
    article_id: str,
    user: Annotated[User, Depends(current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ArticleOut:
    return ArticleOut.model_validate(await _owned(article_id, user, session))


@router.delete("/{article_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_article(
    article_id: str,
    user: Annotated[User, Depends(current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> None:
    article = await _owned(article_id, user, session)
    await session.delete(article)
    await session.commit()
