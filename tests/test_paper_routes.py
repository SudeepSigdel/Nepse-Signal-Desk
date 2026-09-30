"""API tests for /api/paper/* with auth, DB and price feed overridden."""

from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_paper_trading_service, get_price_feed, get_response_cache
from app.cache import ResponseCache
from app.db import get_db
from app.db_models import User
from app.main import app
from app.services.auth_service import get_current_user
from app.trading.rules import NEPAL_TZ
from tests.test_paper_trading_service import Clock, _service

AFTER_CLOSE = datetime(2026, 9, 29, 16, 0, tzinfo=NEPAL_TZ)


@pytest.fixture
def client(db_session):
    user = User(email="trader@example.com", hashed_password="x")
    db_session.add(user)
    db_session.commit()
    service = _service(Clock(AFTER_CLOSE))

    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_paper_trading_service] = lambda: service
    app.dependency_overrides[get_price_feed] = lambda: service.price_feed
    cache = ResponseCache()
    app.dependency_overrides[get_response_cache] = lambda: cache
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def test_account_order_cancel_flow(client):
    account = client.post("/api/paper/accounts", json={"name": "Learner", "starting_cash": 200000}).json()
    assert account["cash"] == 200000 and account["positions"] == []

    order = client.post(
        f"/api/paper/accounts/{account['id']}/orders",
        json={"symbol": "nabil", "side": "buy", "order_type": "limit", "qty": 10, "limit_price": 495},
    )
    assert order.status_code == 201
    body = order.json()
    assert (body["status"], body["symbol"]) == ("pending", "NABIL")

    summary = client.get(f"/api/paper/accounts/{account['id']}").json()
    assert summary["available_cash"] < summary["cash"]

    cancelled = client.post(f"/api/paper/orders/{body['id']}/cancel").json()
    assert cancelled["status"] == "cancelled"
    assert client.post(f"/api/paper/orders/{body['id']}/cancel").status_code == 400

    orders = client.get(f"/api/paper/accounts/{account['id']}/orders").json()
    assert [o["status"] for o in orders] == ["cancelled"]
    assert client.get(f"/api/paper/accounts/{account['id']}/equity").json() == []


def test_validation_and_ownership(client):
    assert client.get("/api/paper/accounts/999").status_code == 404
    bad = client.post("/api/paper/accounts/1/orders", json={"symbol": "NABIL", "side": "hold", "qty": 10})
    assert bad.status_code == 422


def test_quote_fee_preview_and_leaderboard(client):
    quote = client.get("/api/paper/quote/NABIL").json()
    assert quote["source"] == "eod" and quote["circuit_high"] == 550.0
    assert client.get("/api/paper/quote/NOPE").status_code == 404

    fees = client.post("/api/paper/fee-preview", json={"side": "buy", "price": 500, "qty": 100}).json()
    assert fees["net_amount"] == 50187.5
    sell = client.post(
        "/api/paper/fee-preview", json={"side": "sell", "price": 600, "qty": 100, "avg_cost": 500, "holding_days": 400}
    ).json()
    assert sell["cgt_rate"] == 0.05

    client.post("/api/paper/accounts", json={"name": "A"})
    board = client.get("/api/paper/leaderboard").json()
    assert board[0]["rank"] == 1 and board[0]["trader"] == "tr***@example.com"
