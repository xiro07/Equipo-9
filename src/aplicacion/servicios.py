"""Service Layer delgada (ADR-004): orquesta repositorios, dominio, transaccion y eventos. Sin reglas de negocio."""
from __future__ import annotations
from decimal import Decimal
from uuid import UUID

from dominio.comun import DominioException
from dominio.entidades import Folio, Habitacion, Huesped, Reserva
from dominio.enumeraciones import EstadoHabitacion, EstadoReserva
from dominio.repositorios import IFolioRepository, IHabitacionRepository, IReservaRepository, IUnitOfWork
from dominio.servicios import TariffCalculationService, WalkService
from dominio.value_objects import AutorizacionGerencial, DetalleConsumo, GarantiaPago, MonedaMonto, RangoDeFechas

from .abstracciones import (IAutorizacionGerencialService, IEventBus, IReloj, NoEncontradoException,
                            SinDisponibilidadException, transaccion)
from .comandos import (AplicarAjusteFolioCommand, CancelarReservacionCommand, ConfirmarReservacionCommand,
                       ConsultarFolioQuery, ConsultarTarifaQuery, GestionarExcepcionOverbookingCommand,
                       RegistrarCargoCommand, RegistrarCheckInCommand, RegistrarCheckOutCommand,
                       RegistrarPagoCommand)
from .dtos import (CancelacionDto, CargoDto, CheckInDto, CheckOutDto, CotizacionDto, FolioDto,
                   ReservaConfirmadaDto, ReubicacionDto)


def _publicar(agregado, bus: IEventBus) -> None:
    for evento in agregado.eventos_de_dominio:
        bus.publicar(evento)
    agregado.limpiar_eventos()


class ReservacionAppService:
    def __init__(self, reservas: IReservaRepository, habitaciones: IHabitacionRepository, uow: IUnitOfWork,
                 tarifas: TariffCalculationService, event_bus: IEventBus, reloj: IReloj) -> None:
        self._reservas, self._habitaciones, self._uow = reservas, habitaciones, uow
        self._tarifas, self._bus, self._reloj = tarifas, event_bus, reloj

    def consultar_y_calcular_tarifa(self, q: ConsultarTarifaQuery) -> CotizacionDto:
        """Query: disponibilidad + cotizacion estimada."""
        rango = RangoDeFechas(q.fecha_entrada, q.fecha_salida)
        disponibles = self._habitaciones.find_disponibles(rango, q.tipo_habitacion)
        total = self._tarifas.calcular_tarifa(rango, q.tipo_habitacion, q.canal_venta, q.tipo_cliente)
        return CotizacionDto(len(disponibles) > 0, len(disponibles), total.monto,
                             total.dividir(rango.calcular_noches()).monto, total.moneda.value)

    def confirmar_reservacion(self, cmd: ConfirmarReservacionCommand) -> ReservaConfirmadaDto:
        """Secuencia 01: confirma si hay disponibilidad; si no, rechaza sin persistir."""
        ahora = self._reloj.ahora
        rango = RangoDeFechas(cmd.fecha_entrada, cmd.fecha_salida)

        # 2-3. findDisponibles
        if not self._habitaciones.find_disponibles(rango, cmd.tipo_habitacion):
            raise SinDisponibilidadException("No hay disponibilidad para las fechas y el tipo de habitacion solicitados.")

        # 4-5. calcularTarifa (Domain Service)
        tarifa = self._tarifas.calcular_tarifa(rango, cmd.tipo_habitacion, cmd.canal_venta, cmd.tipo_cliente)

        # 6-9. Reserva.confirmar (valida fechas y garantia)
        h = cmd.huesped
        huesped = Huesped(h.nombre_completo, h.identificacion, h.nacionalidad, h.contacto)
        garantia = GarantiaPago(cmd.garantia.tipo, cmd.garantia.referencia) if cmd.garantia else None
        deposito = MonedaMonto.usd(cmd.deposito_grupal_usd) if cmd.deposito_grupal_usd is not None else None
        reserva = Reserva.nueva(cmd.tipo_habitacion, cmd.canal_venta, cmd.tipo_cliente, cmd.numero_habitaciones)
        reserva.confirmar(huesped, rango, garantia, tarifa, ahora, deposito)

        # 10-14. begin / save / commit (con doble verificacion de disponibilidad dentro de la transaccion)
        with transaccion(self._uow):
            if not self._habitaciones.find_disponibles(rango, cmd.tipo_habitacion):
                raise SinDisponibilidadException(
                    "La disponibilidad cambio durante la confirmacion; no se persistio la reserva.")
            self._reservas.save(reserva)

        _publicar(reserva, self._bus)
        return ReservaConfirmadaDto(reserva.id, reserva.estado.value, tarifa.monto, tarifa.moneda.value,
                                    list(reserva.advertencias))

    def cancelar_reservacion(self, cmd: CancelarReservacionCommand) -> CancelacionDto:
        reserva = self._reservas.find_by_id(cmd.reserva_id)
        if reserva is None:
            raise NoEncontradoException("la reserva", cmd.reserva_id)
        penalizacion = reserva.cancelar(self._reloj.ahora)
        with transaccion(self._uow):
            self._reservas.save(reserva)
        _publicar(reserva, self._bus)
        return CancelacionDto(reserva.id, reserva.estado.value, not penalizacion.es_cero,
                              penalizacion.monto, penalizacion.moneda.value)


class RecepcionAppService:
    def __init__(self, reservas: IReservaRepository, folios: IFolioRepository, habitaciones: IHabitacionRepository,
                 uow: IUnitOfWork, walk: WalkService, autorizaciones: IAutorizacionGerencialService,
                 event_bus: IEventBus, reloj: IReloj) -> None:
        self._reservas, self._folios, self._habitaciones, self._uow = reservas, folios, habitaciones, uow
        self._walk, self._autorizaciones, self._bus, self._reloj = walk, autorizaciones, event_bus, reloj

    def registrar_check_in(self, cmd: RegistrarCheckInCommand) -> CheckInDto:
        """Asigna habitacion lista, valida identidad/datos fiscales y abre el folio."""
        ahora = self._reloj.ahora
        reserva = self._obtener_reserva(cmd.reserva_id)
        if reserva.estado != EstadoReserva.CONFIRMADA:
            raise DominioException(f"No se puede hacer check-in: la reserva esta en estado {reserva.estado.value}.")

        habitacion = self._buscar_habitacion_lista(reserva)
        if habitacion is None:
            raise SinDisponibilidadException(
                "No hay habitacion lista para el check-in. Use gestionar_excepcion_overbooking para aplicar la politica de walk.")
        if self._folios.find_active_by_habitacion(habitacion.id) is not None:
            raise DominioException("Ya existe un folio activo para esa habitacion.")

        huesped = reserva.huesped
        huesped.actualizar_identidad(cmd.identificacion, cmd.nacionalidad)
        if cmd.solicita_factura:
            huesped.registrar_datos_fiscales(cmd.rfc or "", cmd.razon_social or "")

        habitacion.ocupar()
        reserva.asignar_habitacion(habitacion.id)
        folio = Folio.abrir(reserva.id, habitacion.id, habitacion.numero, huesped.id, reserva.primera_noche(), ahora)

        with transaccion(self._uow):
            self._habitaciones.save(habitacion)
            self._reservas.save(reserva)
            self._folios.save(folio)

        _publicar(folio, self._bus)
        return CheckInDto(folio.id, reserva.id, habitacion.numero)

    def registrar_cargo(self, cmd: RegistrarCargoCommand) -> FolioDto:
        ahora = self._reloj.ahora
        folio = self._obtener_folio(cmd.folio_id)
        cargo = DetalleConsumo(cmd.descripcion, cmd.numero_vale, MonedaMonto(cmd.monto, folio.moneda), ahora,
                               cmd.origen, folio.numero_habitacion, cmd.firma_huesped)
        folio.agregar_cargo(cargo, ahora)
        with transaccion(self._uow):
            self._folios.save(folio)
        _publicar(folio, self._bus)
        return self._a_dto(folio)

    def registrar_pago(self, cmd: RegistrarPagoCommand) -> FolioDto:
        folio = self._obtener_folio(cmd.folio_id)
        folio.aplicar_pago(MonedaMonto(cmd.monto, folio.moneda), self._reloj.ahora)
        with transaccion(self._uow):
            self._folios.save(folio)
        return self._a_dto(folio)

    def aplicar_ajuste(self, cmd: AplicarAjusteFolioCommand) -> FolioDto:
        """La Aplicacion valida credenciales gerenciales; el Dominio exige el comprobante para ajustes > USD 50 (ADR-006)."""
        ahora = self._reloj.ahora
        folio = self._obtener_folio(cmd.folio_id)
        autorizacion: AutorizacionGerencial | None = None
        if cmd.usuario_gerente and cmd.usuario_gerente.strip():
            autorizacion = self._autorizaciones.validar(cmd.usuario_gerente, cmd.clave_gerente or "", ahora)
        folio.aplicar_ajuste(MonedaMonto(cmd.monto, folio.moneda), cmd.motivo, autorizacion, ahora)
        with transaccion(self._uow):
            self._folios.save(folio)
        _publicar(folio, self._bus)
        return self._a_dto(folio)

    def registrar_check_out(self, cmd: RegistrarCheckOutCommand) -> CheckOutDto:
        """El folio rechaza el cierre con saldo pendiente y la habitacion pasa a Sucia."""
        ahora = self._reloj.ahora
        folio = self._obtener_folio(cmd.folio_id)
        habitacion = self._habitaciones.find_by_id(folio.habitacion_id)
        if habitacion is None:
            raise NoEncontradoException("la habitacion", folio.habitacion_id)

        folio.aplicar_late_check_out(ahora.time(), ahora)
        folio.cerrar(ahora)
        habitacion.marcar_sucia()

        with transaccion(self._uow):
            self._folios.save(folio)
            self._habitaciones.save(habitacion)
        _publicar(folio, self._bus)
        return CheckOutDto(folio.id, folio.estado.value, habitacion.estado.value)

    def gestionar_excepcion_overbooking(self, cmd: GestionarExcepcionOverbookingCommand) -> ReubicacionDto:
        """Secuencia 02: si no hay habitacion lista aplica la politica de walk y reubica la reserva."""
        reserva = self._obtener_reserva(cmd.reserva_id)
        if self._buscar_habitacion_lista(reserva) is not None:
            return ReubicacionDto(False, "Existe habitacion disponible: continuar check-in normal.")

        datos = self._walk.gestionar_reubicacion(reserva)
        reserva.marcar_reubicada(datos.hotel.nombre, self._reloj.ahora)
        with transaccion(self._uow):
            self._reservas.save(reserva)
        _publicar(reserva, self._bus)
        return ReubicacionDto(True, "Reubicacion confirmada.", datos.hotel.nombre,
                              datos.diferencia_tarifaria.monto, datos.costo_transporte.monto, datos.cortesia)

    def consultar_folio(self, q: ConsultarFolioQuery) -> FolioDto:
        return self._a_dto(self._obtener_folio(q.folio_id))

    # -- auxiliares --
    def _buscar_habitacion_lista(self, reserva: Reserva) -> Habitacion | None:
        for h in self._habitaciones.find_disponibles(reserva.rango, reserva.tipo_habitacion, reserva.id):
            if h.estado == EstadoHabitacion.DISPONIBLE:
                return h
        return None

    def _obtener_reserva(self, id: UUID) -> Reserva:
        reserva = self._reservas.find_by_id(id)
        if reserva is None:
            raise NoEncontradoException("la reserva", id)
        return reserva

    def _obtener_folio(self, id: UUID) -> Folio:
        folio = self._folios.find_by_id(id)
        if folio is None:
            raise NoEncontradoException("el folio", id)
        return folio

    @staticmethod
    def _a_dto(f: Folio) -> FolioDto:
        return FolioDto(f.id, f.estado.value, f.numero_habitacion, f.saldo.monto, f.moneda.value,
                        [CargoDto(c.numero_vale, c.descripcion, c.origen, c.monto.monto, c.fecha_hora)
                         for c in f.cargos])
