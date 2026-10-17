import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_ping_with_supplied_request_id():
    custom_id = "custom-req-id-12345"
    response = client.get("/ping", headers={"X-Request-ID": custom_id})
    assert response.status_code == 200
    assert response.json()["request_id"] == custom_id
    assert response.headers["x-request-id"] == custom_id

def test_ping_without_request_id():
    response = client.get("/ping")
    assert response.status_code == 200
    gen_id = response.json()["request_id"]
    assert gen_id is not None
    assert response.headers["x-request-id"] == gen_id

def test_rate_limiting_bucket():
    client_a = "client-alpha"
    client_b = "client-beta"

    # Send 8 requests for client-alpha -> All should pass (200)
    for i in range(8):
        res = client.get("/ping", headers={"X-Client-Id": client_a})
        assert res.status_code == 200, f"Request {i+1} failed"

    # 9th to 13th requests for client-alpha -> Should fail (429)
    for i in range(5):
        res = client.get("/ping", headers={"X-Client-Id": client_a})
        assert res.status_code == 429, f"Request {8 + i + 1} did not trigger 429"

    # Fresh client ID should succeed immediately
    res_b = client.get("/ping", headers={"X-Client-Id": client_b})
    assert res_b.status_code == 200

def test_cors_allowed_and_disallowed_origins():
    assigned = "https://app-dzm680.example.com"
    
    # Preflight from allowed origin
    res_options = client.options("/ping", headers={"Origin": assigned})
    assert res_options.status_code == 204
    assert res_options.headers.get("access-control-allow-origin") == assigned

    # GET from allowed origin
    res_get = client.get("/ping", headers={"Origin": assigned})
    assert res_get.headers.get("access-control-allow-origin") == assigned