"""Listados de laboratorio: solo lectura, permisos y filtros."""

from datos.configuracion import RUTA_BD
from servicios.muestras import conectar, validar_enfermero


SITUACIONES = (
    "Todas",
    "Sin muestras",
    "Sin catálogo",
    "Pendiente de análisis",
    "Pendiente de autorización",
    "Bloqueada",
    "Liberada",
    "Vencida",
    "Usada",
    "Descartada",
    "Reservada",
)

TIPOS = (
    "Todos",
    "A+", "A-",
    "B+", "B-",
    "AB+", "AB-",
    "O+", "O-",
)


def listar_laboratorio(empleado_id, ruta=RUTA_BD):
    with conectar(ruta) as conexion:
        conexion.execute("BEGIN")
        validar_enfermero(conexion, empleado_id)

        unidades = [
            dict(fila)
            for fila in conexion.execute(
                """
                SELECT
                    d.ID AS DONACION_ID,
                    d.DONANTE AS DONANTE_ID,
                    COALESCE(
                        d.TIPO_SANGRE, p.GRUPO_SANGUINEO, '?'
                    ) AS GRUPO,
                    COALESCE(d.FACTOR_RH, p.FACTOR_RH, '?') AS RH,
                    d.FECHA_EXTRACCIÓN AS EXTRACCION,
                    d.FECHA_VENCIMIENTO AS VENCIMIENTO,
                    d.ESTADO AS INVENTARIO,
                    d.ESTADO_LABORATORIO AS LABORATORIO
                FROM DONACIONES AS d
                LEFT JOIN DONANTES AS p ON p.ID = d.DONANTE
                ORDER BY d.ID DESC
                """
            )
        ]

        muestras = [
            dict(fila)
            for fila in conexion.execute(
                """
                SELECT
                    m.ID AS MUESTRA_ID,
                    m.DONACION_ID,
                    m.ESTADO AS ESTADO_MUESTRA,
                    m.FECHA_REGISTRO,
                    m.REGISTRADA_POR,
                    p.NOMBRE AS RESPONSABLE
                FROM MUESTRAS AS m
                JOIN PERSONAL AS p
                    ON p.ID_EMPLEADO = m.REGISTRADA_POR
                ORDER BY m.ID DESC
                """
            )
        ]

        obligatorios = {
            fila[0]
            for fila in conexion.execute(
                """
                SELECT ID
                FROM CATALOGO_ANALISIS
                WHERE ACTIVO = 1 AND OBLIGATORIO = 1
                """
            )
        }

        resultados = [
            dict(fila)
            for fila in conexion.execute(
                """
                SELECT
                    MUESTRA_ID, ANALISIS_ID,
                    RESULTADO, CLASIFICACION
                FROM RESULTADOS_ANALISIS
                """
            )
        ]

    por_muestra = {}
    no_conformes = set()

    for resultado in resultados:
        muestra_id = resultado["MUESTRA_ID"]

        if resultado["CLASIFICACION"] == "No conforme":
            no_conformes.add(muestra_id)

        if (
            resultado["CLASIFICACION"] != "Pendiente"
            and resultado["RESULTADO"].strip()
        ):
            por_muestra.setdefault(muestra_id, set()).add(
                resultado["ANALISIS_ID"]
            )

    por_donacion = {}

    for muestra in muestras:
        hechos = (
            por_muestra.get(muestra["MUESTRA_ID"], set())
            & obligatorios
        )

        muestra["AVANCE"] = (
            f"{len(hechos)}/{len(obligatorios)}"
            if obligatorios
            else "Sin catálogo"
        )
        muestra["COMPLETA"] = (
            bool(obligatorios) and hechos == obligatorios
        )

        por_donacion.setdefault(
            muestra["DONACION_ID"], []
        ).append(muestra)

    por_id = {}

    for unidad in unidades:
        asociadas = por_donacion.get(
            unidad["DONACION_ID"], []
        )

        unidad["TIPO"] = unidad["GRUPO"] + unidad["RH"]
        unidad["NUM_MUESTRAS"] = len(asociadas)

        if unidad["INVENTARIO"] in (
            "Vencida", "Usada", "Descartada", "Reservada"
        ):
            situacion = unidad["INVENTARIO"]
        elif (
            unidad["LABORATORIO"] == "Bloqueada"
            or any(
                muestra["MUESTRA_ID"] in no_conformes
                for muestra in asociadas
            )
        ):
            situacion = "Bloqueada"
        elif not asociadas:
            situacion = "Sin muestras"
        elif not obligatorios:
            situacion = "Sin catálogo"
        elif not all(muestra["COMPLETA"] for muestra in asociadas):
            situacion = "Pendiente de análisis"
        elif unidad["LABORATORIO"] == "Liberada":
            situacion = "Liberada"
        else:
            situacion = "Pendiente de autorización"

        unidad["SITUACION"] = situacion
        por_id[unidad["DONACION_ID"]] = unidad

    for muestra in muestras:
        unidad = por_id[muestra["DONACION_ID"]]
        muestra.update(
            {
                clave: valor
                for clave, valor in unidad.items()
                if clave != "DONACION_ID"
            }
        )

    return {
        "MUESTRAS": muestras,
        "DONACIONES": unidades,
    }


def filtrar_registros(
    filas,
    busqueda="",
    situacion="Todas",
    tipo="Todos",
):
    if situacion not in SITUACIONES or tipo not in TIPOS:
        raise ValueError("Seleccione filtros válidos.")

    texto = busqueda.strip().casefold()

    return [
        fila
        for fila in filas
        if (
            situacion == "Todas"
            or fila["SITUACION"] == situacion
        )
        and (
            tipo == "Todos"
            or fila["TIPO"] == tipo
        )
        and (
            not texto
            or any(
                texto in str(fila.get(campo, "")).casefold()
                for campo in (
                    "MUESTRA_ID",
                    "DONACION_ID",
                    "DONANTE_ID",
                    "RESPONSABLE",
                )
            )
        )
    ]