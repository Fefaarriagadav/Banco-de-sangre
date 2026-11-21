import sqlite3
import unittest
from datetime import date, timedelta
from unittest.mock import patch
from pantallas import stocks, panel_vencimientos

class ControlFalso:
    """Sustituye los controles gráficos y conserva datos visibles y callbacks."""
    creados = []
    def __init__(self, padre=None, **opciones):
        self.padre = padre
        self.opciones = dict(opciones)
        self.hijos = []
        self.filas = []
        self.destruido = False
        self.tarea = None
        self.eventos = {}
        if padre is not None and hasattr(padre, 'hijos'):
            padre.hijos.append(self)
        self.creados.append(self)

    def place(self, **kwargs): pass
    def pack(self, **kwargs): pass
    def grid(self, **kwargs): pass
    def grid_columnconfigure(self, *args, **kwargs): pass
    def grid_rowconfigure(self, *args, **kwargs): pass
    def configure(self, **kwargs): self.opciones.update(kwargs)
    config = configure
    def winfo_children(self): return [h for h in self.hijos if not h.destruido]
    def winfo_exists(self): return not self.destruido
    def destroy(self): self.destruido = True
    def bind(self, evento, callback, **kwargs): self.eventos[evento] = callback
    def after(self, ms, callback):
        self.tarea = (ms, callback)
        return 'temporizador-falso'
    def after_cancel(self, codigo):
        self.tarea = None
        self.cancelado = codigo
    def heading(self, *args, **kwargs): pass
    def column(self, *args, **kwargs): pass
    def yview(self, *args, **kwargs): pass
    def xview(self, *args, **kwargs): pass
    def set(self, *args, **kwargs): pass
    def insert(self, padre, posicion, **kwargs):
        fila = object()
        self.filas.append((fila, kwargs.get('values')))
        return fila
    def get_children(self): return [identificador for identificador, _ in self.filas]
    def delete(self, identificador):
        self.filas = [(ident, v) for ident, v in self.filas if ident is not identificador]

class EstiloFalso:
    def __init__(self, *args, **kwargs): pass
    def configure(self, *args, **kwargs): pass

class PantallasStockVencimientosTest(unittest.TestCase):
    def setUp(self):
        ControlFalso.creados = []
        nombres_ctk = ['CTkFrame', 'CTkLabel', 'CTkButton', 'CTkScrollableFrame']
        for modulo in (stocks, panel_vencimientos):
            parche = patch.multiple(modulo.ctk, **{n: ControlFalso for n in nombres_ctk})
            parche.start()
            self.addCleanup(parche.stop)
        parche_ttk = patch.multiple(stocks.ttk, Style=EstiloFalso,
                                  Treeview=ControlFalso, Scrollbar=ControlFalso)
        parche_ttk.start()
        self.addCleanup(parche_ttk.stop)
        self.raiz = ControlFalso()

    def control_texto(self, texto):
        return next(c for c in ControlFalso.creados if c.opciones.get('text') == texto)

    def texto_contiene(self, fragmento):
        return any(fragmento in str(c.opciones.get('text', ''))
                   for c in ControlFalso.creados if not c.destruido)

    def boton(self, titulo):
        return self.control_texto(titulo).opciones['command']

    def datos_stock(self):
        return {
            'totales': [
                {'grupo': 'A', 'rh': '+', 'unidades': 2, 'litros': 0.75,
                 'proximo_vencimiento': '2026-11-15'},
                {'grupo': 'O', 'rh': '-', 'unidades': 1, 'litros': 0.45,
                 'proximo_vencimiento': '2026-11-18'},
            ],
            'unidades': [
                {'ID': 11, 'GRUPO': 'A', 'RH': '+', 'CANTIDAD': 450,
                 'EXTRACCION': '2026-11-01', 'VENCIMIENTO': '2026-11-15'},
                {'ID': 12, 'GRUPO': 'A', 'RH': '+', 'CANTIDAD': 300,
                 'EXTRACCION': '2026-11-02', 'VENCIMIENTO': '2026-11-17'},
                {'ID': 13, 'GRUPO': 'O', 'RH': '-', 'CANTIDAD': 450,
                 'EXTRACCION': '2026-11-03', 'VENCIMIENTO': '2026-11-18'},
            ],
        }

    def test_stocks_carga_totales_y_detalles(self):
        with patch.object(stocks, 'consultar_stock_detallado', return_value=self.datos_stock()) as consulta:
            stocks.mostrar_stocks(self.raiz)
        consulta.assert_called_once()
        tablas = [c for c in ControlFalso.creados if 'columns' in c.opciones]
        self.assertEqual(len(tablas), 2)
        self.assertEqual(len(tablas[0].filas), 2)
        self.assertEqual(len(tablas[1].filas), 3)
        self.assertEqual(tablas[0].filas[0][1], ('A', '+', 2, '0.75', '15-11-2026'))
        self.assertEqual(tablas[1].filas[0][1], (11, 'A', '+', '0.45', '01-11-2026', '15-11-2026'))
        self.assertTrue(self.texto_contiene('Total disponible: 3 unidades · 1.20 litros'))

    def test_stocks_refrescar_reemplaza_filas(self):
        with patch.object(stocks, 'consultar_stock_detallado', side_effect=[self.datos_stock(),
                       {'totales': [], 'unidades': []}]) as consulta:
            stocks.mostrar_stocks(self.raiz)
            self.boton('Actualizar ahora')()
        self.assertEqual(consulta.call_count, 2)
        tablas = [c for c in ControlFalso.creados if 'columns' in c.opciones]
        self.assertEqual([len(t.filas) for t in tablas], [0, 0])
        self.assertTrue(self.texto_contiene('Total disponible: 0 unidades · 0.00 litros'))

    def test_stocks_error_de_consulta_informa_y_vacia_tablas(self):
        with patch.object(stocks, 'consultar_stock_detallado', side_effect=[
            self.datos_stock(), sqlite3.OperationalError('falló')]):
            stocks.mostrar_stocks(self.raiz)
            self.boton('Actualizar ahora')()
        tablas = [c for c in ControlFalso.creados if 'columns' in c.opciones]
        self.assertEqual([len(t.filas) for t in tablas], [0, 0])
        self.assertTrue(self.texto_contiene('Stock no disponible'))
        self.assertTrue(self.texto_contiene('Se reintentará automáticamente'))

    def test_stocks_reemplaza_pantalla_anterior(self):
        with patch.object(stocks, 'consultar_stock_detallado', return_value=self.datos_stock()):
            stocks.mostrar_stocks(self.raiz)
            anterior = self.raiz._pantalla_stocks
            stocks.mostrar_stocks(self.raiz)
        self.assertTrue(anterior.destruido)
        self.assertIsNot(anterior, self.raiz._pantalla_stocks)

    def test_stocks_temporizador_se_cancela_al_destruir(self):
        with patch.object(stocks, 'consultar_stock_detallado', return_value=self.datos_stock()):
            stocks.mostrar_stocks(self.raiz)
        frame = self.raiz._pantalla_stocks
        self.assertEqual(frame.tarea[0], 1000)
        evento = type('Evento', (), {'widget': frame})()
        frame.eventos['<Destroy>'](evento)
        self.assertEqual(frame.cancelado, 'temporizador-falso')

    def test_stocks_ciclo_no_consulta_dos_veces_en_un_minuto(self):
        with patch.object(stocks, 'consultar_stock_detallado', return_value=self.datos_stock()) as consulta:
            stocks.mostrar_stocks(self.raiz)
            frame = self.raiz._pantalla_stocks
            frame.tarea[1]()
        self.assertEqual(consulta.call_count, 1)

    def test_panel_vencimientos_muestra_alertas_y_dias_restantes(self):
        hoy = date(2026, 11, 13)
        datos = {'proximas': [
            {'ID': 1, 'GRUPO': 'A', 'RH': '+', 'FECHA_VENCIMIENTO': hoy.isoformat()},
            {'ID': 2, 'GRUPO': 'B', 'RH': '-', 'FECHA_VENCIMIENTO': (hoy + timedelta(days=1)).isoformat()},
            {'ID': 3, 'GRUPO': 'O', 'RH': '+', 'FECHA_VENCIMIENTO': (hoy + timedelta(days=5)).isoformat()},
        ]}
        with patch.object(panel_vencimientos, 'consultar_resumen', return_value=datos), \
             patch.object(panel_vencimientos, 'fecha_actual', return_value=hoy):
            panel_vencimientos.mostrar_panel_vencimientos(self.raiz)
        for fragmento in ('Unidad #1', 'Unidad #2', 'Unidad #3',
                          'Vence hoy', 'Vence mañana', 'En 5 días',
                          'Tipo de sangre: A+'):
            self.assertTrue(self.texto_contiene(fragmento), fragmento)

    def test_panel_vencimientos_sin_alertas(self):
        with patch.object(panel_vencimientos, 'consultar_resumen', return_value={'proximas': []}):
            panel_vencimientos.mostrar_panel_vencimientos(self.raiz)
        self.assertTrue(self.texto_contiene('No hay unidades próximas a expirar'))

    def test_panel_vencimientos_muestra_error_y_permita_reintentar(self):
        with patch.object(panel_vencimientos, 'consultar_resumen', side_effect=[
            sqlite3.OperationalError('sin BD'), {'proximas': []}]) as consulta:
            panel_vencimientos.mostrar_panel_vencimientos(self.raiz)
            self.assertTrue(self.texto_contiene('No se pudieron consultar los vencimientos'))
            self.boton('Actualizar')()
            self.assertTrue(self.texto_contiene('No hay unidades próximas a expirar'))
        self.assertEqual(consulta.call_count, 2)

    def test_panel_refrescar_no_duplica_alertas(self):
        datos = {'proximas': [{'ID': 4, 'GRUPO': 'AB', 'RH': '-',
                                'FECHA_VENCIMIENTO': '2026-11-18'}]}
        with patch.object(panel_vencimientos, 'consultar_resumen', return_value=datos), \
             patch.object(panel_vencimientos, 'fecha_actual', return_value=date(2026, 11, 13)):
            panel = panel_vencimientos.mostrar_panel_vencimientos(self.raiz)
            self.boton('Actualizar')()
        # Las alertas antiguas deben estar fuera del árbol activo.
        def descendientes(c):
            return [h2 for h in c.winfo_children() for h2 in [h] + descendientes(h)]
        self.assertEqual(sum(c.opciones.get('text') == 'Unidad #4' for c in descendientes(panel)), 1)

    def test_panel_temporizador_y_cancelacion(self):
        with patch.object(panel_vencimientos, 'consultar_resumen', return_value={'proximas': []}):
            panel = panel_vencimientos.mostrar_panel_vencimientos(self.raiz)
        self.assertEqual(panel.tarea[0], 1000)
        panel.eventos['<Destroy>'](type('Evento', (), {'widget': panel})())
        self.assertEqual(panel.cancelado, 'temporizador-falso')

    def test_panel_ciclo_no_duplica_consulta_mismo_minuto(self):
        with patch.object(panel_vencimientos, 'consultar_resumen', return_value={'proximas': []}) as consulta:
            panel = panel_vencimientos.mostrar_panel_vencimientos(self.raiz)
            panel.tarea[1]()
        self.assertEqual(consulta.call_count, 1)

if __name__ == '__main__':
    unittest.main()