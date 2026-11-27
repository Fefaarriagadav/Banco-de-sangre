import sqlite3
import tempfile
import unittest
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from datos.basededatos import inicializar_base
from servicios import muestras as m
from servicios import vencimientos as v


class MuestrasTest(unittest.TestCase):
    def setUp(self):
        temporal = tempfile.TemporaryDirectory()
        self.addCleanup(temporal.cleanup)

        self.ruta = Path(temporal.name) / "muestras_prueba.db"
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
                    (2, "DEMO-2", "Entrevistador prueba", "Entrevistador"),
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
                    CANTIDAD, UBICACION, ESTADO
                )
                VALUES (
                    1, 1, 'A', '+',
                    '2026-11-20', '2026-12-10',
                    450, 'Refrigerador prueba', 'Disponible'
                )
                """
            )

    def registrar(self, donacion_id=1, empleado_id=1):
        return m.registrar_muestra(
            donacion_id,
            empleado_id,
            ruta=self.ruta,
            ahora=self.ahora,
        )

    def modificar_unidad(self, estado=None, vencimiento=None):
        with closing(sqlite3.connect(self.ruta)) as conexion, conexion:
            if estado is not None:
                conexion.execute(
                    "UPDATE DONACIONES SET ESTADO = ? WHERE ID = 1",
                    (estado,),
                )

            if vencimiento is not None:
                conexion.execute(
                    """
                    UPDATE DONACIONES
                    SET FECHA_VENCIMIENTO = ?
                    WHERE ID = 1
                    """,
                    (vencimiento,),
                )

    def estado_unidad(self):
        with closing(sqlite3.connect(self.ruta)) as conexion:
            return conexion.execute(
                "SELECT ESTADO FROM DONACIONES WHERE ID = 1"
            ).fetchone()[0]

    def contar(self, tabla):
        # Solo admite las tablas fijas utilizadas por estas pruebas.
        if tabla not in ("MUESTRAS", "HISTORIAL_MUESTRAS"):
            raise ValueError("Tabla no admitida.")

        with closing(sqlite3.connect(self.ruta)) as conexion:
            return conexion.execute(
                f"SELECT COUNT(*) FROM {tabla}"
            ).fetchone()[0]

    def test_registro_asocia_muestra_y_deja_unidad_pendiente(self):
        muestra = self.registrar()

        self.assertGreater(muestra["ID"], 0)
        self.assertEqual(muestra["DONACION_ID"], 1)
        self.assertEqual(muestra["ESTADO"], m.PENDIENTE_ANALISIS)
        self.assertEqual(muestra["REGISTRADA_POR"], 1)
        self.assertEqual(
            muestra["ESTADO_UNIDAD"],
            m.PENDIENTE_ANALISIS,
        )
        self.assertEqual(
            self.estado_unidad(),
            m.PENDIENTE_ANALISIS,
        )

        fecha = datetime.fromisoformat(muestra["FECHA_REGISTRO"])
        self.assertEqual(fecha, self.ahora)
        self.assertIsNotNone(fecha.utcoffset())

    def test_varias_muestras_tienen_identificadores_distintos(self):
        primera = self.registrar()
        segunda = self.registrar()

        self.assertNotEqual(primera["ID"], segunda["ID"])
        self.assertEqual(primera["DONACION_ID"], segunda["DONACION_ID"])
        self.assertEqual(self.contar("MUESTRAS"), 2)
        self.assertEqual(self.contar("HISTORIAL_MUESTRAS"), 2)
        self.assertEqual(
            self.estado_unidad(),
            m.PENDIENTE_ANALISIS,
        )

    def test_consulta_por_muestra_y_por_donacion(self):
        primera = self.registrar()
        segunda = self.registrar()

        consultada = m.consultar_muestra(
            primera["ID"], 1, ruta=self.ruta
        )
        self.assertEqual(consultada["ID"], primera["ID"])
        self.assertEqual(
            consultada["RESPONSABLE"],
            "Enfermero prueba",
        )
        self.assertEqual(consultada["TIPO_SANGRE"], "A")
        self.assertEqual(consultada["FACTOR_RH"], "+")

        muestras = m.consultar_muestras_donacion(
            1, 1, ruta=self.ruta
        )
        self.assertEqual(
            {fila["ID"] for fila in muestras},
            {primera["ID"], segunda["ID"]},
        )

    def test_donacion_sin_muestras_devuelve_lista_vacia(self):
        self.assertEqual(
            m.consultar_muestras_donacion(1, 1, ruta=self.ruta),
            [],
        )

    def test_donacion_inexistente_no_crea_registros(self):
        with self.assertRaises(ValueError):
            self.registrar(donacion_id=999)

        self.assertEqual(self.contar("MUESTRAS"), 0)
        self.assertEqual(self.contar("HISTORIAL_MUESTRAS"), 0)
        self.assertEqual(self.estado_unidad(), v.DISPONIBLE)

    def test_identificadores_invalidos_se_rechazan(self):
        for identificador in (None, "", "abc", 0, -1, True, 1.5):
            with self.subTest(identificador=identificador):
                with self.assertRaises(ValueError):
                    self.registrar(donacion_id=identificador)

        self.assertEqual(self.contar("MUESTRAS"), 0)
        self.assertEqual(self.estado_unidad(), v.DISPONIBLE)

    def test_registro_sin_permiso_no_modifica_datos(self):
        for empleado in (2, 999, None, "abc"):
            with self.subTest(empleado=empleado):
                with self.assertRaises(PermissionError):
                    self.registrar(empleado_id=empleado)

        self.assertEqual(self.contar("MUESTRAS"), 0)
        self.assertEqual(self.contar("HISTORIAL_MUESTRAS"), 0)
        self.assertEqual(self.estado_unidad(), v.DISPONIBLE)

    def test_consultas_requieren_enfermero_autorizado(self):
        muestra = self.registrar()

        for empleado in (2, 999, None):
            with self.subTest(empleado=empleado):
                with self.assertRaises(PermissionError):
                    m.consultar_muestra(
                        muestra["ID"], empleado, ruta=self.ruta
                    )

                with self.assertRaises(PermissionError):
                    m.consultar_muestras_donacion(
                        1, empleado, ruta=self.ruta
                    )

    def test_consultas_de_registros_inexistentes(self):
        with self.assertRaises(ValueError):
            m.consultar_muestra(999, 1, ruta=self.ruta)

        with self.assertRaises(ValueError):
            m.consultar_muestras_donacion(999, 1, ruta=self.ruta)

    def test_estados_no_admitidos_no_se_reactivan(self):
        for estado in (
            v.USADA,
            v.DESCARTADA,
            v.VENCIDA,
            "Reservada",
            "Bloqueada",
            v.PENDIENTE,
        ):
            with self.subTest(estado=estado):
                self.modificar_unidad(estado=estado)

                with self.assertRaises(ValueError):
                    self.registrar()

                self.assertEqual(self.estado_unidad(), estado)
                self.assertEqual(self.contar("MUESTRAS"), 0)

    def test_unidad_caducada_no_admite_muestras(self):
        self.modificar_unidad(vencimiento="2026-11-25")

        with self.assertRaises(ValueError):
            self.registrar()

        self.assertEqual(self.contar("MUESTRAS"), 0)
        self.assertEqual(self.contar("HISTORIAL_MUESTRAS"), 0)

    def test_fecha_de_vencimiento_actual_aun_admite_muestra(self):
        self.modificar_unidad(vencimiento="2026-11-26")

        muestra = self.registrar()

        self.assertEqual(muestra["ESTADO"], m.PENDIENTE_ANALISIS)

    def test_historial_conserva_responsable_fecha_y_vinculo(self):
        muestra = self.registrar()

        with closing(sqlite3.connect(self.ruta)) as conexion:
            historial = conexion.execute(
                """
                SELECT
                    MUESTRA_ID, ACCION, ESTADO_ANTERIOR,
                    ESTADO_NUEVO, RESPONSABLE_ID, FECHA, MOTIVO
                FROM HISTORIAL_MUESTRAS
                """
            ).fetchone()

        self.assertEqual(historial[0], muestra["ID"])
        self.assertEqual(historial[1], "Registro de muestra")
        self.assertIsNone(historial[2])
        self.assertEqual(historial[3], m.PENDIENTE_ANALISIS)
        self.assertEqual(historial[4], 1)
        self.assertEqual(
            datetime.fromisoformat(historial[5]),
            self.ahora,
        )
        self.assertIn("Disponible", historial[6])

    def test_fallo_de_historial_revierte_toda_la_operacion(self):
        with closing(sqlite3.connect(self.ruta)) as conexion, conexion:
            conexion.execute(
                """
                CREATE TRIGGER SIMULAR_FALLO_HISTORIAL
                BEFORE INSERT ON HISTORIAL_MUESTRAS
                BEGIN
                    SELECT RAISE(ABORT, 'Fallo de prueba');
                END;
                """
            )

        with self.assertRaises(sqlite3.IntegrityError):
            self.registrar()

        self.assertEqual(self.contar("MUESTRAS"), 0)
        self.assertEqual(self.contar("HISTORIAL_MUESTRAS"), 0)
        self.assertEqual(self.estado_unidad(), v.DISPONIBLE)

    def test_muestra_pendiente_excluye_unidad_del_stock(self):
        self.registrar()

        resumen = v.consultar_resumen(
            ruta=self.ruta,
            ahora=self.ahora,
        )
        detalle = v.consultar_stock_detallado(
            ruta=self.ruta,
            ahora=self.ahora,
        )

        self.assertEqual(resumen["unidades"], 0)
        self.assertEqual(resumen["litros"], 0)
        self.assertEqual(resumen["proximas"], [])
        self.assertEqual(detalle["unidades"], [])
        self.assertEqual(
            self.estado_unidad(),
            m.PENDIENTE_ANALISIS,
        )

    def test_migracion_repetida_conserva_muestra_e_historial(self):
        muestra = self.registrar()

        inicializar_base(self.ruta)
        inicializar_base(self.ruta)

        self.assertEqual(self.contar("MUESTRAS"), 1)
        self.assertEqual(self.contar("HISTORIAL_MUESTRAS"), 1)

        consultada = m.consultar_muestra(
            muestra["ID"], 1, ruta=self.ruta
        )
        self.assertEqual(consultada["DONACION_ID"], 1)
        self.assertEqual(consultada["ESTADO"], m.PENDIENTE_ANALISIS)


if __name__ == "__main__":
    unittest.main()