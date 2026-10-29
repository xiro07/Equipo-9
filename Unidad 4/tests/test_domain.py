#Paso 12
import pytest
from decimal import Decimal
from app.domain import (
    Money, OrderItem, InvalidOrderData, InvalidOrderTransition,
    OrderItemLimitExceeded,
)
from cargar_csv import load_fixture
from app.specifications import discount_rate

def test_money_negativo():
    with pytest.raises(InvalidOrderData):
        Money(Decimal("-1"))

def test_pedido_o001_inicia_draft():
    orders = load_fixture()
    assert orders["O001"].status.value == "DRAFT"
    assert orders["O001"].units == 4
    assert orders["O001"].total.amount == Decimal("2100.00")
def test_21_unidades_se_rechazan():
    o = load_fixture()["O009"]        # ya tiene 19 unidades
    with pytest.raises(OrderItemLimitExceeded):
        o.add_item(OrderItem("SKU003", 2, Money(Decimal("120.00"))))
    assert o.units == 19              # el pedido no se modificó

def test_cliente_inactivo_no_confirma():
    o = load_fixture()["O003"]
    with pytest.raises(InvalidOrderData):
        o.confirm()
    assert o.status.value == "DRAFT"  # no cambió de estado
    assert o.events == []             # y no registró evento

def test_pedido_vacio_no_confirma():
    o = load_fixture()["O007"]
    with pytest.raises(InvalidOrderData):
        o.confirm()

def test_descuento_vip_10_por_ciento():
    o = load_fixture()["O001"]
    assert discount_rate(o) == Decimal("0.10")

def test_descuento_5_por_ciento():
    o = load_fixture()["O006"]
    assert discount_rate(o) == Decimal("0.05")

def test_promocion_activa_excluye_descuento():
    o = load_fixture()["O005"]
    assert discount_rate(o) == Decimal("0")

def test_umbral_estricto_o010():
    o = load_fixture()["O010"]
    assert o.total.amount == Decimal("500.00")   # exactamente 500
    assert discount_rate(o) == Decimal("0")      # no supera el umbral

def test_envio_sin_guia():
    o = load_fixture()["O012"]
    o.confirm()
    with pytest.raises(InvalidOrderData):
        o.ship("")
    assert o.status.value == "CONFIRMED"
    assert [e.name for e in o.events] == ["OrderConfirmed"]

def test_confirmacion_doble():
    o = load_fixture()["O013"]
    o.confirm()
    with pytest.raises(InvalidOrderTransition):
        o.confirm()
    assert len(o.events) == 1

def test_cancelar_desde_shipped():
    o = load_fixture()["O014"]
    o.confirm()
    o.ship("GUIA-014")
    with pytest.raises(InvalidOrderTransition):
        o.cancel("fuera de tiempo")
    assert o.status.value == "SHIPPED"
    assert [e.name for e in o.events] == ["OrderConfirmed", "OrderShipped"]

def test_devolucion_valida():
    o = load_fixture()["O015"]
    o.confirm()
    o.ship("GUIA-015")
    o.return_order()
    assert o.status.value == "RETURNED"
    assert o.events[-1].name == "OrderReturned"

def test_entrega_valida():
    o = load_fixture()["O016"]
    o.confirm()
    o.ship("GUIA-016")
    o.deliver()
    assert o.status.value == "DELIVERED"
    assert [e.name for e in o.events] == [
        "OrderConfirmed", "OrderShipped", "OrderDelivered"
    ]