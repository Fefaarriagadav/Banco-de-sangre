import sqlite3
import tempfile
import unittest
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from datos.basededatos import inicializar_base
from servicios import liberacion as l
from servicios import muestras as m
from servicios import resultados_analisis as r
from servicios import vencimientos as v


class LiberacionTest(unittest.TestCase):
    def setUp(self):
        temporal = tempfile.TemporaryDirectory()
        self.addCleanup(temporal.cleanup)

        self.ruta = Path(temporal.name) / "liberacion_prueba.db"
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
                    (1, "DEMO-1", "Enfermero prueba", "Enfermero"),
                    (2, "DEMO-2", "Entrevistador", "Entrevistador"),
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

            conexion.executemany(
                """
                INSERT INTO DONACIONES (
                    ID, DONANTE, TIPO_SANGRE, FACTOR_RH,
                    FECHA_EXTRACCIÓN, FECHA_VENCIMIENTO,
                    CANTIDAD, ESTADO
                )
                VALUES (
                    ?, 1, 'A', '+',
                    '2026-11-20', '2026-12-10',
                    450, 'Disponible'
                )
                """,
                [(1,), (2,)],
            )

            conexion.executemany(
                """
                INSERT INTO CATALOGO_ANALISIS (
                    ID, CODIGO, NOMBRE, OBLIGATORIO, ACTIVO
                )
                VALUES (?, ?, ?, ?, 1)
                """,
                [
                    (1, "DEMO_1", "Control ficticio uno", 1),
                    (2, "DEMO_2", "Control ficticio dos", 1),
                    (3, "DEMO_OPC", "Control ficticio opcional", 0),
                ],
            )

        self.muestra_id = m.registrar_muestra(
            1, 1, ruta=self.ruta, ahora=self.ahora
        )["ID"]

    def ejecutar(self, sql, parametros=()):
        with closing(sqlite3.connect(self.ruta)) as conexion, conexion:
            conexion.execute(sql, parametros)

    def guardar(
        self,
        analisis_id,
        clasificacion=r.CONFORME,
        muestra_id=None,
    ):
        return r.guardar_resultado(
            muestra_id=(
                self.muestra_id
                if muestra_id is None
                else muestra_id
            ),
            analisis_id=analisis_id,
            resultado="Informe ficticio",
            clasificacion=clasificacion,
            empleado_id=1,
            ruta=self.ruta,
            ahora=self.ahora,
        )

    def completar(self, muestra_id=None):
        self.guardar(1, muestra_id=muestra_id)
        self.guardar(2, muestra_id=muestra_id)

    def consultar(self, donacion_id=1):
        return l.consultar_liberacion(
            donacion_id,
            1,
            ruta=self.ruta,
            ahora=self.ahora,
        )

    def evaluar(self, muestra_id=None):
        return l.evaluar_unidad(
            1,
            1,
            ruta=self.ruta,
            ahora=self.ahora,
            muestra_id=(
                self.muestra_id
                if muestra_id is None
                else muestra_id
            ),
        )

    def autorizar(self, empleado_id=1, motivo="Revisión autorizada"):
        return l.autorizar_liberacion(
            1,
            empleado_id,
            motivo,
            ruta=self.ruta,
            ahora=self.ahora,
        )

    def test_estado_inicial_no_permite_liberacion(self):
        datos = self.consultar()

        self.assertEqual(
            datos["UNIDAD"]["ESTADO_LABORATORIO"],
            l.PENDIENTE_LABORATORIO,
        )
        self.assertFalse(datos["COMPLETOS"])
        self.assertFalse(datos["PUEDE_LIBERARSE"])

        with self.assertRaises(ValueError):
            self.autorizar()

    def test_donacion_sin_muestras_no_puede_liberarse(self):
        datos = self.consultar(donacion_id=2)

        self.assertEqual(datos["MUESTRAS"], [])
        self.assertFalse(datos["PUEDE_LIBERARSE"])

        with self.assertRaises(ValueError):
            l.autorizar_liberacion(
                2,
                1,
                "Intento sin muestras",
                ruta=self.ruta,
                ahora=self.ahora,
            )

    def test_catalogo_sin_obligatorios_impide_liberacion(self):
        self.ejecutar(
            "UPDATE CATALOGO_ANALISIS SET OBLIGATORIO = 0"
        )

        self.assertFalse(self.consultar()["PUEDE_LIBERARSE"])

        with self.assertRaises(ValueError):
            self.autorizar()

    def test_resultados_parciales_impiden_liberacion(self):
        self.guardar(1)

        datos = self.consultar()

        self.assertFalse(datos["COMPLETOS"])
        self.assertTrue(datos["FALTANTES"])

        with self.assertRaises(ValueError):
            self.autorizar()

    def test_completar_no_libera_automaticamente(self):
        self.completar()
        datos = self.evaluar()

        self.assertTrue(datos["PUEDE_LIBERARSE"])
        self.assertEqual(
            datos["UNIDAD"]["ESTADO_LABORATORIO"],
            l.PENDIENTE_LABORATORIO,
        )
        self.assertEqual(
            datos["UNIDAD"]["ESTADO"],
            "Pendiente de análisis",
        )

    def test_autorizacion_expresa_libera_unidad(self):
        self.completar()

        datos = self.autorizar()

        self.assertEqual(
            datos["UNIDAD"]["ESTADO_LABORATORIO"],
            l.LIBERADA,
        )
        self.assertEqual(
            datos["UNIDAD"]["ESTADO"],
            "Disponible",
        )

    def test_no_conforme_bloquea_al_evaluar(self):
        self.guardar(1)
        self.guardar(2, clasificacion=r.NO_CONFORME)

        datos = self.evaluar()

        self.assertEqual(
            datos["UNIDAD"]["ESTADO_LABORATORIO"],
            l.BLOQUEADA,
        )
        self.assertEqual(
            datos["UNIDAD"]["ESTADO"],
            "Bloqueada",
        )
        self.assertFalse(datos["PUEDE_LIBERARSE"])

        with self.assertRaises(ValueError):
            self.autorizar()

    def test_no_conforme_opcional_tambien_impide_liberar(self):
        self.completar()
        self.guardar(3, clasificacion=r.NO_CONFORME)

        datos = self.evaluar()

        self.assertTrue(datos["COMPLETOS"])
        self.assertTrue(datos["NO_CONFORMES"])
        self.assertEqual(
            datos["UNIDAD"]["ESTADO_LABORATORIO"],
            l.BLOQUEADA,
        )

    def test_todas_las_muestras_deben_estar_completas(self):
        self.completar()

        segunda = m.registrar_muestra(
            1, 1, ruta=self.ruta, ahora=self.ahora
        )["ID"]

        with self.assertRaises(ValueError):
            self.autorizar()

        self.completar(muestra_id=segunda)

        datos = self.autorizar()
        self.assertEqual(
            datos["UNIDAD"]["ESTADO_LABORATORIO"],
            l.LIBERADA,
        )

    def test_no_conforme_en_otra_muestra_bloquea_unidad(self):
        self.completar()

        segunda = m.registrar_muestra(
            1, 1, ruta=self.ruta, ahora=self.ahora
        )["ID"]

        self.guardar(
            1,
            clasificacion=r.NO_CONFORME,
            muestra_id=segunda,
        )

        datos = self.evaluar(muestra_id=segunda)

        self.assertEqual(
            datos["UNIDAD"]["ESTADO_LABORATORIO"],
            l.BLOQUEADA,
        )
        self.assertFalse(datos["PUEDE_LIBERARSE"])

    def test_vencimiento_impide_liberar(self):
        self.completar()

        self.ejecutar(
            """
            UPDATE DONACIONES
            SET FECHA_VENCIMIENTO = '2026-11-25'
            WHERE ID = 1
            """
        )

        with self.assertRaises(ValueError):
            self.autorizar()

        datos = self.evaluar()

        self.assertEqual(
            datos["UNIDAD"]["ESTADO"],
            "Vencida",
        )
        self.assertFalse(datos["PUEDE_LIBERARSE"])

    def test_estados_de_inventario_protegidos(self):
        self.completar()

        for estado in ("Usada", "Descartada", "Vencida", "Reservada"):
            with self.subTest(estado=estado):
                self.ejecutar(
                    "UPDATE DONACIONES SET ESTADO = ? WHERE ID = 1",
                    (estado,),
                )

                with self.assertRaises(ValueError):
                    self.autorizar()

                datos = self.evaluar()

                self.assertEqual(
                    datos["UNIDAD"]["ESTADO"],
                    estado,
                )

    def test_operaciones_requieren_enfermero(self):
        self.completar()

        for empleado in (2, 999, None):
            with self.subTest(empleado=empleado):
                with self.assertRaises(PermissionError):
                    self.autorizar(empleado_id=empleado)

                with self.assertRaises(PermissionError):
                    l.evaluar_unidad(
                        1,
                        empleado,
                        ruta=self.ruta,
                        ahora=self.ahora,
                    )

                with self.assertRaises(PermissionError):
                    l.consultar_liberacion(
                        1,
                        empleado,
                        ruta=self.ruta,
                        ahora=self.ahora,
                    )

    def test_motivo_es_obligatorio(self):
        self.completar()

        for motivo in (None, "", " ", "x" * 1001):
            with self.subTest(motivo=motivo):
                with self.assertRaises(ValueError):
                    self.autorizar(motivo=motivo)

        self.assertEqual(
            self.consultar()["UNIDAD"]["ESTADO_LABORATORIO"],
            l.PENDIENTE_LABORATORIO,
        )

    def test_historial_identifica_muestra_y_versiones(self):
        self.completar()
        cantidad_anterior = len(self.consultar()["HISTORIAL"])
        self.evaluar()
        self.autorizar(motivo="Informe revisado por enfermería")

        historial = self.consultar()["HISTORIAL"]

        self.assertEqual(len(historial), cantidad_anterior + 2)
        decision = historial[-1]

        self.assertEqual(decision["DONACION_ID"], 1)
        self.assertEqual(decision["MUESTRA_ID"], self.muestra_id)
        self.assertEqual(decision["RESPONSABLE_ID"], 1)
        self.assertEqual(
            decision["ESTADO_LAB_NUEVO"],
            l.LIBERADA,
        )
        self.assertEqual(
            datetime.fromisoformat(decision["FECHA"]),
            self.ahora,
        )
        self.assertIn(
            "Informe revisado por enfermería",
            decision["MOTIVO"],
        )
        self.assertIn("Versiones de resultados", decision["MOTIVO"])

    def test_fallo_historial_revierte_autorizacion(self):
        self.completar()
        historial_anterior = self.consultar()["HISTORIAL"]

        self.ejecutar(
            """
            CREATE TRIGGER SIMULAR_FALLO_LIBERACION
            BEFORE INSERT ON HISTORIAL_LIBERACION
            BEGIN
                SELECT RAISE(ABORT, 'Fallo simulado');
            END;
            """
        )

        with self.assertRaises(sqlite3.IntegrityError):
            self.autorizar()

        datos = self.consultar()

        self.assertEqual(
            datos["UNIDAD"]["ESTADO_LABORATORIO"],
            l.PENDIENTE_LABORATORIO,
        )
        self.assertEqual(
            datos["UNIDAD"]["ESTADO"],
            "Pendiente de análisis",
        )
        self.assertEqual(
            datos["HISTORIAL"],
            historial_anterior,
        )

    def test_reevaluacion_revoca_autorizacion_anterior(self):
        self.completar()
        self.autorizar()

        segunda = m.registrar_muestra(
            1, 1, ruta=self.ruta, ahora=self.ahora
        )["ID"]

        datos = self.evaluar(muestra_id=segunda)

        self.assertEqual(
            datos["UNIDAD"]["ESTADO_LABORATORIO"],
            l.PENDIENTE_LABORATORIO,
        )
        self.assertEqual(
            datos["UNIDAD"]["ESTADO"],
            "Pendiente de análisis",
        )
        self.assertFalse(datos["PUEDE_LIBERARSE"])

    def test_migracion_repetida_conserva_autorizacion(self):
        self.completar()
        self.autorizar()
        historial_anterior = self.consultar()["HISTORIAL"]

        inicializar_base(self.ruta)
        inicializar_base(self.ruta)

        datos = self.consultar()

        self.assertEqual(
            datos["UNIDAD"]["ESTADO_LABORATORIO"],
            l.LIBERADA,
        )
        self.assertEqual(
            datos["HISTORIAL"],
            historial_anterior,
        )

    def test_guardar_no_conforme_bloquea_sin_evaluacion_manual(self):
        self.guardar(1, clasificacion=r.NO_CONFORME)

        datos = self.consultar()

        self.assertEqual(
            datos["UNIDAD"]["ESTADO_LABORATORIO"],
            l.BLOQUEADA,
        )
        self.assertEqual(
            datos["UNIDAD"]["ESTADO"],
            "Bloqueada",
        )

    def test_nueva_muestra_revoca_liberacion_automaticamente(self):
        self.completar()
        self.autorizar()

        m.registrar_muestra(
            1, 1, ruta=self.ruta, ahora=self.ahora
        )

        datos = self.consultar()

        self.assertEqual(
            datos["UNIDAD"]["ESTADO_LABORATORIO"],
            l.PENDIENTE_LABORATORIO,
        )
        self.assertEqual(
            datos["UNIDAD"]["ESTADO"],
            "Pendiente de análisis",
        )
        self.assertFalse(datos["PUEDE_LIBERARSE"])

    def test_corregir_no_conforme_no_libera_automaticamente(self):
        self.guardar(1)
        self.guardar(2, clasificacion=r.NO_CONFORME)

        r.guardar_resultado(
            muestra_id=self.muestra_id,
            analisis_id=2,
            resultado="Informe ficticio corregido",
            clasificacion=r.CONFORME,
            empleado_id=1,
            motivo_cambio="Corrección del informe de laboratorio",
            ruta=self.ruta,
            ahora=self.ahora,
        )

        datos = self.consultar()

        self.assertFalse(datos["NO_CONFORMES"])
        self.assertTrue(datos["PUEDE_LIBERARSE"])
        self.assertEqual(
            datos["UNIDAD"]["ESTADO_LABORATORIO"],
            l.PENDIENTE_LABORATORIO,
        )
        self.assertEqual(
            datos["UNIDAD"]["ESTADO"],
            "Pendiente de análisis",
        )

        self.autorizar()

        self.assertEqual(
            self.consultar()["UNIDAD"]["ESTADO_LABORATORIO"],
            l.LIBERADA,
        )

    def test_stock_excluye_unidad_sin_muestras_ni_autorizacion(self):
        # La donación 2 está Disponible, pero no tiene muestras
        # ni autorización de laboratorio.
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

    def test_stock_incluye_solo_unidad_autorizada_y_vigente(self):
        self.completar()
        self.autorizar()

        resumen = v.consultar_resumen(
            ruta=self.ruta,
            ahora=self.ahora,
        )
        detalle = v.consultar_stock_detallado(
            ruta=self.ruta,
            ahora=self.ahora,
        )

        self.assertEqual(resumen["unidades"], 1)
        self.assertAlmostEqual(resumen["litros"], 0.45)
        self.assertEqual(
            [unidad["ID"] for unidad in detalle["unidades"]],
            [1],
        )

        # Una autorización previa no impide la caducidad.
        despues = datetime(
            2026, 12, 11, 15, 0, tzinfo=timezone.utc
        )

        resumen = v.consultar_resumen(
            ruta=self.ruta,
            ahora=despues,
        )
        self.assertEqual(resumen["unidades"], 0)

    def test_nueva_muestra_retira_unidad_liberada_del_stock(self):
        self.completar()
        self.autorizar()

        antes = v.consultar_resumen(
            ruta=self.ruta,
            ahora=self.ahora,
        )
        self.assertEqual(antes["unidades"], 1)

        m.registrar_muestra(
            1, 1, ruta=self.ruta, ahora=self.ahora
        )

        despues = v.consultar_resumen(
            ruta=self.ruta,
            ahora=self.ahora,
        )
        detalle = v.consultar_stock_detallado(
            ruta=self.ruta,
            ahora=self.ahora,
        )

        self.assertEqual(despues["unidades"], 0)
        self.assertEqual(detalle["unidades"], [])

if __name__ == "__main__":
    unittest.main()