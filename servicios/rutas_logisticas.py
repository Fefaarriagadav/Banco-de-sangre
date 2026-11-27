import json
import os
import sqlite3
import ssl
from contextlib import closing
from datetime import datetime, timedelta
from email.errors import HeaderParseError
from email.headerregistry import Address
from email.message import EmailMessage
from zoneinfo import ZoneInfo

from datos.configuracion import RUTA_BD
from servicios import enviar_correos
from servicios.despachos import (
    consultar_bolsas_asignadas,
    direccion_de_entrega,
    tabla_solicitud,
    validar_enfermero,
    validar_horario_despacho,
    validar_programacion,
)
from servicios.vencimientos import (
    ZONA_HORARIA,
    validar_fecha,
    fecha_actual,
)


VIGENCIA_INTENTO = timedelta(minutes=5)


def migrar_rutas_logisticas(conexion):
    """Crea las tablas de hojas e intentos sin modificar solicitudes ni reservas."""
    conexion.execute("""
        CREATE TABLE IF NOT EXISTS HOJAS_RUTA (
            ID INTEGER PRIMARY KEY AUTOINCREMENT,
            TIPO_SOLICITUD TEXT NOT NULL CHECK (TIPO_SOLICITUD IN ('Programado', 'Emergencia')),
            SOLICITUD_ID INTEGER NOT NULL,
            GENERADA_POR INTEGER NOT NULL REFERENCES PERSONAL(ID_EMPLEADO),
            FECHA_GENERACION TEXT NOT NULL,
            CONTENIDO TEXT NOT NULL,
            UNIQUE (TIPO_SOLICITUD, SOLICITUD_ID)
        )
    """)
    conexion.execute("""
        CREATE TABLE IF NOT EXISTS NOTIFICACIONES_LOGISTICAS (
            ID INTEGER PRIMARY KEY AUTOINCREMENT,
            HOJA_ID INTEGER NOT NULL REFERENCES HOJAS_RUTA(ID),
            EMPLEADO_ID INTEGER NOT NULL REFERENCES PERSONAL(ID_EMPLEADO),
            FECHA TEXT NOT NULL,
            DESTINATARIO TEXT,
            ESTADO TEXT NOT NULL CHECK (ESTADO IN ('En curso', 'Enviado', 'Fallido', 'Sin confirmar')),
            DETALLE TEXT
        )
    """)
    conexion.execute("""
        CREATE INDEX IF NOT EXISTS IDX_NOTIFICACIONES_LOGISTICAS_HOJA
        ON NOTIFICACIONES_LOGISTICAS (HOJA_ID, ID)
    """)


def _conectar(ruta):
    conexion = sqlite3.connect(ruta)
    conexion.row_factory = sqlite3.Row
    conexion.execute("PRAGMA foreign_keys = ON")
    return conexion


def consultar_despachos_aprobados(empleado_id, *, ruta=RUTA_BD):
    with closing(_conectar(ruta)) as conexion:
        validar_enfermero(conexion, empleado_id, "consultar hojas de ruta")
        despachos = []
        for tipo in ("Emergencia", "Programado"):
            tabla = tabla_solicitud(tipo)
            if conexion.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (tabla,)
            ).fetchone() is None:
                continue
            filas = conexion.execute(f"""
                SELECT s.ID, s.CENTRO, s.GRUPO_SANGUINEO, s.FACTOR_RH, h.ID AS HOJA_ID
                FROM {tabla} AS s
                LEFT JOIN HOJAS_RUTA AS h ON h.TIPO_SOLICITUD = ? AND h.SOLICITUD_ID = s.ID
                WHERE s.ESTADO = 'Aprobada'
                ORDER BY s.ID DESC
            """, (tipo,))
            despachos.extend({**dict(fila), "TIPO": tipo} for fila in filas)
    return despachos


def _buscar_hoja(conexion, tipo, solicitud_id):
    fila = conexion.execute("""
        SELECT ID, CONTENIDO FROM HOJAS_RUTA WHERE TIPO_SOLICITUD = ? AND SOLICITUD_ID = ?
    """, (tipo, solicitud_id)).fetchone()
    if fila is None:
        return None
    hoja = json.loads(fila["CONTENIDO"])
    hoja["id"] = fila["ID"]
    return hoja


def _solicitud_aprobada(conexion, tipo, solicitud_id):
    tabla = tabla_solicitud(tipo)
    existe = conexion.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (tabla,)
    ).fetchone()
    solicitud = conexion.execute(
        f"SELECT * FROM {tabla} WHERE ID = ?", (solicitud_id,)
    ).fetchone() if existe else None
    if solicitud is None:
        raise ValueError("La solicitud no existe.")
    if solicitud["ESTADO"] != "Aprobada":
        raise ValueError("La solicitud debe estar aprobada para generar o notificar la hoja de ruta.")
    return solicitud


def _bolsas_para_traslado(conexion, tipo, solicitud_id):
    bolsas = consultar_bolsas_asignadas(
        conexion, tipo, solicitud_id
    )

    if not bolsas:
        raise ValueError(
            "La solicitud no tiene bolsas asignadas."
        )

    hoy = fecha_actual()

    for bolsa in bolsas:
        if (
            bolsa["ESTADO"] != "Reservada"
            or bolsa["VOLUMEN_ML"] != bolsa["VOLUMEN_REAL_ML"]
        ):
            raise ValueError(
                "Hay bolsas asignadas que ya no coinciden "
                "con la reserva del despacho."
            )

        if bolsa["ESTADO_LABORATORIO"] != "Liberada":
            raise ValueError(
                "Una bolsa asignada no tiene liberación "
                "de laboratorio."
            )

        try:
            vencimiento = validar_fecha(
                bolsa["FECHA_VENCIMIENTO"], "%Y-%m-%d"
            )
        except ValueError:
            raise ValueError(
                "Una bolsa asignada tiene un vencimiento inválido."
            ) from None

        if vencimiento < hoy:
            raise ValueError(
                "Una bolsa asignada está vencida."
            )

    return [
        {
            "id": bolsa["ID"],
            "volumen_ml": bolsa["VOLUMEN_ML"],
        }
        for bolsa in bolsas
    ]


def _texto_obligatorio(valor, nombre):
    if not isinstance(valor, str) or not valor.strip():
        raise ValueError(f"Falta {nombre}.")
    return valor.strip()


def consultar_destino_emergencia(solicitud_id, empleado_id, *, ruta=RUTA_BD):
    with closing(_conectar(ruta)) as conexion:
        validar_enfermero(conexion, empleado_id, "generar hojas de ruta")
        solicitud = _solicitud_aprobada(conexion, "Emergencia", solicitud_id)
        centro = solicitud["CENTRO"]
        return centro, direccion_de_entrega(conexion, centro)


def generar_hoja_ruta(tipo, solicitud_id, empleado_id, *, destino=None, fecha=None,
                      horario=None, ruta=RUTA_BD):
    with closing(_conectar(ruta)) as conexion, conexion:
        conexion.execute("BEGIN IMMEDIATE")
        validar_enfermero(conexion, empleado_id, "generar hojas de ruta")
        solicitud = _solicitud_aprobada(conexion, tipo, solicitud_id)
        solicitud_id = solicitud["ID"]
        # Validar también si la hoja ya había sido generada.
        bolsas = _bolsas_para_traslado(
            conexion, tipo, solicitud_id
        )

        hoja = _buscar_hoja(conexion, tipo, solicitud_id)

        if hoja is not None:
            if bolsas != hoja["bolsas"]:
                raise ValueError(
                    "Las bolsas asignadas cambiaron desde "
                    "que se generó la hoja de ruta."
                )
            return hoja

        if tipo == "Programado":
            destino = solicitud["DESTINO"]
            fecha = validar_fecha(solicitud["FECHA_DESPACHO"], "%Y-%m-%d").isoformat()
            horario = validar_horario_despacho(solicitud["HORA_DESPACHO"])
        else:
            direccion = direccion_de_entrega(conexion, solicitud["CENTRO"])
            if destino is not None and destino != direccion:
                raise ValueError("La dirección del centro cambió. Vuelve a abrir el formulario para revisarla.")
            destino = direccion
            fecha, horario = validar_programacion(fecha, horario)
        hoja = {
            "tipo": tipo,
            "solicitud_id": solicitud_id,
            "centro": _texto_obligatorio(solicitud["CENTRO"], "el centro solicitante"),
            "origen": _texto_obligatorio(os.getenv("HU12_ORIGEN"), "configurar el origen del traslado (HU12_ORIGEN)"),
            "destino": _texto_obligatorio(destino, "el destino del traslado"),
            "fecha": fecha,
            "horario": horario,
            "grupo": solicitud["GRUPO_SANGUINEO"],
            "rh": solicitud["FACTOR_RH"],
            "bolsas": bolsas,
            "condiciones": [{
                "producto": _texto_obligatorio(os.getenv("HU12_PRODUCTO"), "configurar el producto (HU12_PRODUCTO)"),
                "requisitos_termicos": _texto_obligatorio(
                    os.getenv("HU12_REQUISITOS_TERMICOS"), "configurar los requisitos térmicos validados (HU12_REQUISITOS_TERMICOS)"
                ),
                "instrucciones": _texto_obligatorio(
                    os.getenv("HU12_INSTRUCCIONES_TRANSPORTE"), "configurar las instrucciones validadas (HU12_INSTRUCCIONES_TRANSPORTE)"
                ),
            }],
        }
        fila = conexion.execute("""
            INSERT INTO HOJAS_RUTA (TIPO_SOLICITUD, SOLICITUD_ID, GENERADA_POR, FECHA_GENERACION, CONTENIDO)
            VALUES (?, ?, ?, ?, ?)
        """, (tipo, solicitud_id, empleado_id, _ahora().isoformat(), json.dumps(hoja, ensure_ascii=False)))
        hoja["id"] = fila.lastrowid
    return hoja


def consultar_hoja_ruta(tipo, solicitud_id, empleado_id, *, ruta=RUTA_BD):
    tabla_solicitud(tipo)
    with closing(_conectar(ruta)) as conexion:
        validar_enfermero(conexion, empleado_id, "consultar hojas de ruta")
        hoja = _buscar_hoja(conexion, tipo, solicitud_id)
        if hoja is None:
            raise ValueError("Esta solicitud todavía no tiene una hoja de ruta.")
        hoja["notificaciones"] = [dict(fila) for fila in conexion.execute("""
            SELECT ID, EMPLEADO_ID, FECHA, DESTINATARIO, ESTADO, DETALLE
            FROM NOTIFICACIONES_LOGISTICAS WHERE HOJA_ID = ? ORDER BY ID DESC
        """, (hoja["id"],))]
    return hoja


def _ahora():
    return datetime.now(ZoneInfo(ZONA_HORARIA)).replace(microsecond=0)


def notificar_logistica(tipo, solicitud_id, empleado_id, *, ruta=RUTA_BD):
    ahora = _ahora()
    destinatario = os.getenv("HU12_CORREO_LOGISTICA", "").strip()
    with closing(_conectar(ruta)) as conexion, conexion:
        conexion.execute("BEGIN IMMEDIATE")
        validar_enfermero(conexion, empleado_id, "notificar a logística")
        _solicitud_aprobada(conexion, tipo, solicitud_id)
        hoja = _buscar_hoja(conexion, tipo, solicitud_id)
        if hoja is None:
            raise ValueError("Genere la hoja de ruta antes de notificar a logística.")
        bolsas_actuales = _bolsas_para_traslado(conexion, tipo, solicitud_id)
        if bolsas_actuales != hoja["bolsas"]:
            raise ValueError("Las bolsas asignadas cambiaron desde que se generó la hoja de ruta.")

        anterior = conexion.execute("""
            SELECT ID, FECHA, ESTADO FROM NOTIFICACIONES_LOGISTICAS
            WHERE HOJA_ID = ? ORDER BY ID DESC LIMIT 1
        """, (hoja["id"],)).fetchone()
        if anterior and anterior["ESTADO"] == "Enviado":
            raise ValueError("Esta hoja de ruta ya fue aceptada por el servidor de correo.")
        if anterior and anterior["ESTADO"] == "En curso":
            if ahora - datetime.fromisoformat(anterior["FECHA"]) < VIGENCIA_INTENTO:
                raise ValueError("Ya hay una notificación en curso para esta hoja de ruta.")
            conexion.execute("""
                UPDATE NOTIFICACIONES_LOGISTICAS SET ESTADO = 'Sin confirmar', DETALLE = ? WHERE ID = ?
            """, ("El intento anterior se interrumpió y el resultado de envío es desconocido.", anterior["ID"]))
        intento_id = conexion.execute("""
            INSERT INTO NOTIFICACIONES_LOGISTICAS (HOJA_ID, EMPLEADO_ID, FECHA, DESTINATARIO, ESTADO)
            VALUES (?, ?, ?, ?, 'En curso')
        """, (hoja["id"], empleado_id, ahora.isoformat(), destinatario or None)).lastrowid

    estado, detalle = _enviar_hoja(hoja, destinatario)
    with closing(_conectar(ruta)) as conexion, conexion:
        conexion.execute("""
            UPDATE NOTIFICACIONES_LOGISTICAS SET ESTADO = ?, DETALLE = ? WHERE ID = ?
        """, (estado, detalle, intento_id))
    return {"estado": estado, "detalle": detalle}


def _enviar_hoja(hoja, destinatario):
    if not destinatario:
        return "Fallido", "Configure el correo del departamento de Logística en HU12_CORREO_LOGISTICA."
    if not enviar_correos.correo or not enviar_correos.contrasena:
        return "Fallido", "Configure CORREO_REMITENTE y CONTRASENA_APP para enviar el correo."
    try:
        direccion = Address(addr_spec=destinatario)
        if not direccion.domain:
            raise ValueError("Falta el dominio.")
    except (ValueError, HeaderParseError):
        return "Fallido", "Revise la dirección configurada en HU12_CORREO_LOGISTICA."
    try:
        remitente = Address(addr_spec=enviar_correos.correo)
        if not remitente.domain:
            raise ValueError("Falta el dominio.")
    except (ValueError, HeaderParseError):
        return "Fallido", "Revise la dirección configurada en CORREO_REMITENTE."
    mensaje = EmailMessage()
    mensaje["From"] = remitente
    mensaje["To"] = direccion
    mensaje["Subject"] = f"Hoja de ruta #{hoja['id']} | Banco de Sangre"
    mensaje.set_content(formatear_hoja_ruta(hoja))
    try:
        if enviar_correos.enviar_mensaje(mensaje, timeout=12, context=ssl.create_default_context()):
            return "Fallido", "El servidor de correo rechazó el destinatario de logística."
    except OSError:
        return "Fallido", "El servidor de correo no confirmó el envío. Revise la configuración y vuelva a intentar."
    return "Enviado", "Correo aceptado por el servidor. Recepción pendiente de confirmación."


def formatear_hoja_ruta(hoja):
    """Presenta los mismos datos en la aplicación y en la notificación."""
    lineas = [
        f"Hoja de ruta #{hoja['id']}",
        f"Solicitud {hoja['tipo']} #{hoja['solicitud_id']}",
        f"Centro: {hoja['centro']}",
        f"Origen: {hoja['origen']}",
        f"Destino: {hoja['destino']}",
        f"Traslado: {hoja['fecha']} a las {hoja['horario']} (hora de Santiago)",
        f"Grupo sanguíneo: {hoja['grupo']}{hoja['rh']}",
        "",
        f"Bolsas asignadas ({len(hoja['bolsas'])})",
    ]
    lineas.extend(
        f"Bolsa #{bolsa['id']} · {bolsa['volumen_ml']} mL"
        for bolsa in hoja['bolsas']
    )
    lineas.extend(("", "Condiciones de transporte"))
    for condicion in hoja['condiciones']:
        lineas.extend((
            condicion['producto'],
            f"Requisitos térmicos: {condicion['requisitos_termicos']}",
            f"Instrucciones: {condicion['instrucciones']}",
        ))
    return "\n".join(lineas)
