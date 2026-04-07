"""Link Understanding — extract metadata from URLs in messages.

Detects URLs in user messages, fetches og:tags and meta info,
and enriches the prompt with link context so the agent understands
what the user is referencing without needing to fetch it itself.

Uses aiohttp with timeout/size limits for safety.
Caches results in Redis (1h TTL) to avoid re-fetching.
"""
import asyncio
import hashlib
import json
import logging
import re
from dataclasses import dataclass, field
from html.parser import HTMLParser

logger = logging.getLogger(__name__)

# Match URLs in text (http/https)
URL_RE = re.compile(
    r"https?://[^\s<>\"\'\)\]]+",
    re.IGNORECASE,
)

# Max page size to download (256KB — just need headers)
MAX_DOWNLOAD_BYTES = 256 * 1024
FETCH_TIMEOUT = 8  # seconds
CACHE_TTL = 3600  # 1 hour
MAX_URLS_PER_MESSAGE = 3


@dataclass
class LinkMeta:
    """Extracted metadata from a URL."""
    url: str
    title: str = ""
    description: str = ""
    site_name: str = ""
    image: str = ""
    type: str = ""
    error: str = ""

    def to_context(self) -> str:
        """Format as context string for prompt injection."""
        parts = [f"🔗 {self.url}"]
        if self.site_name:
            parts.append(f"  Сайт: {self.site_name}")
        if self.title:
            parts.append(f"  Заголовок: {self.title}")
        if self.description:
            desc = self.description[:300]
            parts.append(f"  Описание: {desc}")
        if self.type:
            parts.append(f"  Тип: {self.type}")
        return "\n".join(parts)


class _MetaParser(HTMLParser):
    """Lightweight HTML parser that extracts <title> and <meta> og/description tags."""

    def __init__(self):
        super().__init__()
        self.title = ""
        self.meta: dict[str, str] = {}
        self._in_title = False
        self._title_data = []

    def handle_starttag(self, tag, attrs):
        if tag == "title":
            self._in_title = True
            self._title_data = []
        elif tag == "meta":
            attr_dict = dict(attrs)
            prop = attr_dict.get("property", "").lower()
            name = attr_dict.get("name", "").lower()
            content = attr_dict.get("content", "")
            if not content:
                return
            # og: tags
            if prop.startswith("og:"):
                self.meta[prop] = content
            # Standard meta
            if name == "description" and "description" not in self.meta:
                self.meta["description"] = content
            if name == "title" and "title" not in self.meta:
                self.meta["title"] = content

    def handle_data(self, data):
        if self._in_title:
            self._title_data.append(data)

    def handle_endtag(self, tag):
        if tag == "title" and self._in_title:
            self._in_title = False
            self.title = " ".join(self._title_data).strip()


def extract_urls(text: str) -> list[str]:
    """Extract up to MAX_URLS_PER_MESSAGE URLs from text."""
    urls = URL_RE.findall(text)
    # Deduplicate while preserving order
    seen = set()
    unique = []
    for u in urls:
        # Clean trailing punctuation
        u = u.rstrip(".,;:!?)")
        if u not in seen:
            seen.add(u)
            unique.append(u)
    return unique[:MAX_URLS_PER_MESSAGE]


async def fetch_link_meta(url: str, redis_client=None) -> LinkMeta:
    """Fetch and parse metadata from a URL.

    Checks Redis cache first. Falls back to aiohttp fetch.
    """
    # Check cache
    if redis_client:
        cache_key = f"neura:linkmeta:{hashlib.md5(url.encode()).hexdigest()}"
        try:
            cached = await redis_client.get(cache_key)
            if cached:
                data = json.loads(cached)
                return LinkMeta(**data)
        except Exception:
            pass

    meta = LinkMeta(url=url)

    try:
        import aiohttp
        timeout = aiohttp.ClientTimeout(total=FETCH_TIMEOUT)
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; NeuraBot/2.0)",
            "Accept": "text/html",
        }

        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, headers=headers,
                                   allow_redirects=True,
                                   max_redirects=3) as resp:
                if resp.status != 200:
                    meta.error = f"HTTP {resp.status}"
                    return meta

                content_type = resp.headers.get("Content-Type", "")
                if "text/html" not in content_type:
                    meta.type = content_type.split(";")[0]
                    meta.title = url.split("/")[-1] or url
                    return meta

                # Read limited bytes
                body = await resp.content.read(MAX_DOWNLOAD_BYTES)
                html = body.decode("utf-8", errors="replace")

    except asyncio.TimeoutError:
        meta.error = "timeout"
        return meta
    except Exception as e:
        meta.error = str(e)[:100]
        return meta

    # Parse HTML
    try:
        parser = _MetaParser()
        parser.feed(html)

        meta.title = (
            parser.meta.get("og:title")
            or parser.meta.get("title")
            or parser.title
            or ""
        )
        meta.description = (
            parser.meta.get("og:description")
            or parser.meta.get("description")
            or ""
        )
        meta.site_name = parser.meta.get("og:site_name", "")
        meta.image = parser.meta.get("og:image", "")
        meta.type = parser.meta.get("og:type", "")
    except Exception as e:
        meta.error = f"parse: {e}"

    # Cache result
    if redis_client and not meta.error:
        try:
            cache_data = json.dumps({
                "url": meta.url, "title": meta.title,
                "description": meta.description, "site_name": meta.site_name,
                "image": meta.image, "type": meta.type,
            })
            await redis_client.set(cache_key, cache_data, ex=CACHE_TTL)
        except Exception:
            pass

    return meta


async def enrich_with_links(text: str, redis_client=None) -> str:
    """Extract URLs from text, fetch metadata, return context block.

    Returns empty string if no URLs found or all fail.
    """
    urls = extract_urls(text)
    if not urls:
        return ""

    # Fetch all URLs concurrently
    tasks = [fetch_link_meta(u, redis_client) for u in urls]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    context_parts = []
    for result in results:
        if isinstance(result, Exception):
            continue
        if result.error:
            continue
        if result.title or result.description:
            context_parts.append(result.to_context())

    if not context_parts:
        return ""

    return "\n📎 Содержимое ссылок из сообщения:\n" + "\n\n".join(context_parts)
