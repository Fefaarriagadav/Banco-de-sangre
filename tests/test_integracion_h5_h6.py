import sqlite3
import tempfile
import unittest
from contextlib import closing
from datetime import date, datetime, timezone
from functools import partial
from pathlib import Path
from unittest.mock import patch

from datos.basededatos import inicializar_base
from pantallas import agregar_donacion as pantalla
from servicios import elegibilidad as e
from servicios import vencimientos as v


class Control:
    """Controles mínimos para ejecutar el formulario sin abrir ventanas."""

    creados = []

    def __init__(self, padre=None, **opciones):
        self.opciones = opciones
        self.valor = ""
        self.creados.append(self)

    def place(self, **opciones): pass
    def grid(self, **opciones): pass
    def pack(self, **opciones): pass
    def configure(self, **opciones): self.opciones.update(opciones)
    def get(self): return self.valor


class IntegracionH5H6Test(unittest.TestCase):
    def setUp(self):
        temporal = tempfile.TemporaryDirectory()
        self.addCleanup(temporal.cleanup)
        self.ruta = Path(temporal.name) / "integracion.db"
        inicializar_base(self.ruta)
        with closing(sqlite3.connect(self.ruta)) as conexion, conexion:
            conexion.execute("""INSERT INTO DONANTES (
                ID, NOMBRE, APELLIDO, EDAD, SEXO, GRUPO_SANGUINEO,
                FACTOR_RH, PESO, EMAIL, ELEGIBLE, FECHA_DE_NACIMIENTO
            ) VALUES (1,'Prueba','Donante',30,'Masculino','AB','-',70,
                      'prueba@example.invalid',?,'1996-01-01')""", (e.APTO,))

        cambios = {
            "RUTA_BD": self.ruta,
            "consultar_donante": partial(e.consultar_donante, ruta=self.ruta),
            "consultar_donanteApto": partial(e.consultar_donanteApto, ruta=self.ruta),
            "consultar_donanteSangre": partial(e.consultar_donanteSangre, ruta=self.ruta),
            "fecha_actual": lambda: date(2026, 11, 11),
        }
        for parche in (
            patch.multiple(pantalla, **cambios),
            patch.multiple(pantalla.ctk, CTkFrame=Control, CTkLabel=Control,
                           CTkEntry=Control, CTkButton=Control),
        ):
            parche.start()
            self.addCleanup(parche.stop)
        Control.creados = []
        self.ahora = datetime(2026, 11, 11, 15, tzinfo=timezone.utc)

    def registrar(self):
        pantalla.mostrar_adonacion(None, "Enfermero")
        entradas = [c for c in Control.creados if "placeholder_text" in c.opciones]
        entradas[0].valor = "1"
        entradas[1].valor = "450.5"
        boton = next(c for c in Control.creados if c.opciones.get("text") == "Ingresar donacion")
        boton.opciones["command"]()

    def test_extraccion_conserva_datos_h5_y_vencimiento_estado_h6(self):
        self.registrar()
        with closing(sqlite3.connect(self.ruta)) as conexion:
            fila = conexion.execute("""SELECT DONANTE, CANTIDAD,
                FECHA_EXTRACCIÓN, FECHA_VENCIMIENTO, TIPO_SANGRE,
                FACTOR_RH, ESTADO FROM DONACIONES""").fetchone()
        self.assertEqual(fila, (1, 450.5, "2026-11-11", "2026-12-01", "AB", "-", v.DISPONIBLE))
        self.assertEqual(e.buscar_sangre("AB", "-", self.ruta), [(1, 450.5, "AB", "-")])

        resumen = v.consultar_resumen(self.ruta, ahora=self.ahora)
        self.assertEqual(resumen["unidades"], 1)
        self.assertAlmostEqual(resumen["litros"], 0.4505)
        detalle = v.consultar_stock_detallado(self.ruta, ahora=self.ahora)
        total = next(t for t in detalle["totales"] if (t["grupo"], t["rh"]) == ("AB", "-"))
        self.assertAlmostEqual(total["litros"], 0.4505)
        self.assertEqual(detalle["unidades"][0]["CANTIDAD"], 450.5)

        v.actualizar_vencimientos(self.ruta, ahora=datetime(2026, 12, 2, 15, tzinfo=timezone.utc))
        with closing(sqlite3.connect(self.ruta)) as conexion:
            self.assertEqual(conexion.execute("SELECT ESTADO FROM DONACIONES").fetchone()[0], v.VENCIDA)

    def test_donante_inhabilitado_no_genera_unidad(self):
        with closing(sqlite3.connect(self.ruta)) as conexion, conexion:
            conexion.execute("UPDATE DONANTES SET ELEGIBLE=? WHERE ID=1", (e.PERMANENTE,))
        self.registrar()
        with closing(sqlite3.connect(self.ruta)) as conexion:
            self.assertEqual(conexion.execute("SELECT COUNT(*) FROM DONACIONES").fetchone()[0], 0)

    def test_entrevistador_no_abre_registro_de_extracciones(self):
        with patch("tkinter.messagebox.showerror") as error:
            pantalla.mostrar_adonacion(None, "Entrevistador")
        error.assert_called_once()
        self.assertEqual(Control.creados, [])
