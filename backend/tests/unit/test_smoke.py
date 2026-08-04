"""Smoke tests — prove the app boots and core plumbing works."""


async def test_health_ok(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["app"]


async def test_version(client):
    resp = await client.get("/api/v1/version")
    assert resp.status_code == 200
    assert resp.json()["api"] == "v1"


async def test_request_id_header(client):
    resp = await client.get("/health")
    assert resp.headers.get("x-request-id")


async def test_unknown_route_uses_error_envelope(client):
    resp = await client.get("/does-not-exist")
    assert resp.status_code == 404
    body = resp.json()
    assert body["error_code"] == "HTTP_404"
    assert body["request_id"]
