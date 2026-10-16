"""Translation Service (Task 1.5) — en ↔ ta ↔ hi with glossary preservation.

Managed-API-first (Sarvam / IndicTrans2 behind a swappable provider). The domain
value is the *glossary placeholder* mechanism, which is provider-independent:

    mask source-language glossary terms → translate → restore target-language
    terms → validate no sentinel survived (fallback to the literal term if one did).

A passthrough provider keeps unit tests and local dev running with no network.
"""

from __future__ import annotations

import hashlib
import re
from abc import ABC, abstractmethod
from functools import lru_cache
from typing import Literal, Protocol

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.redis import RedisCache
from app.services.glossary import GLOSSARY

Lang = Literal["en", "ta", "hi"]
log = get_logger("translation")
CACHE_TTL = 7 * 86400  # Task 1.5: translations kept a week

# Sentinel unlikely to be altered by a translator: private-use bracket + index.
_SENT = "{}"
_SENT_RE = re.compile("(\\d+)")


class TranslationProvider(ABC):
    name: str

    @abstractmethod
    async def translate(self, text: str, src: Lang, tgt: Lang) -> str: ...


class PassthroughTranslationProvider(TranslationProvider):
    """Dev/test provider: returns text unchanged (sentinels survive intact)."""

    name = "passthrough"

    async def translate(self, text: str, src: Lang, tgt: Lang) -> str:
        return text


class SarvamTranslationProvider(TranslationProvider):
    """Managed Indic translation via Sarvam (lazy httpx call)."""

    name = "sarvam"
    _LANG = {"en": "en-IN", "ta": "ta-IN", "hi": "hi-IN"}

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    async def translate(self, text: str, src: Lang, tgt: Lang) -> str:
        import httpx

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://api.sarvam.ai/translate",
                headers={"api-subscription-key": self._api_key},
                json={
                    "input": text,
                    "source_language_code": self._LANG[src],
                    "target_language_code": self._LANG[tgt],
                },
            )
            resp.raise_for_status()
            return resp.json()["translated_text"]


class TranslationCache(Protocol):
    async def get(self, key: str) -> str | None: ...
    async def set(self, key: str, value: str) -> None: ...


def _mask(text: str, src: Lang) -> tuple[str, list[dict[str, str]]]:
    """Replace source-language glossary terms with sentinels (longest first)."""
    entries = sorted(GLOSSARY, key=lambda e: len(e[src]), reverse=True)
    used: list[dict[str, str]] = []
    masked = text
    for entry in entries:
        term = entry[src]
        if not term:
            continue
        # ASCII terms get word boundaries; Indic terms match as substrings.
        pattern = rf"(?<!\w){re.escape(term)}(?!\w)" if term.isascii() else re.escape(term)
        rx = re.compile(pattern, re.IGNORECASE if term.isascii() else 0)
        if rx.search(masked):
            idx = len(used)
            masked = rx.sub(_SENT.format(idx), masked)
            used.append(entry)
    return masked, used


def _restore(text: str, used: list[dict[str, str]], tgt: Lang) -> str:
    def repl(m: re.Match[str]) -> str:
        i = int(m.group(1))
        return used[i][tgt] if i < len(used) else m.group(0)

    return _SENT_RE.sub(repl, text)


class TranslationService:
    def __init__(
        self, provider: TranslationProvider, cache: TranslationCache | None = None
    ) -> None:
        self.provider = provider
        self.cache = cache

    def _key(self, text: str, src: Lang, tgt: Lang) -> str:
        digest = hashlib.sha256(text.encode()).hexdigest()
        return f"tr:{self.provider.name}:{src}:{tgt}:{digest}"

    async def translate(self, text: str, src: Lang, tgt: Lang) -> str:
        if src == tgt or not text.strip():
            return text
        if self.cache is not None:
            hit = await self.cache.get(self._key(text, src, tgt))
            if hit is not None:
                return hit

        masked, used = _mask(text, src)
        translated = await self.provider.translate(masked, src, tgt)
        restored = _restore(translated, used, tgt)

        if _SENT_RE.search(restored):  # a sentinel survived → restoration failure
            log.warning("translation.sentinel_survived", src=src, tgt=tgt)
            restored = _SENT_RE.sub(
                lambda m: used[int(m.group(1))][tgt] if int(m.group(1)) < len(used) else "",
                restored,
            )

        if self.cache is not None:
            await self.cache.set(self._key(text, src, tgt), restored)
        return restored


def _select_provider() -> TranslationProvider:
    s = get_settings()
    if s.translation_provider == "sarvam" and s.sarvam_api_key:
        return SarvamTranslationProvider(s.sarvam_api_key)
    log.info("translation.using_passthrough_provider")
    return PassthroughTranslationProvider()


@lru_cache
def get_translation_service() -> TranslationService:
    return TranslationService(_select_provider(), cache=RedisCache(CACHE_TTL))
