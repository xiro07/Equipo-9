"""Demo del PMS Hotel Costa Azul: recorre las dos secuencias del diagrama y el flujo de estancia.
Reloj fijo (hoy 10:00) para que el resultado sea siempre el mismo. Ejecutar:  python main.py"""
from datetime import date, datetime, time, timedelta

from decimal import Decimal

from aplicacion.comandos import *  # noqa: F401,F403
from dominio.enumeraciones import CanalVenta, EstadoHabitacion, TipoCliente, TipoGarantia, TipoHabitacion
from infraestructura.composicion import PMSComposition
from infraestructura.persistencia import PMSDatabase
from infraestructura.servicios import RelojFijo


def titulo(texto: str) -> None:
    print(f"\n== {texto}")


def intentar(descripcion: str, accion) -> None:
    try:
        accion()
        print(f"   OK: {descripcion}")
    except Exception as ex:  # demo: muestra el rechazo del negocio
        print(f"   RECHAZADO ({descripcion}): {ex}")


def main() -> None:
    hoy = date.today()
    pms = PMSComposition(PMSDatabase.con_datos_iniciales(), RelojFijo(datetime.combine(hoy, time(10, 0))))
    pms.event_bus.suscriptores.append(lambda e: print(f"   [evento] {type(e).__name__}"))

    garantia = GarantiaPagoDto(TipoGarantia.TARJETA_CREDITO, "VISA-****4242")
    huesped = DatosHuespedDto("Ana Lopez", contacto="ana@correo.com")
    d = timedelta

    titulo("Cotizacion (query)")
    c = pms.reservaciones.consultar_y_calcular_tarifa(ConsultarTarifaQuery(
        hoy + d(10), hoy + d(12), TipoHabitacion.DOBLE, CanalVenta.WEB, TipoCliente.INDIVIDUAL))
    print(f"   Disponibles: {c.habitaciones_disponibles} | Total: {c.tarifa_total:,.2f} {c.moneda}")

    titulo("Secuencia 01 - Confirmar reservacion (flujo principal)")
    reserva = pms.reservaciones.confirmar_reservacion(ConfirmarReservacionCommand(
        huesped, hoy, hoy + d(2), TipoHabitacion.DOBLE, CanalVenta.DIRECTO, TipoCliente.INDIVIDUAL, garantia))
    print(f"   reservaId {reserva.reserva_id} | estado {reserva.estado} | tarifa {reserva.tarifa_total:,.2f} {reserva.moneda}")

    titulo("Secuencia 01 - Sin disponibilidad (se rechaza y no se persiste)")
    for i in range(1, 4):
        def reservar_suite(i=i):
            r = pms.reservaciones.confirmar_reservacion(ConfirmarReservacionCommand(
                DatosHuespedDto(f"Cliente {i}"), hoy + d(20), hoy + d(22),
                TipoHabitacion.SUITE, CanalVenta.DIRECTO, TipoCliente.INDIVIDUAL, garantia))
            print(f"   Confirmada {r.reserva_id}")
        intentar(f"Suite #{i}", reservar_suite)

    titulo("Check-in, cargos, ajuste con autorizacion gerencial y check-out")
    check_in = pms.recepcion.registrar_check_in(RegistrarCheckInCommand(reserva.reserva_id, "INE-123456", "Mexicana"))
    print(f"   Habitacion {check_in.numero_habitacion} | folio {check_in.folio_id}")
    folio = pms.recepcion.registrar_cargo(RegistrarCargoCommand(
        check_in.folio_id, "Cena restaurante", "V-0001", Decimal("85.50"), "Restaurante", "Ana Lopez"))
    print(f"   Saldo tras cargo: {folio.saldo:,.2f} {folio.moneda}")

    intentar("Ajuste de -60 USD sin gerente", lambda: pms.recepcion.aplicar_ajuste(
        AplicarAjusteFolioCommand(check_in.folio_id, Decimal("-60"), "Cortesia por demora")))

    def ajuste_con_gerente():
        nonlocal folio
        folio = pms.recepcion.aplicar_ajuste(AplicarAjusteFolioCommand(
            check_in.folio_id, Decimal("-60"), "Cortesia por demora", "gerente", "1234"))
        print(f"   Saldo tras ajuste: {folio.saldo:,.2f}")
    intentar("Ajuste de -60 USD con gerente", ajuste_con_gerente)

    intentar("Check-out con saldo pendiente",
             lambda: pms.recepcion.registrar_check_out(RegistrarCheckOutCommand(check_in.folio_id)))

    def pago_y_salida():
        pms.recepcion.registrar_pago(RegistrarPagoCommand(check_in.folio_id, folio.saldo))
        s = pms.recepcion.registrar_check_out(RegistrarCheckOutCommand(check_in.folio_id))
        print(f"   Folio {s.estado_folio} | habitacion {s.estado_habitacion}")
    intentar("Pago y check-out", pago_y_salida)

    titulo("Secuencia 02 - Overbooking / Walk (excepcion)")
    walk_res = pms.reservaciones.confirmar_reservacion(ConfirmarReservacionCommand(
        DatosHuespedDto("Luis Perez"), hoy + d(1), hoy + d(3),
        TipoHabitacion.SUITE, CanalVenta.DIRECTO, TipoCliente.INDIVIDUAL, garantia))
    intentar("Con habitacion disponible", lambda: print("   " + pms.recepcion.gestionar_excepcion_overbooking(
        GestionarExcepcionOverbookingCommand(walk_res.reserva_id)).mensaje))

    for h in pms.database.habitaciones.values():
        if h.tipo == TipoHabitacion.SUITE:
            h.marcar_fuera_de_servicio()

    def walk():
        r = pms.recepcion.gestionar_excepcion_overbooking(GestionarExcepcionOverbookingCommand(walk_res.reserva_id))
        print(f"   {r.mensaje} Hotel aliado: {r.hotel_aliado} | diferencia {r.diferencia_tarifaria:,.2f} USD | "
              f"transporte {r.costo_transporte:,.2f} USD | {r.cortesia}")
    intentar("Sin habitacion disponible (walk)", walk)

    print("\nFin de la demo.")


if __name__ == "__main__":
    main()
