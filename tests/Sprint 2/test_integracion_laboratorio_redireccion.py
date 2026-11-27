import sqlite3
import tempfile
import unittest
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from datos.basededatos import inicializar_base
from servicios.despachos import crear_tabla_reservas_emergencia
from servicios.redireccion_emergencias import (
    evaluar_deficit_y_seleccionar_centro,
    ejecutar_redireccion_emergencia,
)


class LaboratorioRedireccionTest(unittest.TestCase):
    def setUp(self):
        temporal = tempfile.TemporaryDirectory()
        self.addCleanup(temporal.cleanup)

        self.ruta = Path(temporal.name) / "redireccion_prueba.db"
        inicializar_base(self.ruta)

        self.ahora = datetime(
            2026, 11, 26, 15, 0, tzinfo=timezone.utc
        )

        with closing(sqlite3.connect(self.ruta)) as conexion, conexion:
            crear_tabla_reservas_emergencia(conexion)

            conexion.execute(
                """
                INSERT INTO PERSONAL (ID_EMPLEADO, NOMBRE, ROL)
                VALUES (1, 'Enfermero ficticio', 'Enfermero')
                """
            )

            conexion.executemany(
                """
                INSERT INTO CENTROS_MEDICOS (
                    NOMBRE, DIRECCION, COMUNA
                )
                VALUES (?, ?, ?)
                """,
                [
                    ("Centro solicitante demo", "Calle 1", "Concepción"),
                    ("Centro externo demo", "Calle 2", "Concepción"),
                ],
            )

            # Disponibilidad externa ficticia y determinista.
            conexion.execute("DELETE FROM CENTROS_EXTERNOS_STOCK")
            conexion.execute(
                """
                INSERT INTO CENTROS_EXTERNOS_STOCK (
                    CENTRO, GRUPO_SANGUINEO, FACTOR_RH,
                    VOLUMEN_DISPONIBLE_ML,
                    PRIORIDAD_CERCANIA, ACTUALIZADO_EN
                )
                VALUES (
                    'Centro externo demo', 'AB', '-',
                    900, 1, ?
                )
                """,
                (self.ahora.isoformat(),),
            )

            # Reserva ficticia inicialmente liberada.
            conexion.execute(
                """
                INSERT INTO DONACIONES (
                    ID, TIPO_SANGRE, FACTOR_RH, CANTIDAD,
                    FECHA_EXTRACCIÓN, FECHA_VENCIMIENTO,
                    ESTADO, ESTADO_LABORATORIO
                )
                VALUES (
                    1, 'AB', '-', 450,
                    '2026-11-20', '2026-12-10',
                    'Reservada', 'Liberada'
                )
                """
            )

            conexion.execute(
                """
                INSERT INTO DESPACHOS_EMERGENCIA (
                    ID, CENTRO, GRUPO_SANGUINEO, FACTOR_RH,
                    VOLUMEN_ML, MOTIVO, FECHA_SOLICITUD, ESTADO
                )
                VALUES (
                    1, 'Centro solicitante demo', 'AB', '-',
                    450, 'Prueba de integración', ?,
                    'Pendiente de aprobación'
                )
                """,
                (self.ahora.isoformat(),),
            )

            conexion.execute(
                """
                INSERT INTO RESERVAS_EMERGENCIA (
                    SOLICITUD_ID, DONACION_ID, VOLUMEN_ML
                )
                VALUES (1, 1, 450)
                """
            )

    def cambiar_unidad(self, laboratorio, vencimiento="2026-12-10"):
        with closing(sqlite3.connect(self.ruta)) as conexion, conexion:
            conexion.execute(
                """
                UPDATE DONACIONES
                SET ESTADO_LABORATORIO = ?,
                    FECHA_VENCIMIENTO = ?
                WHERE ID = 1
                """,
                (laboratorio, vencimiento),
            )

    def comprobar_redireccion(self, estado_esperado):
        resultado = ejecutar_redireccion_emergencia(
            1,
            1,
            ruta=self.ruta,
            ahora=self.ahora,
        )

        self.assertTrue(resultado["redirigida"])

        with closing(sqlite3.connect(self.ruta)) as conexion:
            unidad = conexion.execute(
                """
                SELECT ESTADO, CANTIDAD
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

        self.assertEqual(unidad, (estado_esperado, 450))
        self.assertEqual(reservas, 0)

    def test_reserva_liberada_cubre_la_orden(self):
        datos = evaluar_deficit_y_seleccionar_centro(
            1, 1, ruta=self.ruta, ahora=self.ahora
        )

        self.assertFalse(datos["requiere_redireccion"])
        self.assertEqual(datos["stock_propio_ml"], 450)

    def test_reserva_pendiente_no_cubre_y_no_vuelve_disponible(self):
        self.cambiar_unidad("Pendiente de análisis")

        datos = evaluar_deficit_y_seleccionar_centro(
            1, 1, ruta=self.ruta, ahora=self.ahora
        )

        self.assertTrue(datos["requiere_redireccion"])
        self.assertEqual(datos["stock_propio_ml"], 0)

        self.comprobar_redireccion("Pendiente de análisis")

    def test_reserva_bloqueada_no_vuelve_disponible(self):
        self.cambiar_unidad("Bloqueada")
        self.comprobar_redireccion("Bloqueada")

    def test_reserva_vencida_no_vuelve_disponible(self):
        self.cambiar_unidad(
            "Liberada",
            vencimiento="2026-11-25",
        )
        self.comprobar_redireccion("Vencida")


if __name__ == "__main__":
    unittest.main()