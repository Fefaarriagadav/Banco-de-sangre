"""Registro de sangre total y descanso del donante en una sola transacción."""
import calendar
import math
from datetime import date, datetime, timedelta

from datos.configuracion import RUTA_BD
from servicios.elegibilidad import SQL_HABILITADO, TEMPORAL, conectar, validar_id
from servicios.vencimientos import DISPONIBLE, calcular_vencimiento, fecha_actual


def calcular_fecha_habilitacion(fecha_donacion, sexo):
    meses = {"Masculino": 3, "Femenino": 4}.get(sexo)
    if meses is None:
        raise ValueError("El donante debe tener un sexo válido para calcular su habilitación.")
    total = fecha_donacion.year * 12 + fecha_donacion.month - 1 + meses
    anio, mes = divmod(total, 12)
    mes += 1
    dia = min(fecha_donacion.day, calendar.monthrange(anio, mes)[1])
    return date(anio, mes, dia)


def registrar_donacion(donante_id, cantidad, empleado_id, ruta=RUTA_BD, hoy=None):
    donante_id = validar_id(donante_id)
    try:
        cantidad = float(cantidad)
    except (ValueError, TypeError, OverflowError):
        raise ValueError("Ingrese una cantidad válida en cc.") from None
    if not math.isfinite(cantidad) or not 0.1 <= cantidad <= 450:
        raise ValueError("La cantidad debe estar entre 0.1 y 450 cc.")
    hoy = hoy or fecha_actual()
    extraccion = hoy.isoformat()
    vencimiento = calcular_vencimiento(extraccion)

    with conectar(ruta) as conexion:
        # La aptitud se comprueba bajo el mismo bloqueo que guarda la donación.
        conexion.execute("BEGIN IMMEDIATE")
        empleado = conexion.execute(
            "SELECT ROL FROM PERSONAL WHERE ID_EMPLEADO = ?", (empleado_id,)).fetchone()
        if empleado is None or empleado["ROL"] != "Enfermero":
            raise PermissionError("No tiene autorización para registrar donaciones.")
        donante = conexion.execute(
            "SELECT * FROM DONANTES WHERE ID = ? AND " + SQL_HABILITADO,
            (donante_id, extraccion)).fetchone()
        if donante is None:
            raise ValueError("No existe un donante apto con ese ID.")
        #ubicaciones de donde se debe guardar la donación según el grupo sanguíneo y factor rh
        grupo_completo = donante["GRUPO_SANGUINEO"] + donante["FACTOR_RH"]
        if grupo_completo in ['O+', 'O-']:
            ubicacion_asignada = "Refrigerador 1"
        elif grupo_completo in ['A+', 'A-']:
            ubicacion_asignada = "Refrigerador 2"
        elif grupo_completo in ['B+', 'B-', 'AB+', 'AB-']:
            ubicacion_asignada = "Refrigerador 3"
        else:
            ubicacion_asignada = "Cámara General"

        habilitacion = calcular_fecha_habilitacion(hoy, donante["SEXO"])
        # Las consultas de H4 consideran inclusivo el último día de restricción.
        fin = (habilitacion - timedelta(days=1)).isoformat()
        cursor = conexion.execute("""INSERT INTO DONACIONES (
            DONANTE, CANTIDAD, FECHA_EXTRACCIÓN, FECHA_VENCIMIENTO,
            TIPO_SANGRE, FACTOR_RH, ESTADO, UBICACION) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (donante_id, cantidad, extraccion, vencimiento,
             donante["GRUPO_SANGUINEO"], donante["FACTOR_RH"], DISPONIBLE, ubicacion_asignada))
        donacion_id = cursor.lastrowid
        conexion.execute("""UPDATE DONANTES SET FECHA_ULTIMA_DONACION = ?,
            ELEGIBLE = ?, INHABILITACION_INICIO = ?, INHABILITACION_FIN = ? WHERE ID = ?""",
            (extraccion, TEMPORAL, extraccion, fin, donante_id))
        conexion.execute("""INSERT INTO HISTORIAL_HABILITACION (
            DONANTE_ID, ESTADO_ANTERIOR, ESTADO_NUEVO, FECHA_INICIO,
            FECHA_FIN, EMPLEADO_ID, FECHA_CAMBIO) VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (donante_id, donante["ELEGIBLE"], TEMPORAL, extraccion, fin,
             empleado_id, datetime.now().isoformat(timespec="seconds")))

    return {"ID": donacion_id, "DONANTE": donante_id, "CANTIDAD": cantidad,
            "FECHA_EXTRACCION": extraccion, "FECHA_VENCIMIENTO": vencimiento,
            "GRUPO_SANGUINEO": donante["GRUPO_SANGUINEO"], "FACTOR_RH": donante["FACTOR_RH"],
            "FECHA_HABILITACION": habilitacion.isoformat(), "UBICACION": ubicacion_asignada}
