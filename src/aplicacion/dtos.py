from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True)
class CotizacionDto:
    hay_disponibilidad: bool
    habitaciones_disponibles: int
    tarifa_total: Decimal
    tarifa_por_noche: Decimal
    moneda: str


@dataclass(frozen=True)
class ReservaConfirmadaDto:
    reserva_id: UUID
    estado: str
    tarifa_total: Decimal
    moneda: str
    advertencias: list[str]


@dataclass(frozen=True)
class CancelacionDto:
    reserva_id: UUID
    estado: str
    tiene_penalizacion: bool
    penalizacion: Decimal
    moneda: str


@dataclass(frozen=True)
class CheckInDto:
    folio_id: UUID
    reserva_id: UUID
    numero_habitacion: str


@dataclass(frozen=True)
class CargoDto:
    numero_vale: str
    descripcion: str
    origen: str
    monto: Decimal
    fecha_hora: datetime


@dataclass(frozen=True)
class FolioDto:
    folio_id: UUID
    estado: str
    numero_habitacion: str
    saldo: Decimal
    moneda: str
    cargos: list[CargoDto]


@dataclass(frozen=True)
class CheckOutDto:
    folio_id: UUID
    estado_folio: str
    estado_habitacion: str


@dataclass(frozen=True)
class ReubicacionDto:
    requiere_reubicacion: bool
    mensaje: str
    hotel_aliado: str | None = None
    diferencia_tarifaria: Decimal = Decimal("0")
    costo_transporte: Decimal = Decimal("0")
    cortesia: str | None = None
