import sqlite3
import tempfile
import unittest
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from datos.basededatos import inicializar_base
from servicios.muestras import registrar_muestra
from servicios.resultados_analisis import guardar_resultado
from servicios.consulta_laboratorio import (
    listar_laboratorio,
    filtrar_registros,
)


class ConsultaLaboratorioTest(unittest.TestCase):
    def setUp(self):
        temporal = tempfile.TemporaryDirectory()
        self.addCleanup(temporal.cleanup)

        self.ruta = Path(temporal.name) / "listado_prueba.db"
        inicializar_base(self.ruta)

        ahora = datetime(
            2026, 11, 26, 15, 0, tzinfo=timezone.utc
        )

        with closing(sqlite3.connect(self.ruta)) as conexion, conexion:
            conexion.executemany(
                """
                INSERT INTO PERSONAL (
                    ID_EMPLEADO, NOMBRE, ROL
                )
                VALUES (?, ?, ?)
                """,
                [
                    (1, "Enfermero prueba", "Enfermero"),
                    (2, "Entrevistador prueba", "Entrevistador"),
                ],
            )

            for identificador, grupo, rh in (
                (1, "A", "+"),
                (2, "O", "-"),
            ):
                conexion.execute(
                    """
                    INSERT INTO DONANTES (
                        ID, NOMBRE, APELLIDO, EDAD, SEXO,
                        GRUPO_SANGUINEO, FACTOR_RH, PESO,
                        EMAIL, ELEGIBLE, FECHA_DE_NACIMIENTO
                    )
                    VALUES (
                        ?, 'Donante', 'Ficticio', 30, 'Masculino',
                        ?, ?, 70, ?, 'Donante apto', '1996-01-01'
                    )
                    """,
                    (
                        identificador,
                        grupo,
                        rh,
                        f"demo{identificador}@example.invalid",
                    ),
                )

                conexion.execute(
                    """
                    INSERT INTO DONACIONES (
                        ID, DONANTE, TIPO_SANGRE, FACTOR_RH,
                        FECHA_EXTRACCIÓN, FECHA_VENCIMIENTO,
                        CANTIDAD, ESTADO
                    )
                    VALUES (
                        ?, ?, ?, ?,
                        '2026-11-20', '2026-12-10',
                        450, 'Disponible'
                    )
                    """,
                    (identificador, identificador, grupo, rh),
                )

            conexion.execute(
                """
                INSERT INTO CATALOGO_ANALISIS (
                    ID, CODIGO, NOMBRE, OBLIGATORIO, ACTIVO
                )
                VALUES (
                    1, 'DEMO_LISTADO', 'Control ficticio', 1, 1
                )
                """
            )

        self.muestra_id = registrar_muestra(
            1, 1, ruta=self.ruta, ahora=ahora
        )["ID"]

        guardar_resultado(
            muestra_id=self.muestra_id,
            analisis_id=1,
            resultado="Informe ficticio",
            clasificacion="Conforme",
            empleado_id=1,
            ruta=self.ruta,
            ahora=ahora,
        )

    def test_lista_muestras_y_donaciones_sin_busqueda(self):
        datos = listar_laboratorio(1, ruta=self.ruta)

        self.assertEqual(len(datos["DONACIONES"]), 2)
        self.assertEqual(len(datos["MUESTRAS"]), 1)

        muestra = datos["MUESTRAS"][0]
        self.assertEqual(muestra["MUESTRA_ID"], self.muestra_id)
        self.assertEqual(muestra["DONACION_ID"], 1)
        self.assertEqual(muestra["AVANCE"], "1/1")
        self.assertEqual(
            muestra["SITUACION"],
            "Pendiente de autorización",
        )

        sin_muestra = next(
            fila
            for fila in datos["DONACIONES"]
            if fila["DONACION_ID"] == 2
        )
        self.assertEqual(sin_muestra["NUM_MUESTRAS"], 0)
        self.assertEqual(sin_muestra["SITUACION"], "Sin muestras")

    def test_filtros_combinados_y_limpieza(self):
        filas = listar_laboratorio(
            1, ruta=self.ruta
        )["MUESTRAS"]

        filtradas = filtrar_registros(
            filas,
            busqueda="enfermero",
            situacion="Pendiente de autorización",
            tipo="A+",
        )

        self.assertEqual(len(filtradas), 1)
        self.assertEqual(
            filtrar_registros(filas, tipo="O-"),
            [],
        )
        self.assertEqual(
            filtrar_registros(filas, busqueda="inexistente"),
            [],
        )
        self.assertEqual(filtrar_registros(filas), filas)

        with self.assertRaises(ValueError):
            filtrar_registros(filas, situacion="Estado inventado")

    def test_listado_requiere_enfermero(self):
        for empleado in (2, 999, None):
            with self.subTest(empleado=empleado):
                with self.assertRaises(PermissionError):
                    listar_laboratorio(
                        empleado, ruta=self.ruta
                    )

    def test_consultar_no_modifica_datos_ni_historial(self):
        with closing(sqlite3.connect(self.ruta)) as conexion:
            antes = "\n".join(conexion.iterdump())

        listar_laboratorio(1, ruta=self.ruta)

        with closing(sqlite3.connect(self.ruta)) as conexion:
            despues = "\n".join(conexion.iterdump())

        self.assertEqual(antes, despues)


if __name__ == "__main__":
    unittest.main()