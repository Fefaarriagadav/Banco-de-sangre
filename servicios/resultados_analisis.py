"""HU14-T2: resultados administrativos de laboratorio e historial."""

import sqlite3

from datos.configuracion import RUTA_BD
from servicios.muestras import (
    conectar,
    obtener_instante,
    validar_enfermero,
    validar_identificador,
)
from servicios.vencimientos import validar_fecha


PENDIENTE = "Pendiente"
CONFORME = "Conforme"
NO_CONFORME = "No conforme"

CLASIFICACIONES = (PENDIENTE, CONFORME, NO_CONFORME)

PENDIENTE_ANALISIS = "Pendiente de análisis"
PENDIENTE_REVISION = "Pendiente de revisión"


def migrar_resultados(conexion):
    """Crea catálogo, resultados e historial sin cargar reglas clínicas."""
    conexion.execute(
        """
        CREATE TABLE IF NOT EXISTS CATALOGO_ANALISIS (
            ID INTEGER PRIMARY KEY AUTOINCREMENT,
            CODIGO TEXT NOT NULL UNIQUE,
            NOMBRE TEXT NOT NULL,
            OBLIGATORIO INTEGER NOT NULL DEFAULT 1
                CHECK (OBLIGATORIO IN (0, 1)),
            ACTIVO INTEGER NOT NULL DEFAULT 1
                CHECK (ACTIVO IN (0, 1))
        )
        """
    )

    conexion.execute(
        """
        CREATE TABLE IF NOT EXISTS RESULTADOS_ANALISIS (
            ID INTEGER PRIMARY KEY AUTOINCREMENT,
            MUESTRA_ID INTEGER NOT NULL REFERENCES MUESTRAS(ID),
            ANALISIS_ID INTEGER NOT NULL REFERENCES CATALOGO_ANALISIS(ID),
            RESULTADO TEXT NOT NULL,
            CLASIFICACION TEXT NOT NULL
                CHECK (
                    CLASIFICACION IN (
                        'Pendiente', 'Conforme', 'No conforme'
                    )
                ),
            OBSERVACIONES TEXT NOT NULL DEFAULT '',
            RESPONSABLE_ID INTEGER NOT NULL
                REFERENCES PERSONAL(ID_EMPLEADO),
            FECHA TEXT NOT NULL,
            VERSION INTEGER NOT NULL DEFAULT 1,
            UNIQUE (MUESTRA_ID, ANALISIS_ID)
        )
        """
    )

    conexion.execute(
        """
        CREATE TABLE IF NOT EXISTS HISTORIAL_RESULTADOS (
            ID INTEGER PRIMARY KEY AUTOINCREMENT,
            RESULTADO_ID INTEGER NOT NULL
                REFERENCES RESULTADOS_ANALISIS(ID),
            VERSION INTEGER NOT NULL,
            RESULTADO TEXT NOT NULL,
            CLASIFICACION TEXT NOT NULL,
            OBSERVACIONES TEXT NOT NULL,
            RESPONSABLE_ID INTEGER NOT NULL
                REFERENCES PERSONAL(ID_EMPLEADO),
            FECHA TEXT NOT NULL,
            MOTIVO TEXT NOT NULL,
            UNIQUE (RESULTADO_ID, VERSION)
        )
        """
    )


def _texto(valor, nombre, limite, permitir_vacio=False):
    if not isinstance(valor, str):
        raise ValueError(f"{nombre} debe ser texto.")

    valor = valor.strip()

    if not permitir_vacio and not valor:
        raise ValueError(f"Debe ingresar {nombre.lower()}.")

    if len(valor) > limite:
        raise ValueError(
            f"{nombre} no puede superar {limite} caracteres."
        )

    return valor


def _obtener_muestra(conexion, muestra_id):
    muestra = conexion.execute(
        """
        SELECT
            m.ID,
            m.DONACION_ID,
            m.ESTADO,
            d.ESTADO AS ESTADO_UNIDAD,
            d.ESTADO_LABORATORIO,
            d.FECHA_VENCIMIENTO
        FROM MUESTRAS AS m
        JOIN DONACIONES AS d ON d.ID = m.DONACION_ID
        WHERE m.ID = ?
        """,
        (muestra_id,),
    ).fetchone()

    if muestra is None:
        raise ValueError("No existe una muestra con ese ID.")

    return muestra


def _consultar(conexion, muestra_id):
    muestra = _obtener_muestra(conexion, muestra_id)

    catalogo = conexion.execute(
        """
        SELECT ID, CODIGO, NOMBRE, OBLIGATORIO
        FROM CATALOGO_ANALISIS
        WHERE ACTIVO = 1
        ORDER BY CODIGO
        """
    ).fetchall()

    resultados = conexion.execute(
        """
        SELECT
            r.ID,
            r.ANALISIS_ID,
            a.CODIGO,
            a.NOMBRE,
            a.ACTIVO,
            r.RESULTADO,
            r.CLASIFICACION,
            r.OBSERVACIONES,
            r.RESPONSABLE_ID,
            p.NOMBRE AS RESPONSABLE,
            r.FECHA,
            r.VERSION
        FROM RESULTADOS_ANALISIS AS r
        JOIN CATALOGO_ANALISIS AS a ON a.ID = r.ANALISIS_ID
        JOIN PERSONAL AS p ON p.ID_EMPLEADO = r.RESPONSABLE_ID
        WHERE r.MUESTRA_ID = ?
        ORDER BY a.CODIGO
        """,
        (muestra_id,),
    ).fetchall()

    por_analisis = {
        fila["ANALISIS_ID"]: fila for fila in resultados
    }

    obligatorios = [
        fila for fila in catalogo if fila["OBLIGATORIO"]
    ]

    faltantes = [
        fila["CODIGO"]
        for fila in obligatorios
        if (
            fila["ID"] not in por_analisis
            or por_analisis[fila["ID"]]["CLASIFICACION"]
            == PENDIENTE
            or not por_analisis[fila["ID"]]["RESULTADO"].strip()
        )
    ]

    # Sin controles obligatorios definidos no hay completitud.
    configurado = bool(obligatorios)
    completos = configurado and not faltantes

    historial = conexion.execute(
        """
        SELECT
            h.ID,
            r.ANALISIS_ID,
            a.CODIGO,
            h.VERSION,
            h.RESULTADO,
            h.CLASIFICACION,
            h.OBSERVACIONES,
            h.RESPONSABLE_ID,
            p.NOMBRE AS RESPONSABLE,
            h.FECHA,
            h.MOTIVO
        FROM HISTORIAL_RESULTADOS AS h
        JOIN RESULTADOS_ANALISIS AS r ON r.ID = h.RESULTADO_ID
        JOIN CATALOGO_ANALISIS AS a ON a.ID = r.ANALISIS_ID
        JOIN PERSONAL AS p ON p.ID_EMPLEADO = h.RESPONSABLE_ID
        WHERE r.MUESTRA_ID = ?
        ORDER BY h.ID
        """,
        (muestra_id,),
    ).fetchall()

    return {
        "MUESTRA": dict(muestra),
        "CATALOGO": [dict(fila) for fila in catalogo],
        "RESULTADOS": [dict(fila) for fila in resultados],
        "HISTORIAL": [dict(fila) for fila in historial],
        "CATALOGO_CONFIGURADO": configurado,
        "FALTANTES": faltantes,
        "COMPLETOS": completos,
        # Es información para revisión; no autoriza liberación.
        "TIENE_NO_CONFORMES": any(
            fila["CLASIFICACION"] == NO_CONFORME
            for fila in resultados
        ),
    }


def consultar_resultados(
    muestra_id,
    empleado_id,
    ruta=RUTA_BD,
):
    with conectar(ruta) as conexion:
        # Mantiene una vista consistente entre resultados e historial.
        conexion.execute("BEGIN")

        validar_enfermero(conexion, empleado_id)
        muestra_id = validar_identificador(
            muestra_id, "muestra"
        )

        return _consultar(conexion, muestra_id)


def _guardar_resultado_en_conexion(
    conexion,
    muestra_id,
    analisis_id,
    resultado,
    clasificacion,
    empleado_id,
    observaciones,
    motivo_cambio,
    instante,
    actualizar_estado=True,
):

    empleado_id = validar_enfermero(conexion, empleado_id)
    muestra_id = validar_identificador(
        muestra_id, "muestra"
    )
    analisis_id = validar_identificador(
        analisis_id, "análisis"
    )

    muestra = _obtener_muestra(conexion, muestra_id)

    if muestra["ESTADO"] not in (
        PENDIENTE_ANALISIS,
        PENDIENTE_REVISION,
    ):
        raise ValueError(
            "La muestra no admite modificaciones de resultados "
            "en su estado actual."
        )

    pendiente = (
        muestra["ESTADO_UNIDAD"] == PENDIENTE_ANALISIS
        and muestra["ESTADO_LABORATORIO"]
        == PENDIENTE_ANALISIS
    )

    bloqueada_por_laboratorio = (
        muestra["ESTADO_UNIDAD"] == "Bloqueada"
        and muestra["ESTADO_LABORATORIO"] == "Bloqueada"
    )

    if not (pendiente or bloqueada_por_laboratorio):
        raise ValueError(
            "Solo se admiten resultados para unidades pendientes "
            "o bloqueadas por laboratorio. No se modificarán "
            "unidades liberadas, reservadas, usadas, descartadas "
            "o vencidas."
        )

    vencimiento = validar_fecha(
        muestra["FECHA_VENCIMIENTO"], "%Y-%m-%d"
    )

    if vencimiento < instante.date():
        raise ValueError(
            "No se pueden registrar resultados mediante este "
            "flujo para una unidad que ya venció."
        )

    analisis = conexion.execute(
        """
        SELECT ID
        FROM CATALOGO_ANALISIS
        WHERE ID = ? AND ACTIVO = 1
        """,
        (analisis_id,),
    ).fetchone()

    if analisis is None:
        raise ValueError(
            "El análisis no existe o no está activo."
        )

    if clasificacion not in CLASIFICACIONES:
        raise ValueError(
            "Seleccione Pendiente, Conforme o No conforme."
        )

    resultado = _texto(
        resultado,
        "Resultado",
        2000,
        permitir_vacio=clasificacion == PENDIENTE,
    )
    observaciones = _texto(
        observaciones,
        "Observaciones",
        2000,
        permitir_vacio=True,
    )

    anterior = conexion.execute(
        """
        SELECT ID, VERSION
        FROM RESULTADOS_ANALISIS
        WHERE MUESTRA_ID = ? AND ANALISIS_ID = ?
        """,
        (muestra_id, analisis_id),
    ).fetchone()

    fecha = instante.isoformat(timespec="microseconds")

    if anterior is None:
        version = 1
        motivo = "Registro inicial"

        cursor = conexion.execute(
            """
            INSERT INTO RESULTADOS_ANALISIS (
                MUESTRA_ID, ANALISIS_ID,
                RESULTADO, CLASIFICACION, OBSERVACIONES,
                RESPONSABLE_ID, FECHA, VERSION
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                muestra_id,
                analisis_id,
                resultado,
                clasificacion,
                observaciones,
                empleado_id,
                fecha,
                version,
            ),
        )
        resultado_id = cursor.lastrowid

    else:
        motivo = _texto(
            motivo_cambio, "Motivo del cambio", 1000
        )
        resultado_id = anterior["ID"]
        version = anterior["VERSION"] + 1

        conexion.execute(
            """
            UPDATE RESULTADOS_ANALISIS
            SET RESULTADO = ?,
                CLASIFICACION = ?,
                OBSERVACIONES = ?,
                RESPONSABLE_ID = ?,
                FECHA = ?,
                VERSION = ?
            WHERE ID = ?
            """,
            (
                resultado,
                clasificacion,
                observaciones,
                empleado_id,
                fecha,
                version,
                resultado_id,
            ),
        )

    # Cada versión guarda una copia completa del resultado.
    conexion.execute(
        """
        INSERT INTO HISTORIAL_RESULTADOS (
            RESULTADO_ID, VERSION,
            RESULTADO, CLASIFICACION, OBSERVACIONES,
            RESPONSABLE_ID, FECHA, MOTIVO
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            resultado_id,
            version,
            resultado,
            clasificacion,
            observaciones,
            empleado_id,
            fecha,
            motivo,
        ),
    )

    if not actualizar_estado:
        return None

    datos = _consultar(conexion, muestra_id)

    estado_nuevo = (
        PENDIENTE_REVISION
        if datos["COMPLETOS"]
        else PENDIENTE_ANALISIS
    )

    if estado_nuevo != muestra["ESTADO"]:
        conexion.execute(
            "UPDATE MUESTRAS SET ESTADO = ? WHERE ID = ?",
            (estado_nuevo, muestra_id),
        )

        conexion.execute(
            """
            INSERT INTO HISTORIAL_MUESTRAS (
                MUESTRA_ID, ACCION,
                ESTADO_ANTERIOR, ESTADO_NUEVO,
                RESPONSABLE_ID, FECHA, MOTIVO
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                muestra_id,
                "Actualización de resultados",
                muestra["ESTADO"],
                estado_nuevo,
                empleado_id,
                fecha,
                "Actualización de completitud de análisis. "
                "No autoriza la liberación de la unidad.",
            ),
        )
    # HU14-T3: resultado, historial y decisión de laboratorio
    # se confirman o revierten juntos.
    from servicios.liberacion import evaluar_en_transaccion

    evaluar_en_transaccion(
        conexion,
        muestra["DONACION_ID"],
        empleado_id,
        instante,
        muestra_id=muestra_id,
    )

    return _consultar(conexion, muestra_id)

def guardar_resultado(
    muestra_id,
    analisis_id,
    resultado,
    clasificacion,
    empleado_id,
    observaciones="",
    motivo_cambio="",
    ruta=RUTA_BD,
    ahora=None,
):
    instante = obtener_instante(ahora)

    with conectar(ruta) as conexion:
        conexion.execute("BEGIN IMMEDIATE")

        return _guardar_resultado_en_conexion(

            conexion,
            muestra_id,
            analisis_id,
            resultado,
            clasificacion,
            empleado_id,
            observaciones,
            motivo_cambio,
            instante,
        )

def guardar_informe(
    muestra_id,
    controles,
    empleado_id,
    motivo_cambio="",
    ruta=RUTA_BD,
    ahora=None,
):
    """Guarda todos los controles juntos, sin autorizar la liberación."""
    opciones = {
        "PENDIENTE": ("", PENDIENTE),
        "NEGATIVO": ("Negativo", "Conforme"),
        "POSITIVO": ("Positivo", "No conforme"),
    }

    if not isinstance(controles, (list, tuple)) or not controles:
        raise ValueError("El informe debe contener sus controles.")

    instante = obtener_instante(ahora)

    with conectar(ruta) as conexion:
        conexion.execute("BEGIN IMMEDIATE")

        empleado_id = validar_enfermero(conexion, empleado_id)
        muestra_id = validar_identificador(muestra_id, "muestra")

        datos = _consultar(conexion, muestra_id)

        catalogo = {
            fila["ID"]: fila
            for fila in datos["CATALOGO"]
        }

        obligatorios = {
            identificador
            for identificador, fila in catalogo.items()
            if fila["OBLIGATORIO"]
        }

        if not obligatorios:
            raise ValueError(
                "No hay controles obligatorios configurados."
            )

        anteriores = {
            fila["ANALISIS_ID"]: fila
            for fila in datos["RESULTADOS"]
        }

        vistos = set()
        cambios = []

        for control in controles:
            if not isinstance(control, dict):
                raise ValueError(
                    "Cada control debe ser un registro válido."
                )

            identificador = validar_identificador(
                control.get("analisis_id"), "análisis"
            )
            seleccion = control.get("seleccion")

            if (
                not isinstance(seleccion, str)
                or seleccion not in opciones
            ):
                raise ValueError(
                    "Seleccione PENDIENTE, NEGATIVO o POSITIVO."
                )

            if identificador in vistos:
                raise ValueError(
                    "Hay un control repetido en el informe."
                )

            if identificador not in catalogo:
                raise ValueError(
                    "El informe contiene un control "
                    "inexistente o inactivo."
                )

            vistos.add(identificador)

            resultado, clasificacion = opciones[seleccion]
            anterior = anteriores.get(identificador)

            observaciones = _texto(
                control.get(
                    "observaciones",
                    anterior["OBSERVACIONES"] if anterior else "",
                ),
                "Observaciones",
                2000,
                permitir_vacio=True,
            )

            if anterior and (
                anterior["RESULTADO"] == resultado
                and anterior["CLASIFICACION"] == clasificacion
                and anterior["OBSERVACIONES"] == observaciones
            ):
                continue

            cambios.append(
                (
                    identificador,
                    resultado,
                    clasificacion,
                    observaciones,
                )
            )

        if not obligatorios.issubset(vistos):
            raise ValueError(
                "El informe debe incluir todos "
                "los controles obligatorios."
            )

        for posicion, cambio in enumerate(cambios):
            identificador, resultado, clasificacion, observaciones = cambio

            _guardar_resultado_en_conexion(
                conexion=conexion,
                muestra_id=muestra_id,
                analisis_id=identificador,
                resultado=resultado,
                clasificacion=clasificacion,
                empleado_id=empleado_id,
                observaciones=observaciones,
                motivo_cambio=motivo_cambio,
                instante=instante,
                actualizar_estado=posicion == len(cambios) - 1,
            )

        return _consultar(conexion, muestra_id)