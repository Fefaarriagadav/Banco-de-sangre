import sqlite3
import tempfile
import unittest
from pathlib import Path
from datetime import date
from datos.basededatos import inicializar_base
from servicios.elegibilidad import APTO, TEMPORAL, PERMANENTE
from servicios.elegibilidad import guardar_resultado, consultar_donante, conectar, buscar_donantes


class ElegibilidadTest(unittest.TestCase):
    def setUp(self):
        self.temporal = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent)
        self.addCleanup(self.temporal.cleanup)
        self.ruta = Path(self.temporal.name) / 'prueba.db'
        with conectar(self.ruta) as conexion:
            conexion.executescript("""
                CREATE TABLE DONANTES (ID INTEGER PRIMARY KEY, NOMBRE TEXT, APELLIDO TEXT, ELEGIBLE TEXT, EMAIL TEXT);
                CREATE TABLE PERSONAL (ID_EMPLEADO INTEGER PRIMARY KEY, ROL TEXT);
                INSERT INTO DONANTES VALUES (1, 'Donante', 'Prueba', 'Donante apto', 'uno@example.com');
                INSERT INTO DONANTES VALUES (2, 'Otro', 'Donante', 'Donante apto', 'dos@example.com');
                INSERT INTO PERSONAL VALUES (1, 'Entrevistador'), (2, 'Enfermero');
            """)
        inicializar_base(self.ruta)

    def test_buscar_por_identidad(self):
        self.assertEqual(buscar_donantes('pruéba DONANTE', self.ruta)[0]['ID'], 1)
        self.assertEqual(buscar_donantes('dos@example.com', self.ruta)[0]['ID'], 2)
        self.assertEqual(len(buscar_donantes('donante', self.ruta)), 2)
        self.assertEqual(buscar_donantes("' OR 1=1 --", self.ruta), [])
        self.assertEqual(buscar_donantes('%', self.ruta), [])
        with self.assertRaises(ValueError):
            buscar_donantes('  ', self.ruta)

    def guardar(self, donante, estado, empleado=1, inicio=None, fin=None):
        return guardar_resultado(donante, estado, empleado, inicio=inicio, fin=fin,
                                 ruta=self.ruta, hoy=date(2026, 11, 9))

    def test_registrar_consultar_y_actualizar(self):
        self.assertEqual(consultar_donante(1, self.ruta)['RESULTADO'], APTO)
        self.guardar(1, TEMPORAL, inicio='09-11-2026', fin='30-11-2026')
        donante = consultar_donante(1, self.ruta)
        self.assertEqual(donante['RESULTADO'], TEMPORAL)
        self.assertEqual((donante['INICIO'], donante['FIN']), ('2026-11-09', '2026-11-30'))
        self.guardar(1, PERMANENTE)
        donante = consultar_donante(1, self.ruta)
        self.assertEqual(donante['RESULTADO'], PERMANENTE)
        self.assertIsNone(donante['INICIO'])
        self.assertIsNone(donante['FIN'])
        self.assertEqual(consultar_donante(2, self.ruta)['RESULTADO'], APTO)
        inicializar_base(self.ruta)
        self.assertEqual(consultar_donante(1, self.ruta)['RESULTADO'], PERMANENTE)

    def test_rechazos_conservan_resultado_e_historial(self):
        self.guardar(1, TEMPORAL, inicio='09-11-2026', fin='30-11-2026')
        previo = consultar_donante(1, self.ruta)
        for empleado in (2, 999, None):
            with self.subTest(empleado=empleado), self.assertRaises(PermissionError):
                self.guardar(1, PERMANENTE, empleado)
        for donante, resultado in [(999, APTO), (1, 'Seleccione'), (1, ''), ('abc', APTO), (-1, APTO)]:
            with self.subTest(donante=donante, resultado=resultado), self.assertRaises(ValueError):
                self.guardar(donante, resultado)
        for inicio, fin in [(None, None), ('30-11-2026', '09-11-2026'), ('31-02-2026', '30-11-2026')]:
            with self.subTest(inicio=inicio, fin=fin), self.assertRaises(ValueError):
                self.guardar(1, TEMPORAL, inicio=inicio, fin=fin)
        self.assertEqual(consultar_donante(1, self.ruta), previo)
        with conectar(self.ruta) as conexion:
            self.assertEqual(conexion.execute('SELECT COUNT(*) FROM HISTORIAL_HABILITACION').fetchone()[0], 1)

    def test_estado_compartido_sin_recrear_tabla_legada(self):
        self.guardar(1, PERMANENTE)
        with conectar(self.ruta) as conexion:
            self.assertEqual(conexion.execute('SELECT ELEGIBLE FROM DONANTES WHERE ID=1').fetchone()[0], PERMANENTE)
            tablas = {fila[0] for fila in conexion.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            self.assertNotIn('EVALUACIONES_ELEGIBILIDAD', tablas)
            historial = conexion.execute('SELECT DONANTE_ID, ESTADO_ANTERIOR, ESTADO_NUEVO, EMPLEADO_ID FROM HISTORIAL_HABILITACION').fetchone()
            self.assertEqual(tuple(historial), (1, APTO, PERMANENTE, 1))


if __name__ == '__main__':
    unittest.main()
