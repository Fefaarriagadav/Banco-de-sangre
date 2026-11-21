import sqlite3
import tempfile
import unittest
from contextlib import closing
from datetime import date, timedelta
from pathlib import Path
from servicios.despachos import (seleccionar_bolsas_emergencia,crear_tabla_reservas_emergencia,registrar_emergencia,ExcesoVolumenError,)

class TestFEFODespachos(unittest.TestCase):
    def setUp(self):
        temporal = tempfile.TemporaryDirectory()
        self.addCleanup(temporal.cleanup)
        self.ruta = Path(temporal.name) / 'fefo.db'
        self.hoy = date.today()
        with closing(sqlite3.connect(self.ruta)) as conexion, conexion:
            conexion.executescript('''
                CREATE TABLE CENTROS_MEDICOS (NOMBRE TEXT PRIMARY KEY, DIRECCION TEXT, COMUNA TEXT);
                INSERT INTO CENTROS_MEDICOS VALUES ('Hospital Prueba', 'Calle 1', 'Concepcion');
                CREATE TABLE DONANTES (ID INTEGER PRIMARY KEY, GRUPO_SANGUINEO TEXT, FACTOR_RH TEXT);
                CREATE TABLE DONACIONES (
                    ID INTEGER PRIMARY KEY, DONANTE INTEGER,
                    TIPO_SANGRE TEXT, FACTOR_RH TEXT,
                    CANTIDAD INTEGER, ESTADO TEXT, FECHA_VENCIMIENTO TEXT
                );
            ''')
            crear_tabla_reservas_emergencia(conexion)

    def bolsa(self, identificador, volumen, dias=5, estado='Disponible', grupo='A', rh='+'):
        fecha = (self.hoy + timedelta(days=dias)).isoformat()
        with closing(sqlite3.connect(self.ruta)) as conexion, conexion:
            conexion.execute('''INSERT INTO DONACIONES
                (ID, TIPO_SANGRE, FACTOR_RH, CANTIDAD, ESTADO, FECHA_VENCIMIENTO)
                VALUES (?, ?, ?, ?, ?, ?)''',
                (identificador, grupo, rh, volumen, estado, fecha))

    def seleccionar(self, volumen):
        with closing(sqlite3.connect(self.ruta)) as conexion:
            return seleccionar_bolsas_emergencia(conexion, 'A', '+', volumen, self.hoy)

    def test_prioriza_vencimiento_si_hay_varias_combinaciones_exactas(self):
        # La bolsa más próxima vence antes; no debe ignorarse por usar más bolsas.
        self.bolsa(11, 200, dias=1)
        self.bolsa(12, 250, dias=2)
        self.bolsa(13, 450, dias=8)
        bolsas, total = self.seleccionar(450)
        self.assertEqual(total, 450)
        self.assertEqual([bolsa[0] for bolsa in bolsas], [11, 12])

    def test_minimiza_sobrante_antes_de_fefo(self):
        self.bolsa(1, 200, dias=1)
        self.bolsa(2, 450, dias=5)
        self.bolsa(3, 450, dias=9)
        bolsas, total = self.seleccionar(900)
        self.assertEqual(total, 900)
        self.assertEqual([bolsa[0] for bolsa in bolsas], [2, 3])

    def test_excluye_vencidas_reservadas_y_otro_grupo(self):
        self.bolsa(1, 450, dias=-1)
        self.bolsa(2, 450, dias=2, estado='Reservada')
        self.bolsa(3, 450, dias=3, grupo='B')
        self.bolsa(4, 450, dias=4)
        bolsas, total = self.seleccionar(450)
        self.assertEqual(total, 450)
        self.assertEqual([bolsa[0] for bolsa in bolsas], [4])

    def test_registro_reserva_bolsas_y_no_las_duplica(self):
        self.bolsa(1, 200, dias=1)
        self.bolsa(2, 250, dias=2)
        solicitud_id = registrar_emergencia(
            'Hospital Prueba', 'A', '+', 450, 'Urgencia clínica', ruta=self.ruta)
        with closing(sqlite3.connect(self.ruta)) as conexion:
            filas = conexion.execute('''SELECT r.DONACION_ID, d.ESTADO
                FROM RESERVAS_EMERGENCIA r JOIN DONACIONES d ON d.ID=r.DONACION_ID
                WHERE r.SOLICITUD_ID=? ORDER BY r.DONACION_ID''', (solicitud_id,)).fetchall()
        self.assertEqual(filas, [(1, 'Reservada'), (2, 'Reservada')])
        with self.assertRaisesRegex(ValueError, 'Stock insuficiente'):
            registrar_emergencia(
                'Hospital Prueba', 'A', '+', 450, 'Otra urgencia', ruta=self.ruta)

    def test_no_reserva_ni_registra_sin_confirmacion_de_exceso(self):
        self.bolsa(1, 450, dias=2)
        with self.assertRaises(ExcesoVolumenError):
            registrar_emergencia(
                'Hospital Prueba', 'A', '+', 200, 'Urgencia', ruta=self.ruta)
        with closing(sqlite3.connect(self.ruta)) as conexion:
            tabla = conexion.execute("SELECT name FROM sqlite_master WHERE name='DESPACHOS_EMERGENCIA'").fetchone()
            if tabla is not None:
                self.assertEqual(conexion.execute('SELECT COUNT(*) FROM DESPACHOS_EMERGENCIA').fetchone()[0], 0)
            self.assertEqual(conexion.execute('SELECT ESTADO FROM DONACIONES WHERE ID=1').fetchone()[0], 'Disponible')


if __name__ == '__main__':
    unittest.main()
