import os
import tempfile

# must be set before importing product_DB so the app uses a throwaway database
_tmp_dir = tempfile.mkdtemp()
os.environ["PRODUCT_DB_FILE"] = os.path.join(_tmp_dir, "test.db")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect

from product_DB import app, engine, get_current_user


@pytest.fixture
def client():
    # skip the real JWT check so tests don't need to register and log in
    app.dependency_overrides[get_current_user] = lambda: "tester"
    # "with" runs the lifespan: startup before the test, shutdown after it
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_lifespan_opens_and_closes_connection():
    with TestClient(app) as c:
        # startup ran: tables exist and the connection flag is set
        assert app.state.db_connected is True
        assert "products" in inspect(engine).get_table_names()

        res = c.get("/health")
        assert res.status_code == 200
        assert res.json() == {"status": "online", "db_connected": True}

    # shutdown ran after leaving the "with" block
    assert app.state.db_connected is False


def test_add_product(client):
    payload = {"name": "Keyboard", "description": "Mechanical keyboard", "price": 1290.5, "quantity": 3}

    res = client.post("/products/", json=payload)

    assert res.status_code == 200
    data = res.json()
    assert data["id"] > 0
    assert data["name"] == "Keyboard"
    assert data["description"] == "Mechanical keyboard"
    assert data["price"] == 1290.5
    assert data["image"] is None
    assert data["quantity"] == 3
    assert data["status"] == "available"

    # the product was really saved: it can be read back
    res = client.get(f"/products/{data['id']}")
    assert res.status_code == 200
    assert res.json() == data


def test_add_product_missing_field(client):
    res = client.post("/products/", json={"name": "No price", "description": "x"})
    assert res.status_code == 422


def test_products_require_login():
    with TestClient(app) as c:
        assert c.get("/products/").status_code == 401
        assert c.post("/products/", json={"name": "x", "description": "x", "price": 1, "quantity": 1}).status_code == 401



def _new_product(client, quantity=5):
    payload = {"name": "Limited Sneakers", "description": "Last pairs", "price": 4990, "quantity": quantity}
    return client.post("/products/", json=payload).json()["id"]


def _quantity(client, pid):
    return client.get(f"/products/{pid}").json()["quantity"]


def test_reserve_takes_quantity_and_confirm_keeps_it(client):
    pid = _new_product(client, quantity=5)

    res = client.post(f"/products/{pid}/reserve", json={"amount": 2})
    assert res.status_code == 201
    assert res.json()["remaining_quantity"] == 3
    token = res.json()["reservation_token"]
    assert _quantity(client, pid) == 3

    # wrong token is rejected and changes nothing
    assert client.post(f"/products/{pid}/confirm", json={"reservation_token": "nope"}).status_code == 403

    assert client.post(f"/products/{pid}/confirm", json={"reservation_token": token}).status_code == 200
    assert _quantity(client, pid) == 3
    # a confirmed reservation can't be confirmed again
    assert client.post(f"/products/{pid}/confirm", json={"reservation_token": token}).status_code == 409


def test_reserve_only_if_enough_quantity(client):
    pid = _new_product(client, quantity=3)

    res = client.post(f"/products/{pid}/reserve", json={"amount": 4})
    assert res.status_code == 400
    assert _quantity(client, pid) == 3

    # exactly the remaining quantity is allowed
    assert client.post(f"/products/{pid}/reserve", json={"amount": 3}).status_code == 201
    product = client.get(f"/products/{pid}").json()
    assert product["quantity"] == 0
    assert product["status"] == "reserved"
    assert client.post(f"/products/{pid}/reserve", json={"amount": 1}).status_code == 400

    # amount must be positive
    assert client.post(f"/products/{pid}/reserve", json={"amount": 0}).status_code == 422


def test_unconfirmed_reservation_rolls_back_quantity(client, monkeypatch):
    import product_DB

    pid = _new_product(client, quantity=5)
    token = client.post(f"/products/{pid}/reserve", json={"amount": 5}).json()["reservation_token"]
    assert _quantity(client, pid) == 0

    # jump past the 30 second window without confirming
    later = product_DB.time.time() + product_DB.RESERVATION_SECONDS + 1
    monkeypatch.setattr(product_DB.time, "time", lambda: later)

    product = client.get(f"/products/{pid}").json()
    assert product["quantity"] == 5
    assert product["status"] == "available"
    res = client.post(f"/products/{pid}/confirm", json={"reservation_token": token})
    assert res.status_code == 409
    # reading again doesn't return the amount a second time
    assert _quantity(client, pid) == 5


def test_cancel_rolls_back_quantity(client):
    pid = _new_product(client, quantity=4)
    token = client.post(f"/products/{pid}/reserve", json={"amount": 3}).json()["reservation_token"]
    assert _quantity(client, pid) == 1

    assert client.post(f"/products/{pid}/cancel", json={"reservation_token": token}).status_code == 200
    assert _quantity(client, pid) == 4
    assert client.post(f"/products/{pid}/cancel", json={"reservation_token": token}).status_code == 409
    assert _quantity(client, pid) == 4


def test_sold_out_after_confirm(client):
    pid = _new_product(client, quantity=1)
    token = client.post(f"/products/{pid}/reserve", json={"amount": 1}).json()["reservation_token"]
    client.post(f"/products/{pid}/confirm", json={"reservation_token": token})
    assert client.get(f"/products/{pid}").json()["status"] == "sold"
