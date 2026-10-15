"""Unit tests for the Translation Service glossary-preservation mechanism."""

import pytest
from app.services.translation import (
    PassthroughTranslationProvider,
    TranslationProvider,
    TranslationService,
)

SENTINEL_CHARS = (chr(0xE000), chr(0xE001))


@pytest.fixture
def service():
    return TranslationService(PassthroughTranslationProvider())


async def test_glossary_terms_translated_to_target(service):
    out = await service.translate("apply for funding scheme", "en", "ta")
    assert "நிதியளிப்பு" in out  # funding → ta
    assert "திட்டம்" in out  # scheme → ta
    assert not any(c in out for c in SENTINEL_CHARS)  # no sentinel survived


async def test_verbatim_terms_preserved(service):
    out = await service.translate("register on DPIIT and get GST", "en", "hi")
    assert "DPIIT" in out
    assert "GST" in out


async def test_numbers_are_not_corrupted(service):
    # 'revenue' is a glossary term; the number must pass through untouched.
    out = await service.translate("revenue is 50000", "en", "ta")
    assert "50000" in out
    assert "வருவாய்" in out  # revenue → ta
    assert not any(c in out for c in SENTINEL_CHARS)


async def test_same_language_is_noop(service):
    assert await service.translate("no change here", "en", "en") == "no change here"


async def test_empty_text_noop(service):
    assert await service.translate("   ", "en", "ta") == "   "


class _CountingProvider(TranslationProvider):
    name = "count"

    def __init__(self):
        self.calls = 0

    async def translate(self, text, src, tgt):
        self.calls += 1
        return text


class _DictCache:
    def __init__(self):
        self.store = {}

    async def get(self, key):
        return self.store.get(key)

    async def set(self, key, value):
        self.store[key] = value


async def test_cache_prevents_recompute():
    provider = _CountingProvider()
    svc = TranslationService(provider, cache=_DictCache())
    await svc.translate("hello world", "en", "ta")
    await svc.translate("hello world", "en", "ta")
    assert provider.calls == 1
