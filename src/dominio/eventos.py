from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from .comun import DomainEvent


@dataclass(frozen=True)
class ReservaConfirmada(DomainEvent):
    reserva_id: UUID


@dataclass(frozen=True)
class ReservaGrupalConfirmada(DomainEvent):
    reserva_id: UUID
    numero_habitaciones: int


@dataclass(frozen=True)
class ReservaCanceladaSinCargo(DomainEvent):
    reserva_id: UUID


@dataclass(frozen=True)
class ReservaCanceladaConPenalizacion(DomainEvent):
    reserva_id: UUID
    penalizacion: Decimal


@dataclass(frozen=True)
class ReservaNoShow(DomainEvent):
    reserva_id: UUID
    cargo_aplicado: Decimal


@dataclass(frozen=True)
class ReservaReubicada(DomainEvent):
    reserva_id: UUID
    hotel_aliado: str


@dataclass(frozen=True)
class CheckInRegistrado(DomainEvent):
    folio_id: UUID
    reserva_id: UUID


@dataclass(frozen=True)
class CargoAgregadoAlFolio(DomainEvent):
    folio_id: UUID
    numero_vale: str
    monto: Decimal


@dataclass(frozen=True)
class AjusteAplicadoAlFolio(DomainEvent):
    folio_id: UUID
    monto: Decimal
    autorizado_por: str | None


@dataclass(frozen=True)
class CheckOutRegistrado(DomainEvent):
    folio_id: UUID
