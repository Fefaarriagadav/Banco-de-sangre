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
            "Bloqueada",
        )
        self.assertEqual(
            datos["MUESTRA"]["ESTADO_LABORATORIO"],
            "Bloqueada",
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

    def _controles_hu14(self):
        codigos = (
            (1, "VIH_1_2"), (2, "HEPATITIS_B"),
            (5, "HEPATITIS_C"), (6, "HTLV_1_2"),
            (7, "CHAGAS"), (8, "SIFILIS"),
        )
        for identificador, codigo in codigos:
            self.ejecutar(
                """INSERT INTO CATALOGO_ANALISIS
                   (ID, CODIGO, NOMBRE, OBLIGATORIO, ACTIVO)
                   VALUES (?, ?, ?, 1, 1)
                   ON CONFLICT(ID) DO UPDATE SET
                       CODIGO=excluded.CODIGO,
                       NOMBRE=excluded.NOMBRE,
                       OBLIGATORIO=1, ACTIVO=1""",
                (identificador, codigo, f"Control de prueba {codigo}"),
            )
        return [
            {"analisis_id": identificador, "seleccion": "NEGATIVO"}
            for identificador, _ in codigos
        ]

    def _informe_hu14(self, controles, motivo="", empleado=1):
        return r.guardar_informe(
            muestra_id=self.muestra_id,
            controles=controles,
            empleado_id=empleado,
            motivo_cambio=motivo,
            ruta=self.ruta,
            ahora=self.ahora,
        )

    def _filas_hu14(self, sql):
        with closing(sqlite3.connect(self.ruta)) as conexion:
            return conexion.execute(sql).fetchall()

    def _copia_hu14(self):
        with closing(sqlite3.connect(self.ruta)) as conexion:
            return "\n".join(conexion.iterdump())

    def test_informe_seis_negativos_no_libera_automaticamente(self):
        datos = self._informe_hu14(self._controles_hu14())

        self.assertTrue(datos["COMPLETOS"])
        self.assertEqual(len(datos["RESULTADOS"]), 6)
        self.assertEqual(len(datos["HISTORIAL"]), 6)
        self.assertEqual(
            datos["MUESTRA"]["ESTADO_UNIDAD"],
            "Pendiente de análisis",
        )
        self.assertEqual(
            datos["MUESTRA"]["ESTADO_LABORATORIO"],
            "Pendiente de análisis",
        )
        self.assertEqual(
            self._filas_hu14("SELECT ELEGIBLE FROM DONANTES"),
            [("Donante apto",)],
        )

    def test_informe_con_pendiente_no_esta_completo(self):
        controles = self._controles_hu14()
        controles[-1]["seleccion"] = "PENDIENTE"

        datos = self._informe_hu14(controles)

        self.assertFalse(datos["COMPLETOS"])
        self.assertEqual(
            datos["MUESTRA"]["ESTADO"],
            "Pendiente de análisis",
        )

    def test_informe_invalido_no_guarda_parcialmente(self):
        controles = self._controles_hu14()
        invalidos = (
            controles[:-1],
            controles + [controles[0]],
            controles + [
                {"analisis_id": 999, "seleccion": "NEGATIVO"}
            ],
            controles[:-1] + [
                {"analisis_id": 8, "seleccion": "OTRO"}
            ],
        )
        antes = self._copia_hu14()

        for informe in invalidos:
            with self.subTest(informe=informe):
                with self.assertRaises(ValueError):
                    self._informe_hu14(informe)
                self.assertEqual(self._copia_hu14(), antes)

    def test_repetir_informe_sin_cambios_no_duplica_historial(self):
        controles = self._controles_hu14()
        self._informe_hu14(controles)
        antes = self._copia_hu14()

        self._informe_hu14(controles)

        self.assertEqual(self._copia_hu14(), antes)

    def test_corregir_informe_exige_motivo_y_versiona_solo_cambio(self):
        controles = self._controles_hu14()
        self._informe_hu14(controles)
        controles[0]["seleccion"] = "POSITIVO"
        antes = self._copia_hu14()

        with self.assertRaises(ValueError):
            self._informe_hu14(controles)

        self.assertEqual(self._copia_hu14(), antes)

        datos = self._informe_hu14(
            controles, motivo="Corrección de digitación"
        )
        versiones = {
            fila["ANALISIS_ID"]: fila["VERSION"]
            for fila in datos["RESULTADOS"]
        }

        self.assertEqual(
            versiones,
            {1: 2, 2: 1, 5: 1, 6: 1, 7: 1, 8: 1},
        )
        self.assertEqual(
            datos["MUESTRA"]["ESTADO_LABORATORIO"],
            "Bloqueada",
        )

    def test_fallo_final_revierte_informe_donante_e_historiales(self):
        controles = self._controles_hu14()
        controles[0]["seleccion"] = "POSITIVO"

        self.ejecutar(
            """CREATE TRIGGER fallo_hu14
               BEFORE INSERT ON HISTORIAL_LIBERACION
               BEGIN
                   SELECT RAISE(ABORT, 'Fallo simulado');
               END"""
        )
        antes = self._copia_hu14()

        with self.assertRaises(sqlite3.IntegrityError):
            self._informe_hu14(controles)

        self.assertEqual(self._copia_hu14(), antes)

    def test_positivo_individual_inhabilita_y_deja_trazabilidad(self):
        from servicios.elegibilidad import buscar_candidatos

        self._controles_hu14()
        datos = self.guardar(
            resultado="Positivo",
            clasificacion="No conforme",
        )

        self.assertEqual(
            self._filas_hu14(
                "SELECT ELEGIBLE, INHABILITACION_FIN FROM DONANTES"
            ),
            [("Donante NO apto temporalmente", None)],
        )

        historial = self._filas_hu14(
            "SELECT DONANTE_ID, MUESTRA_ID, RESULTADO_ID, "
            "RESULTADO_VERSION, EMPLEADO_ID, MOTIVO "
            "FROM HISTORIAL_HABILITACION"
        )

        self.assertEqual(len(historial), 1)
        self.assertEqual(
            historial[0][:5],
            (
                1,
                self.muestra_id,
                datos["RESULTADOS"][0]["ID"],
                1,
                1,
            ),
        )
        self.assertIn("VIH_1_2", historial[0][5])

        candidatos = buscar_candidatos(
            "A", "+",
            ruta=self.ruta,
            hoy=self.ahora.date(),
        )
        self.assertEqual(candidatos, [])

    def test_correccion_negativa_no_rehabilita_donante(self):
        self._controles_hu14()
        self.guardar(
            resultado="Positivo",
            clasificacion="No conforme",
        )
        self.guardar(
            resultado="Negativo",
            clasificacion="Conforme",
            motivo_cambio="Corrección revisada",
        )

        self.assertEqual(
            self._filas_hu14("SELECT ELEGIBLE FROM DONANTES"),
            [("Donante NO apto temporalmente",)],
        )

    def test_positivo_conserva_inhabilitacion_permanente(self):
        self._controles_hu14()
        self.ejecutar(
            "UPDATE DONANTES "
            "SET ELEGIBLE='Donante NO apto PERMANENTEMENTE'"
        )
        self.guardar(
            resultado="Positivo",
            clasificacion="No conforme",
        )

        self.assertEqual(
            self._filas_hu14("SELECT ELEGIBLE FROM DONANTES"),
            [("Donante NO apto PERMANENTEMENTE",)],
        )

    def test_positivo_impide_fin_automatico_de_restriccion(self):
        self._controles_hu14()
        self.ejecutar(
            "UPDATE DONANTES "
            "SET ELEGIBLE='Donante NO apto temporalmente', "
            "INHABILITACION_INICIO='2026-11-01', "
            "INHABILITACION_FIN='2026-12-01'"
        )
        self.guardar(
            resultado="Positivo",
            clasificacion="No conforme",
        )

        self.assertEqual(
            self._filas_hu14(
                "SELECT INHABILITACION_INICIO, INHABILITACION_FIN "
                "FROM DONANTES"
            ),
            [("2026-11-01", None)],
        )

    def test_entrevistador_no_guarda_informe_ni_inhabilita(self):
        controles = self._controles_hu14()
        controles[0]["seleccion"] = "POSITIVO"
        antes = self._copia_hu14()

        with self.assertRaises(PermissionError):
            self._informe_hu14(controles, empleado=2)

        self.assertEqual(self._copia_hu14(), antes)

    def test_otra_muestra_negativa_no_rehabilita_donante(self):
        controles = self._controles_hu14()
        self.ejecutar(
            """INSERT INTO DONACIONES (
                   ID, DONANTE, TIPO_SANGRE, FACTOR_RH,
                   FECHA_EXTRACCIÓN, FECHA_VENCIMIENTO,
                   CANTIDAD, ESTADO
               )
               VALUES (
                   2, 1, 'A', '+',
                   '2026-11-20', '2026-12-10',
                   450, 'Disponible'
               )"""
        )
        otra = m.registrar_muestra(
            2, 1, ruta=self.ruta, ahora=self.ahora
        )

        self.guardar(
            resultado="Positivo",
            clasificacion="No conforme",
        )
        r.guardar_informe(
            otra["ID"],
            controles,
            1,
            ruta=self.ruta,
            ahora=self.ahora,
        )

        self.assertEqual(
            self._filas_hu14("SELECT ELEGIBLE FROM DONANTES"),
            [("Donante NO apto temporalmente",)],
        )

if __name__ == "__main__":
    unittest.main()