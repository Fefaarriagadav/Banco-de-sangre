import sqlite3
import tempfile
import unittest
from pathlib import Path
from servicios.elegibilidad import preparar_elegibilidad, guardar_resultado, consultar_donante, conectar, buscar_donantes


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
        preparar_elegibilidad(self.ruta)

    def test_buscar_por_identidad(self):
        self.assertEqual(buscar_donantes('pruéba DONANTE', self.ruta)[0]['ID'], 1)
        self.assertEqual(buscar_donantes('dos@example.com', self.ruta)[0]['ID'], 2)
        self.assertEqual(len(buscar_donantes('donante', self.ruta)), 2)
        self.assertEqual(buscar_donantes("' OR 1=1 --", self.ruta), [])
        self.assertEqual(buscar_donantes('%', self.ruta), [])
        with self.assertRaises(ValueError):
            buscar_donantes('  ', self.ruta)

    def test_registrar_consultar_y_actualizar(self):
        self.assertIsNone(consultar_donante(1, self.ruta)['RESULTADO'])
        guardar_resultado(1, 'Apto', 1, self.ruta)
        self.assertEqual(consultar_donante(1, self.ruta)['RESULTADO'], 'Apto')
        guardar_resultado(1, 'No apto', 1, self.ruta)
        self.assertEqual(consultar_donante(1, self.ruta)['RESULTADO'], 'No apto')
        self.assertIsNone(consultar_donante(2, self.ruta)['RESULTADO'])
        preparar_elegibilidad(self.ruta)
        self.assertEqual(consultar_donante(1, self.ruta)['RESULTADO'], 'No apto')

    def test_rechazos_conservan_resultado(self):
        guardar_resultado(1, 'Apto', 1, self.ruta)
        for empleado in (2, 999, None):
            with self.subTest(empleado=empleado), self.assertRaises(PermissionError):
                guardar_resultado(1, 'No apto', empleado, self.ruta)
        for donante, resultado in [(999, 'Apto'), (1, 'Seleccione'), (1, ''), ('abc', 'Apto'), (-1, 'Apto')]:
            with self.subTest(donante=donante, resultado=resultado), self.assertRaises(ValueError):
                guardar_resultado(donante, resultado, 1, self.ruta)
        self.assertEqual(consultar_donante(1, self.ruta)['RESULTADO'], 'Apto')

    def test_sin_respuestas_clinicas_ni_cambios_a_h4(self):
        guardar_resultado(1, 'No apto', 1, self.ruta)
        with conectar(self.ruta) as conexion:
            columnas = [fila[1] for fila in conexion.execute('PRAGMA table_info(EVALUACIONES_ELEGIBILIDAD)')]
            self.assertEqual(columnas, ['DONANTE_ID', 'RESULTADO'])
            self.assertEqual(conexion.execute('SELECT ELEGIBLE FROM DONANTES WHERE ID=1').fetchone()[0], 'Donante apto')
            with self.assertRaises(sqlite3.IntegrityError):
                conexion.execute("INSERT INTO EVALUACIONES_ELEGIBILIDAD VALUES (999, 'Inválido')")


if __name__ == '__main__':
    unittest.main()
