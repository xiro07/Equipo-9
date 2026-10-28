#Paso 12
import pytest
from fastapi.testclient import TestClient

import app.api as api
from cargar_csv import load_fixture

@pytest.fixture
def client():
    api.orders = load_fixture()   # pedidos limpios en cada prueba
    return TestClient(api.app)

def test_404_pedido_inexistente(client):
    r = client.post("/orders/NOPE/confirm")
    assert r.status_code == 404

def test_confirmar_ok(client):
    r = client.post("/orders/O013/confirm")
    assert r.status_code == 200
    assert r.json()["status"] == "CONFIRMED"

def test_409_confirmar_dos_veces(client):
    client.post("/orders/O013/confirm")
    r = client.post("/orders/O013/confirm")
    assert r.status_code == 409

def test_422_confirmar_pedido_vacio(client):
    r = client.post("/orders/O007/confirm")
    assert r.status_code == 422