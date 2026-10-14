import unittest
from datetime import date, datetime, time
from decimal import Decimal

from dominio.comun import DominioException
from dominio.entidades import Folio, Habitacion, Huesped, Reserva
from dominio.enumeraciones import (CanalVenta, EstadoFolio, EstadoHabitacion, EstadoReserva, TipoCliente,
                                   TipoGarantia, TipoHabitacion)
from dominio.servicios import TariffCalculationService
from dominio.value_objects import (AutorizacionGerencial, DetalleConsumo, GarantiaPago, MonedaMonto,
                                   RangoDeFechas)

AHORA = datetime(2026, 10, 13, 10, 0)
TARJETA = GarantiaPago(TipoGarantia.TARJETA_CREDITO, "VISA-4242")
GERENTE = AutorizacionGerencial("gerente", AHORA)


def dias(n: int) -> date:
    return date(2026, 10, 13).fromordinal(date(2026, 10, 13).toordinal() + n)


class ValueObjectsTests(unittest.TestCase):
    def test_rango_salida_debe_ser_posterior(self):
        with self.assertRaises(DominioException):
            RangoDeFechas(dias(0), dias(0))
        with self.assertRaises(DominioException):
            RangoDeFechas(dias(0), dias(-1))

    def test_rango_noches_y_solapamiento(self):
        a, b, c = (RangoDeFechas(date(2026, 11, 1), date(2026, 11, 4)),
                   RangoDeFechas(date(2026, 11, 3), date(2026, 11, 5)),
                   RangoDeFechas(date(2026, 11, 4), date(2026, 11, 6)))
        self.assertEqual(3, a.calcular_noches())
        self.assertTrue(a.solapa(b))
        self.assertFalse(a.solapa(c))

    def test_moneda_monto_suma_resta_y_no_mezcla(self):
        total = MonedaMonto.usd("10.50").sumar(MonedaMonto.usd("4.50")).restar(MonedaMonto.usd(5))
        self.assertEqual(Decimal("10.00"), total.monto)
        with self.assertRaises(DominioException):
            MonedaMonto.usd(1).sumar(MonedaMonto.mxn(1))

    def test_detalle_consumo_exige_datos_del_vale(self):
        vale = DetalleConsumo("Cena", "", MonedaMonto.usd(20), AHORA, "Restaurante", "101", "Ana")
        with self.assertRaises(DominioException):
            vale.validar_datos()


def confirmada(entrada: date, noches=2, garantia=TARJETA, total=200) -> Reserva:
    r = Reserva.nueva(TipoHabitacion.DOBLE, CanalVenta.DIRECTO, TipoCliente.INDIVIDUAL)
    r.confirmar(Huesped("Ana Lopez"), RangoDeFechas(entrada, dias(entrada.toordinal() - dias(0).toordinal() + noches)),
                garantia, MonedaMonto.usd(total), AHORA)
    return r


class ReservaTests(unittest.TestCase):
    def test_confirmar_cambia_estado_y_genera_evento(self):
        r = confirmada(dias(10))
        self.assertEqual(EstadoReserva.CONFIRMADA, r.estado)
        self.assertEqual(1, len(r.eventos_de_dominio))

    def test_confirmar_rechaza_fechas_en_el_pasado(self):
        r = Reserva.nueva(TipoHabitacion.DOBLE, CanalVenta.DIRECTO, TipoCliente.INDIVIDUAL)
        with self.assertRaises(DominioException):
            r.confirmar(Huesped("Ana"), RangoDeFechas(dias(-2), dias(0)), TARJETA, MonedaMonto.usd(100), AHORA)

    def test_sin_garantia_reserva_con_advertencia(self):
        r = Reserva.nueva(TipoHabitacion.DOBLE, CanalVenta.DIRECTO, TipoCliente.INDIVIDUAL)
        r.confirmar(Huesped("Ana"), RangoDeFechas(dias(5), dias(7)), None, MonedaMonto.usd(100), AHORA)
        self.assertEqual(EstadoReserva.CONFIRMADA, r.estado)
        self.assertEqual(1, len(r.advertencias))

    def test_reserva_grupal_requiere_deposito_30(self):
        r = Reserva.nueva(TipoHabitacion.DOBLE, CanalVenta.AGENCIA, TipoCliente.GRUPO, numero_habitaciones=10)
        rango = RangoDeFechas(dias(30), dias(32))
        with self.assertRaises(DominioException):
            r.confirmar(Huesped("Grupo"), rango, TARJETA, MonedaMonto.usd(1000), AHORA, MonedaMonto.usd(299))
        r.confirmar(Huesped("Grupo"), rango, TARJETA, MonedaMonto.usd(1000), AHORA, MonedaMonto.usd(300))
        self.assertEqual(EstadoReserva.CONFIRMADA, r.estado)

    def test_cancelar_con_48h_o_mas_sin_penalizacion(self):
        r = confirmada(dias(5))
        self.assertTrue(r.cancelar(AHORA).es_cero)
        self.assertEqual(EstadoReserva.CANCELADA, r.estado)

    def test_cancelar_con_menos_de_48h_cobra_primera_noche(self):
        r = confirmada(dias(1), noches=2, total=200)
        self.assertEqual(Decimal("100.00"), r.cancelar(AHORA).monto)

    def test_no_show_antes_de_2359_se_rechaza(self):
        with self.assertRaises(DominioException):
            confirmada(dias(0)).marcar_no_show(AHORA)

    def test_no_show_con_tarjeta_cobra_y_sin_tarjeta_no(self):
        con = confirmada(dias(0), total=200)
        self.assertEqual(Decimal("100.00"), con.marcar_no_show(datetime(2026, 10, 13, 23, 59)).monto)
        sin = confirmada(dias(0), garantia=GarantiaPago(TipoGarantia.DEPOSITO, "DEP-1"), total=200)
        self.assertTrue(sin.marcar_no_show(datetime(2026, 10, 14)).es_cero)

    def test_modificar_tarifa_requiere_autorizacion(self):
        r = confirmada(dias(5))
        with self.assertRaises(DominioException):
            r.modificar_tarifa(MonedaMonto.usd(150), None)
        r.modificar_tarifa(MonedaMonto.usd(150), GERENTE)
        self.assertEqual(Decimal("150.00"), r.tarifa.monto)

    def test_reserva_cancelada_no_puede_reubicarse(self):
        r = confirmada(dias(5))
        r.cancelar(AHORA)
        with self.assertRaises(DominioException):
            r.marcar_reubicada("Hotel Aliado", AHORA)


def nuevo_folio() -> Folio:
    from uuid import uuid4
    return Folio.abrir(uuid4(), uuid4(), "101", uuid4(), MonedaMonto.usd(100), AHORA)


def vale(monto=40) -> DetalleConsumo:
    return DetalleConsumo("Cena", "V-1", MonedaMonto.usd(monto), AHORA, "Restaurante", "101", "Ana Lopez")


class FolioHabitacionTests(unittest.TestCase):
    def test_agregar_cargo_actualiza_saldo(self):
        f = nuevo_folio()
        f.agregar_cargo(vale(40), AHORA)
        self.assertEqual(Decimal("40.00"), f.saldo.monto)
        self.assertTrue(f.tiene_saldo_pendiente())

    def test_cargo_sin_datos_de_vale_se_rechaza(self):
        incompleto = DetalleConsumo("Cena", "V-1", MonedaMonto.usd(40), AHORA, "Restaurante", "101", "")
        with self.assertRaises(DominioException):
            nuevo_folio().agregar_cargo(incompleto, AHORA)

    def test_cerrar_con_saldo_pendiente_se_rechaza(self):
        f = nuevo_folio()
        f.agregar_cargo(vale(40), AHORA)
        with self.assertRaises(DominioException):
            f.cerrar(AHORA)
        f.aplicar_pago(MonedaMonto.usd(40), AHORA)
        f.cerrar(AHORA)
        self.assertEqual(EstadoFolio.CERRADO, f.estado)

    def test_ajuste_mayor_a_50_usd_requiere_autorizacion(self):
        f = nuevo_folio()
        f.agregar_cargo(vale(200), AHORA)
        with self.assertRaises(DominioException):
            f.aplicar_ajuste(MonedaMonto.usd(-51), "Descuento", None, AHORA)
        f.aplicar_ajuste(MonedaMonto.usd(-50), "Descuento menor", None, AHORA)  # limite exacto
        f.aplicar_ajuste(MonedaMonto.usd(-51), "Descuento mayor", GERENTE, AHORA)
        self.assertEqual(Decimal("99.00"), f.saldo.monto)

    def test_late_check_out_se_cobra_una_sola_vez(self):
        f = nuevo_folio()
        f.aplicar_late_check_out(time(14, 0), AHORA)
        f.aplicar_late_check_out(time(14, 0), AHORA)
        self.assertEqual(Decimal("50.00"), f.saldo.monto)
        puntual = nuevo_folio()
        puntual.aplicar_late_check_out(time(11, 0), AHORA)
        self.assertTrue(puntual.saldo.es_cero)

    def test_habitacion_ciclo_de_estados(self):
        h = Habitacion("101", TipoHabitacion.SENCILLA)
        h.ocupar(); h.marcar_sucia(); h.marcar_limpia(); h.inspeccionar()
        self.assertEqual(EstadoHabitacion.DISPONIBLE, h.estado)

    def test_habitacion_transiciones_invalidas_y_fuera_de_servicio(self):
        h = Habitacion("101", TipoHabitacion.SENCILLA)
        with self.assertRaises(DominioException):
            h.marcar_sucia()
        h.marcar_fuera_de_servicio()
        with self.assertRaises(DominioException):
            h.ocupar()
        with self.assertRaises(DominioException):
            h.reincorporar(None)
        h.reincorporar(GERENTE)
        self.assertEqual(EstadoHabitacion.SUCIA, h.estado)

    def test_tarifas_temporada_fin_de_semana_canal_y_cliente(self):
        svc = TariffCalculationService()
        r = RangoDeFechas(date(2026, 10, 13), date(2026, 10, 14))  # martes, temporada normal
        self.assertEqual(Decimal("150.00"), svc.calcular_tarifa(
            r, TipoHabitacion.DOBLE, CanalVenta.DIRECTO, TipoCliente.INDIVIDUAL).monto)
        self.assertEqual(Decimal("121.13"), svc.calcular_tarifa(  # 150 * 0.95 * 0.85
            r, TipoHabitacion.DOBLE, CanalVenta.WEB, TipoCliente.CORPORATIVO).monto)
        alta = RangoDeFechas(date(2026, 7, 20), date(2026, 7, 21))  # temporada alta
        self.assertEqual(Decimal("195.00"), svc.calcular_tarifa(
            alta, TipoHabitacion.DOBLE, CanalVenta.DIRECTO, TipoCliente.INDIVIDUAL).monto)
        fin = RangoDeFechas(date(2026, 10, 16), date(2026, 10, 17))  # viernes
        self.assertEqual(Decimal("165.00"), svc.calcular_tarifa(
            fin, TipoHabitacion.DOBLE, CanalVenta.DIRECTO, TipoCliente.INDIVIDUAL).monto)


if __name__ == "__main__":
    unittest.main()
