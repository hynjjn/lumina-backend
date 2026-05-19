"""URL fetch + main-content extraction.

Used by POST /articles/import. Includes a basic SSRF guard: only http(s),
and the host's resolved IPs must all be public.

Known gap (MVP): we check the *initial* host. If a 30x redirects to an
internal address, httpx will follow it. Harden later by disabling redirects
and re-validating each hop, or by using a proxy.
"""

import asyncio
import ipaddress
import re
import socket
from urllib.parse import urlparse

import httpx
import trafilatura
from fastapi import HTTPException, status

UA = "Mozilla/5.0 (compatible; LuminaBot/0.1)"

_IMG_RE = re.compile(r"!\[([^\]]*)\]\(\s*([^)]*?)\s*\)")


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

    # trafilatura is CPU-bound (lxml parsing) — run off the event loop.
    title, content = await asyncio.to_thread(_extract_markdown, resp.text, url)
    if not content:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "Could not extract main content"
        )
    return title, content


def _extract_markdown(html: str, url: str) -> tuple[str, str]:
    # Pull title from metadata; output_format="markdown" returns a bare string,
    # so we fetch the title in a separate call.
    meta = trafilatura.extract_metadata(html)
    title = (getattr(meta, "title", None) or "Untitled").strip()

    content = trafilatura.extract(
        html,
        url=url,
        output_format="markdown",
        include_links=True,
        include_images=True,
        include_formatting=True,
    )
    return title, _clean_markdown(content or "")


def _clean_markdown(md: str) -> str:
    """Normalize image markers so they render in a browser."""

    def _fix(m: re.Match[str]) -> str:
        alt, src = m.group(1), m.group(2).strip()
        if not src:
            return ""  # drop empty ![]() — would render as a broken image
        if src.startswith("//"):
            src = "https:" + src
        elif src.startswith("http://"):
            # Avoid mixed-content blocking when the frontend is on HTTPS.
            src = "https://" + src[len("http://") :]
        return f"![{alt}]({src})"

    md = _IMG_RE.sub(_fix, md)
    # Collapse consecutive duplicate image markers (common on Wikipedia).
    md = re.sub(r"(!\[[^\]]*\]\([^)]+\))(?:\s*\1)+", r"\1", md)
    return md.strip()
