from __future__ import annotations
from abc import ABC, abstractmethod
from contextlib import contextmanager
from datetime import datetime
from typing import Iterator

from dominio.comun import DomainEvent
from dominio.repositorios import IUnitOfWork
from dominio.value_objects import AutorizacionGerencial


class IEventBus(ABC):
    @abstractmethod
    def publicar(self, evento: DomainEvent) -> None: ...


class IReloj(ABC):
    @property
    @abstractmethod
    def ahora(self) -> datetime: ...


class IAutorizacionGerencialService(ABC):
    """Valida credenciales/rol gerencial (ADR-006) y devuelve el comprobante que se pasa al Dominio."""
    @abstractmethod
    def validar(self, usuario: str, clave: str, ahora: datetime) -> AutorizacionGerencial: ...


class AplicacionException(Exception):
    pass


class NoEncontradoException(AplicacionException):
    def __init__(self, entidad: str, id) -> None:
        super().__init__(f"No se encontro {entidad} con id {id}.")


class SinDisponibilidadException(AplicacionException):
    pass


class AutorizacionInvalidaException(AplicacionException):
    def __init__(self) -> None:
        super().__init__("Credenciales gerenciales invalidas.")


@contextmanager
def transaccion(uow: IUnitOfWork) -> Iterator[None]:
    """begin -> bloque -> commit (rollback si falla)."""
    uow.begin()
    try:
        yield
        uow.commit()
    except BaseException:
        uow.rollback()
        raise
