"""Raiz de composicion: arma la aplicacion con sus dependencias."""
from __future__ import annotations

from aplicacion.abstracciones import IAutorizacionGerencialService, IReloj
from aplicacion.servicios import RecepcionAppService, ReservacionAppService
from dominio.servicios import IHotelAliadoCatalogo, TariffCalculationService, WalkService

from .persistencia import (InMemoryFolioRepository, InMemoryHabitacionRepository, InMemoryReservaRepository,
                           InMemoryUnitOfWork, PMSDatabase)
from .servicios import AutorizacionGerencialService, HotelAliadoCatalogoEnMemoria, InMemoryEventBus, SistemaReloj


class PMSComposition:
    def __init__(self, database: PMSDatabase | None = None, reloj: IReloj | None = None,
                 autorizaciones: IAutorizacionGerencialService | None = None,
                 hoteles: IHotelAliadoCatalogo | None = None) -> None:
        self.database = database or PMSDatabase.con_datos_iniciales()
        self.event_bus = InMemoryEventBus()
        reloj = reloj or SistemaReloj()
        autorizaciones = autorizaciones or AutorizacionGerencialService()
        hoteles = hoteles or HotelAliadoCatalogoEnMemoria()

        uow = InMemoryUnitOfWork(self.database)
        reservas = InMemoryReservaRepository(self.database, uow)
        folios = InMemoryFolioRepository(self.database, uow)
        habitaciones = InMemoryHabitacionRepository(self.database, uow)

        tarifas = TariffCalculationService()
        walk = WalkService(hoteles)
        self.reservaciones = ReservacionAppService(reservas, habitaciones, uow, tarifas, self.event_bus, reloj)
        self.recepcion = RecepcionAppService(reservas, folios, habitaciones, uow, walk, autorizaciones,
                                             self.event_bus, reloj)
