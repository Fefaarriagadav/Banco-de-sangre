import unittest
from servicios.vencimientos import consultar_stock_detallado

class TestStockHospitales(unittest.TestCase):
    # TEST 1: Verificar los ocho tipos sanguíneos
    def test_ocho_tipos_sanguineos(self):
        datos = consultar_stock_detallado()
        tipos_esperados = {("A", "+"), ("A", "-"),("B", "+"), ("B", "-"),("AB", "+"), ("AB", "-"),("O", "+"), ("O", "-")}

        tipos_obtenidos = {(total["grupo"], total["rh"])for total in datos["totales"]}

        self.assertTrue(tipos_esperados.issubset(tipos_obtenidos))

    # TEST 2: Verificar las cantidades disponibles
    def test_cantidades_disponibles(self):
        datos = consultar_stock_detallado()
        for total in datos["totales"]:
            cantidad = total["unidades"]
            self.assertIsInstance(cantidad, int)
            self.assertGreaterEqual(cantidad, 0)

if __name__ == "__main__":
    unittest.main()