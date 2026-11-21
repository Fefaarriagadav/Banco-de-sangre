import sqlite3
import tempfile
import unittest
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from datos.basededatos import inicializar_base
from servicios.despachos import (
    consultar_despachos,
    consultar_direccion_despacho,
    registrar_despacho,
    migrar_despachos,
)
from servicios.vencimientos import consultar_stock_detallado


class DespachosProgramadosTest(unittest.TestCase):
    def setUp(self):
        temporal = tempfile.TemporaryDirectory()
        self.addCleanup(temporal.cleanup)
        self.ruta = Path(temporal.name) / "despachos.db"
        # La base local ya contiene el catálogo de centros de HU09.
        with closing(sqlite3.connect(self.ruta)) as conexion, conexion:
            conexion.execute("""
                CREATE TABLE CENTROS_MEDICOS (
                    NOMBRE TEXT PRIMARY KEY NOT NULL, DIRECCION TEXT, COMUNA TEXT
                )
            """)
            conexion.executemany(
                "INSERT INTO CENTROS_MEDICOS (NOMBRE, DIRECCION, COMUNA) VALUES (?, ?, ?)",
                [("Hospital de prueba", "Calle Hospital 10", "Concepción"),
                 ("Clínica de prueba", "Calle Clínica 20", None)],
            )
        inicializar_base(self.ruta)
        # Crear el esquema de HU10 sobre la base temporal antes de los tests.
        with closing(sqlite3.connect(self.ruta)) as conexion, conexion:
            migrar_despachos(conexion)
        # Bolsa AB- disponible durante la fecha simulada de los tests.
        # Todas las solicitudes programadas usan mL, no número de bolsas.
        with closing(sqlite3.connect(self.ruta)) as conexion, conexion:
            conexion.execute("""
                INSERT INTO DONACIONES (
                    TIPO_SANGRE, FACTOR_RH, FECHA_EXTRACCIÓN,
                    FECHA_VENCIMIENTO, CANTIDAD, ESTADO
                ) VALUES ('AB', '-', '2026-11-15', '2026-11-30', 450, 'Disponible')
            """)
        self.ahora = datetime(2026, 11, 20, 15, 0, tzinfo=timezone.utc)
        self.datos = {
            "centro": "Hospital de prueba", "grupo": "AB", "rh": "-",
            "cantidad": "300", "fecha": "20-11-2026", "horario": "12:01",
            "direccion_confirmada": "Calle Hospital 10, Concepción",
            "ruta": self.ruta, "ahora": self.ahora,
        }

    def guardar(self, **cambios):
        return registrar_despacho(**(self.datos | cambios))

    def consultar(self, centro="Hospital de prueba"):
        return consultar_despachos(centro, ruta=self.ruta)

    def test_registra_con_stock_y_conserva_solicitudes_por_centro(self):
        with closing(sqlite3.connect(self.ruta)) as conexion:
            unidades_antes = conexion.execute("SELECT * FROM DONACIONES").fetchall()
        stock_antes = consultar_stock_detallado(self.ruta, ahora=self.ahora)
        self.assertEqual(len(stock_antes["unidades"]), 1)

        primera = self.guardar()
        segunda = self.guardar(centro="Clínica de prueba", direccion_confirmada="Calle Clínica 20")
        self.assertNotEqual(primera, segunda)
        inicializar_base(self.ruta)

        self.assertEqual(self.consultar(), [{
            "ID": primera, "CENTRO": "Hospital de prueba", "GRUPO_SANGUINEO": "AB",
            "FACTOR_RH": "-", "CANTIDAD": None, "VOLUMEN_ML": 300,
            "FECHA_DESPACHO": "2026-11-20",
            "HORA_DESPACHO": "12:01", "DESTINO": "Calle Hospital 10, Concepción",
            "ESTADO": "Pendiente",
        }])
        self.assertEqual([fila["ID"] for fila in self.consultar("Clínica de prueba")], [segunda])
        self.assertEqual(consultar_stock_detallado(self.ruta, ahora=self.ahora), stock_antes)
        with closing(sqlite3.connect(self.ruta)) as conexion:
            self.assertEqual(conexion.execute("SELECT * FROM DONACIONES").fetchall(), unidades_antes)

    def test_rechaza_volumen_superior_al_disponible(self):
        with self.assertRaisesRegex(ValueError, "Stock insuficiente"):
            self.guardar(cantidad="451")
        self.assertEqual(self.consultar(), [])

    def test_rechaza_datos_invalidos_sin_guardar(self):
        casos = (
            ({"grupo": ""}, "grupo"),
            ({"grupo": "Z"}, "grupo"),
            ({"rh": "?"}, "Rh"),
            ({"cantidad": ""}, "volumen entero en mL"),
            ({"cantidad": 0}, "volumen entero en mL"),
            ({"cantidad": -2}, "volumen entero en mL"),
            ({"cantidad": "1.5"}, "volumen entero en mL"),
            ({"cantidad": True}, "volumen entero en mL"),
            ({"cantidad": 2**63}, "máximo"),
            ({"fecha": ""}, "fecha"),
            ({"fecha": "31-02-2027"}, "fecha"),
            ({"horario": "24:00"}, "horario"),
            ({"fecha": "19-11-2026"}, "futuras"),
            ({"horario": "11:59"}, "futuras"),
            ({"horario": "12:00"}, "futuras"),
            ({"direccion_confirmada": ""}, "dirección"),
            ({"direccion_confirmada": "Calle Clínica 20"}, "dirección"),
        )
        for datos, mensaje in casos:
            with self.subTest(datos=datos), self.assertRaisesRegex(ValueError, mensaje):
                self.guardar(**datos)
        self.assertEqual(self.consultar(), [])

    def test_solo_guarda_la_direccion_confirmada_y_conserva_la_historica(self):
        centro = self.datos["centro"]
        direccion_original = consultar_direccion_despacho(centro, ruta=self.ruta)
        self.guardar(direccion_confirmada=direccion_original)

        with closing(sqlite3.connect(self.ruta)) as conexion, conexion:
            conexion.execute(
                "UPDATE CENTROS_MEDICOS SET DIRECCION = ? WHERE NOMBRE = ?",
                ("Avenida Nueva 20", centro),
            )

        with self.assertRaisesRegex(ValueError, "dirección"):
            self.guardar(direccion_confirmada=direccion_original)
        self.assertEqual(len(self.consultar()), 1)

        direccion_nueva = consultar_direccion_despacho(centro, ruta=self.ruta)
        self.assertEqual(direccion_nueva, "Avenida Nueva 20, Concepción")
        self.guardar(direccion_confirmada=direccion_nueva)
        self.assertEqual([fila["DESTINO"] for fila in self.consultar()], [
            "Avenida Nueva 20, Concepción", "Calle Hospital 10, Concepción",
        ])

    def test_centro_sin_direccion_no_puede_registrar(self):
        with closing(sqlite3.connect(self.ruta)) as conexion, conexion:
            conexion.execute(
                "UPDATE CENTROS_MEDICOS SET DIRECCION = NULL WHERE NOMBRE = ?",
                (self.datos["centro"],),
            )
        with self.assertRaisesRegex(ValueError, "no tiene una dirección"):
            consultar_direccion_despacho(self.datos["centro"], ruta=self.ruta)
        with self.assertRaisesRegex(ValueError, "no tiene una dirección"):
            self.guardar()
        self.assertEqual(self.consultar(), [])

    def test_rechaza_centro_fuera_del_catalogo(self):
        for centro in (None, "", "Centro desconocido"):
            with self.subTest(centro=centro):
                with self.assertRaises(PermissionError):
                    self.guardar(centro=centro)
                with self.assertRaises(PermissionError):
                    self.consultar(centro)
        self.assertEqual(self.consultar(), [])

    def test_rechaza_horas_no_representables_por_cambio_de_hora(self):
        ahora = datetime(2026, 1, 1, tzinfo=timezone.utc)
        for fecha, horario in (("04-04-2026", "23:30"), ("06-09-2026", "00:30")):
            with self.subTest(fecha=fecha), self.assertRaisesRegex(ValueError, "cambio de hora"):
                self.guardar(fecha=fecha, horario=horario, ahora=ahora)
        self.assertEqual(self.consultar(), [])

    def test_fallo_de_escritura_no_deja_solicitud(self):
        with closing(sqlite3.connect(self.ruta)) as conexion, conexion:
            conexion.execute("""
                CREATE TRIGGER impedir_despacho AFTER INSERT ON DESPACHOS_PROGRAMADOS
                BEGIN
                    SELECT RAISE(FAIL, 'Fallo simulado');
                END
            """)
        with self.assertRaises(sqlite3.IntegrityError):
            self.guardar()
        self.assertEqual(self.consultar(), [])
