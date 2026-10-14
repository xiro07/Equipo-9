from __future__ import annotations
from datetime import datetime, timedelta, time
from decimal import Decimal
from uuid import UUID, uuid4

from . import eventos as ev
from .comun import AggregateRoot, DominioException
from .enumeraciones import (CanalVenta, EstadoFolio, EstadoHabitacion, EstadoReserva, Moneda,
                            TipoCliente, TipoGarantia, TipoHabitacion)
from .value_objects import (AjusteFolio, AutorizacionGerencial, DetalleConsumo, GarantiaPago,
                            MonedaMonto, PagoFolio, RangoDeFechas)


class Huesped:
    """Entidad de apoyo (no es Aggregate Root). Vive dentro de la Reserva."""

    def __init__(self, nombre_completo: str, identificacion: str | None = None,
                 nacionalidad: str | None = None, contacto: str | None = None) -> None:
        if not nombre_completo or not nombre_completo.strip():
            raise DominioException("El huesped requiere nombre completo.")
        self.id: UUID = uuid4()
        self.nombre_completo = nombre_completo
        self.identificacion = identificacion
        self.nacionalidad = nacionalidad
        self.contacto = contacto
        self.rfc: str | None = None
        self.razon_social: str | None = None

    def actualizar_identidad(self, identificacion: str, nacionalidad: str) -> None:
        """Validaciones obligatorias de identidad al hacer check-in."""
        if not identificacion or not identificacion.strip():
            raise DominioException("La identificacion del huesped es obligatoria para el check-in.")
        if not nacionalidad or not nacionalidad.strip():
            raise DominioException("La nacionalidad del huesped es obligatoria para el check-in.")
        self.identificacion, self.nacionalidad = identificacion, nacionalidad

    def registrar_datos_fiscales(self, rfc: str, razon_social: str) -> None:
        """Obligatorios cuando se solicita factura (RN-07)."""
        if not rfc or not rfc.strip() or not razon_social or not razon_social.strip():
            raise DominioException("Los datos fiscales (RFC y razon social) son obligatorios cuando se solicita factura.")
        self.rfc, self.razon_social = rfc, razon_social


class Habitacion:
    """Entidad con ciclo de vida operativo. Se referencia por Id desde Reserva y Folio (ADR-002)."""

    def __init__(self, numero: str, tipo: TipoHabitacion,
                 estado: EstadoHabitacion = EstadoHabitacion.DISPONIBLE) -> None:
        if not numero or not numero.strip():
            raise DominioException("La habitacion requiere numero.")
        self.id: UUID = uuid4()
        self.numero = numero
        self.tipo = tipo
        self.estado = estado

    def _exigir(self, esperado: EstadoHabitacion, mensaje: str) -> None:
        if self.estado != esperado:
            raise DominioException(f"{mensaje} (estado: {self.estado.value}).")

    def ocupar(self) -> None:
        self._exigir(EstadoHabitacion.DISPONIBLE, f"La habitacion {self.numero} no esta disponible para ocuparse")
        self.estado = EstadoHabitacion.OCUPADA

    def marcar_sucia(self) -> None:
        self._exigir(EstadoHabitacion.OCUPADA, "Solo una habitacion ocupada puede pasar a sucia")
        self.estado = EstadoHabitacion.SUCIA

    def marcar_limpia(self) -> None:
        self._exigir(EstadoHabitacion.SUCIA, "Solo una habitacion sucia puede pasar a limpia")
        self.estado = EstadoHabitacion.LIMPIA

    def inspeccionar(self) -> None:
        self._exigir(EstadoHabitacion.LIMPIA, "Solo una habitacion limpia puede inspeccionarse")
        self.estado = EstadoHabitacion.DISPONIBLE

    def marcar_fuera_de_servicio(self) -> None:
        if self.estado == EstadoHabitacion.OCUPADA:
            raise DominioException("No se puede declarar fuera de servicio una habitacion ocupada.")
        self.estado = EstadoHabitacion.FUERA_DE_SERVICIO

    def reincorporar(self, autorizacion: AutorizacionGerencial | None) -> None:
        """Salir de Fuera de Servicio requiere autorizacion gerencial. Regresa como Sucia."""
        if autorizacion is None:
            raise DominioException("Reincorporar una habitacion fuera de servicio requiere autorizacion gerencial.")
        self._exigir(EstadoHabitacion.FUERA_DE_SERVICIO, "La habitacion no esta fuera de servicio")
        self.estado = EstadoHabitacion.SUCIA


class Reserva(AggregateRoot):
    """
    Aggregate Root del contexto Reservaciones. Protege: fechas validas, politica de cancelacion (RN-04),
    no-show (RN-05), deposito grupal (RN-07) y tarifa confirmada inmodificable sin autorizacion gerencial (RN-08).
    """
    HABITACIONES_PARA_RESERVA_GRUPAL = 10
    PORCENTAJE_DEPOSITO_GRUPAL = Decimal("0.30")
    HORAS_LIMITE_CANCELACION_SIN_CARGO = 48

    def __init__(self, tipo_habitacion: TipoHabitacion, canal_venta: CanalVenta,
                 tipo_cliente: TipoCliente, numero_habitaciones: int = 1) -> None:
        super().__init__()
        if numero_habitaciones < 1:
            raise DominioException("La reserva debe incluir al menos una habitacion.")
        self.id: UUID = uuid4()
        self.estado = EstadoReserva.PENDIENTE
        self.tipo_habitacion = tipo_habitacion
        self.canal_venta = canal_venta
        self.tipo_cliente = tipo_cliente
        self.numero_habitaciones = numero_habitaciones
        self.huesped: Huesped | None = None
        self.rango: RangoDeFechas | None = None
        self.garantia: GarantiaPago | None = None
        self.tarifa: MonedaMonto | None = None
        self.deposito_grupal: MonedaMonto | None = None
        self.habitacion_asignada_id: UUID | None = None
        self.hotel_aliado: str | None = None
        self.advertencias: list[str] = []

    @property
    def es_grupal(self) -> bool:
        return self.numero_habitaciones >= self.HABITACIONES_PARA_RESERVA_GRUPAL

    @classmethod
    def nueva(cls, tipo, canal, cliente, numero_habitaciones: int = 1) -> "Reserva":
        return cls(tipo, canal, cliente, numero_habitaciones)

    def confirmar(self, huesped: Huesped, rango: RangoDeFechas, garantia: GarantiaPago | None,
                  tarifa_final: MonedaMonto, ahora: datetime, deposito_grupal: MonedaMonto | None = None) -> None:
        """Secuencia 01: validarFechas, validarGarantia, reservaConfirmada."""
        if self.estado != EstadoReserva.PENDIENTE:
            raise DominioException(f"Solo una reserva pendiente puede confirmarse (estado: {self.estado.value}).")
        if huesped is None:
            raise DominioException("La reserva requiere los datos del huesped.")
        self._validar_fechas(rango, ahora)
        self._validar_garantia(garantia)
        if tarifa_final is None or tarifa_final.monto <= 0:
            raise DominioException("La tarifa final debe ser mayor a cero.")

        if self.es_grupal:
            minimo = tarifa_final.multiplicar(self.PORCENTAJE_DEPOSITO_GRUPAL)
            if (deposito_grupal is None or deposito_grupal.moneda != minimo.moneda
                    or deposito_grupal.monto < minimo.monto):
                raise DominioException(
                    f"La reserva grupal (>= {self.HABITACIONES_PARA_RESERVA_GRUPAL} habitaciones) requiere un "
                    f"deposito minimo del 30% ({minimo}) antes de confirmarse (RN-07).")
            self.deposito_grupal = deposito_grupal

        self.huesped, self.rango, self.garantia, self.tarifa = huesped, rango, garantia, tarifa_final
        self.estado = EstadoReserva.CONFIRMADA
        self._registrar(ev.ReservaConfirmada(ocurrido_en=ahora, reserva_id=self.id))
        if self.es_grupal:
            self._registrar(ev.ReservaGrupalConfirmada(
                ocurrido_en=ahora, reserva_id=self.id, numero_habitaciones=self.numero_habitaciones))

    @staticmethod
    def _validar_fechas(rango: RangoDeFechas, ahora: datetime) -> None:
        if rango is None:
            raise DominioException("La reserva requiere un rango de fechas.")
        if rango.fecha_entrada < ahora.date():
            raise DominioException("La fecha de entrada no puede estar en el pasado.")

    def _validar_garantia(self, garantia: GarantiaPago | None) -> None:
        if garantia is None:
            self.advertencias.append("Reserva sin garantia de pago: riesgo de no-show sin cobro (US-08).")
        elif not garantia.es_valida():
            raise DominioException("La garantia de pago proporcionada no es valida.")

    def cancelar(self, ahora: datetime) -> MonedaMonto:
        """Si faltan menos de 48 h para la llegada se cobra la primera noche (RN-04)."""
        self._exigir_confirmada("cancelar")
        llegada = datetime.combine(self.rango.fecha_entrada, time.min)
        horas = (llegada - ahora).total_seconds() / 3600
        penalizacion = (self.primera_noche() if horas < self.HORAS_LIMITE_CANCELACION_SIN_CARGO
                        else MonedaMonto.cero(self.tarifa.moneda))
        self.estado = EstadoReserva.CANCELADA
        if penalizacion.es_cero:
            self._registrar(ev.ReservaCanceladaSinCargo(ocurrido_en=ahora, reserva_id=self.id))
        else:
            self._registrar(ev.ReservaCanceladaConPenalizacion(
                ocurrido_en=ahora, reserva_id=self.id, penalizacion=penalizacion.monto))
        return penalizacion

    def marcar_no_show(self, ahora: datetime) -> MonedaMonto:
        """Despues de las 23:59 del dia de llegada; cobra primera noche si hay tarjeta de garantia (RN-05)."""
        self._exigir_confirmada("marcar no-show")
        limite = datetime.combine(self.rango.fecha_entrada, time(23, 59))
        if ahora < limite:
            raise DominioException("El no-show solo puede registrarse despues de las 23:59 de la fecha de llegada.")
        con_tarjeta = self.garantia is not None and self.garantia.tipo == TipoGarantia.TARJETA_CREDITO
        cargo = self.primera_noche() if con_tarjeta else MonedaMonto.cero(self.tarifa.moneda)
        self.estado = EstadoReserva.NO_SHOW
        self._registrar(ev.ReservaNoShow(ocurrido_en=ahora, reserva_id=self.id, cargo_aplicado=cargo.monto))
        return cargo

    def marcar_reubicada(self, hotel_aliado: str, ahora: datetime) -> None:
        """Reubicacion por overbooking (walk) - Secuencia 02."""
        self._exigir_confirmada("reubicar")
        if not hotel_aliado or not hotel_aliado.strip():
            raise DominioException("La reubicacion requiere un hotel aliado.")
        self.hotel_aliado = hotel_aliado
        self.estado = EstadoReserva.REUBICADA
        self._registrar(ev.ReservaReubicada(ocurrido_en=ahora, reserva_id=self.id, hotel_aliado=hotel_aliado))

    def asignar_habitacion(self, habitacion_id: UUID) -> None:
        self._exigir_confirmada("asignar habitacion")
        self.habitacion_asignada_id = habitacion_id
        self.estado = EstadoReserva.CHECK_IN_REALIZADO

    def modificar_tarifa(self, nueva_tarifa: MonedaMonto, autorizacion: AutorizacionGerencial | None) -> None:
        """La tarifa confirmada no puede modificarse sin autorizacion gerencial (RN-08)."""
        self._exigir_confirmada("modificar tarifa")
        if autorizacion is None:
            raise DominioException("Modificar una tarifa confirmada requiere autorizacion gerencial (RN-08).")
        if nueva_tarifa is None or nueva_tarifa.monto <= 0:
            raise DominioException("La nueva tarifa debe ser mayor a cero.")
        self.tarifa = nueva_tarifa

    def primera_noche(self) -> MonedaMonto:
        return self.tarifa.dividir(self.rango.calcular_noches())

    def _exigir_confirmada(self, accion: str) -> None:
        if self.estado != EstadoReserva.CONFIRMADA:
            raise DominioException(f"No se puede {accion}: la reserva esta en estado {self.estado.value}.")


class Folio(AggregateRoot):
    """
    Aggregate Root EstanciaFolio. Invariantes: cargos con datos de vale completos (RN-12), no cerrar con saldo
    distinto de cero (US-13) y ajustes mayores a USD 50 con autorizacion gerencial (RN-10).
    """
    LIMITE_AJUSTE_SIN_AUTORIZACION_USD = Decimal("50")
    HORA_SALIDA_ESTANDAR = time(12, 0)
    HORA_LIMITE_LATE_CHECK_OUT_PARCIAL = time(18, 0)

    def __init__(self, reserva_id: UUID, habitacion_id: UUID, numero_habitacion: str, huesped_id: UUID,
                 tarifa_noche: MonedaMonto, tipo_cambio_por_usd: Decimal = Decimal("1")) -> None:
        super().__init__()
        self.id: UUID = uuid4()
        self.reserva_id = reserva_id
        self.habitacion_id = habitacion_id
        self.numero_habitacion = numero_habitacion
        self.huesped_id = huesped_id
        self.tarifa_noche = tarifa_noche
        self.moneda: Moneda = tarifa_noche.moneda
        self.tipo_cambio_por_usd = Decimal(str(tipo_cambio_por_usd))
        self.saldo = MonedaMonto.cero(self.moneda)
        self.estado = EstadoFolio.ABIERTO
        self.cargos: list[DetalleConsumo] = []
        self.pagos: list[PagoFolio] = []
        self.ajustes: list[AjusteFolio] = []
        self._late_check_out_aplicado = False

    @classmethod
    def abrir(cls, reserva_id, habitacion_id, numero_habitacion, huesped_id, tarifa_noche: MonedaMonto,
              ahora: datetime, tipo_cambio_por_usd=1) -> "Folio":
        """Abre el folio al registrar el check-in."""
        if Decimal(str(tipo_cambio_por_usd)) <= 0:
            raise DominioException("El tipo de cambio debe ser mayor a cero.")
        folio = cls(reserva_id, habitacion_id, numero_habitacion, huesped_id, tarifa_noche, tipo_cambio_por_usd)
        folio._registrar(ev.CheckInRegistrado(ocurrido_en=ahora, folio_id=folio.id, reserva_id=reserva_id))
        return folio

    def agregar_cargo(self, cargo: DetalleConsumo, ahora: datetime) -> None:
        self._exigir_abierto()
        if cargo is None:
            raise DominioException("El cargo es obligatorio.")
        cargo.validar_datos()
        self._exigir_misma_moneda(cargo.monto)
        self.cargos.append(cargo)
        self.saldo = self.saldo.sumar(cargo.monto)
        self._registrar(ev.CargoAgregadoAlFolio(
            ocurrido_en=ahora, folio_id=self.id, numero_vale=cargo.numero_vale, monto=cargo.monto.monto))

    def aplicar_pago(self, pago: MonedaMonto, ahora: datetime) -> None:
        self._exigir_abierto()
        if pago is None or pago.monto <= 0:
            raise DominioException("El pago debe ser mayor a cero.")
        self._exigir_misma_moneda(pago)
        self.pagos.append(PagoFolio(pago, ahora))
        self.saldo = self.saldo.restar(pago)

    def aplicar_ajuste(self, ajuste: MonedaMonto, motivo: str, autorizacion: AutorizacionGerencial | None,
                       ahora: datetime) -> None:
        """Positivo = cargo, negativo = descuento. Mayor a USD 50 exige autorizacion gerencial (RN-10)."""
        self._exigir_abierto()
        if ajuste is None or ajuste.es_cero:
            raise DominioException("El ajuste debe ser distinto de cero.")
        if not motivo or not motivo.strip():
            raise DominioException("El ajuste requiere un motivo.")
        self._exigir_misma_moneda(ajuste)
        limite = self.LIMITE_AJUSTE_SIN_AUTORIZACION_USD * self.tipo_cambio_por_usd
        if abs(ajuste.monto) > limite and autorizacion is None:
            raise DominioException(
                f"Un ajuste mayor a USD {self.LIMITE_AJUSTE_SIN_AUTORIZACION_USD} requiere autorizacion gerencial previa (RN-10).")
        gerente = autorizacion.gerente if autorizacion else None
        self.ajustes.append(AjusteFolio(ajuste, motivo, gerente, ahora))
        self.saldo = self.saldo.sumar(ajuste)
        self._registrar(ev.AjusteAplicadoAlFolio(
            ocurrido_en=ahora, folio_id=self.id, monto=ajuste.monto, autorizado_por=gerente))

    def aplicar_late_check_out(self, hora_salida: time, ahora: datetime) -> None:
        """
        RN-03. Supuesto de implementacion: despues de las 12:00 y hasta las 18:00 se cobra 50% de una noche;
        despues de las 18:00, el 100%. Ajustar a la politica real del hotel.
        """
        self._exigir_abierto()
        if self._late_check_out_aplicado or hora_salida <= self.HORA_SALIDA_ESTANDAR:
            return
        factor = Decimal("0.5") if hora_salida <= self.HORA_LIMITE_LATE_CHECK_OUT_PARCIAL else Decimal("1")
        cargo = DetalleConsumo("Cargo por late check-out", f"LCO-{str(self.id)[:8]}",
                               self.tarifa_noche.multiplicar(factor), ahora, "Recepcion",
                               self.numero_habitacion, "Sistema")
        self.agregar_cargo(cargo, ahora)
        self._late_check_out_aplicado = True

    def tiene_saldo_pendiente(self) -> bool:
        return not self.saldo.es_cero

    def cerrar(self, ahora: datetime) -> None:
        """No puede haber saldo pendiente (US-13)."""
        self._exigir_abierto()
        if self.tiene_saldo_pendiente():
            raise DominioException(f"No se puede cerrar el folio con saldo pendiente ({self.saldo}).")
        self.estado = EstadoFolio.CERRADO
        self._registrar(ev.CheckOutRegistrado(ocurrido_en=ahora, folio_id=self.id))

    def _exigir_abierto(self) -> None:
        if self.estado != EstadoFolio.ABIERTO:
            raise DominioException("El folio esta cerrado.")

    def _exigir_misma_moneda(self, monto: MonedaMonto) -> None:
        if monto.moneda != self.moneda:
            raise DominioException(
                f"El folio opera en {self.moneda.value}; no se admite {monto.moneda.value} sin conversion explicita.")
