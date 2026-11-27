import os
import sqlite3
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path
from threading import Event
from unittest.mock import patch

from datos.basededatos import inicializar_base
from servicios import enviar_correos
from servicios.despachos import aprobar_solicitud, registrar_despacho, registrar_emergencia
from servicios.rutas_logisticas import (
    consultar_destino_emergencia,
    consultar_despachos_aprobados,
    consultar_hoja_ruta,
    generar_hoja_ruta,
    notificar_logistica,
)


CENTRO = "Hospital de prueba"
DESTINO = "Dirección de prueba, Concepción"
ENFERMERO = 1
ENTREVISTADOR = 2
CORREO_LOGISTICA = "logistica@example.invalid"


class RutasLogisticasTest(unittest.TestCase):
    def setUp(self):
        temporal = self.enterContext(tempfile.TemporaryDirectory())
        self.ruta = Path(temporal) / "hu12.db"
        self.enterContext(patch.dict(os.environ, {
            "HU12_ORIGEN": "Banco de prueba",
            "HU12_PRODUCTO": "Producto de prueba",
            "HU12_REQUISITOS_TERMICOS": "Requisitos térmicos de prueba",
            "HU12_INSTRUCCIONES_TRANSPORTE": "Instrucciones de prueba",
            "HU12_CORREO_LOGISTICA": CORREO_LOGISTICA,
        }))
        self.enterContext(patch.object(enviar_correos, "correo", "banco@example.invalid"))
        self.enterContext(patch.object(enviar_correos, "contrasena", "clave-de-prueba"))
        inicializar_base(self.ruta)
        with closing(sqlite3.connect(self.ruta)) as conexion, conexion:
            conexion.executemany("INSERT INTO PERSONAL (ID_EMPLEADO, ROL) VALUES (?, ?)", (
                (ENFERMERO, "Enfermero"), (ENTREVISTADOR, "Entrevistador"),
            ))
            conexion.execute("INSERT INTO CENTROS_MEDICOS VALUES (?, ?, ?)", (CENTRO, "Dirección de prueba", "Concepción"))
            conexion.executemany("""
                INSERT INTO DONACIONES (
                    ID, TIPO_SANGRE, FACTOR_RH, CANTIDAD,
                    FECHA_VENCIMIENTO, ESTADO,
                    ESTADO_LABORATORIO
                )
                VALUES (
                    ?, 'O', '+', ?, '2099-12-30',
                    'Disponible', 'Liberada'
                )
            """, ((1, 400), (2, 250), (3, 350)))

    def registrar_programado(self):
        return registrar_despacho(
            CENTRO, "O", "+", 400, "28-12-2099", "11:30",
            direccion_confirmada=DESTINO, ruta=self.ruta,
        )

    def generar_programado(self):
        solicitud = self.registrar_programado()
        aprobar_solicitud("Programado", solicitud, ENFERMERO, ruta=self.ruta)
        return generar_hoja_ruta("Programado", solicitud, ENFERMERO, ruta=self.ruta)

    def test_programado_usa_los_datos_guardados_y_solo_las_bolsas_asignadas(self):
        hoja = self.generar_programado()
        self.assertEqual(hoja["origen"], "Banco de prueba")
        self.assertEqual(hoja["destino"], DESTINO)
        self.assertEqual(hoja["fecha"], "2099-12-28")
        self.assertEqual(hoja["horario"], "11:30")
        self.assertEqual(hoja["bolsas"], [{"id": 1, "volumen_ml": 400}])
        self.assertEqual(hoja["condiciones"][0]["requisitos_termicos"], "Requisitos térmicos de prueba")

        with patch.dict(os.environ, {"HU12_ORIGEN": "Otro origen"}):
            repetida = generar_hoja_ruta("Programado", hoja["solicitud_id"], ENFERMERO, ruta=self.ruta)
        self.assertEqual(hoja, repetida)
        inicializar_base(self.ruta)
        consultada = consultar_hoja_ruta("Programado", hoja["solicitud_id"], ENFERMERO, ruta=self.ruta)
        self.assertEqual(consultada, {**hoja, "notificaciones": []})
        with closing(sqlite3.connect(self.ruta)) as conexion:
            self.assertEqual(conexion.execute("SELECT ESTADO FROM DESPACHOS_PROGRAMADOS").fetchone(), ("Aprobada",))
            self.assertEqual(conexion.execute("SELECT ESTADO FROM DONACIONES ORDER BY ID").fetchall(),
                             [("Reservada",), ("Disponible",), ("Disponible",)])

    def test_emergencia_requiere_programacion_y_el_tipo_distingue_solicitudes_con_igual_id(self):
        programado = self.generar_programado()
        solicitud = registrar_emergencia(CENTRO, "O", "+", 250, "Motivo de prueba", ruta=self.ruta)
        aprobar_solicitud("Emergencia", solicitud, ENFERMERO, ruta=self.ruta)
        self.assertEqual(consultar_destino_emergencia(solicitud, ENFERMERO, ruta=self.ruta), (CENTRO, DESTINO))
        with self.assertRaisesRegex(ValueError, "fecha válida"):
            generar_hoja_ruta("Emergencia", solicitud, ENFERMERO, ruta=self.ruta)
        hoja = generar_hoja_ruta("Emergencia", solicitud, ENFERMERO,
                                 fecha="29-12-2099", horario="08:15", ruta=self.ruta)
        self.assertEqual(solicitud, programado["solicitud_id"])
        self.assertNotEqual(hoja["id"], programado["id"])
        self.assertEqual((hoja["destino"], hoja["fecha"], hoja["horario"]), (DESTINO, "2099-12-29", "08:15"))
        self.assertEqual(hoja["bolsas"], [{"id": 2, "volumen_ml": 250}])
        filas = consultar_despachos_aprobados(ENFERMERO, ruta=self.ruta)
        self.assertEqual([(fila["TIPO"], fila["HOJA_ID"]) for fila in filas],
                         [("Emergencia", hoja["id"]), ("Programado", programado["id"])])

    def test_emergencia_revisa_si_la_direccion_cambio_despues_de_abrir_el_formulario(self):
        solicitud = registrar_emergencia(CENTRO, "O", "+", 400, "Motivo de prueba", ruta=self.ruta)
        aprobar_solicitud("Emergencia", solicitud, ENFERMERO, ruta=self.ruta)
        _, destino_visible = consultar_destino_emergencia(solicitud, ENFERMERO, ruta=self.ruta)
        with closing(sqlite3.connect(self.ruta)) as conexion, conexion:
            conexion.execute("UPDATE CENTROS_MEDICOS SET DIRECCION = ? WHERE NOMBRE = ?", ("Dirección actualizada", CENTRO))

        with self.assertRaisesRegex(ValueError, "dirección del centro cambió"):
            generar_hoja_ruta("Emergencia", solicitud, ENFERMERO, destino=destino_visible,
                              fecha="29-12-2099", horario="08:15", ruta=self.ruta)
        _, destino_actualizado = consultar_destino_emergencia(solicitud, ENFERMERO, ruta=self.ruta)
        hoja = generar_hoja_ruta("Emergencia", solicitud, ENFERMERO, destino=destino_actualizado,
                                fecha="29-12-2099", horario="08:15", ruta=self.ruta)
        self.assertEqual(hoja["destino"], "Dirección actualizada, Concepción")

    def test_emergencia_sin_direccion_registrada_no_genera_hoja(self):
        solicitud = registrar_emergencia(CENTRO, "O", "+", 400, "Motivo de prueba", ruta=self.ruta)
        aprobar_solicitud("Emergencia", solicitud, ENFERMERO, ruta=self.ruta)
        with closing(sqlite3.connect(self.ruta)) as conexion, conexion:
            conexion.execute("UPDATE CENTROS_MEDICOS SET DIRECCION = NULL WHERE NOMBRE = ?", (CENTRO,))

        with self.assertRaisesRegex(ValueError, "no tiene una dirección registrada"):
            consultar_destino_emergencia(solicitud, ENFERMERO, ruta=self.ruta)
        with self.assertRaisesRegex(ValueError, "no tiene una dirección registrada"):
            generar_hoja_ruta("Emergencia", solicitud, ENFERMERO,
                              fecha="29-12-2099", horario="08:15", ruta=self.ruta)
        with self.assertRaisesRegex(ValueError, "todavía no tiene"):
            consultar_hoja_ruta("Emergencia", solicitud, ENFERMERO, ruta=self.ruta)

    def test_rechaza_solicitud_inexistente_pendiente_y_sin_bolsas(self):
        solicitud = self.registrar_programado()
        for identificador, mensaje in ((99, "no existe"), (solicitud, "debe estar aprobada")):
            with self.subTest(mensaje=mensaje), self.assertRaisesRegex(ValueError, mensaje):
                generar_hoja_ruta("Programado", identificador, ENFERMERO, ruta=self.ruta)
        self.assertEqual(consultar_despachos_aprobados(ENFERMERO, ruta=self.ruta), [])
        with closing(sqlite3.connect(self.ruta)) as conexion, conexion:
            conexion.execute("UPDATE DESPACHOS_PROGRAMADOS SET ESTADO = 'Aprobada'")
        with self.assertRaisesRegex(ValueError, "no tiene bolsas asignadas"):
            generar_hoja_ruta("Programado", solicitud, ENFERMERO, ruta=self.ruta)

    def test_autorizacion_en_el_servicio(self):
        hoja = self.generar_programado()
        for operacion in (generar_hoja_ruta, consultar_hoja_ruta, notificar_logistica):
            for empleado in (ENTREVISTADOR, 99):
                with self.subTest(operacion=operacion.__name__, empleado=empleado), self.assertRaises(PermissionError):
                    operacion("Programado", hoja["solicitud_id"], empleado, ruta=self.ruta)
        with self.assertRaises(PermissionError):
            consultar_despachos_aprobados(ENTREVISTADOR, ruta=self.ruta)

    def test_sin_requisitos_validados_no_queda_una_hoja_parcial(self):
        solicitud = self.registrar_programado()
        aprobar_solicitud("Programado", solicitud, ENFERMERO, ruta=self.ruta)
        with patch.dict(os.environ, {"HU12_REQUISITOS_TERMICOS": " "}):
            with self.assertRaisesRegex(ValueError, "requisitos térmicos validados"):
                generar_hoja_ruta("Programado", solicitud, ENFERMERO, ruta=self.ruta)
        with self.assertRaisesRegex(ValueError, "todavía no tiene"):
            consultar_hoja_ruta("Programado", solicitud, ENFERMERO, ruta=self.ruta)

    def test_configuracion_incompleta_fallo_smtp_y_reintento_quedan_registrados(self):
        hoja = self.generar_programado()
        solicitud = hoja["solicitud_id"]
        with patch.object(enviar_correos.smtplib, "SMTP_SSL") as smtp:
            with patch.dict(os.environ, {"HU12_CORREO_LOGISTICA": ""}):
                resultado = notificar_logistica("Programado", solicitud, ENFERMERO, ruta=self.ruta)
            self.assertEqual(resultado["estado"], "Fallido")
            smtp.assert_not_called()
            servidor = smtp.return_value.__enter__.return_value
            servidor.send_message.side_effect = [OSError("Fallo de prueba"), {}]
            self.assertEqual(notificar_logistica("Programado", solicitud, ENFERMERO, ruta=self.ruta)["estado"], "Fallido")
            self.assertEqual(notificar_logistica("Programado", solicitud, ENFERMERO, ruta=self.ruta)["estado"], "Enviado")
            with self.assertRaisesRegex(ValueError, "ya fue aceptada"):
                notificar_logistica("Programado", solicitud, ENFERMERO, ruta=self.ruta)
            mensaje = servidor.send_message.call_args.args[0]
            self.assertEqual(mensaje["To"], CORREO_LOGISTICA)
            self.assertIn("Bolsa #1", mensaje.get_content())
            self.assertIn("Instrucciones de prueba", mensaje.get_content())
            self.assertEqual(servidor.send_message.call_count, 2)

        historial = consultar_hoja_ruta("Programado", solicitud, ENFERMERO, ruta=self.ruta)["notificaciones"]
        self.assertEqual([fila["ESTADO"] for fila in historial], ["Enviado", "Fallido", "Fallido"])
        self.assertTrue(all(fila["EMPLEADO_ID"] == ENFERMERO and fila["FECHA"] for fila in historial))
        self.assertIn("Recepción pendiente", historial[0]["DETALLE"])
        with closing(sqlite3.connect(self.ruta)) as conexion:
            self.assertEqual(conexion.execute("SELECT ESTADO FROM DESPACHOS_PROGRAMADOS").fetchone(), ("Aprobada",))
            self.assertEqual(conexion.execute("SELECT ESTADO FROM DONACIONES WHERE ID = 1").fetchone(), ("Reservada",))

    def test_logistica_interna_recibe_hojas_de_dos_centros_con_la_cuenta_remitente(self):
        programado = self.generar_programado()
        otro_centro = "Hospital público de prueba"
        with closing(sqlite3.connect(self.ruta)) as conexion, conexion:
            conexion.execute("INSERT INTO CENTROS_MEDICOS VALUES (?, ?, ?)", (otro_centro, "Otra dirección", "Concepción"))
        emergencia = registrar_emergencia(otro_centro, "O", "+", 250, "Motivo de prueba", ruta=self.ruta)
        aprobar_solicitud("Emergencia", emergencia, ENFERMERO, ruta=self.ruta)
        hoja_emergencia = generar_hoja_ruta("Emergencia", emergencia, ENFERMERO,
                                           fecha="29-12-2099", horario="08:15", ruta=self.ruta)
        self.assertEqual(hoja_emergencia["destino"], "Otra dirección, Concepción")

        with patch.object(enviar_correos.smtplib, "SMTP_SSL") as smtp:
            servidor = smtp.return_value.__enter__.return_value
            servidor.send_message.return_value = {}
            for tipo, solicitud_id, centro in (
                ("Programado", programado["solicitud_id"], CENTRO),
                ("Emergencia", emergencia, otro_centro),
            ):
                resultado = notificar_logistica(tipo, solicitud_id, ENFERMERO, ruta=self.ruta)
                self.assertEqual(resultado["estado"], "Enviado")
                correo = servidor.send_message.call_args.args[0]
                self.assertEqual(correo["To"], CORREO_LOGISTICA)
                self.assertEqual(correo["From"], "banco@example.invalid")
                self.assertIn(f"Centro: {centro}", correo.get_content())
                historial = consultar_hoja_ruta(tipo, solicitud_id, ENFERMERO, ruta=self.ruta)["notificaciones"]
                self.assertEqual(historial[0]["DESTINATARIO"], CORREO_LOGISTICA)
            self.assertEqual(servidor.send_message.call_count, 2)
            servidor.login.assert_called_with("banco@example.invalid", "clave-de-prueba")

    def test_correo_interno_ausente_o_invalido_no_contacta_smtp(self):
        hoja = self.generar_programado()
        solicitud = hoja["solicitud_id"]
        configuraciones = (
            ("", "Configure el correo"),
            ("logistica", "Revise la dirección"),
        )
        with patch.object(enviar_correos.smtplib, "SMTP_SSL") as smtp:
            for configuracion, mensaje in configuraciones:
                with self.subTest(configuracion=configuracion), patch.dict(os.environ, {
                    "HU12_CORREO_LOGISTICA": configuracion,
                    "HU12_CORREOS_LOGISTICA": '{"Hospital de prueba":"hospital@example.invalid"}',
                }):
                    resultado = notificar_logistica("Programado", solicitud, ENFERMERO, ruta=self.ruta)
                    self.assertEqual(resultado["estado"], "Fallido")
                    self.assertIn(mensaje, resultado["detalle"])
            smtp.assert_not_called()

        intentos = consultar_hoja_ruta("Programado", solicitud, ENFERMERO, ruta=self.ruta)["notificaciones"]
        self.assertEqual(len(intentos), len(configuraciones))
        self.assertEqual([fila["DESTINATARIO"] for fila in intentos], ["logistica", None])

    def test_un_envio_en_curso_evita_notificaciones_concurrentes(self):
        hoja = self.generar_programado()
        iniciado = Event()
        finalizar = Event()

        def enviar_simulado(*args, **kwargs):
            iniciado.set()
            if not finalizar.wait(timeout=5):
                raise OSError("Finalización de prueba fuera de tiempo")
            return {}

        with patch.object(enviar_correos, "enviar_mensaje", side_effect=enviar_simulado), ThreadPoolExecutor(1) as ejecutor:
            futuro = ejecutor.submit(notificar_logistica, "Programado", hoja["solicitud_id"], ENFERMERO, ruta=self.ruta)
            try:
                self.assertTrue(iniciado.wait(timeout=5))
                with self.assertRaisesRegex(ValueError, "notificación en curso"):
                    notificar_logistica("Programado", hoja["solicitud_id"], ENFERMERO, ruta=self.ruta)
            finally:
                finalizar.set()
            self.assertEqual(futuro.result(timeout=5)["estado"], "Enviado")

    def test_no_genera_hoja_sin_liberacion_de_laboratorio(self):
        solicitud = self.registrar_programado()

        aprobar_solicitud(
            "Programado",
            solicitud,
            ENFERMERO,
            ruta=self.ruta,
        )

        with closing(sqlite3.connect(self.ruta)) as conexion, conexion:
            conexion.execute(
                """
                UPDATE DONACIONES
                SET ESTADO_LABORATORIO = 'Pendiente de análisis'
                WHERE ESTADO = 'Reservada'
                """
            )

        with self.assertRaisesRegex(
            ValueError, "liberación de laboratorio"
        ):
            generar_hoja_ruta(
                "Programado",
                solicitud,
                ENFERMERO,
                ruta=self.ruta,
            )

        with closing(sqlite3.connect(self.ruta)) as conexion:
            cantidad = conexion.execute(
                "SELECT COUNT(*) FROM HOJAS_RUTA"
            ).fetchone()[0]

        self.assertEqual(cantidad, 0)

    def test_hoja_existente_no_evade_validacion_de_laboratorio(self):
        hoja = self.generar_programado()

        with closing(sqlite3.connect(self.ruta)) as conexion, conexion:
            conexion.execute(
                """
                UPDATE DONACIONES
                SET ESTADO_LABORATORIO = 'Bloqueada'
                WHERE ESTADO = 'Reservada'
                """
            )

        with self.assertRaisesRegex(
            ValueError, "liberación de laboratorio"
        ):
            generar_hoja_ruta(
                "Programado",
                hoja["solicitud_id"],
                ENFERMERO,
                ruta=self.ruta,
            )

        # Se conserva el documento como registro histórico.
        historica = consultar_hoja_ruta(
            "Programado",
            hoja["solicitud_id"],
            ENFERMERO,
            ruta=self.ruta,
        )

        self.assertEqual(historica["id"], hoja["id"])

    def test_no_notifica_hoja_con_laboratorio_revocado(self):
        hoja = self.generar_programado()

        with closing(sqlite3.connect(self.ruta)) as conexion, conexion:
            conexion.execute(
                """
                UPDATE DONACIONES
                SET ESTADO_LABORATORIO = 'Pendiente de análisis'
                WHERE ESTADO = 'Reservada'
                """
            )

        with patch(
            "servicios.rutas_logisticas._enviar_hoja"
        ) as enviar:
            with self.assertRaisesRegex(
                ValueError, "liberación de laboratorio"
            ):
                notificar_logistica(
                    "Programado",
                    hoja["solicitud_id"],
                    ENFERMERO,
                    ruta=self.ruta,
                )

            enviar.assert_not_called()

        with closing(sqlite3.connect(self.ruta)) as conexion:
            cantidad = conexion.execute(
                "SELECT COUNT(*) FROM NOTIFICACIONES_LOGISTICAS"
            ).fetchone()[0]

        self.assertEqual(cantidad, 0)

if __name__ == "__main__":
    unittest.main()