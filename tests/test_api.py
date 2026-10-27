import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app, store


@pytest.fixture(autouse=True)
def clean_store():
    store.clear()
    yield
    store.clear()


@pytest.fixture
def client():
    return TestClient(app)


def test_health_and_ready(client):
    assert client.get("/health").json() == {"status": "ok"}
    body = client.get("/ready").json()
    assert body["status"] == "ready"
    assert "version" in body


def test_security_headers(client):
    r = client.get("/health")
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["X-Frame-Options"] == "DENY"
    assert "default-src 'none'" in r.headers["Content-Security-Policy"]


def test_list_products(client):
    ids = {p["id"] for p in client.get("/api/v1/products").json()}
    assert {"racket-pro", "balls-4", "grip-3"} <= ids


def test_create_and_get_order(client):
    r = client.post("/api/v1/orders", json={"product_id": "balls-4", "quantity": 3})
    assert r.status_code == 201
    order = r.json()
    assert order["total_cents"] == 3 * 1290
    got = client.get(f"/api/v1/orders/{order['id']}")
    assert got.status_code == 200
    assert got.json()["id"] == order["id"]
    assert len(client.get("/api/v1/orders").json()) == 1


@pytest.mark.parametrize(
    "payload",
    [
        {"product_id": "balls-4", "quantity": 0},
        {"product_id": "balls-4", "quantity": 21},
        {"product_id": "BALLS; DROP TABLE", "quantity": 1},
        {"product_id": "balls-4", "quantity": 1, "price_cents": 1},
        {"quantity": 1},
    ],
)
def test_invalid_orders_are_rejected(client, payload):
    assert client.post("/api/v1/orders", json=payload).status_code == 422


def test_unknown_product(client):
    r = client.post("/api/v1/orders", json={"product_id": "does-not-exist", "quantity": 1})
    assert r.status_code == 422
    assert r.json()["detail"] == "unknown product"


def test_missing_order_is_404(client):
    assert client.get(f"/api/v1/orders/{uuid.uuid4()}").status_code == 404


def test_bad_order_id_is_422(client):
    assert client.get("/api/v1/orders/not-a-uuid").status_code == 422


def test_metrics_endpoint(client):
    client.get("/health")
    text = client.get("/metrics").text
    assert "http_requests_total" in text
    assert 'path="/health"' in text
