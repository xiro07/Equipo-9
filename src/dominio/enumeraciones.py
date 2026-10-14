from enum import Enum


class Moneda(Enum):
    USD = "USD"
    MXN = "MXN"


class TipoHabitacion(Enum):
    SENCILLA = "Sencilla"
    DOBLE = "Doble"
    SUITE = "Suite"


class CanalVenta(Enum):
    DIRECTO = "Directo"
    WEB = "Web"
    AGENCIA = "Agencia"


class TipoCliente(Enum):
    INDIVIDUAL = "Individual"
    CORPORATIVO = "Corporativo"
    GRUPO = "Grupo"


class EstadoReserva(Enum):
    PENDIENTE = "Pendiente"
    CONFIRMADA = "Confirmada"
    CANCELADA = "Cancelada"
    NO_SHOW = "NoShow"
    REUBICADA = "Reubicada"
    CHECK_IN_REALIZADO = "CheckInRealizado"


class EstadoFolio(Enum):
    ABIERTO = "Abierto"
    CERRADO = "Cerrado"


class EstadoHabitacion(Enum):
    """Disponible -> Ocupada -> Sucia -> Limpia -> (inspeccion) -> Disponible. FueraDeServicio es ortogonal."""
    DISPONIBLE = "Disponible"
    OCUPADA = "Ocupada"
    SUCIA = "Sucia"
    LIMPIA = "Limpia"
    FUERA_DE_SERVICIO = "FueraDeServicio"


class TipoGarantia(Enum):
    TARJETA_CREDITO = "TarjetaCredito"
    DEPOSITO = "Deposito"
    CARTA_EMPRESA = "CartaEmpresa"
