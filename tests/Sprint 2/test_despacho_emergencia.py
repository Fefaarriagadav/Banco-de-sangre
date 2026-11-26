from contextlib import closing
import unittest
import sqlite3
import tempfile
from pathlib import Path
from servicios.despachos import (registrar_emergencia,crear_tabla_emergencias,crear_tabla_reservas_emergencia)

class TestDespachoEmergencia(unittest.TestCase):
    def setUp(self):
        # Base de datos temporal para las pruebas
        self.temporal = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporal.cleanup)

        self.ruta = str(
            Path(self.temporal.name) / "test_emergencia.db"
        )

        with closing(sqlite3.connect(self.ruta)) as conexion, conexion:

            conexion.executescript("""
                CREATE TABLE CENTROS_MEDICOS (
                    NOMBRE TEXT PRIMARY KEY,
                    DIRECCION TEXT,
                    COMUNA TEXT
                );

                INSERT INTO CENTROS_MEDICOS VALUES (
                    'Hospital Prueba',
                    'Calle 123',
                    'Concepción'
                );

                CREATE TABLE DONANTES (
                    ID INTEGER PRIMARY KEY,
                    GRUPO_SANGUINEO TEXT,
                    FACTOR_RH TEXT
                );

                CREATE TABLE DONACIONES (
                    ID INTEGER PRIMARY KEY,
                    DONANTE INTEGER,
                    TIPO_SANGRE TEXT,
                    FACTOR_RH TEXT,
                    CANTIDAD INTEGER,
                    ESTADO TEXT,
                    FECHA_VENCIMIENTO TEXT
                );

                INSERT INTO DONACIONES VALUES
                (1, NULL, 'A', '+', 200, 'Disponible', '2099-01-01'),
                (2, NULL, 'A', '+', 450, 'Disponible', '2099-01-01'),
                (3, NULL, 'A', '+', 450, 'Disponible', '2099-01-01');
            """)

            # Crear las tablas de emergencia
            crear_tabla_emergencias(conexion)
            crear_tabla_reservas_emergencia(conexion)

    # TEST 1: Registrar emergencia correctamente
    def test_registrar_emergencia(self):

        solicitud_id = registrar_emergencia(
            "Hospital Prueba",
            "A",
            "+",
            900,
            "Paciente requiere transfusión urgente",
            ruta=self.ruta
        )

        with closing(sqlite3.connect(self.ruta)) as conexion, conexion:

            solicitud = conexion.execute("""
                SELECT
                    CENTRO,
                    GRUPO_SANGUINEO,
                    FACTOR_RH,
                    VOLUMEN_ML,
                    MOTIVO,
                    FECHA_SOLICITUD,
                    ESTADO
                FROM DESPACHOS_EMERGENCIA
                WHERE ID = ?
            """, (solicitud_id,)).fetchone()

            reservas = conexion.execute("""
                SELECT COUNT(*), SUM(VOLUMEN_ML)
                FROM RESERVAS_EMERGENCIA
                WHERE SOLICITUD_ID = ?
            """, (solicitud_id,)).fetchone()

        self.assertIsNotNone(solicitud)
        self.assertEqual(solicitud[0], "Hospital Prueba")
        self.assertEqual(solicitud[1], "A")
        self.assertEqual(solicitud[2], "+")
        self.assertEqual(solicitud[3], 900)
        self.assertEqual(
            solicitud[4],
            "Paciente requiere transfusión urgente"
        )
        self.assertTrue(solicitud[5])
        self.assertEqual(
            solicitud[6],
            "Pendiente de aprobación"
        )

        self.assertEqual(reservas, (2, 900))

    # TEST 2: No permitir solicitar más del stock
    def test_stock_insuficiente(self):

        with self.assertRaisesRegex(
            ValueError, "Stock insuficiente"
        ):

            registrar_emergencia(
                "Hospital Prueba",
                "A",
                "+",
                2000,
                "Emergencia médica",
                ruta=self.ruta
            )

        with closing(sqlite3.connect(self.ruta)) as conexion, conexion:

            solicitudes = conexion.execute("""
                SELECT COUNT(*)
                FROM DESPACHOS_EMERGENCIA
            """).fetchone()[0]

            reservas = conexion.execute("""
                SELECT COUNT(*)
                FROM RESERVAS_EMERGENCIA
            """).fetchone()[0]

        self.assertEqual(solicitudes, 0)
        self.assertEqual(reservas, 0)

    # TEST 3: No permitir motivo vacío
    def test_motivo_obligatorio(self):

        with self.assertRaises(ValueError):

            registrar_emergencia(
                "Hospital Prueba",
                "A",
                "+",
                450,
                "",
                ruta=self.ruta
            )

        with closing(sqlite3.connect(self.ruta)) as conexion, conexion:

            solicitudes = conexion.execute("""
                SELECT COUNT(*)
                FROM DESPACHOS_EMERGENCIA
            """).fetchone()[0]

        self.assertEqual(solicitudes, 0)


if __name__ == "__main__":
    unittest.main()
