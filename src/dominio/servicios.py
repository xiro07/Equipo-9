from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from .comun import DominioException
from .entidades import Reserva
from .enumeraciones import CanalVenta, EstadoReserva, TipoCliente, TipoHabitacion
from .value_objects import MonedaMonto, RangoDeFechas


class TariffCalculationService:
    """
    Domain Service sin estado: tarifa final segun temporada, dia, canal y tipo de cliente (RN-01, RN-13).
    Los valores por defecto (BAR y factores) son supuestos parametrizables.
    """
    FACTOR_TEMPORADA_ALTA = Decimal("1.30")
    FACTOR_FIN_DE_SEMANA = Decimal("1.10")
    FACTORES_CANAL = {CanalVenta.WEB: Decimal("0.95"), CanalVenta.AGENCIA: Decimal("0.90")}
    FACTORES_CLIENTE = {TipoCliente.CORPORATIVO: Decimal("0.85"), TipoCliente.GRUPO: Decimal("0.90")}

    def __init__(self, bar_por_tipo: dict[TipoHabitacion, Decimal] | None = None) -> None:
        self._bar = bar_por_tipo or {
            TipoHabitacion.SENCILLA: Decimal("100"),
            TipoHabitacion.DOBLE: Decimal("150"),
            TipoHabitacion.SUITE: Decimal("300"),
        }

    def calcular_tarifa(self, rango: RangoDeFechas, tipo: TipoHabitacion,
                        canal: CanalVenta, cliente: TipoCliente) -> MonedaMonto:
        total = Decimal("0")
        dia = rango.fecha_entrada
        from datetime import timedelta
        while dia < rango.fecha_salida:
            total += self.tarifa_de_la_noche(dia, tipo)
            dia += timedelta(days=1)
        total *= self.FACTORES_CANAL.get(canal, Decimal("1")) * self.FACTORES_CLIENTE.get(cliente, Decimal("1"))
        return MonedaMonto.usd(total)

    def tarifa_de_la_noche(self, noche: date, tipo: TipoHabitacion) -> Decimal:
        if tipo not in self._bar:
            raise DominioException(f"No hay tarifa BAR definida para {tipo.value}.")
        tarifa = self._bar[tipo]
        if self.es_temporada_alta(noche):
            tarifa *= self.FACTOR_TEMPORADA_ALTA
        if noche.weekday() in (4, 5):  # viernes y sabado
            tarifa *= self.FACTOR_FIN_DE_SEMANA
        return tarifa

    @staticmethod
    def es_temporada_alta(fecha: date) -> bool:
        return (fecha.month in (7, 8) or (fecha.month == 12 and fecha.day >= 15)
                or (fecha.month == 1 and fecha.day <= 5))


@dataclass(frozen=True)
class HotelAliado:
    nombre: str
    categoria: TipoHabitacion
    tarifa_por_noche_usd: Decimal
    costo_transporte_usd: Decimal


class IHotelAliadoCatalogo(ABC):
    @abstractmethod
    def obtener_hoteles_aliados(self) -> list[HotelAliado]: ...


@dataclass(frozen=True)
class DatosReubicacion:
    hotel: HotelAliado
    diferencia_tarifaria: MonedaMonto
    costo_transporte: MonedaMonto
    cortesia: str


class WalkService:
    """Aplica la politica de walk (RN-06): hotel aliado, diferencia tarifaria, transporte y cortesia."""
    CORTESIA_POR_DEFECTO = "Traslado sin costo y desayuno de cortesia"

    def __init__(self, catalogo: IHotelAliadoCatalogo) -> None:
        self._catalogo = catalogo

    def gestionar_reubicacion(self, reserva: Reserva) -> DatosReubicacion:
        if reserva is None:
            raise DominioException("Se requiere la reserva a reubicar.")
        if reserva.estado != EstadoReserva.CONFIRMADA or reserva.rango is None or reserva.tarifa is None:
            raise DominioException("Solo una reserva confirmada puede reubicarse por overbooking.")
        hotel = self._buscar_hotel_aliado(reserva.tipo_habitacion)
        diferencia = self._calcular_diferencia_tarifaria(reserva, hotel)
        return DatosReubicacion(hotel, diferencia, MonedaMonto.usd(hotel.costo_transporte_usd),
                                self.CORTESIA_POR_DEFECTO)

    def _buscar_hotel_aliado(self, tipo: TipoHabitacion) -> HotelAliado:
        candidatos = sorted((h for h in self._catalogo.obtener_hoteles_aliados() if h.categoria == tipo),
                            key=lambda h: h.tarifa_por_noche_usd)
        if not candidatos:
            raise DominioException(f"No hay hotel aliado disponible para habitaciones {tipo.value}.")
        return candidatos[0]

    @staticmethod
    def _calcular_diferencia_tarifaria(reserva: Reserva, hotel: HotelAliado) -> MonedaMonto:
        """Si el hotel aliado es mas caro, la diferencia la absorbe el Hotel Costa Azul."""
        costo = MonedaMonto.usd(hotel.tarifa_por_noche_usd * reserva.rango.calcular_noches())
        diferencia = costo.restar(reserva.tarifa)
        return diferencia if diferencia.monto > 0 else MonedaMonto.cero()
