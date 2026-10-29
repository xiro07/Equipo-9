#Paso 11
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from cargar_csv import load_fixture
from app.domain import InvalidOrderTransition, InvalidOrderData

app = FastAPI(title="TechStore U4")
orders = load_fixture()
class ShipBody(BaseModel):
    tracking_number: str


class CancelBody(BaseModel):
    reason: str

def buscar_pedido(order_id):
    order = orders.get(order_id)
    if order is None:
        raise HTTPException(
            status_code=404,
            detail=f"El pedido '{order_id}' no existe en el sistema."
        )
    return order

@app.get("/orders/{order_id}")
def get_order(order_id: str):
    order = buscar_pedido(order_id)
    return {
        "id": order.id,
        "customer_id": order.customer.id,
        "status": order.status.value,
        "units": order.units,
        "total": str(order.total.amount),
        "events": [e.name for e in order.events],
    }

@app.post("/orders/{order_id}/confirm")
def confirm_order(order_id: str):
    order = buscar_pedido(order_id)
    try:
        order.confirm()
    except InvalidOrderTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except InvalidOrderData as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return {"id": order.id, "status": order.status.value}

@app.post("/orders/{order_id}/ship")
def ship_order(order_id: str, body: ShipBody):
    order = buscar_pedido(order_id)
    try:
        order.ship(body.tracking_number)
    except InvalidOrderTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except InvalidOrderData as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return {"id": order.id, "status": order.status.value}

@app.post("/orders/{order_id}/cancel")
def cancel_order(order_id: str, body: CancelBody):
    order = buscar_pedido(order_id)
    try:
        order.cancel(body.reason)
    except InvalidOrderTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except InvalidOrderData as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return {"id": order.id, "status": order.status.value}