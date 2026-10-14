"""Piezas comunes del dominio."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime


class DominioException(Exception):
    """Se lanza cuando se viola una regla/invariante del negocio."""


@dataclass(frozen=True)
class DomainEvent:
    ocurrido_en: datetime


class AggregateRoot:
    """Base de los Aggregate Roots: acumula los eventos de dominio generados."""

    def __init__(self) -> None:
        self._eventos: list[DomainEvent] = []

    @property
    def eventos_de_dominio(self) -> list[DomainEvent]:
        return list(self._eventos)

    def _registrar(self, evento: DomainEvent) -> None:
        self._eventos.append(evento)

    def limpiar_eventos(self) -> None:
        self._eventos.clear()
