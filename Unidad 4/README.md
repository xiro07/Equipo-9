# TechStore U4 — Implementación del Núcleo de Negocio

Proyecto desarrollado para la **Unidad 4 de Componentes de Lógica de Negocio**.

El objetivo del proyecto es implementar el núcleo de negocio de una tienda ficticia llamada **TechStore**, utilizando conceptos de Domain-Driven Design (DDD), Value Objects, Specification Pattern, máquinas de estado, Domain Events, excepciones de dominio, pruebas automatizadas y una API REST desarrollada con FastAPI.

---

## 1. Funcionalidades implementadas

El proyecto permite:

- Cargar clientes, productos y pedidos desde archivos CSV.
- Representar cantidades monetarias mediante el Value Object `Money`.
- Administrar clientes mediante la entidad `Customer`.
- Representar productos dentro de un pedido mediante `OrderItem`.
- Gestionar pedidos mediante el Aggregate Root `Order`.
- Limitar un pedido a un máximo de 20 unidades.
- Calcular automáticamente el total de los pedidos.
- Evaluar reglas de descuento mediante Specification Pattern.
- Controlar el ciclo de vida de un pedido mediante una máquina de estados.
- Registrar Domain Events después de transiciones válidas.
- Exponer operaciones mediante una API REST con FastAPI.
- Manejar errores mediante códigos HTTP 404, 409 y 422.
- Ejecutar pruebas automáticas con pytest.
- Ejecutar los 15 escenarios E01–E15 proporcionados en la práctica.

---

## 2. Estructura del proyecto

```text
Equipo_9/
├── app/
│   ├── __init__.py
│   ├── domain.py
│   ├── specifications.py
│   └── api.py
│
├── datos/
│   ├── clientes.csv
│   ├── productos.csv
│   ├── pedidos.csv
│   ├── detalle_pedidos.csv
│   └── escenarios.csv
│
├── tests/
│   ├── test_domain.py
│   └── test_api.py
│
├── Evidencias/
│   ├── carga_16_pedidos.png
│   ├── pytest_18_passed.png
│   ├── swagger_exito.png
│   ├── swagger_error_404.png
│   └── diagrama_estados_order.png
│
├── bitacora.py
├── bitacora.md
├── cargar_csv.py
├── README.md
└── .gitignore
```

---

## 3. Requisitos

Para ejecutar el proyecto se requiere:

- Python 3.11 o superior.
- FastAPI.
- Uvicorn.
- Pytest.
- HTTPX.

No se requiere instalar MySQL, SQL Server, SQLite ni otra base de datos, ya que los datos se trabajan **en memoria** a partir de los archivos CSV proporcionados.

---

## 4. Instalación

### 4.1 Clonar o descargar el proyecto

Descargar el repositorio y abrir una terminal dentro de la carpeta raíz del proyecto.

### 4.2 Crear un entorno virtual

En Windows PowerShell:

```powershell
python -m venv .venv
```

Activar el entorno:

```powershell
.venv\Scripts\Activate.ps1
```

En Windows CMD:

```cmd
.venv\Scripts\activate.bat
```

### 4.3 Instalar las dependencias

```powershell
python -m pip install fastapi uvicorn pytest httpx
```

---

## 5. Carga de datos

Los datos iniciales se encuentran en la carpeta `datos/`.

Los archivos utilizados son:

| Archivo | Contenido |
|---|---|
| `clientes.csv` | Información de clientes, estado activo y membresía VIP |
| `productos.csv` | Productos, precios y existencia |
| `pedidos.csv` | Pedidos iniciales |
| `detalle_pedidos.csv` | Productos y cantidades de cada pedido |
| `escenarios.csv` | Casos E01–E15 utilizados para validar las reglas |

Para cargar los pedidos ejecutar:

```powershell
python cargar_csv.py
```

El sistema debe cargar **16 pedidos**, todos inicialmente con estado `DRAFT`.

Como punto de comprobación, el pedido `O001` debe mostrar:

```text
Estado: DRAFT
Unidades: 4
Total: 2100.00 MXN
```

---

## 6. Modelo de dominio

### Money

`Money` es un Value Object inmutable utilizado para representar cantidades monetarias.

Sus principales reglas son:

- El monto no puede ser negativo.
- El monto debe ser finito.
- Solo pueden sumarse objetos que utilicen la misma moneda.
- La moneda utilizada por los pedidos es MXN.

### Customer

Representa a un cliente de TechStore.

Contiene:

- Identificador.
- Estado VIP.
- Estado activo.

Un cliente inactivo no puede confirmar pedidos.

### OrderItem

Representa un producto agregado a un pedido.

Contiene:

- SKU.
- Cantidad.
- Precio unitario.

La cantidad debe ser mayor que cero y el subtotal se calcula automáticamente.

### Order

`Order` funciona como el Aggregate Root del sistema.

Es responsable de:

- Mantener los productos del pedido.
- Calcular el total de unidades.
- Calcular el importe total.
- Evitar pedidos con más de 20 unidades.
- Controlar las transiciones de estado.
- Registrar los Domain Events correspondientes.

---

## 7. Reglas de negocio

### Máximo de unidades

Un pedido puede contener como máximo **20 unidades**.

El límite se calcula sumando las cantidades de todos los artículos y no contando únicamente los renglones del pedido.

Por ejemplo:

```text
Producto A: 10 unidades
Producto B: 7 unidades
Producto C: 3 unidades

Total: 20 unidades → válido
```

Agregar una unidad adicional provoca `OrderItemLimitExceeded`.

---

## 8. Specification Pattern

Las reglas de descuento se implementaron mediante Specification Pattern.

Las Specifications disponibles son:

- `MinimumAmountSpec`
- `VIPCustomerSpec`
- `MinimumUnitsSpec`
- `ActivePromotionSpec`

También se implementaron los operadores de composición:

- `AND` mediante `&`
- `OR` mediante `|`
- `NOT` mediante `~`

### Descuento del 10 %

Se aplica cuando el pedido cumple todas las siguientes condiciones:

- Total mayor a $500 MXN.
- Cliente VIP.
- Al menos 4 unidades.
- No existe una promoción activa.

La regla se representa como:

```text
Total > 500
AND Cliente VIP
AND Unidades >= 4
AND NOT Promoción activa
```

### Descuento del 5 %

Se aplica cuando:

- El total es mayor a $5,000 MXN.
- No existe una promoción activa.

```text
Total > 5000
AND NOT Promoción activa
```

Si un pedido cumple ambas reglas, se aplica primero el descuento del **10 %**.

Casos de referencia:

| Pedido | Resultado esperado |
|---|---|
| O001 | 10 % |
| O006 | 5 % |
| O005 | 0 %, debido a promoción activa |
| O010 | 0 %, porque el total es exactamente $500 |

---

## 9. Máquina de estados

Los pedidos comienzan en estado:

```text
DRAFT
```

Las transiciones válidas son:

```text
DRAFT
  │
  │ confirm()
  ▼
CONFIRMED
  │
  ├──────── cancel(reason) ────────> CANCELLED
  │
  │ ship(tracking_number)
  ▼
SHIPPED
  │
  ├──────── return_order() ────────> RETURNED
  │
  │ deliver()
  ▼
DELIVERED
```

Los estados disponibles son:

- `DRAFT`
- `CONFIRMED`
- `SHIPPED`
- `DELIVERED`
- `CANCELLED`
- `RETURNED`

Las transiciones que no pertenecen al flujo permitido generan `InvalidOrderTransition`.

---

## 10. Domain Events

Después de cada transición válida se genera un Domain Event.

| Operación | Nuevo estado | Evento |
|---|---|---|
| `confirm()` | CONFIRMED | `OrderConfirmed` |
| `ship()` | SHIPPED | `OrderShipped` |
| `cancel()` | CANCELLED | `OrderCancelled` |
| `deliver()` | DELIVERED | `OrderDelivered` |
| `return_order()` | RETURNED | `OrderReturned` |

Los eventos solamente se registran **después de que las validaciones de la operación se cumplen y el cambio de estado se realiza correctamente**.

Si una operación es rechazada:

- El estado del pedido no cambia.
- No se registra un evento nuevo.

---

## 11. Ejecución de los escenarios E01–E15

Para ejecutar los escenarios proporcionados en `datos/escenarios.csv`:

```powershell
python bitacora.py
```

El programa evalúa los 15 escenarios y genera automáticamente:

```text
bitacora.md
```

La bitácora contiene:

- Caso.
- Pedido.
- Estado inicial.
- Operación.
- Resultado real.
- Domain Events.
- Explicación.

Los escenarios comprueban descuentos, promociones, clientes inactivos, pedidos vacíos, límites de unidades y transiciones válidas e inválidas.

---

## 12. API REST

La API se desarrolló utilizando **FastAPI**.

Para iniciarla ejecutar:

```powershell
uvicorn app.api:app --reload
```

Una vez iniciada estará disponible en:

```text
http://127.0.0.1:8000
```

La documentación interactiva Swagger se encuentra en:

```text
http://127.0.0.1:8000/docs
```

El contrato OpenAPI se encuentra en:

```text
http://127.0.0.1:8000/openapi.json
```

---

## 13. Endpoints

### Consultar pedido

```http
GET /orders/{order_id}
```

Ejemplo:

```text
GET /orders/O001
```

Devuelve información como:

- ID del pedido.
- ID del cliente.
- Estado.
- Unidades.
- Total.
- Eventos registrados.

---

### Confirmar pedido

```http
POST /orders/{order_id}/confirm
```

Ejemplo:

```text
POST /orders/O013/confirm
```

Si la operación es válida:

```json
{
  "id": "O013",
  "status": "CONFIRMED"
}
```

---

### Enviar pedido

```http
POST /orders/{order_id}/ship
```

Requiere un número de guía.

Ejemplo del cuerpo:

```json
{
  "tracking_number": "GUIA-013"
}
```

El pedido debe encontrarse en estado `CONFIRMED`.

---

### Cancelar pedido

```http
POST /orders/{order_id}/cancel
```

Requiere indicar un motivo.

Ejemplo del cuerpo:

```json
{
  "reason": "Cancelación solicitada por el cliente"
}
```

El pedido debe encontrarse en estado `CONFIRMED`.

---

## 14. Códigos HTTP

La API utiliza códigos HTTP para diferenciar los resultados.

| Código | Significado en el proyecto |
|---|---|
| `200 OK` | Operación realizada correctamente |
| `404 Not Found` | El pedido solicitado no existe |
| `409 Conflict` | Se intentó realizar una transición de estado no permitida |
| `422 Unprocessable Entity` | Los datos no cumplen las reglas del dominio |

Ejemplos:

```text
POST /orders/NOPE/confirm
→ 404
```

Confirmar dos veces el mismo pedido:

```text
POST /orders/O013/confirm
POST /orders/O013/confirm
→ segunda petición: 409
```

Confirmar un pedido vacío:

```text
POST /orders/O007/confirm
→ 422
```

---

## 15. Pruebas automatizadas

Las pruebas fueron desarrolladas utilizando **pytest**.

Para ejecutarlas:

```powershell
python -m pytest -q
```

Actualmente el proyecto contiene **18 pruebas automatizadas**.

Las pruebas verifican, entre otros casos:

- Rechazo de montos negativos.
- Carga correcta del pedido O001.
- Límite máximo de 20 unidades.
- Rechazo de un cliente inactivo.
- Rechazo de pedidos vacíos.
- Descuento VIP del 10 %.
- Descuento alternativo del 5 %.
- Exclusión de pedidos con promoción activa.
- Total exactamente igual a $500.
- Envío sin número de guía.
- Confirmación doble.
- Cancelación desde estado SHIPPED.
- Devolución válida.
- Entrega válida.
- HTTP 404.
- HTTP 200.
- HTTP 409.
- HTTP 422.

El resultado esperado es:

```text
18 passed
```

---

## 16. Evidencias

Para la entrega se deben conservar las siguientes evidencias:

1. Captura de `python cargar_csv.py` mostrando los 16 pedidos.
2. Captura de `python -m pytest -q` con todas las pruebas aprobadas.
3. Captura de Swagger `/docs` mostrando una operación exitosa.
4. Captura de Swagger `/docs` mostrando una operación rechazada.
5. Bitácora de escenarios E01–E15.
6. Diagrama de estados.
7. Explicación de los Domain Events.

---


---

## 17. Tecnologías utilizadas

- Python
- FastAPI
- Uvicorn
- Pytest
- HTTPX
- Pydantic
- CSV
- Swagger / OpenAPI

---

## 18. Ejecución rápida

Después de instalar las dependencias:

```powershell
# Cargar y verificar los pedidos
python cargar_csv.py

# Ejecutar los 15 escenarios
python bitacora.py

# Ejecutar las pruebas
python -m pytest -q

# Iniciar la API
uvicorn app.api:app --reload
```

Después abrir:

```text
http://127.0.0.1:8000/docs
```

para probar los endpoints mediante Swagger.

---

## 19. Objetivo académico

La práctica demuestra que las reglas de negocio permanecen dentro del dominio y no dentro de la interfaz HTTP.

Las entidades y Value Objects protegen sus invariantes, las Specifications permiten representar reglas reutilizables, la máquina de estados impide transiciones inválidas, los Domain Events registran hechos relevantes del negocio y FastAPI actúa únicamente como punto de entrada hacia la lógica implementada.
