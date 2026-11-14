import sqlite3
import tempfile
import unittest
from contextlib import closing
from datetime import date, datetime, timezone
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

    def place(self, **opciones):
        pass

    def grid(self, **opciones):
        pass

    def pack(self, **opciones):
        pass

    def configure(self, **opciones):
        self.opciones.update(opciones)

    def get(self):
        return self.valor

class IntegracionH5H6Test(unittest.TestCase):
    def setUp(self):
        # Crear una base de datos temporal para no modificar la real
        temporal = tempfile.TemporaryDirectory()
        self.addCleanup(temporal.cleanup)

        self.ruta = Path(temporal.name) / "integracion.db"
        inicializar_base(self.ruta)
        # crear un donante apto y un enfermero de prueba
        with closing(sqlite3.connect(self.ruta)) as conexion, conexion:

            conexion.execute("""
                INSERT INTO DONANTES (
                    ID, NOMBRE, APELLIDO, EDAD, SEXO,
                    GRUPO_SANGUINEO, FACTOR_RH, PESO,
                    EMAIL, ELEGIBLE, FECHA_DE_NACIMIENTO
                )
                VALUES (
                    1, 'Prueba', 'Donante', 30, 'Masculino',
                    'AB', '-', 70, 'prueba@example.invalid',
                    ?, '1996-01-01'
                )
            """, (e.APTO,))

            conexion.execute("""
                INSERT INTO PERSONAL (
                    ID_EMPLEADO, NOMBRE, ROL
                )
                VALUES (
                    1, 'Enfermero Prueba', 'Enfermero'
                )
            """)
        #evitar usar la base real y fijar la fecha del test
        cambios = {
            "RUTA_BD": self.ruta,
            "fecha_actual": lambda: date(2026, 11, 11),}
        for parche in (
            patch.multiple(pantalla, **cambios),
            patch.multiple(
                pantalla.ctk,
                CTkFrame=Control,
                CTkLabel=Control,
                CTkEntry=Control,
                CTkButton=Control
            ),
        ):
            parche.start()
            self.addCleanup(parche.stop)

        Control.creados = []

        self.ahora = datetime(
            2026, 11, 11, 15,
            tzinfo=timezone.utc
        )

    def registrar(self):
        #simular el formulario de registro de donaciones
        pantalla.mostrar_adonacion(None, "Enfermero", 1)
        entradas = [
            c for c in Control.creados
            if "placeholder_text" in c.opciones
        ]
        #ingresar ID de donante y cantidad de sangre
        entradas[0].valor = "1"
        entradas[1].valor = "450"

        #buscar el botón de registro y simular un clic
        boton = next(
            c for c in Control.creados
            if c.opciones.get("text") == "Ingresar donacion"
        )

        boton.opciones["command"]()

    def test_extraccion_conserva_datos_h5_y_vencimiento_estado_h6(self):
        #registrar una donación mediante el formulario
        self.registrar()

        #comprobar que se guardó correctamente en SQLite
        with closing(sqlite3.connect(self.ruta)) as conexion:
            fila = conexion.execute("""
                SELECT
                    DONANTE,
                    CANTIDAD,
                    FECHA_EXTRACCIÓN,
                    FECHA_VENCIMIENTO,
                    TIPO_SANGRE,
                    FACTOR_RH,
                    ESTADO
                FROM DONACIONES
            """).fetchone()

        self.assertEqual(
            fila,
            (
                1,
                450,
                "2026-11-11",
                "2026-12-01",
                "AB",
                "-",
                v.DISPONIBLE
            )
        )

        #comprobar la búsqueda de sangre
        self.assertEqual(
            e.buscar_sangre("AB", "-", self.ruta),
            [(1, 450, "AB", "-", "Refrigerador 3")]
        )

        #comprobar el resumen de stock
        resumen = v.consultar_resumen(
            self.ruta,
            ahora=self.ahora
        )

        self.assertEqual(resumen["unidades"], 1)
        self.assertAlmostEqual(resumen["litros"], 0.45)

        #comprobar el stock detallado
        detalle = v.consultar_stock_detallado(
            self.ruta,
            ahora=self.ahora
        )

        total = next(
            t for t in detalle["totales"]
            if (t["grupo"], t["rh"]) == ("AB", "-")
        )

        self.assertAlmostEqual(total["litros"], 0.45)

        self.assertEqual(
            detalle["unidades"][0]["CANTIDAD"],
            450
        )

        #comprobar que la donación cambia a vencida
        v.actualizar_vencimientos(
            self.ruta,
            ahora=datetime(
                2026, 12, 2, 15,
                tzinfo=timezone.utc
            )
        )

        with closing(sqlite3.connect(self.ruta)) as conexion:
            estado = conexion.execute("""
                SELECT ESTADO
                FROM DONACIONES
            """).fetchone()[0]

            self.assertEqual(estado, v.VENCIDA)

    def test_donante_inhabilitado_no_genera_unidad(self):
        #inhabilitar al donante antes de intentar registrar
        with closing(sqlite3.connect(self.ruta)) as conexion, conexion:
            conexion.execute("""
                UPDATE DONANTES
                SET ELEGIBLE = ?
                WHERE ID = 1
            """, (e.PERMANENTE,))

        #intentar registrar una donación
        self.registrar()

        #comprobar que no se creó ninguna donación
        with closing(sqlite3.connect(self.ruta)) as conexion:
            cantidad = conexion.execute("""
                SELECT COUNT(*)
                FROM DONACIONES
            """).fetchone()[0]

            self.assertEqual(cantidad, 0)

    def test_entrevistador_no_abre_registro_de_extracciones(self):
        #comprobar que un entrevistador no puede registrar donaciones
        with patch("tkinter.messagebox.showerror") as error:
            pantalla.mostrar_adonacion(
                None,
                "Entrevistador",
                1
            )

        error.assert_called_once()
        #no debe haberse creado ningún control del formulario
        self.assertEqual(Control.creados, [])


if __name__ == "__main__":
    unittest.main()
