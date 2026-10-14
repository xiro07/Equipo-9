"""CQRS basico (ADR-005): Commands (modifican estado) y Queries (solo leen)."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from dominio.enumeraciones import CanalVenta, TipoCliente, TipoGarantia, TipoHabitacion


@dataclass(frozen=True)
class DatosHuespedDto:
    nombre_completo: str
    identificacion: str | None = None
    nacionalidad: str | None = None
    contacto: str | None = None


@dataclass(frozen=True)
class GarantiaPagoDto:
    tipo: TipoGarantia
    referencia: str


@dataclass(frozen=True)
class ConfirmarReservacionCommand:
    huesped: DatosHuespedDto
    fecha_entrada: date
    fecha_salida: date
    tipo_habitacion: TipoHabitacion
    canal_venta: CanalVenta
    tipo_cliente: TipoCliente
    garantia: GarantiaPagoDto | None = None
    numero_habitaciones: int = 1
    deposito_grupal_usd: Decimal | None = None


@dataclass(frozen=True)
class CancelarReservacionCommand:
    reserva_id: UUID


@dataclass(frozen=True)
class RegistrarCheckInCommand:
    reserva_id: UUID
    identificacion: str
    nacionalidad: str
    solicita_factura: bool = False
    rfc: str | None = None
    razon_social: str | None = None


@dataclass(frozen=True)
class RegistrarCargoCommand:
    folio_id: UUID
    descripcion: str
    numero_vale: str
    monto: Decimal
    origen: str
    firma_huesped: str


@dataclass(frozen=True)
class RegistrarPagoCommand:
    folio_id: UUID
    monto: Decimal


@dataclass(frozen=True)
class AplicarAjusteFolioCommand:
    folio_id: UUID
    monto: Decimal
    motivo: str
    usuario_gerente: str | None = None
    clave_gerente: str | None = None


@dataclass(frozen=True)
class RegistrarCheckOutCommand:
    folio_id: UUID


@dataclass(frozen=True)
class GestionarExcepcionOverbookingCommand:
    reserva_id: UUID


@dataclass(frozen=True)
class ConsultarTarifaQuery:
    fecha_entrada: date
    fecha_salida: date
    tipo_habitacion: TipoHabitacion
    canal_venta: CanalVenta
    tipo_cliente: TipoCliente


@dataclass(frozen=True)
class ConsultarFolioQuery:
    folio_id: UUID
