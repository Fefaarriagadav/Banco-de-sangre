import re
import sqlite3
from contextlib import closing
from datetime import datetime, time, timezone
from zoneinfo import ZoneInfo

from datos.configuracion import RUTA_BD
from servicios.vencimientos import ZONA_HORARIA, validar_fecha


GRUPOS = ("A", "B", "AB", "O")
FACTORES_RH = ("+", "-")
PENDIENTE = "Pendiente"


def migrar_despachos(conexion):
    conexion.execute("""
        CREATE TABLE IF NOT EXISTS CENTROS_MEDICOS (
            NOMBRE TEXT PRIMARY KEY NOT NULL,
            DIRECCION TEXT,
            COMUNA TEXT
        )
    """)
    conexion.execute("""
        CREATE TABLE IF NOT EXISTS DESPACHOS_PROGRAMADOS (
            ID INTEGER PRIMARY KEY AUTOINCREMENT,
            CENTRO TEXT NOT NULL REFERENCES CENTROS_MEDICOS(NOMBRE),
            GRUPO_SANGUINEO TEXT NOT NULL CHECK (GRUPO_SANGUINEO IN ('A', 'B', 'AB', 'O')),
            FACTOR_RH TEXT NOT NULL CHECK (FACTOR_RH IN ('+', '-')),
            CANTIDAD INTEGER NOT NULL CHECK (typeof(CANTIDAD) = 'integer' AND CANTIDAD > 0),
            FECHA_DESPACHO TEXT NOT NULL,
            HORA_DESPACHO TEXT NOT NULL,
            DESTINO TEXT NOT NULL CHECK (length(trim(DESTINO)) > 0),
            ESTADO TEXT NOT NULL DEFAULT 'Pendiente'
        )
    """)
    conexion.execute("""
        CREATE INDEX IF NOT EXISTS IDX_DESPACHOS_CENTRO_ID
        ON DESPACHOS_PROGRAMADOS (CENTRO, ID)
    """)


def _datos_centro(conexion, centro):
    if isinstance(centro, str) and centro.strip():
        datos = conexion.execute(
            "SELECT DIRECCION, COMUNA FROM CENTROS_MEDICOS WHERE NOMBRE = ?", (centro,)
        ).fetchone()
        if datos is not None:
            return datos
    raise PermissionError("El centro médico no tiene acceso a solicitudes programadas.")


def _direccion_de_entrega(conexion, centro):
    direccion, comuna = _datos_centro(conexion, centro)
    direccion = (direccion or "").strip()
    comuna = (comuna or "").strip()
    if not direccion:
        raise ValueError("El centro no tiene una dirección registrada para el despacho.")
    return f"{direccion}, {comuna}" if comuna else direccion


def consultar_direccion_despacho(centro, *, ruta=RUTA_BD):
    with closing(sqlite3.connect(ruta)) as conexion:
        return _direccion_de_entrega(conexion, centro)


def _validar_cantidad(cantidad):
    mensaje = "Ingrese una cantidad entera de bolsas mayor que cero."
    if isinstance(cantidad, str):
        cantidad = cantidad.strip()
        if not re.fullmatch(r"[0-9]+", cantidad):
            raise ValueError(mensaje)
        digitos = cantidad.lstrip("0") or "0"
        if len(digitos) > 19:
            raise ValueError("La cantidad ingresada supera el máximo admitido.")
        cantidad = int(digitos)
    if type(cantidad) is not int or cantidad <= 0:
        raise ValueError(mensaje)
    if cantidad > 2**63 - 1:
        raise ValueError("La cantidad ingresada supera el máximo admitido.")
    return cantidad


def _validar_programacion(fecha, horario, ahora):
    fecha_despacho = validar_fecha(fecha.strip() if isinstance(fecha, str) else fecha)
    horario = horario.strip() if isinstance(horario, str) else ""
    if not re.fullmatch(r"(?:[01][0-9]|2[0-3]):[0-5][0-9]", horario):
        raise ValueError("Ingrese un horario válido en formato HH:MM (24 horas).")

    zona = ZoneInfo(ZONA_HORARIA)
    hora_local = datetime.combine(fecha_despacho, time.fromisoformat(horario))
    # El cambio de hora puede omitir o repetir una hora local.
    instantes = set()
    try:
        for fold in (0, 1):
            instante = hora_local.replace(tzinfo=zona, fold=fold).astimezone(timezone.utc)
            if instante.astimezone(zona).replace(tzinfo=None) == hora_local:
                instantes.add(instante)
    except OverflowError:
        raise ValueError("La fecha y la hora están fuera del rango admitido.") from None
    if len(instantes) != 1:
        raise ValueError("El horario es ambiguo o no existe por el cambio de hora. Elija otro.")

    ahora = datetime.now(timezone.utc) if ahora is None else ahora
    if ahora.tzinfo is None or ahora.utcoffset() is None:
        raise ValueError("La hora actual debe incluir zona horaria.")
    if instantes.pop() <= ahora.astimezone(timezone.utc):
        raise ValueError("La fecha y hora del despacho deben ser futuras (hora de Santiago).")
    return fecha_despacho.isoformat(), horario


def registrar_despacho(centro, grupo, rh, cantidad, fecha, horario, *,
                       direccion_confirmada, ruta=RUTA_BD, ahora=None):
    if grupo not in GRUPOS:
        raise ValueError("Seleccione un grupo sanguíneo válido (A, B, AB u O).")
    if rh not in FACTORES_RH:
        raise ValueError("Seleccione un factor Rh válido (+ o -).")
    cantidad = _validar_cantidad(cantidad)
    with closing(sqlite3.connect(ruta)) as conexion, conexion:
        conexion.execute("PRAGMA foreign_keys = ON")
        conexion.execute("BEGIN IMMEDIATE")
        destino = _direccion_de_entrega(conexion, centro)
        if direccion_confirmada != destino:
            raise ValueError(
                "La dirección del centro cambió o no se confirmó. "
                "Vuelva a abrir el formulario para revisarla."
            )
        fecha_despacho, hora_despacho = _validar_programacion(fecha, horario, ahora)
        cursor = conexion.execute("""
            INSERT INTO DESPACHOS_PROGRAMADOS (
                CENTRO, GRUPO_SANGUINEO, FACTOR_RH, CANTIDAD,
                FECHA_DESPACHO, HORA_DESPACHO, DESTINO
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (centro, grupo, rh, cantidad, fecha_despacho, hora_despacho, destino))
        return cursor.lastrowid


def consultar_despachos(centro, *, ruta=RUTA_BD):
    with closing(sqlite3.connect(ruta)) as conexion, conexion:
        conexion.row_factory = sqlite3.Row
        conexion.execute("BEGIN")
        _datos_centro(conexion, centro)
        filas = conexion.execute("""
            SELECT ID, CENTRO, GRUPO_SANGUINEO, FACTOR_RH, CANTIDAD,
                   FECHA_DESPACHO, HORA_DESPACHO, DESTINO, ESTADO
            FROM DESPACHOS_PROGRAMADOS
            WHERE CENTRO = ?
            ORDER BY ID DESC
        """, (centro,))
        return [dict(fila) for fila in filas]
