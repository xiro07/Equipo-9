"""Persistencia en memoria (reemplaza la base SQL del diagrama para probar sin instalar nada)."""
from __future__ import annotations
from threading import RLock
from typing import Callable
from uuid import UUID

from dominio.entidades import Folio, Habitacion, Reserva
from dominio.enumeraciones import EstadoFolio, EstadoHabitacion, EstadoReserva, TipoHabitacion
from dominio.repositorios import IFolioRepository, IHabitacionRepository, IReservaRepository, IUnitOfWork
from dominio.value_objects import RangoDeFechas


class PMSDatabase:
    def __init__(self) -> None:
        self.reservas: dict[UUID, Reserva] = {}
        self.folios: dict[UUID, Folio] = {}
        self.habitaciones: dict[UUID, Habitacion] = {}
        self.sync = RLock()  # una unidad de trabajo a la vez protege el inventario

    @classmethod
    def con_datos_iniciales(cls) -> "PMSDatabase":
        """5 sencillas, 5 dobles y 2 suites."""
        db = cls()
        for i in range(1, 6):
            db.agregar(Habitacion(f"10{i}", TipoHabitacion.SENCILLA))
        for i in range(1, 6):
            db.agregar(Habitacion(f"20{i}", TipoHabitacion.DOBLE))
        for i in range(1, 3):
            db.agregar(Habitacion(f"30{i}", TipoHabitacion.SUITE))
        return db

    def agregar(self, habitacion: Habitacion) -> Habitacion:
        self.habitaciones[habitacion.id] = habitacion
        return habitacion


class InMemoryUnitOfWork(IUnitOfWork):
    """Las escrituras se aplican juntas en commit(); rollback() las descarta. begin() toma el cerrojo."""

    def __init__(self, db: PMSDatabase) -> None:
        self._db = db
        self._pendientes: list[Callable[[], None]] = []
        self.activa = False

    def begin(self) -> None:
        if self.activa:
            raise RuntimeError("Ya hay una transaccion activa.")
        self._db.sync.acquire()
        self.activa = True
        self._pendientes.clear()

    def commit(self) -> None:
        if not self.activa:
            raise RuntimeError("No hay una transaccion activa.")
        try:
            for escritura in self._pendientes:
                escritura()
        finally:
            self._terminar()

    def rollback(self) -> None:
        if self.activa:
            self._terminar()

    def registrar(self, escritura: Callable[[], None]) -> None:
        """Usado por los repositorios: difiere la escritura si hay transaccion; si no, la aplica de inmediato."""
        if self.activa:
            self._pendientes.append(escritura)
        else:
            with self._db.sync:
                escritura()

    def _terminar(self) -> None:
        self._pendientes.clear()
        self.activa = False
        self._db.sync.release()


class InMemoryReservaRepository(IReservaRepository):
    def __init__(self, db: PMSDatabase, uow: InMemoryUnitOfWork) -> None:
        self._db, self._uow = db, uow

    def find_by_id(self, id: UUID) -> Reserva | None:
        return self._db.reservas.get(id)

    def save(self, reserva: Reserva) -> None:
        self._uow.registrar(lambda: self._db.reservas.__setitem__(reserva.id, reserva))


class InMemoryFolioRepository(IFolioRepository):
    def __init__(self, db: PMSDatabase, uow: InMemoryUnitOfWork) -> None:
        self._db, self._uow = db, uow

    def find_by_id(self, id: UUID) -> Folio | None:
        return self._db.folios.get(id)

    def find_active_by_habitacion(self, habitacion_id: UUID) -> Folio | None:
        return next((f for f in self._db.folios.values()
                     if f.habitacion_id == habitacion_id and f.estado == EstadoFolio.ABIERTO), None)

    def save(self, folio: Folio) -> None:
        self._uow.registrar(lambda: self._db.folios.__setitem__(folio.id, folio))


class InMemoryHabitacionRepository(IHabitacionRepository):
    def __init__(self, db: PMSDatabase, uow: InMemoryUnitOfWork) -> None:
        self._db, self._uow = db, uow

    def find_by_id(self, id: UUID) -> Habitacion | None:
        return self._db.habitaciones.get(id)

    def find_disponibles(self, rango: RangoDeFechas, tipo: TipoHabitacion,
                         excluir_reserva_id: UUID | None = None) -> list[Habitacion]:
        comprometidas = [r for r in self._db.reservas.values()
                         if r.tipo_habitacion == tipo and r.id != excluir_reserva_id
                         and r.estado in (EstadoReserva.CONFIRMADA, EstadoReserva.CHECK_IN_REALIZADO)
                         and r.rango is not None and r.rango.solapa(rango)]
        asignadas = {r.habitacion_asignada_id for r in comprometidas if r.habitacion_asignada_id}
        # Las reservas confirmadas sin habitacion asignada consumen inventario del tipo.
        sin_asignar = sum(r.numero_habitaciones for r in comprometidas if not r.habitacion_asignada_id)

        libres = [h for h in self._db.habitaciones.values()
                  if h.tipo == tipo and h.estado != EstadoHabitacion.FUERA_DE_SERVICIO and h.id not in asignadas]
        # se descuentan primero las habitaciones aun no listas, para conservar las Disponibles
        libres.sort(key=lambda h: (h.estado == EstadoHabitacion.DISPONIBLE, h.numero))
        return sorted(libres[sin_asignar:], key=lambda h: h.numero)

    def save(self, habitacion: Habitacion) -> None:
        self._uow.registrar(lambda: self._db.habitaciones.__setitem__(habitacion.id, habitacion))
