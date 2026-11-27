import unittest
import tempfile
from pathlib import Path
from datos.basededatos import inicializar_base
from servicios.vencimientos import consultar_stock_detallado

class TestStockHospitales(unittest.TestCase):
    def setUp(self):
        temporal = tempfile.TemporaryDirectory()
        self.addCleanup(temporal.cleanup)

        self.ruta = Path(temporal.name) / "stock_prueba.db"
        inicializar_base(self.ruta)

    # TEST 1: Verificar los ocho tipos sanguíneos
    def test_ocho_tipos_sanguineos(self):
        datos = consultar_stock_detallado(ruta=self.ruta)
        tipos_esperados = {("A", "+"), ("A", "-"),("B", "+"), ("B", "-"),("AB", "+"), ("AB", "-"),("O", "+"), ("O", "-")}

        tipos_obtenidos = {(total["grupo"], total["rh"])for total in datos["totales"]}

        self.assertTrue(tipos_esperados.issubset(tipos_obtenidos))

    # TEST 2: Verificar las cantidades disponibles
    def test_cantidades_disponibles(self):
        datos = consultar_stock_detallado(ruta=self.ruta)
        for total in datos["totales"]:
            cantidad = total["unidades"]
            self.assertIsInstance(cantidad, int)
            self.assertGreaterEqual(cantidad, 0)

if __name__ == "__main__":
    unittest.main()