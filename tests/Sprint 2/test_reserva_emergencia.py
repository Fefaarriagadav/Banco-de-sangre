
import sqlite3
import tempfile
import unittest

from pathlib import Path

from servicios.despachos import registrar_emergencia


class TestReservaEmergencia(unittest.TestCase):

    def setUp(self):
        temporal = tempfile.TemporaryDirectory()
        self.addCleanup(temporal.cleanup)

        self.ruta = str(
            Path(temporal.name) / "pruebas_emergencia.db"
        )

        with sqlite3.connect(self.ruta) as conexion:
            conexion.executescript("""
                PRAGMA foreign_keys = ON;

                CREATE TABLE CENTROS_MEDICOS (
                    NOMBRE TEXT PRIMARY KEY,
                    DIRECCION TEXT,
                    COMUNA TEXT
                );

                INSERT INTO CENTROS_MEDICOS
                VALUES ('Hospital Prueba', 'Calle 123', 'Concepción');

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

    def test_reserva_bolsas_completas(self):
        solicitud = registrar_emergencia(
            "Hospital Prueba", "A", "+",
            900, "Urgencia médica", ruta=self.ruta
        )

        with sqlite3.connect(self.ruta) as conexion:
            reservas = conexion.execute("""
                SELECT COUNT(*), SUM(VOLUMEN_ML)
                FROM RESERVAS_EMERGENCIA
                WHERE SOLICITUD_ID = ?
            """, (solicitud,)).fetchone()

            estado = conexion.execute("""
                SELECT ESTADO
                FROM DESPACHOS_EMERGENCIA
                WHERE ID = ?
            """, (solicitud,)).fetchone()[0]

            self.assertEqual(reservas, (2, 900))
            self.assertEqual(estado, "Pendiente de aprobación")

    def test_no_permite_reservar_dos_veces(self):
        registrar_emergencia(
            "Hospital Prueba", "A", "+",
            900, "Primera emergencia", ruta=self.ruta
        )

        with self.assertRaisesRegex(ValueError, "Stock insuficiente"):
            registrar_emergencia(
                "Hospital Prueba", "A", "+",
                900, "Segunda emergencia", ruta=self.ruta
            )

        with sqlite3.connect(self.ruta) as conexion:
            cantidad = conexion.execute("""
                SELECT COUNT(*)
                FROM DESPACHOS_EMERGENCIA
            """).fetchone()[0]

            self.assertEqual(cantidad, 1)


if __name__ == "__main__":
    unittest.main()
