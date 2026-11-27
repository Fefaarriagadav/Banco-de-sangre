from contextlib import closing
import unittest
import sqlite3
import tempfile
from pathlib import Path
from servicios.despachos import (aprobar_solicitud,rechazar_solicitud)

class TestAprobacionDespachos(unittest.TestCase):
    def setUp(self):

        # Crear una base de datos temporal
        self.temporal = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporal.cleanup)

        self.ruta = str(
            Path(self.temporal.name) / "test_aprobacion.db"
        )

        with closing(sqlite3.connect(self.ruta)) as conexion, conexion:

            conexion.executescript("""
                PRAGMA foreign_keys = ON;

                CREATE TABLE PERSONAL (
                    ID_EMPLEADO INTEGER PRIMARY KEY,
                    NOMBRE TEXT,
                    ROL TEXT
                );

                INSERT INTO PERSONAL VALUES
                (100001, 'Enfermero Prueba', 'Enfermero'),
                (100002, 'Entrevistador Prueba', 'Entrevistador');

                CREATE TABLE CENTROS_MEDICOS (
                    NOMBRE TEXT PRIMARY KEY,
                    DIRECCION TEXT,
                    COMUNA TEXT
                );

                INSERT INTO CENTROS_MEDICOS VALUES
                ('Hospital Prueba', 'Calle 123', 'Concepción');

                CREATE TABLE DONACIONES (
                    ID INTEGER PRIMARY KEY,
                    CANTIDAD INTEGER,
                    ESTADO TEXT,
                    FECHA_VENCIMIENTO TEXT
                );

                INSERT INTO DONACIONES VALUES
                (1, 450, 'Reservada', '2099-01-01');

                CREATE TABLE DESPACHOS_EMERGENCIA (
                    ID INTEGER PRIMARY KEY,
                    CENTRO TEXT,
                    GRUPO_SANGUINEO TEXT,
                    FACTOR_RH TEXT,
                    VOLUMEN_ML INTEGER,
                    MOTIVO TEXT,
                    FECHA_SOLICITUD TEXT,
                    ESTADO TEXT
                );

                INSERT INTO DESPACHOS_EMERGENCIA VALUES
                (
                    1,
                    'Hospital Prueba',
                    'A',
                    '+',
                    450,
                    'Emergencia médica',
                    '2026-11-21T12:00:00-03:00',
                    'Pendiente de aprobación'
                );

                CREATE TABLE RESERVAS_EMERGENCIA (
                    ID INTEGER PRIMARY KEY,
                    SOLICITUD_ID INTEGER,
                    DONACION_ID INTEGER UNIQUE,
                    VOLUMEN_ML INTEGER
                );

                INSERT INTO RESERVAS_EMERGENCIA VALUES
                (1, 1, 1, 450);

                CREATE TABLE DESPACHOS_PROGRAMADOS (
                    ID INTEGER PRIMARY KEY,
                    CENTRO TEXT,
                    GRUPO_SANGUINEO TEXT,
                    FACTOR_RH TEXT,
                    CANTIDAD INTEGER,
                    VOLUMEN_ML INTEGER,
                    FECHA_DESPACHO TEXT,
                    HORA_DESPACHO TEXT,
                    DESTINO TEXT,
                    ESTADO TEXT
                );
            """)
            # Reserva ficticia inicialmente aprobada por laboratorio.
            conexion.execute(
                """
                ALTER TABLE DONACIONES
                ADD COLUMN ESTADO_LABORATORIO TEXT NOT NULL
                DEFAULT 'Liberada'
                """
            )

    # TEST 1: Aprobar una emergencia
    def test_aprobar_emergencia(self):

        aprobar_solicitud(
            "Emergencia",
            1,
            100001,
            ruta=self.ruta
        )

        with closing(sqlite3.connect(self.ruta)) as conexion, conexion:

            estado = conexion.execute("""
                SELECT ESTADO
                FROM DESPACHOS_EMERGENCIA
                WHERE ID = 1
            """).fetchone()[0]

            bolsa = conexion.execute("""
                SELECT ESTADO
                FROM DONACIONES
                WHERE ID = 1
            """).fetchone()[0]

        self.assertEqual(estado, "Aprobada")
        self.assertEqual(bolsa, "Reservada")

    # TEST 2: Rechazar y liberar el stock
    def test_rechazar_emergencia(self):

        rechazar_solicitud(
            "Emergencia",
            1,
            100001,
            "Solicitud cancelada",
            ruta=self.ruta
        )

        with closing(sqlite3.connect(self.ruta)) as conexion, conexion:

            estado = conexion.execute("""
                SELECT ESTADO, MOTIVO_RECHAZO
                FROM DESPACHOS_EMERGENCIA
                WHERE ID = 1
            """).fetchone()

            bolsa = conexion.execute("""
                SELECT ESTADO
                FROM DONACIONES
                WHERE ID = 1
            """).fetchone()[0]

            reservas = conexion.execute("""
                SELECT COUNT(*)
                FROM RESERVAS_EMERGENCIA
                WHERE SOLICITUD_ID = 1
            """).fetchone()[0]

        self.assertEqual(estado[0], "Rechazada")
        self.assertEqual(estado[1], "Solicitud cancelada")
        self.assertEqual(bolsa, "Disponible")
        self.assertEqual(reservas, 0)

    # TEST 3: El entrevistador no puede aprobar
    def test_entrevistador_no_puede_aprobar(self):

        with self.assertRaises(PermissionError):

            aprobar_solicitud(
                "Emergencia",
                1,
                100002,
                ruta=self.ruta
            )

        # Verificar que la solicitud siga pendiente
        with closing(sqlite3.connect(self.ruta)) as conexion, conexion:

            estado = conexion.execute("""
                SELECT ESTADO
                FROM DESPACHOS_EMERGENCIA
                WHERE ID = 1
            """).fetchone()[0]

        self.assertEqual(
            estado,
            "Pendiente de aprobación"
        )

    def test_no_aprueba_reserva_sin_liberacion_laboratorio(self):
        for laboratorio in (
            "Pendiente de análisis",
            "Bloqueada",
        ):
            with self.subTest(laboratorio=laboratorio):
                with closing(
                    sqlite3.connect(self.ruta)
                ) as conexion, conexion:
                    conexion.execute(
                        """
                        UPDATE DONACIONES
                        SET ESTADO_LABORATORIO = ?
                        WHERE ID = 1
                        """,
                        (laboratorio,),
                    )
                    estado_anterior = conexion.execute(
                        """
                        SELECT ESTADO
                        FROM DESPACHOS_EMERGENCIA
                        WHERE ID = 1
                        """
                    ).fetchone()[0]

                with self.assertRaisesRegex(
                    ValueError, "liberación de laboratorio"
                ):
                    aprobar_solicitud(
                        "Emergencia",
                        1,
                        100001,
                        ruta=self.ruta,
                    )

                with closing(
                    sqlite3.connect(self.ruta)
                ) as conexion:
                    estado_actual = conexion.execute(
                        """
                        SELECT ESTADO
                        FROM DESPACHOS_EMERGENCIA
                        WHERE ID = 1
                        """
                    ).fetchone()[0]

                self.assertEqual(
                    estado_actual,
                    estado_anterior,
                )

    def test_rechazo_no_reactiva_unidad_pendiente_laboratorio(self):
        with closing(
            sqlite3.connect(self.ruta)
        ) as conexion, conexion:
            conexion.execute(
                """
                UPDATE DONACIONES
                SET ESTADO_LABORATORIO = 'Pendiente de análisis'
                WHERE ID = 1
                """
            )

        rechazar_solicitud(
            "Emergencia",
            1,
            100001,
            "Cancelación ficticia",
            ruta=self.ruta,
        )

        with closing(sqlite3.connect(self.ruta)) as conexion:
            unidad = conexion.execute(
                """
                SELECT ESTADO, ESTADO_LABORATORIO
                FROM DONACIONES
                WHERE ID = 1
                """
            ).fetchone()

            reservas = conexion.execute(
                """
                SELECT COUNT(*)
                FROM RESERVAS_EMERGENCIA
                WHERE SOLICITUD_ID = 1
                """
            ).fetchone()[0]

        self.assertEqual(
            unidad,
            ("Pendiente de análisis", "Pendiente de análisis"),
        )
        self.assertEqual(reservas, 0)

    def test_rechazo_no_reactiva_unidad_bloqueada_laboratorio(self):
        with closing(
            sqlite3.connect(self.ruta)
        ) as conexion, conexion:
            conexion.execute(
                """
                UPDATE DONACIONES
                SET ESTADO_LABORATORIO = 'Bloqueada'
                WHERE ID = 1
                """
            )

        rechazar_solicitud(
            "Emergencia",
            1,
            100001,
            "Cancelación ficticia",
            ruta=self.ruta,
        )

        with closing(sqlite3.connect(self.ruta)) as conexion:
            unidad = conexion.execute(
                """
                SELECT ESTADO, ESTADO_LABORATORIO
                FROM DONACIONES
                WHERE ID = 1
                """
            ).fetchone()

        self.assertEqual(
            unidad,
            ("Bloqueada", "Bloqueada"),
        )

if __name__ == "__main__":
    unittest.main()
