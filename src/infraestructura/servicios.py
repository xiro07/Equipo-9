from __future__ import annotations
from datetime import datetime
from decimal import Decimal
from typing import Callable

from aplicacion.abstracciones import AutorizacionInvalidaException, IAutorizacionGerencialService, IEventBus, IReloj
from dominio.comun import DomainEvent
from dominio.enumeraciones import TipoHabitacion
from dominio.servicios import HotelAliado, IHotelAliadoCatalogo
from dominio.value_objects import AutorizacionGerencial


class SistemaReloj(IReloj):
    @property
    def ahora(self) -> datetime:
        return datetime.now()


class RelojFijo(IReloj):
    """Reloj controlable (demo y pruebas deterministas)."""

    def __init__(self, ahora: datetime) -> None:
        self._ahora = ahora

    @property
    def ahora(self) -> datetime:
        return self._ahora

    @ahora.setter
    def ahora(self, valor: datetime) -> None:
        self._ahora = valor


class InMemoryEventBus(IEventBus):
    def __init__(self) -> None:
        self.publicados: list[DomainEvent] = []
        self.suscriptores: list[Callable[[DomainEvent], None]] = []

    def publicar(self, evento: DomainEvent) -> None:
        self.publicados.append(evento)
        for s in self.suscriptores:
            s(evento)


class AutorizacionGerencialService(IAutorizacionGerencialService):
    """Valida contra una lista en memoria (sustituir por el proveedor de identidad real)."""

    def __init__(self, gerentes: dict[str, str] | None = None) -> None:
        self._gerentes = gerentes or {"gerente": "1234"}

    def validar(self, usuario: str, clave: str, ahora: datetime) -> AutorizacionGerencial:
        if self._gerentes.get(usuario) != clave:
            raise AutorizacionInvalidaException()
        return AutorizacionGerencial(usuario, ahora)


class HotelAliadoCatalogoEnMemoria(IHotelAliadoCatalogo):
    def __init__(self, hoteles: list[HotelAliado] | None = None) -> None:
        self._hoteles = hoteles or [
            HotelAliado("Hotel Brisa Marina", TipoHabitacion.SENCILLA, Decimal("110"), Decimal("15")),
            HotelAliado("Hotel Brisa Marina", TipoHabitacion.DOBLE, Decimal("165"), Decimal("15")),
            HotelAliado("Gran Hotel Palmas", TipoHabitacion.SUITE, Decimal("340"), Decimal("20")),
        ]

    def obtener_hoteles_aliados(self) -> list[HotelAliado]:
        return list(self._hoteles)
