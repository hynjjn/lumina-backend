"""Gemini wrapper for the gloss endpoint.

Single structured-output call returns EN learner-friendly definitions + a Korean
translation + example sentences. Context is used to disambiguate words with
multiple senses (e.g., "bank" near "river" vs "deposit").
"""

import asyncio

from fastapi import HTTPException, status
from google import genai
from google.genai import types
from pydantic import BaseModel

from app.config import settings


class GlossResult(BaseModel):
    part_of_speech: str
    definitions_en: list[str]
    definition_ko: str
    examples: list[str]


_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if not settings.gemini_api_key:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Gemini is not configured (set GEMINI_API_KEY in .env)",
        )
    if _client is None:
        _client = genai.Client(api_key=settings.gemini_api_key)
    return _client


def _build_gloss_prompt(word: str, context: str | None) -> str:
    lines = [
        "You are a dictionary for English-language learners.",
        f'Define the English word: "{word}"',
    ]
    if context:
        lines.append(
            f'Context (use this to disambiguate the intended sense): "{context}"'
        )
    lines.extend(
        [
            "Use simple, learner-friendly wording (Longman-style).",
            "definitions_en: 1–3 short English definitions, most common sense first.",
            "definition_ko: a single natural Korean translation (한국어 번역).",
            "examples: 1–2 short example sentences using the word in this sense.",
            "part_of_speech: e.g., 'noun', 'verb', 'adjective' (add register if useful, e.g., 'noun, formal').",
        ]
    )
    return "\n".join(lines)


async def gloss_word(word: str, context: str | None = None) -> GlossResult:
    client = _get_client()
    try:
        resp = await asyncio.to_thread(
            client.models.generate_content,
            model=settings.gemini_model,
            contents=_build_gloss_prompt(word, context),
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=GlossResult,
            ),
        )
    except Exception as e:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            f"Gemini call failed: {type(e).__name__}: {e}",
        ) from e

    parsed = resp.parsed
    if isinstance(parsed, GlossResult):
        return parsed
    # Fallback: SDK didn't auto-parse — try raw JSON
    try:
        return GlossResult.model_validate_json(resp.text)
    except Exception as e:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            f"Could not parse Gemini response: {e}",
        ) from e
