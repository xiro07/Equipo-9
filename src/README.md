# PMS Hotel Costa Azul – Python 3.10+

Implementación del diagrama de clases (DDD) y de las 2 secuencias, separada en capas. Sin dependencias externas.

| Paquete | Capa | Contenido |
|---|---|---|
| `dominio/` | Dominio | `Reserva` y `Folio` (Aggregate Roots), `Habitacion`, `Huesped`; Value Objects (`MonedaMonto`, `RangoDeFechas`, `GarantiaPago`, `DetalleConsumo`, `AutorizacionGerencial`); `TariffCalculationService`, `WalkService`; eventos; interfaces de repositorio y `IUnitOfWork`. |
| `aplicacion/` | Aplicación | `ReservacionAppService`, `RecepcionAppService`; Commands/Queries/DTOs (CQRS básico); abstracciones (`IEventBus`, `IReloj`, `IAutorizacionGerencialService`). Solo depende del Dominio. |
| `infraestructura/` | Infraestructura | Base en memoria, repositorios, `InMemoryUnitOfWork`, event bus, validación gerencial, catálogo de hoteles aliados, `PMSComposition`. |
| `main.py` | Demo | Secuencia 01, secuencia 02 y flujo check-in → cargos → ajuste → check-out. |
| `tests/` | Pruebas | 35 pruebas `unittest`. |

## Ejecutar
```
python main.py
python -m unittest discover -s tests -t . -v
```
En Visual Studio / VS Code: abrir la carpeta, usar un intérprete Python 3.10+ y ejecutar `main.py`.

## Correspondencia con los diagramas
- Secuencia 01: `ReservacionAppService.confirmar_reservacion`.
- Secuencia 02: `RecepcionAppService.gestionar_excepcion_overbooking`.
- Reglas: RN-03 late check-out, RN-04 cancelación <48 h, RN-05 no-show 23:59, RN-06 overbooking/walk, RN-07 datos fiscales y depósito grupal 30 %, RN-08/RN-10 autorización gerencial (ajustes > USD 50, ADR-006), RN-12 datos del vale, RN-13 tarifas.

## Supuestos (la documentación no da el valor exacto; fáciles de cambiar)
- Tarifas: BAR Sencilla 100 / Doble 150 / Suite 300 USD; temporada alta (jul-ago, 15-dic a 5-ene) +30 %; viernes y sábado +10 %; canal Web −5 %, Agencia −10 %; cliente Corporativo −15 %, Grupo −10 %.
- Late check-out: tras 12:00 hasta 18:00 = 50 % de una noche; tras 18:00 = 100 %.
- Hoteles aliados y credenciales de gerente (`gerente` / `1234`) son datos de ejemplo.
- Se añadió el estado `CheckInRealizado` a la reserva (evita dobles check-in); una habitación que sale de Fuera de Servicio regresa como `Sucia`.
- La base es en memoria (en lugar de SQL); para SQL basta crear nuevas implementaciones de las interfaces del Dominio.
- Limitación: el Unit of Work en memoria aplica las escrituras en `commit()`, pero los objetos leídos son las mismas instancias almacenadas.
