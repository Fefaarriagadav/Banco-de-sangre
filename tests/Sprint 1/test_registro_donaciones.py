import sqlite3
import tempfile
import unittest
from contextlib import closing
from datetime import date
from pathlib import Path

from datos.basededatos import inicializar_base
from servicios.donaciones import calcular_fecha_habilitacion, registrar_donacion
from servicios.elegibilidad import APTO, PERMANENTE, TEMPORAL
from servicios.vencimientos import DISPONIBLE


HOY = date(2026, 11, 13)


class RegistroDonacionesTest(unittest.TestCase):
    def setUp(self):
        temporal = tempfile.TemporaryDirectory()
        self.addCleanup(temporal.cleanup)
        self.ruta = Path(temporal.name) / "hu05.db"
        inicializar_base(self.ruta)
        with closing(sqlite3.connect(self.ruta)) as conexion, conexion:
            conexion.execute(
                "INSERT INTO PERSONAL (ID_EMPLEADO, NOMBRE, ROL) VALUES (1, 'Ana', 'Enfermero')"
            )
            conexion.execute(
                "INSERT INTO PERSONAL (ID_EMPLEADO, NOMBRE, ROL) VALUES (2, 'Luis', 'Entrevistador')"
            )
            self.insertar_donante(conexion, 10, "Masculino", "A", "+")
            self.insertar_donante(conexion, 11, "Femenino", "O", "-")

    @staticmethod
    def insertar_donante(conexion, id_, sexo, grupo, rh, elegible=APTO):
        conexion.execute(
            """INSERT INTO DONANTES (
                ID, NOMBRE, APELLIDO, EDAD, SEXO, GRUPO_SANGUINEO,
                FACTOR_RH, PESO, EMAIL, ELEGIBLE, FECHA_DE_NACIMIENTO
            ) VALUES (?, 'Donante', 'Prueba', 30, ?, ?, ?, 70, ?, ?, '1996-01-01')""",
            (id_, sexo, grupo, rh, f"d{id_}@example.invalid", elegible),
        )

    def consultar(self, sql, params=()):
        with closing(sqlite3.connect(self.ruta)) as conexion:
            return conexion.execute(sql, params).fetchall()

    def registrar(self, donante=10, cantidad=450, empleado=1, hoy=HOY):
        return registrar_donacion(donante, cantidad, empleado, ruta=self.ruta, hoy=hoy)

    def test_registro_valido_guarda_donacion_y_id(self):
        respuesta = self.registrar()
        id_ = respuesta["ID"]
        self.assertIsInstance(id_, int)
        self.assertGreater(id_, 0)
        self.assertEqual(respuesta["DONANTE"], 10)
        self.assertEqual(respuesta["FECHA_EXTRACCION"], "2026-11-13")
        self.assertEqual(respuesta["FECHA_VENCIMIENTO"], "2026-12-03")
        self.assertEqual(respuesta["UBICACION"], "Refrigerador 2")
        self.assertEqual(
            self.consultar(
                """SELECT ID, DONANTE, CANTIDAD, TIPO_SANGRE, FACTOR_RH, ESTADO, UBICACION
                   FROM DONACIONES"""
            ),
            [(id_, 10, 450, "A", "+", DISPONIBLE, "Refrigerador 2")],
        )

    def test_registro_inhabilita_temporalmente_y_crea_historial(self):
        self.registrar()
        self.assertEqual(
            self.consultar(
                """SELECT ELEGIBLE, FECHA_ULTIMA_DONACION,
                          INHABILITACION_INICIO, INHABILITACION_FIN
                   FROM DONANTES WHERE ID=10"""
            ),
            [(TEMPORAL, "2026-11-13", "2026-11-13", "2027-02-12")],
        )
        self.assertEqual(
            self.consultar(
                """SELECT DONANTE_ID, ESTADO_ANTERIOR, ESTADO_NUEVO,
                          FECHA_INICIO, FECHA_FIN, EMPLEADO_ID
                   FROM HISTORIAL_HABILITACION"""
            ),
            [(10, APTO, TEMPORAL, "2026-11-13", "2027-02-12", 1)],
        )

    def test_femenino_descanso_cuatro_meses(self):
        respuesta = self.registrar(donante=11, cantidad=300)
        self.assertEqual(respuesta["FECHA_HABILITACION"], "2027-03-13")
        self.assertEqual(respuesta["UBICACION"], "Refrigerador 1")
        self.assertEqual(
            self.consultar("SELECT INHABILITACION_FIN FROM DONANTES WHERE ID=11"),
            [("2027-03-12",)],
        )

    def test_fechas_extremas_ajustan_fin_de_mes(self):
        self.assertEqual(
            calcular_fecha_habilitacion(date(2026, 11, 30), "Masculino"),
            date(2027, 2, 28),
        )
        self.assertEqual(
            calcular_fecha_habilitacion(date(2028, 1, 31), "Femenino"),
            date(2028, 5, 31),
        )
        with self.assertRaises(ValueError):
            calcular_fecha_habilitacion(HOY, "Desconocido")

    def test_rechaza_cantidades_invalidas_sin_escribir(self):
        for cantidad in (None, "", "abc", 0, -1, 450.01, 451, float("nan"), float("inf")):
            with self.subTest(cantidad=cantidad), self.assertRaises(ValueError):
                self.registrar(cantidad=cantidad)
        self.assertEqual(self.consultar("SELECT COUNT(*) FROM DONACIONES"), [(0,)])
        self.assertEqual(self.consultar("SELECT COUNT(*) FROM HISTORIAL_HABILITACION"), [(0,)])

    def test_acepta_limites_de_cantidad(self):
        self.registrar(donante=10, cantidad="0.1")
        self.registrar(donante=11, cantidad="450")
        self.assertEqual(
            self.consultar("SELECT CANTIDAD FROM DONACIONES ORDER BY ID"),
            [(0.1,), (450,)],
        )

    def test_solo_enfermero_autorizado(self):
        for empleado in (2, 999, None):
            with self.subTest(empleado=empleado), self.assertRaises(PermissionError):
                self.registrar(empleado=empleado)
        self.assertEqual(self.consultar("SELECT COUNT(*) FROM DONACIONES"), [(0,)])

    def test_rechaza_donante_inexistente_o_id_invalido(self):
        for donante in (999, 0, -1, "abc", None):
            with self.subTest(donante=donante), self.assertRaises(ValueError):
                self.registrar(donante=donante)
        self.assertEqual(self.consultar("SELECT COUNT(*) FROM DONACIONES"), [(0,)])

    def test_rechaza_donante_no_apto_y_segunda_donacion(self):
        with closing(sqlite3.connect(self.ruta)) as conexion, conexion:
            conexion.execute("UPDATE DONANTES SET ELEGIBLE=? WHERE ID=11", (PERMANENTE,))
        with self.assertRaises(ValueError):
            self.registrar(donante=11)
        primera = self.registrar(donante=10)
        with self.assertRaises(ValueError):
            self.registrar(donante=10)
        self.assertEqual(self.consultar("SELECT ID FROM DONACIONES"), [(primera["ID"],)])
        self.assertEqual(self.consultar("SELECT COUNT(*) FROM HISTORIAL_HABILITACION"), [(1,)])

    def test_ubicacion_por_grupo(self):
        grupos = [
            ("O", "+", "Refrigerador 1"),
            ("A", "-", "Refrigerador 2"),
            ("B", "+", "Refrigerador 3"),
            ("AB", "-", "Refrigerador 3"),
        ]
        with closing(sqlite3.connect(self.ruta)) as conexion, conexion:
            for id_, (grupo, rh, _) in enumerate(grupos, start=20):
                self.insertar_donante(conexion, id_, "Masculino", grupo, rh)
        for id_, (_, _, destino) in enumerate(grupos, start=20):
            with self.subTest(id=id_, destino=destino):
                self.assertEqual(self.registrar(donante=id_)["UBICACION"], destino)

    def test_error_en_historial_revierte_toda_la_operacion(self):
        with closing(sqlite3.connect(self.ruta)) as conexion, conexion:
            conexion.execute("""CREATE TRIGGER prueba_fallo_historial
                BEFORE INSERT ON HISTORIAL_HABILITACION
                BEGIN SELECT RAISE(ABORT, 'fallo simulado'); END""")
        with self.assertRaises(sqlite3.IntegrityError):
            self.registrar()
        self.assertEqual(self.consultar("SELECT COUNT(*) FROM DONACIONES"), [(0,)])
        self.assertEqual(self.consultar("SELECT ELEGIBLE FROM DONANTES WHERE ID=10"), [(APTO,)])
        self.assertEqual(self.consultar("SELECT COUNT(*) FROM HISTORIAL_HABILITACION"), [(0,)])

    def test_id_de_donacion_es_clave_primaria_autoincremental(self):
        columnas = self.consultar("PRAGMA table_info(DONACIONES)")
        id_columna = next(col for col in columnas if col[1] == "ID")
        self.assertEqual(id_columna[2].upper(), "INTEGER")
        self.assertEqual(id_columna[5], 1)
        respuesta = self.registrar()
        self.assertEqual(
            self.consultar("SELECT ID FROM DONACIONES"),
            [(respuesta["ID"],)],
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
