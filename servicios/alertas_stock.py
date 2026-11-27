import sqlite3
from contextlib import closing

from datos.configuracion import RUTA_BD
from servicios.vencimientos import DISPONIBLE
from servicios.vencimientos import DISPONIBLE, fecha_actual


def obtener_alertas_sobreabastecimiento():
    """Evalúa el stock disponible frente a los umbrales."""
    try:
        with closing(sqlite3.connect(RUTA_BD)) as conexion:
            cursor = conexion.cursor()

            cursor.execute(
                """
                SELECT TIPO_SANGRE, FACTOR_RH, COUNT(ID)
                FROM DONACIONES
                WHERE ESTADO = ?
                  AND ESTADO_LABORATORIO = 'Liberada'
                  AND FECHA_VENCIMIENTO >= ?
                GROUP BY TIPO_SANGRE, FACTOR_RH
                """,
                (DISPONIBLE, fecha_actual().isoformat()),
            )

            stock_agrupado = {
                f"{fila[0]}{fila[1]}": fila[2]
                for fila in cursor.fetchall()
            }

            cursor.execute(
                """
                SELECT GRUPO_SANGUINEO, FACTOR_RH, UMBRAL_MAXIMO
                FROM UMBRALES
                """
            )
            umbrales = cursor.fetchall()

        alertas = []

        for grupo, rh, umbral_max in umbrales:
            if umbral_max is None or umbral_max < 0:
                continue

            stock_actual = stock_agrupado.get(
                f"{grupo}{rh}", 0
            )

            if stock_actual > umbral_max:
                alertas.append(
                    {
                        "grupo": grupo,
                        "rh": rh,
                        "stock": stock_actual,
                        "umbral": umbral_max,
                        "excedente": stock_actual - umbral_max,
                    }
                )

        return alertas

    except sqlite3.Error as error:
        raise ValueError(
            "Error de base de datos al evaluar abastecimiento."
        ) from error


def sugerir_redistribucion(grupo, rh):
    """Consulta hospitales que necesitan ese grupo y Rh."""
    try:
        with closing(sqlite3.connect(RUTA_BD)) as conexion:
            destinos = conexion.execute(
                """
                SELECT NOMBRE, DIRECCION, CANTIDAD_REQUERIDA
                FROM HOSPITALES
                WHERE GRUPO_SANGUINEO_REQUERIDO = ?
                  AND FACTOR_RH_REQUERIDO = ?
                  AND CANTIDAD_REQUERIDA > 0
                """,
                (grupo, rh),
            ).fetchall()

        return [
            {
                "nombre": nombre,
                "direccion": direccion,
                "requiere": cantidad,
            }
            for nombre, direccion, cantidad in destinos
        ]

    except sqlite3.Error as error:
        raise ValueError(
            "Error al buscar sugerencias de destino."
        ) from error