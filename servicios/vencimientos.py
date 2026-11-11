"""H6: vencimientos, alertas y stock de unidades de sangre."""

import argparse
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from datos.configuracion import RUTA_BD

VIDA_UTIL_DIAS = 20

ZONA_HORARIA = "America/Santiago"
INTERVALO_COMPROBACION_MS = 60_000

DISPONIBLE = "Disponible"
VENCIDA = "Vencida"
USADA = "Usada"
DESCARTADA = "Descartada"
PENDIENTE = "Pendiente de revisión"


@contextmanager
def conectar(ruta=RUTA_BD):
    conexion = sqlite3.connect(ruta, timeout=10)
    conexion.row_factory = sqlite3.Row

    try:
        with conexion:
            yield conexion
    finally:
        conexion.close()


def fecha_actual(ahora=None): #Obtenemos fecha de Concepción
    if ahora is None:
        ahora = datetime.now(ZoneInfo(ZONA_HORARIA))

    if ahora.tzinfo is None or ahora.utcoffset() is None:
        raise ValueError("La hora debe incluir zona horaria.")

    return ahora.astimezone(ZoneInfo(ZONA_HORARIA)).date()


def validar_fecha(valor, formato="%d-%m-%Y"):
    if formato == "%d-%m-%Y":
        patron = r"[0-9]{2}-[0-9]{2}-[0-9]{4}"
        formato_visible = "DD-MM-AAAA"
    elif formato == "%Y-%m-%d":
        patron = r"[0-9]{4}-[0-9]{2}-[0-9]{2}"
        formato_visible = "AAAA-MM-DD"
    else:
        raise ValueError("Formato de fecha no admitido.")

    if not isinstance(valor, str) or not re.fullmatch(patron, valor):
        raise ValueError(
            f"Ingrese una fecha válida con formato {formato_visible}."
        )

    try:
        return datetime.strptime(valor, formato).date()
    except ValueError:
        raise ValueError("La fecha indicada no existe.") from None

def calcular_vencimiento(
    fecha_extraccion,
    vida_util_dias=VIDA_UTIL_DIAS,
):
    if (
        not isinstance(vida_util_dias, int)
        or isinstance(vida_util_dias, bool)
        or vida_util_dias <= 0
    ):
        raise ValueError(
            "La vida útil debe ser un número entero positivo."
        )

    extraccion = validar_fecha(
        fecha_extraccion, "%Y-%m-%d"
    )
    vencimiento = extraccion + timedelta(days=vida_util_dias)

    return vencimiento.isoformat()


def validar_id(valor):
    texto = str(valor).strip()

    if not re.fullmatch(r"[0-9]+", texto) or int(texto) <= 0:
        raise ValueError("Ingrese un ID de unidad válido.")

    return int(texto)


def migrar(conexion):
    columnas = {
        fila[1]
        for fila in conexion.execute("PRAGMA table_info(DONACIONES)")
    }

    if not columnas:
        raise RuntimeError(
            "Inicialice la base de datos antes de ejecutar H6."
        )

    if "ESTADO" not in columnas:
        conexion.execute(
            """
            ALTER TABLE DONACIONES
            ADD COLUMN ESTADO TEXT NOT NULL
            DEFAULT 'Pendiente de revisión'
            """
        )

    conexion.execute(
        """
        CREATE INDEX IF NOT EXISTS IDX_DONACIONES_VENCIMIENTO
        ON DONACIONES(FECHA_VENCIMIENTO)
        """
    )


def _actualizar(conexion, hoy):
    migrar(conexion)

    unidades = conexion.execute(
        """
        SELECT ID, FECHA_EXTRACCIÓN, FECHA_VENCIMIENTO, ESTADO
        FROM DONACIONES
        """
    ).fetchall()

    estados_revisables = (
        DISPONIBLE,
        PENDIENTE,
        "Apta",
        None,
        "",
    )

    for unidad in unidades:
        anterior = unidad["ESTADO"]

        # Estos estados no deben reactivarse automáticamente.
        if anterior in (USADA, DESCARTADA, VENCIDA):
            continue

        try:
            extraccion = validar_fecha(
                unidad["FECHA_EXTRACCIÓN"], "%Y-%m-%d"
            )
            vencimiento = validar_fecha(
                unidad["FECHA_VENCIMIENTO"], "%Y-%m-%d"
            )

            if vencimiento < extraccion:
                raise ValueError(
                    "El vencimiento es anterior a la extracción."
                )

            # Sigue vigente durante todo el día de vencimiento.
            nuevo_estado = (
                VENCIDA if vencimiento < hoy else DISPONIBLE
            )
        except ValueError:
            nuevo_estado = PENDIENTE

        # Conserva reservas u otros estados incorporados por H5/H7,
        # salvo cuando una fecha válida indica que ya vencieron.
        if (
            anterior not in estados_revisables
            and nuevo_estado != VENCIDA
        ):
            continue

        if nuevo_estado != anterior:
            conexion.execute(
                "UPDATE DONACIONES SET ESTADO = ? WHERE ID = ?",
                (nuevo_estado, unidad["ID"]),
            )


def actualizar_vencimientos(ruta=RUTA_BD, ahora=None):
    #Marca unidades vencidas sin necesitar una consulta de pantalla.
    hoy = fecha_actual(ahora)

    with conectar(ruta) as conexion:
        _actualizar(conexion, hoy)


def guardar_vencimiento(
    unidad_id,
    fecha,
    ruta=RUTA_BD,
    ahora=None,
):
    #Guarda DD-MM-AAAA como ISO; los errores conservan el dato previo.
    unidad_id = validar_id(unidad_id)
    vencimiento = validar_fecha(fecha)
    hoy = fecha_actual(ahora)

    with conectar(ruta) as conexion:
        unidad = conexion.execute(
            """
            SELECT FECHA_EXTRACCIÓN
            FROM DONACIONES
            WHERE ID = ?
            """,
            (unidad_id,),
        ).fetchone()

        if unidad is None:
            raise ValueError("No existe una unidad con ese ID.")

        extraccion = validar_fecha(
            unidad["FECHA_EXTRACCIÓN"], "%Y-%m-%d"
        )

        if vencimiento < extraccion:
            raise ValueError(
                "El vencimiento no puede ser anterior a la extracción."
            )

        migrar(conexion)

        actual = conexion.execute(
            """
            SELECT ESTADO, FECHA_VENCIMIENTO
            FROM DONACIONES
            WHERE ID = ?
            """,
            (unidad_id,),
        ).fetchone()

        estado = actual["ESTADO"]

        if estado in (USADA, DESCARTADA, VENCIDA):
            raise ValueError(
                "No se puede modificar una unidad usada, "
                "descartada o vencida."
            )

        # Impide extender una unidad que ya caducó aunque todavía
        # no se haya ejecutado la actualización automática.
        try:
            vencimiento_anterior = validar_fecha(
                actual["FECHA_VENCIMIENTO"], "%Y-%m-%d"
            )
        except ValueError:
            vencimiento_anterior = None

        if (
            vencimiento_anterior is not None
            and extraccion <= vencimiento_anterior < hoy
        ):
            raise ValueError(
                "La unidad ya alcanzó su vencimiento; "
                "no puede extenderse su vigencia."
            )

        nuevo_estado = (
            VENCIDA if vencimiento < hoy else DISPONIBLE
        )

        if estado not in (DISPONIBLE, PENDIENTE, "Apta", None, ""):
            nuevo_estado = estado

        conexion.execute(
            """
            UPDATE DONACIONES
            SET FECHA_VENCIMIENTO = ?, ESTADO = ?
            WHERE ID = ?
            """,
            (vencimiento.isoformat(), nuevo_estado, unidad_id),
        )


def iniciar_actualizacion(widget, ruta=RUTA_BD):
    #Comprueba cada minuto si corresponde la actualización diaria.
    import logging

    ultimo_dia = None
    tarea = None

    def comprobar():
        nonlocal ultimo_dia, tarea

        try:
            hoy = fecha_actual()

            if hoy != ultimo_dia:
                actualizar_vencimientos(ruta)
                ultimo_dia = hoy

        except (sqlite3.Error, ValueError, RuntimeError):
            logging.exception(
                "No se pudo actualizar la caducidad; "
                "se reintentará en un minuto."
            )

        tarea = widget.after(
            INTERVALO_COMPROBACION_MS, comprobar
        )

    def cancelar(event):
        nonlocal tarea

        if event.widget == widget and tarea is not None:
            widget.after_cancel(tarea)
            tarea = None

    widget.bind("<Destroy>", cancelar, add="+")
    comprobar()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Actualizar vencimientos sin interfaz gráfica."
    )
    parser.add_argument("--bd", default=str(RUTA_BD))
    argumentos = parser.parse_args()

    actualizar_vencimientos(argumentos.bd)
    print("Vencimientos actualizados correctamente.")