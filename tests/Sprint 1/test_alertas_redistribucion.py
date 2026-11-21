import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from servicios import alertas_stock as servicio
from pantallas import alertas_redistribucion as interfaz

class BaseTemporal(unittest.TestCase):
    def setUp(self):
        temporal = tempfile.TemporaryDirectory()
        self.addCleanup(temporal.cleanup)
        self.ruta = Path(temporal.name) / 'alertas_prueba.db'
        with sqlite3.connect(self.ruta) as bd:
            bd.executescript("""
                CREATE TABLE DONACIONES (
                    ID INTEGER PRIMARY KEY AUTOINCREMENT,
                    TIPO_SANGRE TEXT,
                    FACTOR_RH TEXT,
                    ESTADO TEXT,
                    FECHA_VENCIMIENTO TEXT
                );
                CREATE TABLE UMBRALES (
                    GRUPO_SANGUINEO TEXT,
                    FACTOR_RH TEXT,
                    UMBRAL_MAXIMO INTEGER
                );
                CREATE TABLE HOSPITALES (
                    NOMBRE TEXT,
                    DIRECCION TEXT,
                    GRUPO_SANGUINEO_REQUERIDO TEXT,
                    FACTOR_RH_REQUERIDO TEXT,
                    CANTIDAD_REQUERIDA INTEGER
                );
                INSERT INTO UMBRALES VALUES ('A', '+', 5);
                INSERT INTO UMBRALES VALUES ('O', '-', 2);
                INSERT INTO UMBRALES VALUES ('AB', '+', 0);
            """)
        self.parche_ruta = patch.object(servicio, 'RUTA_BD', self.ruta)
        self.parche_ruta.start()
        self.addCleanup(self.parche_ruta.stop)

    def bolsas(self, grupo='A', rh='+', cantidad=1, estado='Disponible'):
        with sqlite3.connect(self.ruta) as bd:
            bd.executemany(
                'INSERT INTO DONACIONES (TIPO_SANGRE, FACTOR_RH, ESTADO) VALUES (?, ?, ?)',
                [(grupo, rh, estado)] * cantidad,
            )

    def hospital(self, nombre, grupo='A', rh='+', cantidad=3, direccion='Concepción'):
        with sqlite3.connect(self.ruta) as bd:
            bd.execute(
                'INSERT INTO HOSPITALES VALUES (?, ?, ?, ?, ?)',
                (nombre, direccion, grupo, rh, cantidad),
            )

class AlertasStockTest(BaseTemporal):
    def test_sin_bolsas_no_hay_alertas(self):
        self.assertEqual(servicio.obtener_alertas_sobreabastecimiento(), [])

    def test_stock_menor_al_umbral_no_genera_alerta(self):
        self.bolsas(cantidad=4)
        self.assertEqual(servicio.obtener_alertas_sobreabastecimiento(), [])

    def test_stock_igual_al_umbral_no_genera_alerta(self):
        self.bolsas(cantidad=5)
        self.assertEqual(servicio.obtener_alertas_sobreabastecimiento(), [])

    def test_superar_umbral_calcula_excedente(self):
        self.bolsas(cantidad=7)
        self.assertEqual(servicio.obtener_alertas_sobreabastecimiento(), [{
            'grupo': 'A', 'rh': '+', 'stock': 7, 'umbral': 5, 'excedente': 2,
        }])

    def test_grupos_y_factores_no_se_mezclan(self):
        self.bolsas('A', '+', 6)
        self.bolsas('A', '-', 9)  # Sin umbral configurado: no genera alerta.
        self.bolsas('O', '-', 4)
        alertas = servicio.obtener_alertas_sobreabastecimiento()
        datos = {(a['grupo'], a['rh']): a['excedente'] for a in alertas}
        self.assertEqual(datos, {('A', '+'): 1, ('O', '-'): 2})

    def test_no_cuenta_estados_distintos_de_disponible(self):
        self.bolsas(cantidad=4)
        for estado in ('Vencida', 'Usada', 'Descartada', 'Reservada', 'Pendiente de revisión'):
            self.bolsas(cantidad=3, estado=estado)
        self.assertEqual(servicio.obtener_alertas_sobreabastecimiento(), [])

    def test_umbral_cero_alerta_desde_una_bolsa(self):
        self.bolsas('AB', '+', 1)
        self.assertEqual(servicio.obtener_alertas_sobreabastecimiento()[0]['excedente'], 1)

    def test_umbrales_invalidos_se_omiten(self):
        with sqlite3.connect(self.ruta) as bd:
            bd.execute("UPDATE UMBRALES SET UMBRAL_MAXIMO=-1 WHERE GRUPO_SANGUINEO='A'")
            bd.execute("UPDATE UMBRALES SET UMBRAL_MAXIMO=NULL WHERE GRUPO_SANGUINEO='O'")
        self.bolsas('A', '+', 8)
        self.bolsas('O', '-', 8)
        self.assertEqual(servicio.obtener_alertas_sobreabastecimiento(), [])

    def test_error_sql_se_traduce_a_valueerror(self):
        with sqlite3.connect(self.ruta) as bd:
            bd.execute('DROP TABLE UMBRALES')
        with self.assertRaisesRegex(ValueError, 'base de datos'):
            servicio.obtener_alertas_sobreabastecimiento()

class SugerenciasTest(BaseTemporal):
    def test_sin_hospitales_no_hay_sugerencias(self):
        self.assertEqual(servicio.sugerir_redistribucion('A', '+'), [])

    def test_filtra_por_grupo_y_rh_y_cantidad_positiva(self):
        self.hospital('Hospital correcto', 'A', '+', 6)
        self.hospital('Rh distinto', 'A', '-', 8)
        self.hospital('Grupo distinto', 'O', '+', 9)
        self.hospital('Sin necesidad', 'A', '+', 0)
        self.hospital('Cantidad negativa', 'A', '+', -2)
        self.assertEqual(servicio.sugerir_redistribucion('A', '+'), [{
            'nombre': 'Hospital correcto', 'direccion': 'Concepción', 'requiere': 6,
        }])

    def test_devuelve_varios_hospitales(self):
        self.hospital('Hospital 1', cantidad=2)
        self.hospital('Hospital 2', cantidad=4)
        destinos = servicio.sugerir_redistribucion('A', '+')
        self.assertEqual({d['nombre'] for d in destinos}, {'Hospital 1', 'Hospital 2'})
        self.assertEqual(sum(d['requiere'] for d in destinos), 6)

    def test_consulta_no_modifica_inventario(self):
        self.bolsas(cantidad=6)
        self.hospital('Hospital 1', cantidad=3)
        with sqlite3.connect(self.ruta) as bd:
            antes = bd.execute('SELECT COUNT(*) FROM DONACIONES').fetchone()[0]
        servicio.sugerir_redistribucion('A', '+')
        with sqlite3.connect(self.ruta) as bd:
            despues = bd.execute('SELECT COUNT(*) FROM DONACIONES').fetchone()[0]
        self.assertEqual(antes, despues)

    def test_error_sql_se_traduce_a_valueerror(self):
        with sqlite3.connect(self.ruta) as bd:
            bd.execute('DROP TABLE HOSPITALES')
        with self.assertRaisesRegex(ValueError, 'destino'):
            servicio.sugerir_redistribucion('A', '+')

class ControlFalso:
    """Sustituto de widgets CustomTkinter, sin abrir ventanas."""
    creados = []

    def __init__(self, padre=None, **opciones):
        self.padre = padre
        self.opciones = opciones
        self.hijos = []
        self.destruido = False
        self.creados.append(self)
        if padre is not None:
            padre.hijos.append(self)

    def place(self, **kw): pass
    def pack(self, **kw): pass
    def grid(self, **kw): pass
    def grid_columnconfigure(self, *a, **kw): pass
    def winfo_children(self): return [h for h in self.hijos if not h.destruido]
    def destroy(self):
        self.destruido = True
        if self.padre is not None and self in self.padre.hijos:
            self.padre.hijos.remove(self)

class PantallaAlertasTest(unittest.TestCase):
    def setUp(self):
        ControlFalso.creados = []
        self.pantalla = ControlFalso()
        widgets = ('CTkFrame', 'CTkScrollableFrame', 'CTkLabel', 'CTkButton')
        parche = patch.multiple(interfaz.ctk, **{w: ControlFalso for w in widgets})
        parche.start()
        self.addCleanup(parche.stop)

    def boton(self, texto):
        return next(c for c in ControlFalso.creados
                    if c.opciones.get('text') == texto and not c.destruido)

    def textos_activos(self):
        return [c.opciones['text'] for c in ControlFalso.creados
                if not c.destruido and 'text' in c.opciones]

    def test_sin_alertas_muestra_niveles_normales(self):
        with patch.object(interfaz, 'obtener_alertas_sobreabastecimiento', return_value=[]):
            interfaz.mostrar_alertas_redistribucion(self.pantalla)
        self.assertTrue(any('Niveles normales' in t for t in self.textos_activos()))

    def test_alerta_y_boton_muestran_destino(self):
        alertas = [{'grupo': 'O', 'rh': '-', 'stock': 8, 'umbral': 5, 'excedente': 3}]
        destinos = [{'nombre': 'Hospital de prueba', 'direccion': 'Concepción', 'requiere': 2}]
        with patch.object(interfaz, 'obtener_alertas_sobreabastecimiento', return_value=alertas), \
             patch.object(interfaz, 'sugerir_redistribucion', return_value=destinos) as sugerir:
            interfaz.mostrar_alertas_redistribucion(self.pantalla)
            self.boton('Ver Destinos').opciones['command']()
        sugerir.assert_called_once_with('O', '-')
        textos = self.textos_activos()
        self.assertTrue(any('Hospital de prueba' in t for t in textos))
        self.assertTrue(any('3 unidades de O-' in t for t in textos))

    def test_sin_destinos_muestra_aviso(self):
        alertas = [{'grupo': 'A', 'rh': '+', 'stock': 6, 'umbral': 5, 'excedente': 1}]
        with patch.object(interfaz, 'obtener_alertas_sobreabastecimiento', return_value=alertas), \
             patch.object(interfaz, 'sugerir_redistribucion', return_value=[]):
            interfaz.mostrar_alertas_redistribucion(self.pantalla)
            self.boton('Ver Destinos').opciones['command']()
        self.assertTrue(any('no hay una' in t for t in self.textos_activos()))

    def test_error_en_alertas_muestra_mensaje(self):
        with patch.object(interfaz, 'obtener_alertas_sobreabastecimiento', side_effect=ValueError('error')):
            interfaz.mostrar_alertas_redistribucion(self.pantalla)
        self.assertTrue(any('Datos de stock' in t for t in self.textos_activos()))

    def test_actualizar_alertas_refresca_la_pantalla(self):
        with patch.object(interfaz, 'obtener_alertas_sobreabastecimiento', side_effect=[[], []]) as consultar:
            interfaz.mostrar_alertas_redistribucion(self.pantalla)
            self.boton('Actualizar Alertas').opciones['command']()
        self.assertEqual(consultar.call_count, 2)

if __name__ == '__main__':
    unittest.main(verbosity=2)