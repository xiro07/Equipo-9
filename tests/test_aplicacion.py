import unittest
from datetime import date, datetime, timedelta
from decimal import Decimal

from aplicacion.abstracciones import (AutorizacionInvalidaException, NoEncontradoException,
                                      SinDisponibilidadException)
from aplicacion.comandos import *  # noqa: F401,F403
from dominio.comun import DominioException
from dominio.enumeraciones import CanalVenta, EstadoReserva, TipoCliente, TipoGarantia, TipoHabitacion
from infraestructura.composicion import PMSComposition
from infraestructura.persistencia import PMSDatabase
from infraestructura.servicios import RelojFijo

AHORA = datetime(2026, 10, 13, 10, 0)
HOY = AHORA.date()
TARJETA = GarantiaPagoDto(TipoGarantia.TARJETA_CREDITO, "VISA-4242")


def crear() -> PMSComposition:
    return PMSComposition(PMSDatabase.con_datos_iniciales(), RelojFijo(AHORA))


def reserva_cmd(tipo, dias_desde_hoy=5, nombre="Ana Lopez") -> ConfirmarReservacionCommand:
    entrada = HOY + timedelta(days=dias_desde_hoy)
    return ConfirmarReservacionCommand(DatosHuespedDto(nombre), entrada, entrada + timedelta(days=2),
                                       tipo, CanalVenta.DIRECTO, TipoCliente.INDIVIDUAL, TARJETA)


def fuera_de_servicio_suites(pms: PMSComposition) -> None:
    for h in pms.database.habitaciones.values():
        if h.tipo == TipoHabitacion.SUITE:
            h.marcar_fuera_de_servicio()


class Secuencia01Tests(unittest.TestCase):
    def test_confirmar_con_disponibilidad_persiste_y_publica_evento(self):
        pms = crear()
        r = pms.reservaciones.confirmar_reservacion(reserva_cmd(TipoHabitacion.DOBLE))
        self.assertEqual("Confirmada", r.estado)
        self.assertEqual(1, len(pms.database.reservas))
        self.assertTrue(any(type(e).__name__ == "ReservaConfirmada" for e in pms.event_bus.publicados))

    def test_sin_disponibilidad_rechaza_y_no_persiste(self):
        pms = crear()  # 2 suites
        pms.reservaciones.confirmar_reservacion(reserva_cmd(TipoHabitacion.SUITE))
        pms.reservaciones.confirmar_reservacion(reserva_cmd(TipoHabitacion.SUITE))
        with self.assertRaises(SinDisponibilidadException):
            pms.reservaciones.confirmar_reservacion(reserva_cmd(TipoHabitacion.SUITE))
        self.assertEqual(2, len(pms.database.reservas))

    def test_fechas_distintas_no_compiten_por_inventario(self):
        pms = crear()
        pms.reservaciones.confirmar_reservacion(reserva_cmd(TipoHabitacion.SUITE, 5))
        pms.reservaciones.confirmar_reservacion(reserva_cmd(TipoHabitacion.SUITE, 5))
        otra = pms.reservaciones.confirmar_reservacion(reserva_cmd(TipoHabitacion.SUITE, 20))
        self.assertEqual("Confirmada", otra.estado)

    def test_consultar_y_calcular_tarifa(self):
        pms = crear()
        q = ConsultarTarifaQuery(HOY + timedelta(5), HOY + timedelta(7), TipoHabitacion.SENCILLA,
                                 CanalVenta.DIRECTO, TipoCliente.INDIVIDUAL)
        c = pms.reservaciones.consultar_y_calcular_tarifa(q)
        self.assertTrue(c.hay_disponibilidad)
        self.assertEqual(5, c.habitaciones_disponibles)
        self.assertGreater(c.tarifa_total, 0)

    def test_cancelar_con_mas_de_48h_no_cobra(self):
        pms = crear()
        r = pms.reservaciones.confirmar_reservacion(reserva_cmd(TipoHabitacion.DOBLE, 10))
        c = pms.reservaciones.cancelar_reservacion(CancelarReservacionCommand(r.reserva_id))
        self.assertFalse(c.tiene_penalizacion)
        self.assertEqual("Cancelada", c.estado)

    def test_cancelar_con_menos_de_48h_cobra_primera_noche(self):
        pms = crear()
        r = pms.reservaciones.confirmar_reservacion(reserva_cmd(TipoHabitacion.DOBLE, 1))
        c = pms.reservaciones.cancelar_reservacion(CancelarReservacionCommand(r.reserva_id))
        self.assertTrue(c.tiene_penalizacion)
        self.assertEqual(r.tarifa_total / 2, c.penalizacion)


class EstanciaTests(unittest.TestCase):
    def test_flujo_completo_deja_habitacion_sucia(self):
        pms = crear()
        r = pms.reservaciones.confirmar_reservacion(reserva_cmd(TipoHabitacion.DOBLE, 0))
        ci = pms.recepcion.registrar_check_in(RegistrarCheckInCommand(r.reserva_id, "INE-1", "Mexicana"))
        pms.recepcion.registrar_cargo(RegistrarCargoCommand(
            ci.folio_id, "Cena", "V-1", Decimal("85.50"), "Restaurante", "Ana Lopez"))

        with self.assertRaises(DominioException):
            pms.recepcion.aplicar_ajuste(AplicarAjusteFolioCommand(ci.folio_id, Decimal("-60"), "Cortesia"))
        with self.assertRaises(AutorizacionInvalidaException):
            pms.recepcion.aplicar_ajuste(
                AplicarAjusteFolioCommand(ci.folio_id, Decimal("-60"), "Cortesia", "gerente", "mal"))
        folio = pms.recepcion.aplicar_ajuste(
            AplicarAjusteFolioCommand(ci.folio_id, Decimal("-60"), "Cortesia", "gerente", "1234"))
        self.assertEqual(Decimal("25.50"), folio.saldo)

        with self.assertRaises(DominioException):
            pms.recepcion.registrar_check_out(RegistrarCheckOutCommand(ci.folio_id))
        pms.recepcion.registrar_pago(RegistrarPagoCommand(ci.folio_id, Decimal("25.50")))
        salida = pms.recepcion.registrar_check_out(RegistrarCheckOutCommand(ci.folio_id))
        self.assertEqual("Cerrado", salida.estado_folio)
        self.assertEqual("Sucia", salida.estado_habitacion)

    def test_check_in_con_factura_requiere_datos_fiscales(self):
        pms = crear()
        r = pms.reservaciones.confirmar_reservacion(reserva_cmd(TipoHabitacion.DOBLE, 0))
        with self.assertRaises(DominioException):
            pms.recepcion.registrar_check_in(
                RegistrarCheckInCommand(r.reserva_id, "INE-1", "Mexicana", solicita_factura=True))
        ok = pms.recepcion.registrar_check_in(RegistrarCheckInCommand(
            r.reserva_id, "INE-1", "Mexicana", True, "XAXX010101000", "Ana Lopez SA"))
        self.assertIsNotNone(ok.folio_id)

    def test_no_permite_dos_check_in_de_la_misma_reserva(self):
        pms = crear()
        r = pms.reservaciones.confirmar_reservacion(reserva_cmd(TipoHabitacion.DOBLE, 0))
        pms.recepcion.registrar_check_in(RegistrarCheckInCommand(r.reserva_id, "INE-1", "Mexicana"))
        with self.assertRaises(DominioException):
            pms.recepcion.registrar_check_in(RegistrarCheckInCommand(r.reserva_id, "INE-1", "Mexicana"))

    def test_folio_inexistente(self):
        from uuid import uuid4
        with self.assertRaises(NoEncontradoException):
            crear().recepcion.registrar_cargo(RegistrarCargoCommand(uuid4(), "x", "V", Decimal("1"), "Spa", "Ana"))


class Secuencia02Tests(unittest.TestCase):
    def test_con_habitacion_disponible_continua_check_in_normal(self):
        pms = crear()
        r = pms.reservaciones.confirmar_reservacion(reserva_cmd(TipoHabitacion.SUITE, 0))
        res = pms.recepcion.gestionar_excepcion_overbooking(GestionarExcepcionOverbookingCommand(r.reserva_id))
        self.assertFalse(res.requiere_reubicacion)
        self.assertEqual(EstadoReserva.CONFIRMADA, pms.database.reservas[r.reserva_id].estado)

    def test_sin_habitacion_aplica_walk_y_marca_reubicada(self):
        pms = crear()
        r = pms.reservaciones.confirmar_reservacion(reserva_cmd(TipoHabitacion.SUITE, 0))
        fuera_de_servicio_suites(pms)
        res = pms.recepcion.gestionar_excepcion_overbooking(GestionarExcepcionOverbookingCommand(r.reserva_id))
        self.assertTrue(res.requiere_reubicacion)
        self.assertEqual("Gran Hotel Palmas", res.hotel_aliado)
        self.assertEqual(Decimal("20.00"), res.costo_transporte)
        self.assertEqual(Decimal("80.00"), res.diferencia_tarifaria)
        self.assertEqual(EstadoReserva.REUBICADA, pms.database.reservas[r.reserva_id].estado)
        self.assertTrue(any(type(e).__name__ == "ReservaReubicada" for e in pms.event_bus.publicados))

    def test_check_in_sin_habitacion_lista_lanza_sin_disponibilidad(self):
        pms = crear()
        r = pms.reservaciones.confirmar_reservacion(reserva_cmd(TipoHabitacion.SUITE, 0))
        fuera_de_servicio_suites(pms)
        with self.assertRaises(SinDisponibilidadException):
            pms.recepcion.registrar_check_in(RegistrarCheckInCommand(r.reserva_id, "INE-1", "Mexicana"))


if __name__ == "__main__":
    unittest.main()
