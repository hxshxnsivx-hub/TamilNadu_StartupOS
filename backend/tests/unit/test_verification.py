"""Unit tests for local validators and the VerificationGateway."""

from app.verification.gateway import CircuitBreaker, StubVerificationProvider, VerificationGateway
from app.verification.validators import cin_is_valid, gstin_is_valid, pan_is_valid


def test_cin_validator():
    assert cin_is_valid("U72900TN2020PTC123456")
    assert not cin_is_valid("INVALID123")
    assert not cin_is_valid("Z72900TN2020PTC123456")  # bad prefix


def test_pan_validator():
    assert pan_is_valid("ABCDE1234F")
    assert not pan_is_valid("ABCD1234F")  # too short


def test_gstin_checksum():
    assert gstin_is_valid("27AAPFU0939F1ZV")  # known-valid sample
    assert not gstin_is_valid("27AAPFU0939F1ZX")  # corrupted check digit
    assert not gstin_is_valid("27AAPFU0939F1Z")  # wrong length


async def test_gateway_verifies_wellformed():
    gw = VerificationGateway(StubVerificationProvider())
    r = await gw.verify("cin", "U72900TN2020PTC123456")
    assert r.verified and r.status == "verified"
    assert r.source == "stub"
    assert r.value_masked.endswith("3456") and r.value_masked.startswith("X")


async def test_gateway_rejects_malformed_without_provider():
    class Boom(StubVerificationProvider):
        async def verify(self, kind, value):  # should never be called
            raise AssertionError("provider must not be called on malformed input")

    gw = VerificationGateway(Boom())
    r = await gw.verify("gstin", "not-a-gstin")
    assert not r.verified and r.status == "malformed" and r.source == "local"


def test_circuit_breaker_opens_and_recovers():
    cb = CircuitBreaker(failure_threshold=2, reset_timeout=0)
    assert cb.allow()
    cb.record_failure()
    cb.record_failure()
    # opened, but reset_timeout=0 → immediately half-open
    assert cb.allow()
    cb.record_success()
    assert cb.failures == 0
