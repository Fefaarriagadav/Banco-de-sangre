import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch
from datos.basededatos import inicializar_base
from pantallas import agregar_donante as pantalla

class ControlFalso:
    creados = []
    def __init__(self, padre=None, **opciones):
        self.opciones = dict(opciones)
        self.valor = opciones.get('placeholder_text', '')
        self.creados.append(self)

    def place(self, **opciones): pass
    def grid(self, **opciones): pass
    def pack(self, **opciones): pass
    def set(self, valor): self.valor = valor
    def get(self): return self.valor
    def configure(self, **opciones): self.opciones.update(opciones)

class RegistroDonantesTest(unittest.TestCase):
    def setUp(self):
        temporal = tempfile.TemporaryDirectory()
        self.addCleanup(temporal.cleanup)
        self.ruta = Path(temporal.name) / 'donantes_test.db'
        inicializar_base(self.ruta)
        ControlFalso.creados = []
        for parche in (
            patch.object(pantalla, 'RUTA_BD', self.ruta),
            patch.multiple(pantalla.ctk, CTkFrame=ControlFalso, CTkLabel=ControlFalso,
                           CTkEntry=ControlFalso, CTkOptionMenu=ControlFalso,
                           CTkButton=ControlFalso),
        ):
            parche.start()
            self.addCleanup(parche.stop)
        pantalla.mostrar_registro(None, 'Entrevistador')
        self.valores_validos()

    def entrada(self, texto):
        return next(c for c in ControlFalso.creados
                    if c.opciones.get('placeholder_text') == texto)

    def entrada_email(self):
        return next(c for c in ControlFalso.creados
                    if c.opciones.get('placeholder_text', '').startswith('Ingrese email'))

    def opciones(self, valores):
        return next(c for c in ControlFalso.creados if c.opciones.get('values') == valores)

    def mensaje(self):
        return next(c for c in ControlFalso.creados
                    if c.opciones.get('text_color') == 'red' and c.opciones.get('text') == '')

    def valores_validos(self):
        self.entrada('Ingrese el nombre').valor = ' Ana '
        self.entrada('Ingrese el apellido').valor = ' Pérez '
        self.entrada('Ingrese el peso').valor = '65.5'
        self.entrada_email().valor = 'ana@example.com'
        self.entrada('DD-MM-AAAA').valor = ''
        self.opciones([str(i) for i in range(1, 32)]).set('15')
        self.opciones(['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
                      'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']).set('Marzo')
        self.opciones([str(i) for i in range(1920, 2027)]).set('2000')
        self.opciones(['A', 'B', 'AB', 'O']).set('AB')
        self.opciones(['Positivo', 'Negativo']).set('Negativo')
        self.opciones(['Femenino', 'Masculino']).set('Femenino')
        self.opciones(['Donante apto', 'Donante NO apto temporalmente',
                      'Donante NO apto PERMANENTEMENTE']).set('Donante apto')

    def registrar(self):
        boton = next(c for c in ControlFalso.creados
                     if c.opciones.get('text') == 'Ingresar donante')
        boton.opciones['command']()

    def filas(self):
        with closing(sqlite3.connect(self.ruta)) as conexion:
            return conexion.execute('SELECT * FROM DONANTES ORDER BY ID').fetchall()

    def test_registro_valido_persiste_datos(self):
        self.registrar()
        with closing(sqlite3.connect(self.ruta)) as conexion:
            fila = conexion.execute('''SELECT NOMBRE, APELLIDO, SEXO, GRUPO_SANGUINEO,
                        FACTOR_RH, PESO, EMAIL, ELEGIBLE, FECHA_DE_NACIMIENTO
                        FROM DONANTES''').fetchone()
        self.assertEqual(fila, ('Ana', 'Pérez', 'Femenino', 'AB', '-', 65.5,
                                'ana@example.com', 'Donante apto', '2000-03-15'))

    def test_registro_asigna_id_automatico_en_base(self):
        self.registrar()
        with closing(sqlite3.connect(self.ruta)) as conexion:
            fila = conexion.execute('SELECT ID FROM DONANTES').fetchone()
            estructura = conexion.execute('PRAGMA table_info(DONANTES)').fetchall()
        self.assertIsInstance(fila[0], int)
        self.assertGreater(fila[0], 0)
        self.assertEqual(next(col[5] for col in estructura if col[1] == 'ID'), 1)

    def test_rechaza_nombre_y_apellido_vacios(self):
        for campo in ('Ingrese el nombre', 'Ingrese el apellido'):
            with self.subTest(campo=campo):
                self.entrada(campo).valor = '   '
                self.registrar()
                self.assertEqual(self.filas(), [])
                self.valores_validos()

    def test_rechaza_fecha_incompleta_o_inexistente(self):
        self.opciones([str(i) for i in range(1, 32)]).set('Seleccione')
        self.registrar()
        self.assertEqual(self.filas(), [])
        self.valores_validos()
        self.opciones([str(i) for i in range(1, 32)]).set('31')
        self.opciones(['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
                      'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']).set('Febrero')
        self.registrar()
        self.assertEqual(self.filas(), [])

    def test_rechaza_peso_no_numerico_y_no_positivo(self):
        for valor in ('', 'abc', '0', '-5', 'nan', 'inf'):
            with self.subTest(peso=valor):
                self.entrada('Ingrese el peso').valor = valor
                self.registrar()
                self.assertEqual(self.filas(), [])
                self.valores_validos()

    def test_rechaza_email_invalido(self):
        for correo in ('', 'sin-arroba', 'ana@', 'ana@dominio'):
            with self.subTest(correo=correo):
                self.entrada_email().valor = correo
                self.registrar()
                self.assertEqual(self.filas(), [])
                self.valores_validos()

    def test_rechaza_sangre_rh_sexo_y_elegibilidad_sin_seleccionar(self):
        campos = [['A', 'B', 'AB', 'O'], ['Positivo', 'Negativo'],
                  ['Femenino', 'Masculino'],
                  ['Donante apto', 'Donante NO apto temporalmente',
                   'Donante NO apto PERMANENTEMENTE']]
        for opciones in campos:
            with self.subTest(opciones=opciones):
                self.opciones(opciones).set('Seleccione')
                self.registrar()
                self.assertEqual(self.filas(), [])
                self.valores_validos()

    def test_fecha_ultima_donacion_invalida_no_inserta(self):
        for fecha in ('fecha mala', '31-02-2026', '01-01-1900'):
            with self.subTest(fecha=fecha):
                self.entrada('DD-MM-AAAA').valor = fecha
                self.registrar()
                self.assertEqual(self.filas(), [])
                self.valores_validos()

    def test_fecha_ultima_donacion_valida_se_guarda(self):
        self.entrada('DD-MM-AAAA').valor = '01-02-2026'
        self.registrar()
        with closing(sqlite3.connect(self.ruta)) as conexion:
            ultima = conexion.execute('SELECT FECHA_ULTIMA_DONACION FROM DONANTES').fetchone()[0]
        self.assertEqual(ultima, '2026-02-01')

    def test_rol_no_autorizado_no_abre_formulario(self):
        ControlFalso.creados = []
        with patch('tkinter.messagebox.showerror') as mensaje:
            pantalla.mostrar_registro(None, 'Enfermero')
        mensaje.assert_called_once()
        self.assertEqual(ControlFalso.creados, [])
        self.assertEqual(self.filas(), [])

if __name__ == '__main__':
    unittest.main()