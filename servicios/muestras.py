"""HU14-T1: registro y consulta de muestras asociadas a donaciones."""

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from zoneinfo import ZoneInfo

from datos.configuracion import RUTA_BD
from servicios.vencimientos import (
    DISPONIBLE,
    ZONA_HORARIA,
    validar_fecha,
)


PENDIENTE_ANALISIS = "Pendiente de análisis"


@contextmanager
def conectar(ruta=RUTA_BD):
    conexion = sqlite3.connect(ruta, timeout=10)
    conexion.row_factory = sqlite3.Row
    conexion.execute("PRAGMA foreign_keys = ON")

    try:
        with conexion:
            yield conexion
    finally:
        conexion.close()


def migrar_muestras(conexion):
    """Crea las tablas de HU14 sin borrar datos existentes."""
    conexion.execute(
        """
        CREATE TABLE IF NOT EXISTS MUESTRAS (
            ID INTEGER PRIMARY KEY AUTOINCREMENT,
            DONACION_ID INTEGER NOT NULL
                REFERENCES DONACIONES(ID),
            ESTADO TEXT NOT NULL DEFAULT 'Pendiente de análisis',
            REGISTRADA_POR INTEGER NOT NULL
                REFERENCES PERSONAL(ID_EMPLEADO),
            FECHA_REGISTRO TEXT NOT NULL
        )
        """
    )

    conexion.execute(
        """
        CREATE INDEX IF NOT EXISTS IDX_MUESTRAS_DONACION
        ON MUESTRAS(DONACION_ID)
        """
    )

    conexion.execute(
        """
        CREATE TABLE IF NOT EXISTS HISTORIAL_MUESTRAS (
            ID INTEGER PRIMARY KEY AUTOINCREMENT,
            MUESTRA_ID INTEGER NOT NULL
                REFERENCES MUESTRAS(ID),
            ACCION TEXT NOT NULL,
            ESTADO_ANTERIOR TEXT,
            ESTADO_NUEVO TEXT NOT NULL,
            RESPONSABLE_ID INTEGER NOT NULL
                REFERENCES PERSONAL(ID_EMPLEADO),
            FECHA TEXT NOT NULL,
            MOTIVO TEXT NOT NULL
        )
        """
    )


def validar_identificador(valor, nombre):
    texto = str(valor).strip()

    if not texto.isascii() or not texto.isdecimal():
        raise ValueError(f"Ingrese un ID de {nombre} válido.")

    identificador = int(texto)

    if identificador <= 0:
        raise ValueError(f"Ingrese un ID de {nombre} válido.")

    return identificador


def validar_enfermero(conexion, empleado_id):
    try:
        empleado_id = validar_identificador(
            empleado_id, "empleado"
        )
    except ValueError:
        raise PermissionError(
            "Debe identificarse como enfermero autorizado."
        ) from None

    empleado = conexion.execute(
        """
        SELECT ROL
        FROM PERSONAL
        WHERE ID_EMPLEADO = ?
        """,
        (empleado_id,),
    ).fetchone()

    if (
        empleado is None
        or str(empleado["ROL"]).strip().casefold() != "enfermero"
    ):
        raise PermissionError(
            "Solo un enfermero autorizado puede gestionar muestras."
        )

    return empleado_id


def obtener_instante(ahora=None):
    if ahora is None:
        ahora = datetime.now(ZoneInfo(ZONA_HORARIA))

    if ahora.tzinfo is None or ahora.utcoffset() is None:
        raise ValueError("La fecha y hora deben incluir zona horaria.")

    return ahora.astimezone(ZoneInfo(ZONA_HORARIA))


def _consultar_muestra(conexion, muestra_id):
    fila = conexion.execute(
        """
        SELECT
            m.ID,
            m.DONACION_ID,
            m.ESTADO,
            m.REGISTRADA_POR,
            m.FECHA_REGISTRO,
            p.NOMBRE AS RESPONSABLE,
            d.ESTADO AS ESTADO_UNIDAD,
            d.TIPO_SANGRE,
            d.FACTOR_RH,
            d.FECHA_EXTRACCIÓN AS FECHA_EXTRACCION,
            d.FECHA_VENCIMIENTO
        FROM MUESTRAS AS m
        JOIN DONACIONES AS d ON d.ID = m.DONACION_ID
        JOIN PERSONAL AS p
            ON p.ID_EMPLEADO = m.REGISTRADA_POR
        WHERE m.ID = ?
        """,
        (muestra_id,),
    ).fetchone()

    if fila is None:
        raise ValueError("No existe una muestra con ese ID.")

    return dict(fila)


def registrar_muestra(
    donacion_id,
    empleado_id,
    ruta=RUTA_BD,
    ahora=None,
):
    instante = obtener_instante(ahora)

    with conectar(ruta) as conexion:
        # El registro y el cambio de disponibilidad son atómicos.
        conexion.execute("BEGIN IMMEDIATE")

        empleado_id = validar_enfermero(conexion, empleado_id)
        donacion_id = validar_identificador(
            donacion_id, "donación"
        )

        donacion = conexion.execute(
            """
            SELECT ID, ESTADO, FECHA_EXTRACCIÓN, FECHA_VENCIMIENTO
            FROM DONACIONES
            WHERE ID = ?
            """,
            (donacion_id,),
        ).fetchone()

        if donacion is None:
            raise ValueError("No existe una donación con ese ID.")

        if donacion["ESTADO"] not in (
            DISPONIBLE,
            PENDIENTE_ANALISIS,
        ):
            raise ValueError(
                "No se puede registrar una muestra para una unidad "
                "en ese estado. Debe estar Disponible o "
                "Pendiente de análisis."
            )

        extraccion = validar_fecha(
            donacion["FECHA_EXTRACCIÓN"], "%Y-%m-%d"
        )
        vencimiento = validar_fecha(
            donacion["FECHA_VENCIMIENTO"], "%Y-%m-%d"
        )
        hoy = instante.date()

        if extraccion > hoy or vencimiento < extraccion:
            raise ValueError(
                "Las fechas de la donación son inconsistentes."
            )

        if vencimiento < hoy:
            raise ValueError(
                "No se puede registrar una muestra para una "
                "unidad que ya venció."
            )

        conexion.execute(
            """
            UPDATE DONACIONES
            SET ESTADO = ?
            WHERE ID = ?
            """,
            (PENDIENTE_ANALISIS, donacion_id),
        )

        fecha_registro = instante.isoformat(
            timespec="microseconds"
        )

        cursor = conexion.execute(
            """
            INSERT INTO MUESTRAS (
                DONACION_ID,
                ESTADO,
                REGISTRADA_POR,
                FECHA_REGISTRO
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                donacion_id,
                PENDIENTE_ANALISIS,
                empleado_id,
                fecha_registro,
            ),
        )
        muestra_id = cursor.lastrowid

        conexion.execute(
            """
            INSERT INTO HISTORIAL_MUESTRAS (
                MUESTRA_ID,
                ACCION,
                ESTADO_ANTERIOR,
                ESTADO_NUEVO,
                RESPONSABLE_ID,
                FECHA,
                MOTIVO
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                muestra_id,
                "Registro de muestra",
                None,
                PENDIENTE_ANALISIS,
                empleado_id,
                fecha_registro,
                "Muestra registrada sin resultados. "
                f"Estado previo de la unidad: {donacion['ESTADO']}.",
            ),
        )
        # HU14-T3: una nueva muestra invalida la autorización
        # anterior y reevalúa todas las muestras de la unidad.
        from servicios.liberacion import evaluar_en_transaccion

        evaluar_en_transaccion(
            conexion,
            donacion_id,
            empleado_id,
            instante,
            muestra_id=muestra_id,
        )

        return _consultar_muestra(conexion, muestra_id)


def consultar_muestra(
    muestra_id,
    empleado_id,
    ruta=RUTA_BD,
):
    with conectar(ruta) as conexion:
        validar_enfermero(conexion, empleado_id)
        muestra_id = validar_identificador(
            muestra_id, "muestra"
        )
        return _consultar_muestra(conexion, muestra_id)


def consultar_muestras_donacion(
    donacion_id,
    empleado_id,
    ruta=RUTA_BD,
):
    with conectar(ruta) as conexion:
        validar_enfermero(conexion, empleado_id)
        donacion_id = validar_identificador(
            donacion_id, "donación"
        )

        existe = conexion.execute(
            "SELECT ID FROM DONACIONES WHERE ID = ?",
            (donacion_id,),
        ).fetchone()

        if existe is None:
            raise ValueError("No existe una donación con ese ID.")

        filas = conexion.execute(
            """
            SELECT ID
            FROM MUESTRAS
            WHERE DONACION_ID = ?
            ORDER BY FECHA_REGISTRO DESC, ID DESC
            """,
            (donacion_id,),
        ).fetchall()

        return [
            _consultar_muestra(conexion, fila["ID"])
            for fila in filas
        ]