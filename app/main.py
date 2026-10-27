"""shop-api — a small, production-style HTTP API.

The business logic is deliberately small. The point of this repository is everything
around it: tests, scans, a signed image, hardened Kubernetes manifests and GitOps.
"""

from __future__ import annotations

import logging
import os
import time
from threading import Lock
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import FastAPI, HTTPException, Path, Request, Response, status
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from pydantic import BaseModel, ConfigDict, Field

from app import __version__

# ---------- settings (12-factor: everything from the environment) ----------
APP_ENV = os.getenv("APP_ENV", "dev")
ALLOWED_HOSTS = [h.strip() for h in os.getenv("ALLOWED_HOSTS", "*").split(",") if h.strip()]
MAX_ORDERS = int(os.getenv("MAX_ORDERS", "1000"))

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='{"time":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","msg":"%(message)s"}',
)
log = logging.getLogger("shop-api")

# ---------- metrics ----------
REQUESTS = Counter("http_requests_total", "HTTP requests", ["method", "path", "status"])
LATENCY = Histogram("http_request_duration_seconds", "Request latency", ["method", "path"])

# ---------- data model ----------
PRODUCTS = {
    "racket-pro": {"name": "Tennis racket Pro", "price_cents": 24900},
    "balls-4": {"name": "Tennis balls (4)", "price_cents": 1290},
    "grip-3": {"name": "Overgrip (3)", "price_cents": 990},
}


class OrderIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    product_id: str = Field(pattern=r"^[a-z0-9-]{2,40}$")
    quantity: int = Field(ge=1, le=20)


class Order(OrderIn):
    id: UUID
    total_cents: int
    created_at: float


class Store:
    """In-memory store. Thread-safe; a real deployment would use PostgreSQL."""

    def __init__(self) -> None:
        self._orders: dict[UUID, Order] = {}
        self._lock = Lock()

    def add(self, data: OrderIn) -> Order:
        product = PRODUCTS.get(data.product_id)
        if product is None:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "unknown product")
        with self._lock:
            if len(self._orders) >= MAX_ORDERS:
                raise HTTPException(status.HTTP_507_INSUFFICIENT_STORAGE, "order limit reached")
            order = Order(
                id=uuid4(),
                product_id=data.product_id,
                quantity=data.quantity,
                total_cents=product["price_cents"] * data.quantity,
                created_at=time.time(),
            )
            self._orders[order.id] = order
        return order

    def get(self, order_id: UUID) -> Order | None:
        return self._orders.get(order_id)

    def list(self) -> list[Order]:
        return sorted(self._orders.values(), key=lambda o: o.created_at)

    def clear(self) -> None:
        with self._lock:
            self._orders.clear()


store = Store()

app = FastAPI(title="shop-api", version=__version__, docs_url="/docs" if APP_ENV != "prod" else None, redoc_url=None)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=ALLOWED_HOSTS)


@app.middleware("http")
async def security_and_metrics(request: Request, call_next):
    started = time.perf_counter()
    response: Response = await call_next(request)
    route = request.scope.get("route")
    path = getattr(route, "path", "unmatched")
    LATENCY.labels(request.method, path).observe(time.perf_counter() - started)
    REQUESTS.labels(request.method, path, str(response.status_code)).inc()
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"
    response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
    return response


# ---------- endpoints ----------
@app.get("/health", tags=["ops"])
def health() -> dict[str, str]:
    """Liveness: the process is up."""
    return {"status": "ok"}


@app.get("/ready", tags=["ops"])
def ready() -> dict[str, str]:
    """Readiness: the service can take traffic."""
    return {"status": "ready", "version": __version__, "env": APP_ENV}


@app.get("/metrics", tags=["ops"], include_in_schema=False)
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/api/v1/products", tags=["shop"])
def list_products() -> list[dict]:
    return [{"id": pid, **p} for pid, p in PRODUCTS.items()]


@app.post("/api/v1/orders", status_code=status.HTTP_201_CREATED, tags=["shop"])
def create_order(data: OrderIn) -> Order:
    order = store.add(data)
    log.info("order created id=%s product=%s qty=%s", order.id, order.product_id, order.quantity)
    return order


@app.get("/api/v1/orders", tags=["shop"])
def list_orders() -> list[Order]:
    return store.list()


@app.get("/api/v1/orders/{order_id}", tags=["shop"])
def get_order(order_id: Annotated[UUID, Path()]) -> Order:
    order = store.get(order_id)
    if order is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "order not found")
    return order
