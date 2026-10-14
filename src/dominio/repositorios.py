"""Interfaces de persistencia: viven en el Dominio (ADR-004) y se implementan en Infraestructura."""
from __future__ import annotations
from abc import ABC, abstractmethod
from uuid import UUID

from .entidades import Folio, Habitacion, Reserva
from .enumeraciones import TipoHabitacion
from .value_objects import RangoDeFechas


class IReservaRepository(ABC):
    @abstractmethod
    def find_by_id(self, id: UUID) -> Reserva | None: ...

    @abstractmethod
    def save(self, reserva: Reserva) -> None: ...


class IFolioRepository(ABC):
    @abstractmethod
    def find_by_id(self, id: UUID) -> Folio | None: ...

    @abstractmethod
    def find_active_by_habitacion(self, habitacion_id: UUID) -> Folio | None: ...

    @abstractmethod
    def save(self, folio: Folio) -> None: ...


class IHabitacionRepository(ABC):
    @abstractmethod
    def find_by_id(self, id: UUID) -> Habitacion | None: ...

    @abstractmethod
    def find_disponibles(self, rango: RangoDeFechas, tipo: TipoHabitacion,
                         excluir_reserva_id: UUID | None = None) -> list[Habitacion]:
        """Habitaciones con inventario libre en el rango (no fuera de servicio, no comprometidas por otras reservas)."""

    @abstractmethod
    def save(self, habitacion: Habitacion) -> None: ...


class IUnitOfWork(ABC):
    @abstractmethod
    def begin(self) -> None: ...

    @abstractmethod
    def commit(self) -> None: ...

    @abstractmethod
    def rollback(self) -> None: ...
