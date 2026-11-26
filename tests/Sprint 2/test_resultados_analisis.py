import sqlite3
import tempfile
import unittest
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from datos.basededatos import inicializar_base
from servicios import muestras as m
from servicios import resultados_analisis as r
from servicios import vencimientos as v


class ResultadosAnalisisTest(unittest.TestCase):
    def setUp(self):
        temporal = tempfile.TemporaryDirectory()
        self.addCleanup(temporal.cleanup)

        self.ruta = Path(temporal.name) / "resultados_prueba.db"
        inicializar_base(self.ruta)

        self.ahora = datetime(
            2026, 11, 26, 15, 0, tzinfo=timezone.utc
        )

        with closing(sqlite3.connect(self.ruta)) as conexion, conexion:
            conexion.executemany(
                """
                INSERT INTO PERSONAL (
                    ID_EMPLEADO, RUT, NOMBRE, ROL
                )
                VALUES (?, ?, ?, ?)
                """,
                [
                    (1, "DEMO-1", "Enfermero uno", "Enfermero"),
                    (2, "DEMO-2", "Entrevistador", "Entrevistador"),
                    (3, "DEMO-3", "Enfermero dos", "Enfermero"),
                ],
            )

            conexion.execute(
                """
                INSERT INTO DONANTES (
                    ID, NOMBRE, APELLIDO, EDAD, SEXO,
                    GRUPO_SANGUINEO, FACTOR_RH, PESO,
                    EMAIL, ELEGIBLE, FECHA_DE_NACIMIENTO
                )
                VALUES (
                    1, 'Donante', 'Prueba', 30, 'Masculino',
                    'A', '+', 70, 'demo@example.invalid',
                    'Donante apto', '1996-01-01'
                )
                """
            )

            conexion.execute(
                """
                INSERT INTO DONACIONES (
                    ID, DONANTE, TIPO_SANGRE, FACTOR_RH,
                    FECHA_EXTRACCIÓN, FECHA_VENCIMIENTO,
                    CANTIDAD, ESTADO
                )
                VALUES (
                    1, 1, 'A', '+',
                    '2026-11-20', '2026-12-10',
                    450, 'Disponible'
                )
                """
            )

            conexion.executemany(
                """
                INSERT INTO CATALOGO_ANALISIS (
                    ID, CODIGO, NOMBRE, OBLIGATORIO, ACTIVO
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                [
                    (1, "DEMO_1", "Control ficticio uno", 1, 1),
                    (2, "DEMO_2", "Control ficticio dos", 1, 1),
                    (3, "DEMO_OPC", "Control ficticio opcional", 0, 1),
                    (4, "DEMO_INACT", "Control ficticio inactivo", 1, 0),
                ],
            )

        muestra = m.registrar_muestra(
            1, 1, ruta=self.ruta, ahora=self.ahora
        )
        self.muestra_id = muestra["ID"]

    def ejecutar(self, sql, parametros=()):
        with closing(sqlite3.connect(self.ruta)) as conexion, conexion:
            conexion.execute(sql, parametros)

    def consultar(self):
        return r.consultar_resultados(
            self.muestra_id, 1, ruta=self.ruta
        )

    def guardar(
        self,
        analisis_id=1,
        resultado="Resultado ficticio",
        clasificacion=r.CONFORME,
        empleado_id=1,
        motivo_cambio="",
        muestra_id=None,
    ):
        return r.guardar_resultado(
            muestra_id=(
                self.muestra_id
                if muestra_id is None
                else muestra_id
            ),
            analisis_id=analisis_id,
            resultado=resultado,
            clasificacion=clasificacion,
            empleado_id=empleado_id,
            observaciones="Observación de prueba",
            motivo_cambio=motivo_cambio,
            ruta=self.ruta,
            ahora=self.ahora,
        )

    def test_registro_inicial_conserva_datos_y_responsable(self):
        datos = self.guardar()
        resultado = datos["RESULTADOS"][0]
        historial = datos["HISTORIAL"][0]

        self.assertEqual(resultado["ANALISIS_ID"], 1)
        self.assertEqual(resultado["RESULTADO"], "Resultado ficticio")
        self.assertEqual(resultado["CLASIFICACION"], r.CONFORME)
        self.assertEqual(resultado["RESPONSABLE_ID"], 1)
        self.assertEqual(resultado["VERSION"], 1)
        self.assertEqual(
            datetime.fromisoformat(resultado["FECHA"]),
            self.ahora,
        )

        self.assertEqual(historial["VERSION"], 1)
        self.assertEqual(historial["MOTIVO"], "Registro inicial")
        self.assertEqual(historial["RESULTADO"], resultado["RESULTADO"])

    def test_resultados_parciales_permanecen_pendientes(self):
        datos = self.guardar(analisis_id=1)

        self.assertFalse(datos["COMPLETOS"])
        self.assertEqual(datos["FALTANTES"], ["DEMO_2"])
        self.assertEqual(
            datos["MUESTRA"]["ESTADO"],
            r.PENDIENTE_ANALISIS,
        )
        self.assertEqual(
            datos["MUESTRA"]["ESTADO_UNIDAD"],
            r.PENDIENTE_ANALISIS,
        )

    def test_completos_pasan_a_revision_sin_liberar_unidad(self):
        self.guardar(analisis_id=1)
        datos = self.guardar(analisis_id=2)

        self.assertTrue(datos["COMPLETOS"])
        self.assertEqual(datos["FALTANTES"], [])
        self.assertEqual(
            datos["MUESTRA"]["ESTADO"],
            r.PENDIENTE_REVISION,
        )
        self.assertEqual(
            datos["MUESTRA"]["ESTADO_UNIDAD"],
            r.PENDIENTE_ANALISIS,
        )

    def test_no_conforme_se_registra_sin_liberacion(self):
        self.guardar(analisis_id=1)
        datos = self.guardar(
            analisis_id=2,
            clasificacion=r.NO_CONFORME,
        )

        self.assertTrue(datos["COMPLETOS"])
        self.assertTrue(datos["TIENE_NO_CONFORMES"])
        self.assertEqual(
            datos["MUESTRA"]["ESTADO_UNIDAD"],
            r.PENDIENTE_ANALISIS,
        )

    def test_sin_catalogo_obligatorio_no_hay_completitud(self):
        self.ejecutar(
            "UPDATE CATALOGO_ANALISIS SET ACTIVO = 0"
        )

        datos = self.consultar()

        self.assertFalse(datos["CATALOGO_CONFIGURADO"])
        self.assertFalse(datos["COMPLETOS"])
        self.assertEqual(datos["RESULTADOS"], [])

    def test_correccion_conserva_version_anterior(self):
        self.guardar(resultado="Valor inicial")

        datos = self.guardar(
            resultado="Valor corregido",
            empleado_id=3,
            motivo_cambio="Corrección del informe",
        )

        self.assertEqual(len(datos["RESULTADOS"]), 1)
        self.assertEqual(datos["RESULTADOS"][0]["VERSION"], 2)
        self.assertEqual(
            datos["RESULTADOS"][0]["RESPONSABLE_ID"], 3
        )

        historial = datos["HISTORIAL"]
        self.assertEqual(len(historial), 2)
        self.assertEqual(historial[0]["RESULTADO"], "Valor inicial")
        self.assertEqual(historial[0]["RESPONSABLE_ID"], 1)
        self.assertEqual(historial[1]["RESULTADO"], "Valor corregido")
        self.assertEqual(historial[1]["RESPONSABLE_ID"], 3)
        self.assertEqual(
            historial[1]["MOTIVO"],
            "Corrección del informe",
        )

    def test_correccion_sin_motivo_conserva_valor_anterior(self):
        self.guardar(resultado="Valor inicial")

        with self.assertRaises(ValueError):
            self.guardar(
                resultado="Valor cambiado",
                motivo_cambio=" ",
            )

        datos = self.consultar()
        self.assertEqual(
            datos["RESULTADOS"][0]["RESULTADO"],
            "Valor inicial",
        )
        self.assertEqual(datos["RESULTADOS"][0]["VERSION"], 1)
        self.assertEqual(len(datos["HISTORIAL"]), 1)

    def test_registro_rechaza_personal_no_autorizado(self):
        for empleado in (2, 999, None, "abc"):
            with self.subTest(empleado=empleado):
                with self.assertRaises(PermissionError):
                    self.guardar(empleado_id=empleado)

        self.assertEqual(self.consultar()["RESULTADOS"], [])

    def test_consulta_rechaza_personal_no_autorizado(self):
        for empleado in (2, 999, None):
            with self.subTest(empleado=empleado):
                with self.assertRaises(PermissionError):
                    r.consultar_resultados(
                        self.muestra_id,
                        empleado,
                        ruta=self.ruta,
                    )

    def test_muestra_y_analisis_inexistentes(self):
        with self.assertRaises(ValueError):
            self.guardar(muestra_id=999)

        with self.assertRaises(ValueError):
            self.guardar(analisis_id=999)

        with self.assertRaises(ValueError):
            r.consultar_resultados(
                999, 1, ruta=self.ruta
            )

        self.assertEqual(self.consultar()["RESULTADOS"], [])

    def test_datos_invalidos_no_generan_resultados(self):
        casos = [
            {"resultado": ""},
            {"resultado": None},
            {"resultado": "x" * 2001},
            {"clasificacion": "Seleccione"},
            {"analisis_id": -1},
            {"muestra_id": "abc"},
        ]

        for argumentos in casos:
            with self.subTest(argumentos=argumentos):
                with self.assertRaises(ValueError):
                    self.guardar(**argumentos)

        datos = self.consultar()
        self.assertEqual(datos["RESULTADOS"], [])
        self.assertEqual(datos["HISTORIAL"], [])

    def test_analisis_inactivo_no_admite_registro(self):
        with self.assertRaises(ValueError):
            self.guardar(analisis_id=4)

        self.assertEqual(self.consultar()["RESULTADOS"], [])

    def test_resultado_pendiente_admite_texto_vacio(self):
        datos = self.guardar(
            resultado="",
            clasificacion=r.PENDIENTE,
        )

        self.assertFalse(datos["COMPLETOS"])
        self.assertIn("DEMO_1", datos["FALTANTES"])
        self.assertEqual(
            datos["RESULTADOS"][0]["CLASIFICACION"],
            r.PENDIENTE,
        )

    def test_corregir_a_pendiente_revierte_completitud(self):
        self.guardar(analisis_id=1)
        self.guardar(analisis_id=2)

        datos = self.guardar(
            analisis_id=1,
            resultado="",
            clasificacion=r.PENDIENTE,
            motivo_cambio="Repetición solicitada",
        )

        self.assertFalse(datos["COMPLETOS"])
        self.assertEqual(
            datos["MUESTRA"]["ESTADO"],
            r.PENDIENTE_ANALISIS,
        )
        self.assertIn("DEMO_1", datos["FALTANTES"])

    def test_resultados_completos_no_devuelven_unidad_al_stock(self):
        self.guardar(analisis_id=1)
        self.guardar(analisis_id=2)

        resumen = v.consultar_resumen(
            ruta=self.ruta,
            ahora=self.ahora,
        )
        detalle = v.consultar_stock_detallado(
            ruta=self.ruta,
            ahora=self.ahora,
        )

        self.assertEqual(resumen["unidades"], 0)
        self.assertEqual(detalle["unidades"], [])

    def test_fallo_historial_revierte_resultado_y_estado(self):
        self.ejecutar(
            """
            CREATE TRIGGER SIMULAR_FALLO_RESULTADOS
            BEFORE INSERT ON HISTORIAL_RESULTADOS
            BEGIN
                SELECT RAISE(ABORT, 'Fallo simulado');
            END;
            """
        )

        with self.assertRaises(sqlite3.IntegrityError):
            self.guardar()

        datos = self.consultar()
        self.assertEqual(datos["RESULTADOS"], [])
        self.assertEqual(datos["HISTORIAL"], [])
        self.assertEqual(
            datos["MUESTRA"]["ESTADO"],
            r.PENDIENTE_ANALISIS,
        )

    def test_unidad_vencida_o_no_admitida_rechaza_resultados(self):
        for estado in (
            v.USADA,
            v.DESCARTADA,
            v.VENCIDA,
            "Reservada",
            "Bloqueada",
        ):
            with self.subTest(estado=estado):
                self.ejecutar(
                    "UPDATE DONACIONES SET ESTADO = ? WHERE ID = 1",
                    (estado,),
                )

                with self.assertRaises(ValueError):
                    self.guardar()

        self.ejecutar(
            """
            UPDATE DONACIONES
            SET ESTADO = ?, FECHA_VENCIMIENTO = ?
            WHERE ID = 1
            """,
            (r.PENDIENTE_ANALISIS, "2026-11-25"),
        )

        with self.assertRaises(ValueError):
            self.guardar()

        self.assertEqual(self.consultar()["RESULTADOS"], [])

    def test_migracion_repetida_conserva_resultados_e_historial(self):
        self.guardar()

        inicializar_base(self.ruta)
        inicializar_base(self.ruta)

        datos = self.consultar()
        self.assertEqual(len(datos["RESULTADOS"]), 1)
        self.assertEqual(len(datos["HISTORIAL"]), 1)
        self.assertEqual(datos["RESULTADOS"][0]["VERSION"], 1)


if __name__ == "__main__":
    unittest.main()