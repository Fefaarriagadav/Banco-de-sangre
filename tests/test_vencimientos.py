import sqlite3
import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import patch
from contextlib import closing

from datos.basededatos import inicializar_base
from servicios import vencimientos as v


class VencimientosTest(unittest.TestCase):
    def setUp(self):
        self.temporal = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporal.cleanup)

        self.ruta = Path(self.temporal.name) / "prueba.db"
        inicializar_base(self.ruta)

        # 11 de noviembre, mediodía en Chile.
        self.ahora = datetime(
            2026, 11, 11, 15, 0, tzinfo=timezone.utc
        )

    def insertar_unidad(
        self,
        vencimiento="2026-11-18",
        estado=v.DISPONIBLE,
        extraccion="2026-11-01",
        cantidad=0.45,
    ):
        with closing(sqlite3.connect(self.ruta)) as conexion, conexion:
            cursor = conexion.execute(
                """
                INSERT INTO DONACIONES (
                    FECHA_EXTRACCIÓN,
                    FECHA_VENCIMIENTO,
                    CANTIDAD,
                    ESTADO
                )
                VALUES (?, ?, ?, ?)
                """,
                (extraccion, vencimiento, cantidad, estado),
            )
            return cursor.lastrowid

    def consultar_unidad(self, unidad_id):
        with closing(sqlite3.connect(self.ruta)) as conexion, conexion:
            return conexion.execute(
                """
                SELECT FECHA_VENCIMIENTO, ESTADO
                FROM DONACIONES
                WHERE ID = ?
                """,
                (unidad_id,),
            ).fetchone()

    def test_guardar_vencimiento_valido(self):
        unidad_id = self.insertar_unidad()

        v.guardar_vencimiento(
            unidad_id,
            "20-11-2026",
            ruta=self.ruta,
            ahora=self.ahora,
        )

        self.assertEqual(
            self.consultar_unidad(unidad_id),
            ("2026-11-20", v.DISPONIBLE),
        )

    def test_fechas_invalidas_conservan_valor_anterior(self):
        unidad_id = self.insertar_unidad()
        anterior = self.consultar_unidad(unidad_id)

        fechas_invalidas = [
            None,
            "",
            " ",
            "2026-11-20",
            "31-02-2026",
            "1-12-2026",
            "texto",
            "31-10-2026",  # Anterior a la extracción.
        ]

        for fecha in fechas_invalidas:
            with self.subTest(fecha=fecha):
                with self.assertRaises(ValueError):
                    v.guardar_vencimiento(
                        unidad_id,
                        fecha,
                        ruta=self.ruta,
                        ahora=self.ahora,
                    )

                self.assertEqual(
                    self.consultar_unidad(unidad_id),
                    anterior,
                )

    def test_rechazar_unidad_inexistente_e_id_invalido(self):
        for unidad_id in (999, 0, -1, "abc", None):
            with self.subTest(unidad_id=unidad_id):
                with self.assertRaises(ValueError):
                    v.guardar_vencimiento(
                        unidad_id,
                        "20-11-2026",
                        ruta=self.ruta,
                        ahora=self.ahora,
                    )

    def test_vencimiento_igual_a_extraccion_es_valido(self):
        unidad_id = self.insertar_unidad(
            extraccion="2026-11-11",
            vencimiento=None,
            estado=v.PENDIENTE,
        )

        v.guardar_vencimiento(
            unidad_id,
            "11-11-2026",
            ruta=self.ruta,
            ahora=self.ahora,
        )

        self.assertEqual(
            self.consultar_unidad(unidad_id),
            ("2026-11-11", v.DISPONIBLE),
        )

    def test_corte_de_vencimiento_a_medianoche_chilena(self):
        unidad_id = self.insertar_unidad("2026-11-11")

        # En noviembre Santiago usa UTC-3:
        # 02:59 UTC = 23:59 del día anterior en Chile.
        antes_del_corte = datetime(
            2026, 11, 12, 2, 59, tzinfo=timezone.utc
        )
        v.actualizar_vencimientos(
            ruta=self.ruta,
            ahora=antes_del_corte,
        )

        self.assertEqual(
            self.consultar_unidad(unidad_id)[1],
            v.DISPONIBLE,
        )

        # 03:00 UTC = 00:00 del día siguiente en Chile.
        al_corte = datetime(
            2026, 11, 12, 3, 0, tzinfo=timezone.utc
        )
        v.actualizar_vencimientos(
            ruta=self.ruta,
            ahora=al_corte,
        )

        self.assertEqual(
            self.consultar_unidad(unidad_id)[1],
            v.VENCIDA,
        )


    def test_unidad_caducada_no_puede_extenderse(self):
        # Todavía figura Disponible, pero su fecha ya pasó.
        unidad_id = self.insertar_unidad("2026-11-10")
        anterior = self.consultar_unidad(unidad_id)

        with self.assertRaises(ValueError):
            v.guardar_vencimiento(
                unidad_id,
                "20-11-2026",
                ruta=self.ruta,
                ahora=self.ahora,
            )

        self.assertEqual(
            self.consultar_unidad(unidad_id),
            anterior,
        )

        v.actualizar_vencimientos(
            ruta=self.ruta,
            ahora=self.ahora,
        )
        self.assertEqual(
            self.consultar_unidad(unidad_id)[1],
            v.VENCIDA,
        )

    def test_estados_terminales_no_se_reactivan(self):
        for estado in (v.USADA, v.DESCARTADA, v.VENCIDA):
            with self.subTest(estado=estado):
                unidad_id = self.insertar_unidad(
                    "2026-11-18",
                    estado=estado,
                )

                with self.assertRaises(ValueError):
                    v.guardar_vencimiento(
                        unidad_id,
                        "20-11-2026",
                        ruta=self.ruta,
                        ahora=self.ahora,
                    )

                v.actualizar_vencimientos(
                    ruta=self.ruta,
                    ahora=self.ahora,
                )

                self.assertEqual(
                    self.consultar_unidad(unidad_id),
                    ("2026-11-18", estado),
                )


    def test_migracion_repetida_conserva_donaciones(self):
        ruta_legada = Path(self.temporal.name) / "legada.db"

        # Simula la tabla de H5 antes de incorporar ESTADO.
        with closing(sqlite3.connect(ruta_legada)) as conexion, conexion:
            conexion.execute(
                """
                CREATE TABLE DONACIONES (
                    ID INTEGER PRIMARY KEY,
                    DONANTE INTEGER,
                    TIPO_SANGRE TEXT,
                    FACTOR_RH TEXT,
                    FECHA_EXTRACCIÓN TEXT,
                    FECHA_VENCIMIENTO TEXT,
                    CANTIDAD REAL,
                    UBICACION TEXT
                )
                """
            )
            conexion.execute(
                """
                INSERT INTO DONACIONES
                VALUES (
                    1, NULL, 'A', '+',
                    '2026-11-01', '2026-11-18',
                    0.45, 'Refrigerador 1'
                )
                """
            )

        inicializar_base(ruta_legada)
        inicializar_base(ruta_legada)

        with closing(sqlite3.connect(ruta_legada)) as conexion, conexion:
            columnas = {
                fila[1]
                for fila in conexion.execute(
                    "PRAGMA table_info(DONACIONES)"
                )
            }
            unidad = conexion.execute(
                """
                SELECT ID, FECHA_VENCIMIENTO, CANTIDAD, UBICACION
                FROM DONACIONES
                """
            ).fetchall()

        self.assertIn("ESTADO", columnas)
        self.assertEqual(
            unidad,
            [(1, "2026-11-18", 0.45, "Refrigerador 1")],
        )

        v.actualizar_vencimientos(
            ruta=ruta_legada,
            ahora=self.ahora,
        )

        with closing(sqlite3.connect(ruta_legada)) as conexion:
            estado = conexion.execute(
                "SELECT ESTADO FROM DONACIONES WHERE ID = 1"
            ).fetchone()[0]

        self.assertEqual(estado, v.DISPONIBLE)

    def test_temporizador_actualiza_al_cambiar_el_dia(self):
        class WidgetSimulado:
            def __init__(self):
                self.callback = None
                self.evento_destruir = None
                self.canceladas = []

            def after(self, intervalo, callback):
                self.callback = callback
                return "tarea-h6"

            def after_cancel(self, tarea):
                self.canceladas.append(tarea)

            def bind(self, evento, callback, add=None):
                self.evento_destruir = callback

        widget = WidgetSimulado()

        with patch.object(
            v,
            "fecha_actual",
            side_effect=[
                date(2026, 11, 11),
                date(2026, 11, 11),
                date(2026, 11, 12),
            ],
        ), patch.object(v, "actualizar_vencimientos") as actualizar:
            v.iniciar_actualizacion(widget, ruta=self.ruta)

            widget.callback()  # Mismo día: no repite.
            widget.callback()  # Día siguiente: actualiza.

            self.assertEqual(actualizar.call_count, 2)

        evento = type("Evento", (), {"widget": widget})()
        widget.evento_destruir(evento)

        self.assertEqual(widget.canceladas, ["tarea-h6"])

    def test_calcular_vencimiento_cambios_de_calendario(self):
        casos = [
            ("2026-11-11", "2026-12-01"),
            ("2026-01-20", "2026-02-09"),
            ("2026-12-20", "2027-01-09"),
            ("2028-02-10", "2028-03-01"),
        ]

        for extraccion, esperado in casos:
            with self.subTest(extraccion=extraccion):
                self.assertEqual(
                    v.calcular_vencimiento(
                        extraccion, vida_util_dias=20
                    ),
                    esperado,
                )

    def test_calcular_vencimiento_rechaza_datos_invalidos(self):
        for fecha in (None, "", "31-02-2026", "2026-02-31"):
            with self.subTest(fecha=fecha):
                with self.assertRaises(ValueError):
                    v.calcular_vencimiento(fecha)

        for dias in (0, -1, 1.5, True, "20"):
            with self.subTest(dias=dias):
                with self.assertRaises(ValueError):
                    v.calcular_vencimiento(
                        "2026-11-11",
                        vida_util_dias=dias,
                    )

    def test_vencimiento_calculado_se_persiste(self):
        extraccion = "2026-11-11"
        vencimiento = v.calcular_vencimiento(extraccion)

        unidad_id = self.insertar_unidad(
            extraccion=extraccion,
            vencimiento=vencimiento,
            estado=v.DISPONIBLE,
        )

        v.actualizar_vencimientos(
            ruta=self.ruta,
            ahora=self.ahora,
        )

        self.assertEqual(
            self.consultar_unidad(unidad_id),
            ("2026-12-01", v.DISPONIBLE),
        )

    def test_ventana_alerta_y_stock(self):
        vence_hoy = self.insertar_unidad("2026-11-11")
        vence_en_siete = self.insertar_unidad("2026-11-18")
        self.insertar_unidad("2026-11-19")
        vencida = self.insertar_unidad("2026-11-10")
        self.insertar_unidad("2026-11-12", estado=v.USADA)
        self.insertar_unidad("2026-11-12", estado=v.DESCARTADA)

        resumen = v.consultar_resumen(
            ruta=self.ruta,
            ahora=self.ahora,
        )

        self.assertEqual(
            [unidad["ID"] for unidad in resumen["proximas"]],
            [vence_hoy, vence_en_siete],
        )
        self.assertEqual(resumen["unidades"], 3)
        self.assertAlmostEqual(resumen["litros"], 1.35)
        self.assertEqual(
            self.consultar_unidad(vencida)[1],
            v.VENCIDA,
        )

    def test_fechas_invalidas_no_cuentan_como_stock(self):
        fechas = [
            None,
            "",
            "fecha inválida",
            "2026-02-31",
            "2026-10-31",
        ]

        for fecha in fechas:
            self.insertar_unidad(vencimiento=fecha)

        resumen = v.consultar_resumen(
            ruta=self.ruta,
            ahora=self.ahora,
        )

        self.assertEqual(resumen["unidades"], 0)
        self.assertEqual(resumen["litros"], 0)
        self.assertEqual(resumen["proximas"], [])
        self.assertEqual(resumen["pendientes"], len(fechas))

    def test_reservadas_no_cuentan_y_caducan(self):
        vigente = self.insertar_unidad(
            "2026-11-18",
            estado="Reservada",
        )
        caducada = self.insertar_unidad(
            "2026-11-10",
            estado="Reservada",
        )

        resumen = v.consultar_resumen(
            ruta=self.ruta,
            ahora=self.ahora,
        )

        self.assertEqual(
            self.consultar_unidad(vigente)[1],
            "Reservada",
        )
        self.assertEqual(
            self.consultar_unidad(caducada)[1],
            v.VENCIDA,
        )
        self.assertEqual(resumen["unidades"], 0)
        self.assertEqual(resumen["proximas"], [])

    def test_ventana_configurable_y_parametros_invalidos(self):
        vence_hoy = self.insertar_unidad("2026-11-11")
        self.insertar_unidad("2026-11-12")

        resumen = v.consultar_resumen(
            ruta=self.ruta,
            ahora=self.ahora,
            dias_alerta=0,
        )

        self.assertEqual(
            [unidad["ID"] for unidad in resumen["proximas"]],
            [vence_hoy],
        )
        self.assertEqual(resumen["unidades"], 2)

        for dias in (-1, 1.5, True, "7"):
            with self.subTest(dias=dias):
                with self.assertRaises(ValueError):
                    v.consultar_resumen(
                        ruta=self.ruta,
                        ahora=self.ahora,
                        dias_alerta=dias,
                    )

    def test_stock_agrupado_por_tipo_y_rh(self):
        primera = self.insertar_unidad(
            "2026-11-14", cantidad=0.45
        )
        segunda = self.insertar_unidad(
            "2026-11-18", cantidad=0.30
        )
        tercera = self.insertar_unidad(
            "2026-11-19", cantidad=0.45
        )

        self.insertar_unidad("2026-11-10")
        self.insertar_unidad(
            "2026-11-14", estado=v.USADA
        )

        with closing(sqlite3.connect(self.ruta)) as conexion, conexion:
            conexion.execute(
                """
                UPDATE DONACIONES
                SET TIPO_SANGRE = 'A', FACTOR_RH = '+'
                WHERE ID IN (?, ?)
                """,
                (primera, segunda),
            )
            conexion.execute(
                """
                UPDATE DONACIONES
                SET TIPO_SANGRE = 'O', FACTOR_RH = '-'
                WHERE ID = ?
                """,
                (tercera,),
            )

        datos = v.consultar_stock_detallado(
            ruta=self.ruta,
            ahora=self.ahora,
        )

        totales = {
            (fila["grupo"], fila["rh"]): fila
            for fila in datos["totales"]
        }

        self.assertEqual(totales[("A", "+")]["unidades"], 2)
        self.assertAlmostEqual(
            totales[("A", "+")]["litros"], 0.75
        )
        self.assertEqual(
            totales[("A", "+")]["proximo_vencimiento"],
            "2026-11-14",
        )
        self.assertEqual(totales[("O", "-")]["unidades"], 1)
        self.assertEqual(totales[("AB", "+")]["unidades"], 0)
        self.assertEqual(
            {fila["ID"] for fila in datos["unidades"]},
            {primera, segunda, tercera},
        )
    def test_extraccion_futura_no_cuenta_en_stock(self):
        unidad_id = self.insertar_unidad(
            extraccion="2026-11-12",
            vencimiento="2026-12-02",
        )

        resumen = v.consultar_resumen(
            ruta=self.ruta,
            ahora=self.ahora,
        )
        detalle = v.consultar_stock_detallado(
            ruta=self.ruta,
            ahora=self.ahora,
        )

        self.assertEqual(resumen["unidades"], 0)
        self.assertEqual(resumen["pendientes"], 1)
        self.assertEqual(detalle["unidades"], [])
        self.assertEqual(
            self.consultar_unidad(unidad_id)[1],
            v.PENDIENTE,
        )

        # H6 conserva las fechas originales para su revisión.
        with closing(sqlite3.connect(self.ruta)) as conexion:
            fechas = conexion.execute(
                """
                SELECT FECHA_EXTRACCIÓN, FECHA_VENCIMIENTO
                FROM DONACIONES
                WHERE ID = ?
                """,
                (unidad_id,),
            ).fetchone()

        self.assertEqual(
            fechas,
            ("2026-11-12", "2026-12-02"),
        )

    def test_cantidades_invalidas_se_excluyen_del_stock(self):
        cantidades = [
            None,
            0,
            -0.45,
            float("inf"),
            float("-inf"),
            "cantidad inválida",
        ]

        for cantidad in cantidades:
            self.insertar_unidad(
                vencimiento="2026-11-14",
                cantidad=cantidad,
            )

        resumen = v.consultar_resumen(
            ruta=self.ruta,
            ahora=self.ahora,
        )
        detalle = v.consultar_stock_detallado(
            ruta=self.ruta,
            ahora=self.ahora,
        )

        self.assertEqual(resumen["unidades"], 0)
        self.assertEqual(resumen["litros"], 0)
        self.assertEqual(resumen["proximas"], [])
        self.assertEqual(
            resumen["pendientes"],
            len(cantidades),
        )
        self.assertEqual(detalle["unidades"], [])

    def test_transaccion_protege_estados_de_otras_escrituras(self):
        unidad_id = self.insertar_unidad()

        with v.conectar(self.ruta) as conexion:
            estado = conexion.execute(
                "SELECT ESTADO FROM DONACIONES WHERE ID = ?",
                (unidad_id,),
            ).fetchone()[0]

            self.assertEqual(estado, v.DISPONIBLE)

            # Simula otro proceso intentando usar la unidad
            # mientras H6 está consultando y actualizando.
            with closing(
                sqlite3.connect(self.ruta, timeout=0)
            ) as otra:
                with self.assertRaisesRegex(
                    sqlite3.OperationalError,
                    "locked",
                ):
                    otra.execute(
                        """
                        UPDATE DONACIONES
                        SET ESTADO = ?
                        WHERE ID = ?
                        """,
                        (v.USADA, unidad_id),
                    )

        # Al finalizar H6, el otro proceso puede escribir.
        with closing(
            sqlite3.connect(self.ruta)
        ) as otra, otra:
            otra.execute(
                """
                UPDATE DONACIONES
                SET ESTADO = ?
                WHERE ID = ?
                """,
                (v.USADA, unidad_id),
            )

        v.actualizar_vencimientos(
            ruta=self.ruta,
            ahora=self.ahora,
        )

        self.assertEqual(
            self.consultar_unidad(unidad_id)[1],
            v.USADA,
        )

if __name__ == "__main__":
    unittest.main()