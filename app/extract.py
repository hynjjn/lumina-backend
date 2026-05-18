"""URL fetch + main-content extraction.

Used by POST /articles/import. Includes a basic SSRF guard: only http(s),
and the host's resolved IPs must all be public.

Known gap (MVP): we check the *initial* host. If a 30x redirects to an
internal address, httpx will follow it. Harden later by disabling redirects
and re-validating each hop, or by using a proxy.
"""

import asyncio
import ipaddress
import json
import socket
from urllib.parse import urlparse

import httpx
import trafilatura
from fastapi import HTTPException, status

UA = "Mozilla/5.0 (compatible; LuminaBot/0.1)"


async def _ensure_safe_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Only http(s) URLs allowed")
    host = parsed.hostname
    if not host:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid URL host")

    loop = asyncio.get_running_loop()
    try:
        addrs = await loop.getaddrinfo(host, None)
    except socket.gaierror as e:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, f"Could not resolve host: {e}"
        ) from e

    for *_, sockaddr in addrs:
        ip = ipaddress.ip_address(sockaddr[0])
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        ):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "URL resolves to a private/internal address",
            )


async def fetch_and_extract(url: str) -> tuple[str, str]:
    """Fetch a URL and return (title, cleaned_text)."""
    await _ensure_safe_url(url)

    try:
        async with httpx.AsyncClient(
            timeout=15.0, follow_redirects=True, headers={"User-Agent": UA}
        ) as client:
            resp = await client.get(url)
    except httpx.HTTPError as e:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"Fetch failed: {e}") from e

    if resp.status_code != 200:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY, f"Source returned {resp.status_code}"
        )

    # trafilatura.extract is CPU-bound (lxml parsing) — run off the event loop.
    extracted = await asyncio.to_thread(
        trafilatura.extract,
        resp.text,
        output_format="json",
        with_metadata=True,
    )
    if not extracted:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "Could not extract main content"
        )

    data = json.loads(extracted)
    title = data.get("title") or "Untitled"
    text = (data.get("text") or "").strip()
    if not text:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "Extracted content was empty"
        )
    return title, text
