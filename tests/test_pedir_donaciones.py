import sqlite3
import unittest
from unittest.mock import Mock, patch
from pantallas import pedir_donaciones as pantalla
from servicios import enviar_correos as correo_servicio

class ControlSimulado:
    """Imita los métodos de CustomTkinter que utiliza la pantalla HU03."""
    creados = []
    def __init__(self, padre=None, **opciones):
        self.padre = padre
        self.opciones = dict(opciones)
        self.valor = opciones.get('text', '')
        self.hijos = []
        self.destruido = False
        self.tareas = {}
        self.siguiente_tarea = 0
        if isinstance(padre, ControlSimulado):
            padre.hijos.append(self)
        self.creados.append(self)

    def place(self, **opciones):
        pass

    def grid(self, **opciones):
        pass

    def pack(self, **opciones):
        pass

    def grid_columnconfigure(self, *args, **kwargs):
        pass

    def configure(self, **opciones):
        self.opciones.update(opciones)

    def get(self):
        return self.valor

    def set(self, valor):
        self.valor = valor

    def winfo_children(self):
        return [h for h in self.hijos if not h.destruido]

    def destroy(self):
        self.destruido = True
        if isinstance(self.padre, ControlSimulado) and self in self.padre.hijos:
            self.padre.hijos.remove(self)

    def after(self, milisegundos, callback):
        self.siguiente_tarea += 1
        tarea = f'tarea-{self.siguiente_tarea}'
        self.tareas[tarea] = callback
        return tarea

    def after_cancel(self, tarea):
        self.tareas.pop(tarea, None)

    def winfo_toplevel(self):
        return self

    def winfo_rootx(self):
        return 0

    def winfo_rooty(self):
        return 0

    def winfo_width(self):
        return 1000

    def winfo_height(self):
        return 800

    def title(self, texto):
        self.titulo = texto

    def update_idletasks(self):
        pass

    def geometry(self, texto):
        self.geometria = texto

    def transient(self, padre):
        pass

    def grab_set(self):
        pass

class PedirDonacionesTest(unittest.TestCase):
    def setUp(self):
        ControlSimulado.creados = []
        self.buscar = patch.object(pantalla, 'buscar_candidatos').start()
        self.revalidar = patch.object(pantalla, 'candidato_vigente').start()
        self.enviar = patch.object(pantalla, 'enviar_correo').start()
        self.addCleanup(patch.stopall)
        self.buscar.return_value = []
        self.revalidar.side_effect = lambda did, grupo, rh: (did, f'd{did}@example.invalid')

        controles = patch.multiple(
            pantalla.ctk,
            CTkFrame=ControlSimulado,
            CTkScrollableFrame=ControlSimulado,
            CTkLabel=ControlSimulado,
            CTkOptionMenu=ControlSimulado,
            CTkButton=ControlSimulado,
            CTkToplevel=ControlSimulado,
        )
        controles.start()
        self.addCleanup(controles.stop)
        pantalla.mostrar_pedir_donaciones(None)

        menus = [c for c in ControlSimulado.creados if 'values' in c.opciones]
        self.grupo, self.rh = menus
        self.boton_buscar = self.control('Buscar')
        self.boton_limpiar = self.control('Limpiar filtros')
        self.boton_correo = self.control('Enviar correo')
        self.mensaje = next(c for c in ControlSimulado.creados
                            if c.opciones.get('text_color') == '#DC2626'
                            and c.opciones.get('text') == '')
        self.total = self.control('Total de donantes aptos: 0')

    def control(self, texto):
        return next(c for c in ControlSimulado.creados if c.opciones.get('text') == texto)

    def pulsar(self, boton):
        boton.opciones['command']()

    def seleccionar(self, grupo='A', rh='Positivo'):
        self.grupo.set(grupo)
        self.rh.set(rh)

    def buscar_resultados(self, filas=((1, 'A', '+', 'uno@example.invalid'),)):
        self.buscar.return_value = list(filas)
        self.seleccionar()
        self.pulsar(self.boton_buscar)

    def confirmar(self):
        self.pulsar(self.boton_correo)
        ventana = next(c for c in ControlSimulado.creados
                       if getattr(c, 'titulo', None) == 'Confirmar envío')
        confirmar = self.control('Confirmar envío')
        self.pulsar(confirmar)
        return ventana

    def test_inicialmente_no_permite_enviar_correo(self):
        self.assertEqual(self.boton_correo.opciones['state'], 'disabled')
        self.assertEqual(self.total.opciones['text'], 'Total de donantes aptos: 0')

    def test_exige_ambos_filtros(self):
        self.pulsar(self.boton_buscar)
        self.buscar.assert_not_called()
        self.assertIn('seleccione ambos filtros', self.mensaje.opciones['text'])
        self.assertEqual(self.boton_correo.opciones['state'], 'disabled')

    def test_busca_grupo_rh_positivo_y_muestra_contador(self):
        self.buscar_resultados()
        self.buscar.assert_called_once_with('A', '+')
        self.assertEqual(self.total.opciones['text'], 'Total de donantes aptos: 1')
        self.assertEqual(self.boton_correo.opciones['state'], 'normal')
        self.assertFalse(any(c.opciones.get('text') == 'uno@example.invalid'
                             for c in ControlSimulado.creados))

    def test_rh_negativo_se_traduce_a_signo_menos(self):
        self.seleccionar('O', 'Negativo')
        self.pulsar(self.boton_buscar)
        self.buscar.assert_called_once_with('O', '-')

    def test_sin_donantes_no_habilita_envio(self):
        self.buscar_resultados(())
        self.assertEqual(self.boton_correo.opciones['state'], 'disabled')
        self.assertIn('No hay donantes aptos', self.mensaje.opciones['text'])

    def test_error_sql_al_buscar_muestra_mensaje(self):
        self.buscar.side_effect = sqlite3.OperationalError('error simulado')
        self.seleccionar()
        self.pulsar(self.boton_buscar)
        self.assertIn('No se pudo consultar', self.mensaje.opciones['text'])
        self.assertEqual(self.boton_correo.opciones['state'], 'disabled')

    def test_cambiar_filtro_invalida_resultados(self):
        self.buscar_resultados()
        self.grupo.set('B')
        self.grupo.opciones['command']('B')
        self.assertEqual(self.boton_correo.opciones['state'], 'disabled')
        self.assertEqual(self.total.opciones['text'], 'Total de donantes aptos: 0')

    def test_limpiar_filtros_borra_resultados(self):
        self.buscar_resultados()
        self.pulsar(self.boton_limpiar)
        self.assertEqual(self.grupo.get(), 'Seleccione')
        self.assertEqual(self.rh.get(), 'Seleccione')
        self.assertEqual(self.total.opciones['text'], 'Total de donantes aptos: 0')
        self.assertEqual(self.boton_correo.opciones['state'], 'disabled')

    def test_sin_resultados_no_envia_correo(self):
        self.pulsar(self.boton_correo)
        self.enviar.assert_not_called()
        self.assertIn('No hay donantes', self.mensaje.opciones['text'])

    def test_no_envia_si_cambiaron_filtros(self):
        self.buscar_resultados()
        self.rh.set('Negativo')  # Simula un cambio no notificado por el control.
        self.pulsar(self.boton_correo)
        self.enviar.assert_not_called()
        self.assertIn('Los filtros cambiaron', self.mensaje.opciones['text'])

    def test_revalida_cada_donante_antes_de_confirmar(self):
        self.buscar_resultados(((1, 'A', '+', 'uno@example.invalid'),
                                (2, 'A', '+', 'dos@example.invalid')))
        self.revalidar.side_effect = [(1, 'uno@example.invalid'), None]
        self.pulsar(self.boton_correo)
        self.assertEqual(self.revalidar.call_count, 2)
        self.enviar.assert_not_called()
        self.assertEqual(self.boton_correo.opciones['state'], 'disabled')
        self.assertIn('elegibilidad', self.mensaje.opciones['text'])

    def test_error_sql_en_revalidacion_impide_envio(self):
        self.buscar_resultados()
        self.revalidar.side_effect = sqlite3.OperationalError('error simulado')
        self.pulsar(self.boton_correo)
        self.enviar.assert_not_called()
        self.assertIn('No se pudo verificar', self.mensaje.opciones['text'])

    def test_cancelar_confirmacion_no_envia(self):
        self.buscar_resultados()
        self.pulsar(self.boton_correo)
        self.pulsar(self.control('Cancelar'))
        self.enviar.assert_not_called()

    def test_confirmar_envia_una_vez_a_cada_destinatario(self):
        self.buscar_resultados(((1, 'A', '+', 'uno@example.invalid'),
                                (2, 'A', '+', 'dos@example.invalid')))
        self.revalidar.side_effect = [(1, 'uno@example.invalid'),
                                      (2, 'dos@example.invalid')]
        self.confirmar()
        self.assertEqual(self.enviar.call_count, 2)
        self.assertEqual([c.args[0] for c in self.enviar.call_args_list],
                         ['uno@example.invalid', 'dos@example.invalid'])
        self.assertIn('Correos aceptados: 2. Fallidos: 0', self.mensaje.opciones['text'])
        self.assertEqual(self.boton_correo.opciones['state'], 'disabled')

    def test_un_error_de_envio_no_detiene_los_demas(self):
        self.buscar_resultados(((1, 'A', '+', 'uno@example.invalid'),
                                (2, 'A', '+', 'dos@example.invalid')))
        self.revalidar.side_effect = [(1, 'uno@example.invalid'),
                                      (2, 'dos@example.invalid')]
        self.enviar.side_effect = [OSError('SMTP simulado'), None]
        self.confirmar()
        self.assertEqual(self.enviar.call_count, 2)
        self.assertIn('Correos aceptados: 1. Fallidos: 1', self.mensaje.opciones['text'])

class EnviarCorreosTest(unittest.TestCase):
    def test_construye_mensaje_y_usa_smtp_simulado(self):
        with patch.object(correo_servicio, 'correo', 'pruebas@example.invalid'), \
             patch.object(correo_servicio, 'contrasena', 'clave-falsa'), \
             patch.object(correo_servicio.smtplib, 'SMTP_SSL') as smtp:
            correo_servicio.enviar_correo('destinatario@example.invalid')

        smtp.assert_called_once_with('smtp.gmail.com', 465)
        servidor = smtp.return_value.__enter__.return_value
        servidor.login.assert_called_once_with('pruebas@example.invalid', 'clave-falsa')
        mensaje = servidor.send_message.call_args.args[0]
        self.assertEqual(mensaje['From'], 'pruebas@example.invalid')
        self.assertEqual(mensaje['To'], 'destinatario@example.invalid')
        self.assertIn('Banco de Sangre', mensaje['Subject'])
        self.assertIn('Banco de Sangre', mensaje.get_content())

    def test_error_de_servidor_se_propaga_sin_envios_reales(self):
        with patch.object(correo_servicio, 'correo', 'pruebas@example.invalid'), \
             patch.object(correo_servicio, 'contrasena', 'clave-falsa'), \
             patch.object(correo_servicio.smtplib, 'SMTP_SSL') as smtp:
            smtp.return_value.__enter__.return_value.login.side_effect = OSError('SMTP simulado')
            with self.assertRaises(OSError):
                correo_servicio.enviar_correo('destinatario@example.invalid')
            smtp.return_value.__enter__.return_value.send_message.assert_not_called()

if __name__ == '__main__':
    unittest.main()