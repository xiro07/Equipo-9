#Paso 10
from decimal import Decimal
from cargar_csv import load_fixture
from app.domain import Money, OrderItem, DomainException
from app.specifications import discount_rate
from pathlib import Path

ENCABEZADO = ("Caso", "Pedido", "Estado inicial", "Operación",
              "Resultado real", "Eventos", "Explicación")
filas = []

EXPLICACION = {
    "E01": "VIP, es un total > 500, de 4 unidades y sin promoción: cumple la regla del 10 %",
    "E02": "No es VIP y el total no pasa de 5000: no hay un descuento",
    "E03": "El cliente está inactivo, así que no se puede confirmar",
    "E04": "La promoción activa bloquea cualquier descuento",
    "E05": "Total de 18000 (> 5000) y sin promoción: aplica el 5 %",
    "E06": "El pedido no tiene artículos",
    "E07": "20 unidades es el máximo permitido, no lo supera",
    "E08": "19 + 2 = 21 unidades supera el límite; el pedido no cambió",
    "E09": "El total es exactamente 500 y la regla exige más de 500",
    "E10": "Es VIP, pero solo tiene 3 unidades y se requieren 4",
    "E11": "Confirmar es válido, pero enviar exige una guía no vacía",
    "E12": "Solo se confirma desde DRAFT; la segunda vez ya estaba CONFIRMED",
    "E13": "Solo se cancela desde CONFIRMED; ya estaba SHIPPED",
    "E14": "Devolver es válido desde SHIPPED y termina en RETURNED",
    "E15": "Entregar es válido desde SHIPPED y termina en DELIVERED",
}

def nuevo(pedido_id):
    """Pedido recién cargado: cada caso empieza limpio."""
    return load_fixture()[pedido_id]

def fila(caso, pedido, inicial, operacion, resultado, eventos):
    filas.append((caso, pedido, inicial, operacion, resultado, eventos))

def imprimir():
    """Imprime la tabla y la guarda en bitacora.md (UTF-8)."""
    filas_ordenadas = [f + (EXPLICACION.get(f[0], ""),) for f in sorted(filas)]
    todas = [ENCABEZADO] + filas_ordenadas
    anchos = [max(len(f[i]) for f in todas) for i in range(len(ENCABEZADO))]

    def linea(celdas):
        return "| " + " | ".join(c.ljust(a) for c, a in zip(celdas, anchos)) + " |"

    lineas = [linea(ENCABEZADO),
              "|" + "|".join("-" * (a + 2) for a in anchos) + "|"]
    lineas += [linea(f) for f in filas_ordenadas]

    print("\n".join(lineas))
    destino = Path(__file__).parent / "bitacora.md"
    destino.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    

# E01: evaluar descuento de O001
o = nuevo("O001")
fila("E01", "O001", o.status.value, "evaluar descuento",
     f"descuento {int(discount_rate(o) * 100)}%", "sin evento")

# E02, E04, E05, E09, E10: evaluar descuento
for caso, pid in [("E02", "O002"), ("E04", "O005"), ("E05", "O006"),
                  ("E09", "O010"), ("E10", "O011")]:
    o = nuevo(pid)
    fila(caso, pid, o.status.value, "evaluar descuento",
         f"descuento {int(discount_rate(o) * 100)}%", "sin evento")

# E03, E06, E07: confirmar
for caso, pid in [("E03", "O003"), ("E06", "O007"), ("E07", "O008")]:
    o = nuevo(pid)
    inicial = o.status.value
    try:
        o.confirm()
        resultado = f"OK -> {o.status.value}"
    except DomainException as x:
        resultado = f"RECHAZO: {x}"
    eventos = ", ".join(ev.name for ev in o.events) or "sin evento"
    fila(caso, pid, inicial, "confirmar", resultado, eventos)

# E08: agregar SKU003 x2 a O009 (ya tiene 19 unidades)
o = nuevo("O009")
inicial = o.status.value
unidades_antes = o.units
try:
    o.add_item(OrderItem("SKU003", 2, Money(Decimal("120.00"))))
    resultado = "OK"
except DomainException as x:
    resultado = f"RECHAZO: {x} (unidades: {unidades_antes} -> {o.units})"
eventos = ", ".join(ev.name for ev in o.events) or "sin evento"
fila("E08", "O009", inicial, "agregar SKU003 x2", resultado, eventos)

def nombres(o):
    """Eventos del pedido como texto, o 'sin evento'."""
    return ", ".join(ev.name for ev in o.events) or "sin evento"

# E11: confirmar y enviar sin guía (O012)
o = nuevo("O012")
inicial = o.status.value
o.confirm()
try:
    o.ship("")
    resultado = "OK"
except DomainException as x:
    resultado = f"confirmó; envío RECHAZADO: {x}"
fila("E11", "O012", inicial, "confirmar y enviar sin guía", resultado, nombres(o))

# E12: confirmar dos veces (O013)
o = nuevo("O013")
inicial = o.status.value
o.confirm()
try:
    o.confirm()
    resultado = "OK"
except DomainException as x:
    resultado = f"1ª OK; 2ª RECHAZADA: {x}"
fila("E12", "O013", inicial, "confirmar dos veces", resultado, nombres(o))

# E13: confirmar, enviar y cancelar (O014)
o = nuevo("O014")
inicial = o.status.value
o.confirm()
o.ship("GUIA-014")
try:
    o.cancel("fuera de tiempo")
    resultado = "OK"
except DomainException as x:
    resultado = f"cancelación RECHAZADA: {x}"
fila("E13", "O014", inicial, "confirmar, enviar y cancelar", resultado, nombres(o))

# E14: confirmar, enviar y devolver (O015)
o = nuevo("O015")
inicial = o.status.value
o.confirm()
o.ship("GUIA-015")
o.return_order()
fila("E14", "O015", inicial, "confirmar, enviar y devolver",
     f"OK -> {o.status.value}", nombres(o))

# E15: confirmar, enviar y entregar (O016)
o = nuevo("O016")
inicial = o.status.value
o.confirm()
o.ship("GUIA-016")
o.deliver()
fila("E15", "O016", inicial, "confirmar, enviar y entregar",
     f"OK -> {o.status.value}", nombres(o))

imprimir()