"""VerificationGateway (design §A · Task 2.1).

A single façade over swappable KYC vendor drivers. Local pre-filters reject
malformed identifiers for free; well-formed ones go to the provider (behind a
circuit breaker). A deterministic stub keeps this runnable offline; real drivers
(SurePass / Setu / Sandbox) are config-selected in production.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from functools import lru_cache

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.logging import get_logger
from app.verification.validators import (
    cin_is_valid,
    dpiit_is_wellformed,
    gstin_is_valid,
    pan_is_valid,
)

log = get_logger("verification")

_PREFILTER = {
    "cin": cin_is_valid,
    "gstin": gstin_is_valid,
    "pan": pan_is_valid,
    "dpiit": dpiit_is_wellformed,
}


@dataclass
class VerificationResult:
    kind: str
    value_masked: str
    verified: bool
    status: str  # "verified" | "rejected" | "malformed"
    source: str
    reason: str | None = None
    details: dict = field(default_factory=dict)


def _mask(value: str) -> str:
    v = value.strip()
    return ("X" * max(0, len(v) - 4)) + v[-4:] if len(v) > 4 else v


class VerificationProvider(ABC):
    name: str

    @abstractmethod
    async def verify(self, kind: str, value: str) -> tuple[bool, dict, str | None]:
        """Return (verified, details, reason)."""


class StubVerificationProvider(VerificationProvider):
    """Offline provider: treats any well-formed identifier as verified."""

    name = "stub"

    async def verify(self, kind: str, value: str) -> tuple[bool, dict, str | None]:
        details = {
            "cin": {"company_name": "(stub) Verified Pvt Ltd", "status": "active"},
            "gstin": {"status": "active", "filing": "regular"},
            "pan": {"status": "valid"},
            "dpiit": {"recognition": "recognized"},
        }.get(kind, {})
        return True, details, None


class CircuitBreaker:
    """Prevent cascading failures from a flaky external registry."""

    def __init__(self, failure_threshold: int = 5, reset_timeout: int = 60) -> None:
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.failures = 0
        self.opened_at: float | None = None

    def allow(self) -> bool:
        if self.opened_at is None:
            return True
        if time.time() - self.opened_at >= self.reset_timeout:
            self.opened_at = None  # half-open: allow a trial
            return True
        return False

    def record_success(self) -> None:
        self.failures = 0
        self.opened_at = None

    def record_failure(self) -> None:
        self.failures += 1
        if self.failures >= self.failure_threshold:
            self.opened_at = time.time()


class VerificationGateway:
    def __init__(self, provider: VerificationProvider) -> None:
        self.provider = provider
        self._breaker = CircuitBreaker()

    async def verify(self, kind: str, value: str) -> VerificationResult:
        kind = kind.lower()
        if kind not in _PREFILTER:
            raise AppError("UNKNOWN_ID_TYPE", f"Unsupported id type: {kind}", status_code=400)

        v = value.strip().upper()
        masked = _mask(v)

        # Free local pre-filter — malformed never reaches the vendor.
        if not _PREFILTER[kind](v):
            return VerificationResult(
                kind, masked, False, "malformed", "local", reason=f"Invalid {kind.upper()} format"
            )

        if not self._breaker.allow():
            raise AppError(
                "VERIFICATION_UNAVAILABLE",
                "Verification service temporarily unavailable",
                status_code=503,
            )

        try:
            verified, details, reason = await self.provider.verify(kind, v)
            self._breaker.record_success()
        except Exception as exc:  # noqa: BLE001 - breaker records any provider failure
            self._breaker.record_failure()
            log.warning("verification.provider_error", kind=kind, error=str(exc))
            raise AppError(
                "VERIFICATION_FAILED", "Verification provider error", status_code=502
            ) from exc

        return VerificationResult(
            kind,
            masked,
            verified,
            "verified" if verified else "rejected",
            self.provider.name,
            reason=reason,
            details=details,
        )


def _select_provider() -> VerificationProvider:
    s = get_settings()
    if s.verification_provider and s.verification_api_key:
        # Real driver (SurePass/Setu/Sandbox) plugs in here; falls through to stub
        # until a driver module is added.
        log.info("verification.provider_key_present_using_stub_until_driver_added")
    return StubVerificationProvider()


@lru_cache
def get_gateway() -> VerificationGateway:
    return VerificationGateway(_select_provider())
