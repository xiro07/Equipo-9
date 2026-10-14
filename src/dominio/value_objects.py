from __future__ import annotations
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP

from .comun import DominioException
from .enumeraciones import Moneda, TipoGarantia


def _redondear(valor) -> Decimal:
    return Decimal(str(valor)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class MonedaMonto:
    """Cantidad monetaria con su divisa. Impide mezclar monedas sin conversion explicita."""
    monto: Decimal
    moneda: Moneda = Moneda.USD

    def __post_init__(self) -> None:
        object.__setattr__(self, "monto", _redondear(self.monto))

    @staticmethod
    def usd(monto) -> "MonedaMonto":
        return MonedaMonto(monto, Moneda.USD)

    @staticmethod
    def mxn(monto) -> "MonedaMonto":
        return MonedaMonto(monto, Moneda.MXN)

    @staticmethod
    def cero(moneda: Moneda = Moneda.USD) -> "MonedaMonto":
        return MonedaMonto(0, moneda)

    @property
    def es_cero(self) -> bool:
        return self.monto == 0

    def sumar(self, otro: "MonedaMonto") -> "MonedaMonto":
        self._validar_misma_moneda(otro)
        return MonedaMonto(self.monto + otro.monto, self.moneda)

    def restar(self, otro: "MonedaMonto") -> "MonedaMonto":
        self._validar_misma_moneda(otro)
        return MonedaMonto(self.monto - otro.monto, self.moneda)

    def multiplicar(self, factor) -> "MonedaMonto":
        return MonedaMonto(self.monto * Decimal(str(factor)), self.moneda)

    def dividir(self, divisor) -> "MonedaMonto":
        if Decimal(str(divisor)) == 0:
            raise DominioException("No se puede dividir un monto entre cero.")
        return MonedaMonto(self.monto / Decimal(str(divisor)), self.moneda)

    def _validar_misma_moneda(self, otro: "MonedaMonto") -> None:
        if otro.moneda != self.moneda:
            raise DominioException(
                f"No se pueden mezclar monedas ({self.moneda.value} y {otro.moneda.value}) sin conversion explicita.")

    def __str__(self) -> str:
        return f"{self.monto:,.2f} {self.moneda.value}"


def _a_fecha(valor) -> date:
    return valor.date() if isinstance(valor, datetime) else valor


@dataclass(frozen=True)
class RangoDeFechas:
    """Fecha de entrada y salida. La salida debe ser estrictamente posterior a la entrada."""
    fecha_entrada: date
    fecha_salida: date

    def __post_init__(self) -> None:
        entrada, salida = _a_fecha(self.fecha_entrada), _a_fecha(self.fecha_salida)
        if salida <= entrada:
            raise DominioException("La fecha de salida debe ser posterior a la fecha de entrada.")
        object.__setattr__(self, "fecha_entrada", entrada)
        object.__setattr__(self, "fecha_salida", salida)

    def calcular_noches(self) -> int:
        return (self.fecha_salida - self.fecha_entrada).days

    def solapa(self, otro: "RangoDeFechas") -> bool:
        """Dos rangos se solapan si comparten al menos una noche."""
        return self.fecha_entrada < otro.fecha_salida and otro.fecha_entrada < self.fecha_salida


@dataclass(frozen=True)
class GarantiaPago:
    """Respaldo de pago. Su ausencia no impide reservar, solo genera una advertencia (US-08)."""
    tipo: TipoGarantia
    referencia: str

    def es_valida(self) -> bool:
        return bool(self.referencia and self.referencia.strip())


@dataclass(frozen=True)
class DetalleConsumo:
    """Cargo generado en un punto de venta. Datos obligatorios segun RN-12."""
    descripcion: str
    numero_vale: str
    monto: MonedaMonto
    fecha_hora: datetime
    origen: str
    numero_habitacion: str
    firma_huesped: str

    def validar_datos(self) -> None:
        for valor, nombre in ((self.descripcion, "descripcion"), (self.numero_vale, "numero de vale"),
                              (self.origen, "punto de venta de origen"),
                              (self.numero_habitacion, "numero de habitacion"),
                              (self.firma_huesped, "nombre/firma del huesped")):
            if not valor or not valor.strip():
                raise DominioException(f"El vale requiere {nombre} (RN-12).")
        if self.monto is None or self.monto.monto <= 0:
            raise DominioException("El monto del consumo debe ser mayor a cero.")


@dataclass(frozen=True)
class PagoFolio:
    monto: MonedaMonto
    fecha: datetime


@dataclass(frozen=True)
class AjusteFolio:
    """Ajuste con trazabilidad de quien lo autorizo (RN-08, RN-10)."""
    monto: MonedaMonto
    motivo: str
    autorizado_por: str | None
    fecha: datetime


@dataclass(frozen=True)
class AutorizacionGerencial:
    """Comprobante de autorizacion gerencial (ADR-006): la Aplicacion valida credenciales y lo entrega al Dominio."""
    gerente: str
    fecha_hora: datetime

    def __post_init__(self) -> None:
        if not self.gerente or not self.gerente.strip():
            raise DominioException("La autorizacion gerencial requiere identificar al gerente.")
