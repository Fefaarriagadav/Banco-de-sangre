"""HU14-T3: autorización de laboratorio y trazabilidad de decisiones."""
import math

from datos.configuracion import RUTA_BD
from servicios.muestras import (
    conectar,
    obtener_instante,
    validar_enfermero,
    validar_identificador,
)
from servicios.vencimientos import validar_fecha

PENDIENTE_LABORATORIO = "Pendiente de análisis"
LIBERADA = "Liberada"
BLOQUEADA = "Bloqueada"


def migrar_liberacion(conexion):
    columnas = {
        fila[1]
        for fila in conexion.execute(
            "PRAGMA table_info(DONACIONES)"
        )
    }

    if not columnas:
        raise RuntimeError(
            "Debe existir DONACIONES antes de inicializar HU14-T3."
        )

    if "ESTADO_LABORATORIO" not in columnas:
        conexion.execute(
            """
            ALTER TABLE DONACIONES
            ADD COLUMN ESTADO_LABORATORIO TEXT NOT NULL
            DEFAULT 'Pendiente de análisis'
            CHECK (
                ESTADO_LABORATORIO IN (
                    'Pendiente de análisis',
                    'Liberada',
                    'Bloqueada'
                )
            )
            """
        )

    conexion.execute(
        """
        CREATE TABLE IF NOT EXISTS HISTORIAL_LIBERACION (
            ID INTEGER PRIMARY KEY AUTOINCREMENT,

            DONACION_ID INTEGER NOT NULL
                REFERENCES DONACIONES(ID),

            MUESTRA_ID INTEGER
                REFERENCES MUESTRAS(ID),

            ACCION TEXT NOT NULL,

            ESTADO_LAB_ANTERIOR TEXT NOT NULL,
            ESTADO_LAB_NUEVO TEXT NOT NULL,

            ESTADO_UNIDAD_ANTERIOR TEXT,
            ESTADO_UNIDAD_NUEVO TEXT,

            RESPONSABLE_ID INTEGER NOT NULL
                REFERENCES PERSONAL(ID_EMPLEADO),

            FECHA TEXT NOT NULL,
            MOTIVO TEXT NOT NULL
        )
        """
    )

    conexion.execute(
        """
        CREATE INDEX IF NOT EXISTS IDX_LIBERACION_DONACION
        ON HISTORIAL_LIBERACION(DONACION_ID)
        """
    )
def _evaluar(conexion, donacion_id, instante):
    unidad = conexion.execute(
        """
        SELECT
            ID, ESTADO, ESTADO_LABORATORIO,
            FECHA_EXTRACCIÓN, FECHA_VENCIMIENTO, CANTIDAD
        FROM DONACIONES
        WHERE ID = ?
        """,
        (donacion_id,),
    ).fetchone()

    if unidad is None:
        raise ValueError("No existe una donación con ese ID.")

    muestras = conexion.execute(
        """
        SELECT ID
        FROM MUESTRAS
        WHERE DONACION_ID = ?
        ORDER BY ID
        """,
        (donacion_id,),
    ).fetchall()

    obligatorios = conexion.execute(
        """
        SELECT ID, CODIGO
        FROM CATALOGO_ANALISIS
        WHERE ACTIVO = 1 AND OBLIGATORIO = 1
        ORDER BY CODIGO
        """
    ).fetchall()

    resultados = conexion.execute(
        """
        SELECT
            r.ID, r.MUESTRA_ID, r.ANALISIS_ID,
            r.RESULTADO, r.CLASIFICACION, r.VERSION
        FROM RESULTADOS_ANALISIS AS r
        JOIN MUESTRAS AS m ON m.ID = r.MUESTRA_ID
        WHERE m.DONACION_ID = ?
        ORDER BY r.ID
        """,
        (donacion_id,),
    ).fetchall()

    por_control = {
        (fila["MUESTRA_ID"], fila["ANALISIS_ID"]): fila
        for fila in resultados
    }

    faltantes = []

    for muestra in muestras:
        for control in obligatorios:
            resultado = por_control.get(
                (muestra["ID"], control["ID"])
            )

            if (
                resultado is None
                or resultado["CLASIFICACION"] == "Pendiente"
                or not resultado["RESULTADO"].strip()
            ):
                faltantes.append(
                    f"Muestra #{muestra['ID']}: "
                    f"{control['CODIGO']}"
                )

    no_conformes = [
        {
            "RESULTADO_ID": fila["ID"],
            "MUESTRA_ID": fila["MUESTRA_ID"],
            "VERSION": fila["VERSION"],
        }
        for fila in resultados
        if fila["CLASIFICACION"] == "No conforme"
    ]

    problemas = []
    vencida = unidad["ESTADO"] == "Vencida"

    try:
        extraccion = validar_fecha(
            unidad["FECHA_EXTRACCIÓN"], "%Y-%m-%d"
        )
        vencimiento = validar_fecha(
            unidad["FECHA_VENCIMIENTO"], "%Y-%m-%d"
        )

        vencida = vencida or vencimiento < instante.date()

        if extraccion > instante.date():
            problemas.append("La extracción está en el futuro.")

        if vencimiento < extraccion:
            problemas.append(
                "El vencimiento es anterior a la extracción."
            )

        if vencida:
            problemas.append("La unidad está vencida.")

    except ValueError:
        problemas.append("Las fechas de la unidad no son válidas.")

    try:
        cantidad = float(unidad["CANTIDAD"])

        if not math.isfinite(cantidad) or cantidad <= 0:
            problemas.append("La cantidad no es válida.")
    except (ValueError, TypeError, OverflowError):
        problemas.append("La cantidad no es válida.")

    completos = (
        bool(muestras)
        and bool(obligatorios)
        and not faltantes
    )

    if not muestras:
        problemas.append("La donación no tiene muestras.")

    if not obligatorios:
        problemas.append(
            "No hay controles obligatorios activos configurados."
        )

    if faltantes:
        problemas.append("Existen controles pendientes.")

    if no_conformes:
        problemas.append("Existen resultados No conformes.")

    if unidad["ESTADO"] not in (
        "Disponible",
        "Pendiente de análisis",
    ):
        problemas.append(
            f"El estado de inventario es {unidad['ESTADO']}."
        )

    return {
        "UNIDAD": dict(unidad),
        "MUESTRAS": [fila["ID"] for fila in muestras],
        "COMPLETOS": completos,
        "FALTANTES": faltantes,
        "NO_CONFORMES": no_conformes,
        "PROBLEMAS": problemas,
        "VENCIDA": vencida,
        "PUEDE_LIBERARSE": completos and not problemas,
        "VERSIONES": [
            {
                "ID": fila["ID"],
                "VERSION": fila["VERSION"],
            }
            for fila in resultados
        ],
    }


def _guardar_decision(
    conexion,
    evaluacion,
    empleado_id,
    instante,
    accion,
    estado_lab,
    estado_unidad,
    motivo,
    muestra_id=None,
):
    unidad = evaluacion["UNIDAD"]

    if muestra_id is not None:
        muestra_id = validar_identificador(
            muestra_id, "muestra"
        )

        if muestra_id not in evaluacion["MUESTRAS"]:
            raise ValueError(
                "La muestra no pertenece a esta donación."
            )

    # La autorización abarca todas las muestras, no solo una.
    referencia = (
        f"Muestras evaluadas: {evaluacion['MUESTRAS']}. "
        f"Versiones de resultados: {evaluacion['VERSIONES']}."
    )

    conexion.execute(
        """
        UPDATE DONACIONES
        SET ESTADO_LABORATORIO = ?, ESTADO = ?
        WHERE ID = ?
        """,
        (estado_lab, estado_unidad, unidad["ID"]),
    )

    conexion.execute(
        """
        INSERT INTO HISTORIAL_LIBERACION (
            DONACION_ID, MUESTRA_ID, ACCION,
            ESTADO_LAB_ANTERIOR, ESTADO_LAB_NUEVO,
            ESTADO_UNIDAD_ANTERIOR, ESTADO_UNIDAD_NUEVO,
            RESPONSABLE_ID, FECHA, MOTIVO
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            unidad["ID"],
            muestra_id,
            accion,
            unidad["ESTADO_LABORATORIO"],
            estado_lab,
            unidad["ESTADO"],
            estado_unidad,
            empleado_id,
            instante.isoformat(timespec="microseconds"),
            f"{motivo} {referencia}",
        ),
    )


def evaluar_unidad(
    donacion_id,
    empleado_id,
    ruta=RUTA_BD,
    ahora=None,
    muestra_id=None,
):
    """
    Reevalúa tras registrar una muestra o cambiar resultados.
    Invalida la autorización anterior; nunca libera automáticamente.
    """
    instante = obtener_instante(ahora)

    with conectar(ruta) as conexion:
        conexion.execute("BEGIN IMMEDIATE")

        empleado_id = validar_enfermero(
            conexion, empleado_id
        )
        donacion_id = validar_identificador(
            donacion_id, "donación"
        )

        return evaluar_en_transaccion(
            conexion,
            donacion_id,
            empleado_id,
            instante,
            muestra_id=muestra_id,
        )


def evaluar_en_transaccion(
    conexion,
    donacion_id,
    empleado_id,
    instante,
    muestra_id=None,
):
    """
    Uso interno: exige una transacción y empleado ya autorizado.
    Permite evaluar dentro del guardado de resultados.
    """
    evaluacion = _evaluar(
        conexion, donacion_id, instante
    )
    unidad = evaluacion["UNIDAD"]

    estado_lab = (
        BLOQUEADA
        if evaluacion["NO_CONFORMES"]
        else PENDIENTE_LABORATORIO
    )

    estado_unidad = unidad["ESTADO"]

    if estado_unidad not in ("Usada", "Descartada", "Vencida"):
        if evaluacion["VENCIDA"]:
            estado_unidad = "Vencida"
        elif estado_unidad != "Reservada":
            estado_unidad = (
                "Bloqueada"
                if estado_lab == BLOQUEADA
                else "Pendiente de análisis"
            )

    motivo = (
        "Bloqueo por resultado No conforme."
        if estado_lab == BLOQUEADA
        else "Evaluación actualizada; requiere autorización explícita."
    )

    _guardar_decision(
        conexion,
        evaluacion,
        empleado_id,
        instante,
        accion="Evaluación de laboratorio",
        estado_lab=estado_lab,
        estado_unidad=estado_unidad,
        motivo=motivo,
        muestra_id=muestra_id,
    )

    return _evaluar(conexion, donacion_id, instante)


def autorizar_liberacion(
    donacion_id,
    empleado_id,
    motivo,
    ruta=RUTA_BD,
    ahora=None,
):
    instante = obtener_instante(ahora)

    if (
        not isinstance(motivo, str)
        or not motivo.strip()
        or len(motivo.strip()) > 1000
    ):
        raise ValueError(
            "Ingrese un motivo de autorización de hasta 1000 caracteres."
        )

    with conectar(ruta) as conexion:
        conexion.execute("BEGIN IMMEDIATE")

        empleado_id = validar_enfermero(
            conexion, empleado_id
        )
        donacion_id = validar_identificador(
            donacion_id, "donación"
        )

        evaluacion = _evaluar(
            conexion, donacion_id, instante
        )

        if not evaluacion["PUEDE_LIBERARSE"]:
            raise ValueError(
                "No se puede liberar: "
                + " ".join(evaluacion["PROBLEMAS"])
            )

        if evaluacion["UNIDAD"]["ESTADO_LABORATORIO"] == BLOQUEADA:
            raise ValueError(
                "La unidad permanece bloqueada. "
                "Debe corregirse y reevaluarse antes de autorizar."
            )

        if evaluacion["UNIDAD"]["ESTADO_LABORATORIO"] == LIBERADA:
            raise ValueError(
                "La unidad ya tiene autorización de laboratorio."
            )

        _guardar_decision(
            conexion,
            evaluacion,
            empleado_id,
            instante,
            accion="Autorización de liberación",
            estado_lab=LIBERADA,
            estado_unidad="Disponible",
            motivo=motivo.strip(),
            muestra_id=(
                evaluacion["MUESTRAS"][-1]
                if len(evaluacion["MUESTRAS"]) == 1
                else None
            ),
        )

        return _evaluar(conexion, donacion_id, instante)


def consultar_liberacion(
    donacion_id,
    empleado_id,
    ruta=RUTA_BD,
    ahora=None,
):
    instante = obtener_instante(ahora)

    with conectar(ruta) as conexion:
        conexion.execute("BEGIN")

        validar_enfermero(conexion, empleado_id)
        donacion_id = validar_identificador(
            donacion_id, "donación"
        )

        datos = _evaluar(
            conexion, donacion_id, instante
        )

        historial = conexion.execute(
            """
            SELECT
                h.*,
                p.NOMBRE AS RESPONSABLE
            FROM HISTORIAL_LIBERACION AS h
            JOIN PERSONAL AS p
                ON p.ID_EMPLEADO = h.RESPONSABLE_ID
            WHERE h.DONACION_ID = ?
            ORDER BY h.ID
            """,
            (donacion_id,),
        ).fetchall()

        datos["HISTORIAL"] = [
            dict(fila) for fila in historial
        ]

        return datos