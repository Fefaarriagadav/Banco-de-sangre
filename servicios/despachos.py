import re
import sqlite3
from contextlib import closing
from datetime import datetime, time, timezone
from zoneinfo import ZoneInfo
from datos.configuracion import RUTA_BD
from servicios.vencimientos import ZONA_HORARIA, validar_fecha, fecha_actual

GRUPOS = ("A", "B", "AB", "O")
FACTORES_RH = ("+", "-")
PENDIENTE = "Pendiente"

def migrar_despachos(conexion):
    conexion.execute("""
        CREATE TABLE IF NOT EXISTS CENTROS_MEDICOS (
            NOMBRE TEXT PRIMARY KEY NOT NULL,
            DIRECCION TEXT,
            COMUNA TEXT)""")

    # Esquema para instalaciones nuevas
    conexion.execute("""
        CREATE TABLE IF NOT EXISTS DESPACHOS_PROGRAMADOS (
            ID INTEGER PRIMARY KEY AUTOINCREMENT,
            CENTRO TEXT NOT NULL REFERENCES CENTROS_MEDICOS(NOMBRE),
            GRUPO_SANGUINEO TEXT NOT NULL
                CHECK (GRUPO_SANGUINEO IN ('A', 'B', 'AB', 'O')),
            FACTOR_RH TEXT NOT NULL
                CHECK (FACTOR_RH IN ('+', '-')),
            CANTIDAD INTEGER
                CHECK (CANTIDAD IS NULL OR CANTIDAD > 0),
            VOLUMEN_ML INTEGER
                CHECK (VOLUMEN_ML IS NULL OR VOLUMEN_ML > 0),
            FECHA_DESPACHO TEXT NOT NULL,
            HORA_DESPACHO TEXT NOT NULL,
            DESTINO TEXT NOT NULL
                CHECK (length(trim(DESTINO)) > 0),
            ESTADO TEXT NOT NULL DEFAULT 'Pendiente',
            CHECK ((CANTIDAD IS NULL) != (VOLUMEN_ML IS NULL)))""")
    # Comprobar si la tabla existente es la versión antigua
    columnas = {
        fila[1]
        for fila in conexion.execute(
            "PRAGMA table_info(DESPACHOS_PROGRAMADOS)")}

    if "VOLUMEN_ML" not in columnas:
        # Crear una tabla con el nuevo esquema
        conexion.execute("""
            CREATE TABLE DESPACHOS_PROGRAMADOS_NUEVO (
                ID INTEGER PRIMARY KEY AUTOINCREMENT,
                CENTRO TEXT NOT NULL REFERENCES CENTROS_MEDICOS(NOMBRE),
                GRUPO_SANGUINEO TEXT NOT NULL
                    CHECK (GRUPO_SANGUINEO IN ('A', 'B', 'AB', 'O')),
                FACTOR_RH TEXT NOT NULL
                    CHECK (FACTOR_RH IN ('+', '-')),
                CANTIDAD INTEGER
                    CHECK (CANTIDAD IS NULL OR CANTIDAD > 0),
                VOLUMEN_ML INTEGER
                    CHECK (VOLUMEN_ML IS NULL OR VOLUMEN_ML > 0),
                FECHA_DESPACHO TEXT NOT NULL,
                HORA_DESPACHO TEXT NOT NULL,
                DESTINO TEXT NOT NULL
                    CHECK (length(trim(DESTINO)) > 0),
                ESTADO TEXT NOT NULL DEFAULT 'Pendiente',
                CHECK ((CANTIDAD IS NULL) != (VOLUMEN_ML IS NULL)))""")
        # Conservar las solicitudes antiguas como bolsas
        conexion.execute("""
            INSERT INTO DESPACHOS_PROGRAMADOS_NUEVO (
                ID, CENTRO, GRUPO_SANGUINEO, FACTOR_RH,
                CANTIDAD, FECHA_DESPACHO, HORA_DESPACHO,
                DESTINO, ESTADO)
            SELECT
                ID, CENTRO, GRUPO_SANGUINEO, FACTOR_RH,
                CANTIDAD, FECHA_DESPACHO, HORA_DESPACHO,
                DESTINO, ESTADO
            FROM DESPACHOS_PROGRAMADOS""")
        # Sustituir la tabla antigua por la migrada
        conexion.execute("DROP TABLE DESPACHOS_PROGRAMADOS")
        conexion.execute("""ALTER TABLE DESPACHOS_PROGRAMADOS_NUEVO RENAME TO DESPACHOS_PROGRAMADOS""")
    conexion.execute("""
        CREATE INDEX IF NOT EXISTS IDX_DESPACHOS_CENTRO_ID
        ON DESPACHOS_PROGRAMADOS (CENTRO, ID)""")

def _datos_centro(conexion, centro):
    if isinstance(centro, str) and centro.strip():
        datos = conexion.execute(
            "SELECT DIRECCION, COMUNA FROM CENTROS_MEDICOS WHERE NOMBRE = ?", (centro,)
        ).fetchone()
        if datos is not None:
            return datos
    raise PermissionError("El centro médico no tiene acceso a solicitudes programadas.")

def direccion_de_entrega(conexion, centro):
    direccion, comuna = _datos_centro(conexion, centro)
    direccion = (direccion or "").strip()
    comuna = (comuna or "").strip()
    if not direccion:
        raise ValueError("El centro no tiene una dirección registrada para el despacho.")
    return f"{direccion}, {comuna}" if comuna else direccion

def consultar_direccion_despacho(centro, *, ruta=RUTA_BD):
    with closing(sqlite3.connect(ruta)) as conexion:
        return direccion_de_entrega(conexion, centro)

def _validar_cantidad(cantidad):
    mensaje = "Ingrese un volumen entero en mL mayor que cero."
    if isinstance(cantidad, str):
        cantidad = cantidad.strip()
        if not re.fullmatch(r"[0-9]+", cantidad):
            raise ValueError(mensaje)
        digitos = cantidad.lstrip("0") or "0"
        if len(digitos) > 19:
            raise ValueError("La cantidad ingresada supera el máximo admitido.")
        cantidad = int(digitos)
    if type(cantidad) is not int or cantidad <= 0:
        raise ValueError(mensaje)
    if cantidad > 2**63 - 1:
        raise ValueError("La cantidad ingresada supera el máximo admitido.")
    return cantidad

def validar_horario_despacho(horario):
    horario = horario.strip() if isinstance(horario, str) else ""
    if not re.fullmatch(r"(?:[01][0-9]|2[0-3]):[0-5][0-9]", horario):
        raise ValueError("Ingrese un horario válido en formato HH:MM (24 horas).")
    return horario


def validar_programacion(fecha, horario, ahora=None):
    fecha_despacho = validar_fecha(fecha.strip() if isinstance(fecha, str) else fecha)
    horario = validar_horario_despacho(horario)

    zona = ZoneInfo(ZONA_HORARIA)
    hora_local = datetime.combine(fecha_despacho, time.fromisoformat(horario))
    # El cambio de hora puede omitir o repetir una hora local.
    instantes = set()
    try:
        for fold in (0, 1):
            instante = hora_local.replace(tzinfo=zona, fold=fold).astimezone(timezone.utc)
            if instante.astimezone(zona).replace(tzinfo=None) == hora_local:
                instantes.add(instante)
    except OverflowError:
        raise ValueError("La fecha y la hora están fuera del rango admitido.") from None
    if len(instantes) != 1:
        raise ValueError("El horario es ambiguo o no existe por el cambio de hora. Elija otro.")

    ahora = datetime.now(timezone.utc) if ahora is None else ahora
    if ahora.tzinfo is None or ahora.utcoffset() is None:
        raise ValueError("La hora actual debe incluir zona horaria.")
    if instantes.pop() <= ahora.astimezone(timezone.utc):
        raise ValueError("La fecha y hora del despacho deben ser futuras (hora de Santiago).")
    return fecha_despacho.isoformat(), horario

def consultar_volumen_disponible(centro, grupo, rh, *, ruta=RUTA_BD, ahora=None):
    if grupo not in GRUPOS or rh not in FACTORES_RH:
        raise ValueError("Seleccione un grupo sanguíneo y factor Rh válidos.")
    with closing(sqlite3.connect(ruta)) as conexion:
        _datos_centro(conexion, centro)
        return _volumen_disponible(conexion,grupo,rh,fecha_actual(ahora))

def _volumen_disponible(conexion, grupo, rh, hoy):
    fila = conexion.execute("""
        SELECT COALESCE(SUM(u.CANTIDAD), 0)
        FROM DONACIONES AS u
        LEFT JOIN DONANTES AS d ON d.ID = u.DONANTE
        WHERE u.ESTADO = 'Disponible'
          AND u.FECHA_VENCIMIENTO >= ?
          AND COALESCE(u.TIPO_SANGRE, d.GRUPO_SANGUINEO, '?') = ?
          AND COALESCE(u.FACTOR_RH, d.FACTOR_RH, '?') = ?
          AND u.CANTIDAD > 0
    """, (hoy.isoformat(), grupo, rh)).fetchone()
    return int(fila[0])

def registrar_despacho(centro, grupo, rh, cantidad, fecha, horario, *,
                       direccion_confirmada, ruta=RUTA_BD, ahora=None):
    if grupo not in GRUPOS:
        raise ValueError("Seleccione un grupo sanguíneo válido (A, B, AB u O).")
    if rh not in FACTORES_RH:
        raise ValueError("Seleccione un factor Rh válido (+ o -).")

    # La cantidad solicitada ahora representa mL
    volumen_ml = _validar_cantidad(cantidad)
    with closing(sqlite3.connect(ruta)) as conexion, conexion:
        conexion.execute("PRAGMA foreign_keys = ON")
        conexion.execute("BEGIN IMMEDIATE")
        # Adaptar la tabla si todavía tiene el esquema antiguo
        migrar_despachos(conexion)
        destino = direccion_de_entrega(conexion, centro)
        if direccion_confirmada != destino:
            raise ValueError("La dirección del centro cambió o no se confirmó. " "Vuelva a abrir el formulario para revisarla.")
        fecha_despacho, hora_despacho = validar_programacion(fecha, horario, ahora)

        # Consultar volumen real en el momento del registro
        disponible_ml = _volumen_disponible(conexion,grupo,rh,fecha_actual(ahora))

        # Rechazar solicitudes superiores al stock disponible
        if volumen_ml > disponible_ml:
            raise ValueError(f"Stock insuficiente para {grupo}{rh}: " f"hay {disponible_ml} mL disponibles " f"y solicitó {volumen_ml} mL.")

        # Guardar la solicitud en mililitros
        cursor = conexion.execute("""INSERT INTO DESPACHOS_PROGRAMADOS (CENTRO,GRUPO_SANGUINEO,FACTOR_RH,VOLUMEN_ML,FECHA_DESPACHO,HORA_DESPACHO,DESTINO)
            VALUES (?, ?, ?, ?, ?, ?, ?)""", (centro,grupo,rh,volumen_ml,fecha_despacho,hora_despacho,destino))
        return cursor.lastrowid

def consultar_despachos(centro, *, ruta=RUTA_BD):
    with closing(sqlite3.connect(ruta)) as conexion, conexion:
        conexion.row_factory = sqlite3.Row
        conexion.execute("BEGIN")
        _datos_centro(conexion, centro)
        # Detectar si ya existe la nueva columna
        columnas = {
            fila[1]
            for fila in conexion.execute(
                "PRAGMA table_info(DESPACHOS_PROGRAMADOS)")}
        if "VOLUMEN_ML" in columnas:
            volumen = "VOLUMEN_ML"
        else:
            volumen = "NULL AS VOLUMEN_ML"

        filas = conexion.execute(f"""SELECT ID,CENTRO,GRUPO_SANGUINEO,FACTOR_RH,CANTIDAD,{volumen},FECHA_DESPACHO,HORA_DESPACHO,DESTINO,ESTADO
            FROM DESPACHOS_PROGRAMADOS WHERE CENTRO = ? ORDER BY ID DESC """, (centro,))
        return [dict(fila) for fila in filas]

def crear_tabla_emergencias(conexion):
    conexion.execute("""
        CREATE TABLE IF NOT EXISTS DESPACHOS_EMERGENCIA (
            ID INTEGER PRIMARY KEY AUTOINCREMENT,
            CENTRO TEXT NOT NULL
                REFERENCES CENTROS_MEDICOS(NOMBRE),
            GRUPO_SANGUINEO TEXT NOT NULL
                CHECK (GRUPO_SANGUINEO IN ('A', 'B', 'AB', 'O')),
            FACTOR_RH TEXT NOT NULL
                CHECK (FACTOR_RH IN ('+', '-')),
            VOLUMEN_ML INTEGER NOT NULL
                CHECK (VOLUMEN_ML > 0),
            MOTIVO TEXT NOT NULL
                CHECK (length(trim(MOTIVO)) > 0),
            FECHA_SOLICITUD TEXT NOT NULL,
            ESTADO TEXT NOT NULL DEFAULT 'Pendiente de aprobación')""")

class ExcesoVolumenError(ValueError):
    def __init__(self, solicitado, asignado):
        self.solicitado = solicitado
        self.asignado = asignado
        super().__init__(f"Se solicitaron {solicitado} mL, pero las bolsas " f"seleccionadas contienen {asignado} mL.")

def crear_tabla_reservas_emergencia(conexion):
    conexion.execute("""
        CREATE TABLE IF NOT EXISTS RESERVAS_EMERGENCIA (
            ID INTEGER PRIMARY KEY AUTOINCREMENT,
            SOLICITUD_ID INTEGER NOT NULL
                REFERENCES DESPACHOS_EMERGENCIA(ID),
            DONACION_ID INTEGER NOT NULL UNIQUE
                REFERENCES DONACIONES(ID),
            VOLUMEN_ML INTEGER NOT NULL
                CHECK (VOLUMEN_ML > 0))""")

def seleccionar_bolsas_emergencia(conexion, grupo, rh, volumen_solicitado, hoy):
    # Buscar bolsas disponibles, vigentes y del grupo solicitado
    filas = conexion.execute("""
        SELECT u.ID, u.CANTIDAD
        FROM DONACIONES AS u
        LEFT JOIN DONANTES AS d
            ON d.ID = u.DONANTE
        WHERE u.ESTADO = 'Disponible'
          AND u.FECHA_VENCIMIENTO >= ?
          AND COALESCE(
              u.TIPO_SANGRE, d.GRUPO_SANGUINEO, '?'
          ) = ?
          AND COALESCE(
              u.FACTOR_RH, d.FACTOR_RH, '?'
          ) = ?
          AND u.CANTIDAD > 0
          AND NOT EXISTS (
              SELECT 1
              FROM RESERVAS_EMERGENCIA AS r
              WHERE r.DONACION_ID = u.ID
          )
        ORDER BY u.FECHA_VENCIMIENTO ASC, u.ID ASC
    """, (hoy.isoformat(), grupo, rh)).fetchall()

    bolsas = []

    for id_bolsa, cantidad in filas:
        # Solo se pueden asignar volúmenes enteros positivos
        if (
            cantidad is not None
            and cantidad > 0
            and int(cantidad) == cantidad
        ):
            bolsas.append((id_bolsa, int(cantidad)))

    disponible = sum(ml for _, ml in bolsas)

    if disponible < volumen_solicitado:
        raise ValueError(
            f"Stock insuficiente para {grupo}{rh}. "
            f"Disponible: {disponible} mL. "
            f"Solicitado: {volumen_solicitado} mL."
        )

   
    #minimizar sobrante y priorizar FEFO entre combinaciones que entregan el mismo volumen.
    max_bolsa = max(ml for _, ml in bolsas)
    limite = volumen_solicitado + max_bolsa
    #las bolsas ya están ordenadas por vencimiento e ID guardamos sus índices para comparar combinaciones.
    combinaciones = {0: ()}
    for indice, (_, ml) in enumerate(bolsas):
        for volumen_actual, indices in list(combinaciones.items()):
            nuevo_volumen = volumen_actual + ml
            if nuevo_volumen > limite:
                continue
            nueva_combinacion = indices + (indice,)
            existente = combinaciones.get(nuevo_volumen)
            if existente is None or nueva_combinacion < existente:
                combinaciones[nuevo_volumen] = nueva_combinacion
    candidatos = [volumen
        for volumen in combinaciones
        if volumen >= volumen_solicitado]
    if not candidatos:
        raise ValueError("No se encontró una combinación de bolsas " "completas que cubra la solicitud.")
    volumen_asignado = min(candidatos)
    indices_seleccionados = combinaciones[volumen_asignado]
    seleccionadas = [bolsas[indice]
        for indice in indices_seleccionados]
    return seleccionadas, volumen_asignado

def registrar_emergencia(centro, grupo, rh, volumen_ml, motivo,*, ruta=RUTA_BD, confirmar_volumen=None):
    if grupo not in GRUPOS:
        raise ValueError("Seleccione un grupo sanguíneo válido.")
    if rh not in FACTORES_RH:
        raise ValueError("Seleccione un factor Rh válido.")
    volumen_ml = _validar_cantidad(volumen_ml)
    if not isinstance(motivo, str) or not motivo.strip():
        raise ValueError("Ingrese el motivo de la emergencia.")
    if len(motivo.strip()) > 1000:
        raise ValueError("El motivo no puede superar los 1000 caracteres.")

    fecha = datetime.now(ZoneInfo(ZONA_HORARIA)).isoformat(timespec="seconds")
    with closing(sqlite3.connect(ruta)) as conexion:
        conexion.execute("PRAGMA foreign_keys = ON")
        try:
            #bloqueo
            conexion.execute("BEGIN IMMEDIATE")
            #verificación de hospital
            _datos_centro(conexion, centro)
            #crear tablas en caso de que todavia no existen
            crear_tabla_emergencias(conexion)
            crear_tabla_reservas_emergencia(conexion)
            hoy = fecha_actual()

            #seleccionar donaciones existentes
            bolsas, volumen_asignado = seleccionar_bolsas_emergencia(conexion,grupo,rh,volumen_ml,hoy)

            #si se necesita mas, pedir
            if volumen_asignado > volumen_ml:
                if confirmar_volumen != volumen_asignado:
                    raise ExcesoVolumenError(volumen_ml,volumen_asignado)

            #registarr solicitud pendiente
            cursor = conexion.execute("""
                INSERT INTO DESPACHOS_EMERGENCIA (CENTRO,GRUPO_SANGUINEO,FACTOR_RH,VOLUMEN_ML,MOTIVO,FECHA_SOLICITUD,ESTADO) VALUES (?, ?, ?, ?, ?, ?, ?)""", (
                centro,grupo,rh,volumen_ml,motivo.strip(),fecha,"Pendiente de aprobación"))
            solicitud_id = cursor.lastrowid
            #se reservan las bolsas soliciidas
            for id_bolsa, ml in bolsas:
                actualizacion = conexion.execute("""UPDATE DONACIONES SET ESTADO = 'Reservada' WHERE ID = ? AND ESTADO = 'Disponible' AND FECHA_VENCIMIENTO >= ? """, (id_bolsa, hoy.isoformat()))

                if actualizacion.rowcount != 1:
                    raise ValueError("El stock cambió durante la reserva. " "Vuelva a intentar.")

                #unir bolsa con solicitud
                conexion.execute("""INSERT INTO RESERVAS_EMERGENCIA (SOLICITUD_ID,DONACION_ID,VOLUMEN_ML)VALUES (?, ?, ?)""", (solicitud_id,id_bolsa,ml))

            #junta todo
            conexion.commit()
            return solicitud_id

        except Exception:
            #si algo falla deshace todo
            conexion.rollback()
            raise

def consultar_mis_solicitudes(centro, *, ruta=RUTA_BD):
    solicitudes = []
    with closing(sqlite3.connect(ruta)) as conexion:
        conexion.row_factory = sqlite3.Row
        #verifica que el hospital este en lalista
        _datos_centro(conexion, centro)
        # solicitudes programadas
        tablas = {
            fila[0]
            for fila in conexion.execute("""SELECT name FROM sqlite_master WHERE type = 'table' """)}
        if "DESPACHOS_PROGRAMADOS" in tablas:
            columnas = {
                fila[1]
                for fila in conexion.execute("PRAGMA table_info(DESPACHOS_PROGRAMADOS)")}

            volumen = ("VOLUMEN_ML"
                       if "VOLUMEN_ML" in columnas 
                       else "NULL AS VOLUMEN_ML")

            filas = conexion.execute(f"""SELECT ID,CENTRO,GRUPO_SANGUINEO,FACTOR_RH,CANTIDAD,{volumen},FECHA_DESPACHO,HORA_DESPACHO, ESTADO FROM DESPACHOS_PROGRAMADOS WHERE CENTRO = ? ORDER BY ID DESC """, (centro,)).fetchall()
            for fila in filas:
                solicitud = dict(fila)
                solicitud["TIPO"] = "Programado"
                solicitudes.append(solicitud)

        #solicitudes de emergncia
        if "DESPACHOS_EMERGENCIA" in tablas:
            filas = conexion.execute("""SELECT ID,CENTRO,GRUPO_SANGUINEO,FACTOR_RH,VOLUMEN_ML,MOTIVO,FECHA_SOLICITUD,ESTADO FROM DESPACHOS_EMERGENCIA WHERE CENTRO = ? ORDER BY ID DESC """, (centro,)).fetchall()
            for fila in filas:
                solicitud = dict(fila)
                solicitud["TIPO"] = "Emergencia"
                solicitudes.append(solicitud)
    return solicitudes

def consultar_solicitudes_pendientes(*, ruta=RUTA_BD):
    """Obtiene todas las solicitudes, priorizando emergencias."""
    resultado = []
    ahora = datetime.now(ZoneInfo(ZONA_HORARIA))
    fecha_hoy = ahora.strftime("%Y-%m-%d")
    hora_actual = ahora.strftime("%H:%M")

    with closing(sqlite3.connect(ruta)) as conexion:
        conexion.row_factory = sqlite3.Row
        tablas = {
            fila[0]
            for fila in conexion.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}

        #emergencias tienen prioridad alta ( vienen primero)
        if "DESPACHOS_EMERGENCIA" in tablas:
            filas = conexion.execute("""SELECT ID, CENTRO, GRUPO_SANGUINEO,FACTOR_RH, VOLUMEN_ML, MOTIVO,FECHA_SOLICITUD, ESTADO FROM DESPACHOS_EMERGENCIA
                WHERE ESTADO IN ('Pendiente', 'Pendiente de aprobación') ORDER BY FECHA_SOLICITUD ASC, ID ASC """).fetchall()

            for fila in filas:
                solicitud = dict(fila)
                solicitud["TIPO"] = "Emergencia"
                resultado.append(solicitud)

        #programados no tiene prioridad (normal)
        if "DESPACHOS_PROGRAMADOS" in tablas:
            columnas = {fila[1] for fila in conexion.execute("PRAGMA table_info(DESPACHOS_PROGRAMADOS)")}

            volumen = ("VOLUMEN_ML"
                if "VOLUMEN_ML" in columnas
                else "NULL AS VOLUMEN_ML")

            filas = conexion.execute(f"""SELECT ID, CENTRO, GRUPO_SANGUINEO,FACTOR_RH, CANTIDAD, {volumen},FECHA_DESPACHO, HORA_DESPACHO, ESTADO
                FROM DESPACHOS_PROGRAMADOS WHERE ESTADO IN ('Pendiente', 'Pendiente de aprobación') AND(FECHA_DESPACHO > ? OR (FECHA_DESPACHO = ? AND HORA_DESPACHO > ?)) ORDER BY FECHA_DESPACHO ASC,HORA_DESPACHO ASC, ID ASC""", (fecha_hoy,fecha_hoy,hora_actual)).fetchall()

            for fila in filas:
                solicitud = dict(fila)
                solicitud["TIPO"] = "Programado"
                resultado.append(solicitud)
    return resultado

def preparar_aprobaciones(conexion):
    """Prepara el seguimiento de decisiones sin borrar solicitudes."""
    crear_tabla_emergencias(conexion)
    for tabla in ("DESPACHOS_PROGRAMADOS", "DESPACHOS_EMERGENCIA"):
        columnas = {fila[1]
            for fila in conexion.execute(f"PRAGMA table_info({tabla})")}

        nuevos_campos = { "DECIDIDO_POR": "INTEGER", "FECHA_DECISION": "TEXT", "MOTIVO_RECHAZO": "TEXT"}
        for nombre, tipo in nuevos_campos.items():
            if nombre not in columnas:
                conexion.execute(f"ALTER TABLE {tabla} ADD COLUMN {nombre} {tipo}")

    #reservas de donaciones a despachos programados
    conexion.execute("""CREATE TABLE IF NOT EXISTS RESERVAS_PROGRAMADAS (ID INTEGER PRIMARY KEY AUTOINCREMENT,SOLICITUD_ID INTEGER NOT NULL REFERENCES DESPACHOS_PROGRAMADOS(ID),
            DONACION_ID INTEGER NOT NULL UNIQUE REFERENCES DONACIONES(ID),VOLUMEN_ML INTEGER NOT NULL CHECK (VOLUMEN_ML > 0)) """)

def validar_enfermero(conexion, empleado_id, accion="aprobar o rechazar despachos"):
    fila = conexion.execute("""SELECT ROL FROM PERSONAL WHERE ID_EMPLEADO = ? """, (empleado_id,)).fetchone()
    if fila is None or str(fila[0]).strip().casefold() != "enfermero":
        raise PermissionError(f"Solo un enfermero autorizado puede {accion}.")

def tabla_solicitud(tipo):
    if tipo == "Emergencia":
        return "DESPACHOS_EMERGENCIA"
    if tipo == "Programado":
        return "DESPACHOS_PROGRAMADOS"
    raise ValueError("Tipo de solicitud inválido.")


def aprobar_solicitud(tipo, solicitud_id, empleado_id, *, ruta=RUTA_BD):
    tabla = tabla_solicitud(tipo)
    with closing(sqlite3.connect(ruta)) as conexion:
        conexion.execute("PRAGMA foreign_keys = ON")
        try:
            conexion.execute("BEGIN IMMEDIATE")
            validar_enfermero(conexion, empleado_id)
            preparar_aprobaciones(conexion)
            solicitud = conexion.execute(f"SELECT * FROM {tabla} WHERE ID = ?",(solicitud_id,)).fetchone()

            if solicitud is None:
                raise ValueError("La solicitud no existe.")
            columnas = [fila[1]
                for fila in conexion.execute(f"PRAGMA table_info({tabla})")]
            datos = dict(zip(columnas, solicitud))

            if datos["ESTADO"] not in ("Pendiente", "Pendiente de aprobación"):
                raise ValueError("Esta solicitud ya fue resuelta.")
            hoy = fecha_actual()
            ahora = datetime.now(ZoneInfo(ZONA_HORARIA))

            if tipo == "Emergencia":
                #la emergencia reserva la docnaión al registrarse
                reservas = conexion.execute("""SELECT r.DONACION_ID,r.VOLUMEN_ML,d.CANTIDAD,d.ESTADO,d.FECHA_VENCIMIENTO
                    FROM RESERVAS_EMERGENCIA AS r JOIN DONACIONES AS d ON d.ID = r.DONACION_ID WHERE r.SOLICITUD_ID = ? """, (solicitud_id,)).fetchall()

                if not reservas:
                    raise ValueError("Esta emergencia no tiene bolsas reservadas. " "No es posible aprobarla.")

                for donacion_id, ml_reservados, ml_real, estado, vencimiento in reservas:
                    if (estado != "Reservada" or vencimiento < hoy.isoformat() or ml_reservados != ml_real):
                        raise ValueError("Una bolsa reservada ya no es apta. " "Revise la solicitud antes de aprobar.")

                volumen_asignado = sum(fila[1] for fila in reservas)

                if volumen_asignado < datos["VOLUMEN_ML"]:
                    raise ValueError("El volumen reservado no cubre la emergencia.")

            else:
                #para despachso programdos no se puedne aprobar si es que la fecha ya paso 
                fecha_despacho = datetime.strptime(datos["FECHA_DESPACHO"] + " " + datos["HORA_DESPACHO"],"%Y-%m-%d %H:%M").replace(tzinfo=ZoneInfo(ZONA_HORARIA))

                if fecha_despacho <= ahora:
                    raise ValueError("No puede aprobar un despacho cuya fecha ya pasó.")

                volumen_pedido = datos["VOLUMEN_ML"]
                if volumen_pedido is None:
                    raise ValueError("Esta solicitud antigua está expresada en bolsas. " "Debe revisarse y registrarse su volumen en mL " "antes de aprobar.")

                #crear tabla si no existe
                crear_tabla_reservas_emergencia(conexion)
                bolsas, volumen_asignado = seleccionar_bolsas_emergencia(conexion,datos["GRUPO_SANGUINEO"],datos["FACTOR_RH"],volumen_pedido,hoy)

                #no asiganr volumen extra sin autorización
                if volumen_asignado != volumen_pedido:
                    raise ValueError(f"Las bolsas completas suman {volumen_asignado} mL, " f"pero se solicitaron {volumen_pedido} mL. " "No se puede aprobar automáticamente esta combinación.")
                for donacion_id, ml in bolsas:
                    resultado = conexion.execute("""UPDATE DONACIONES SET ESTADO = 'Reservada' WHERE ID = ? AND ESTADO = 'Disponible' AND FECHA_VENCIMIENTO >= ? """, (donacion_id, hoy.isoformat()))
                    if resultado.rowcount != 1:
                        raise ValueError("El inventario cambió. Actualice las solicitudes.")

                    conexion.execute("""INSERT INTO RESERVAS_PROGRAMADAS (SOLICITUD_ID, DONACION_ID, VOLUMEN_ML) VALUES (?, ?, ?)""", (solicitud_id, donacion_id, ml))
            fecha_decision = ahora.isoformat(timespec="seconds")
            resultado = conexion.execute(f"""UPDATE {tabla} SET ESTADO = 'Aprobada', DECIDIDO_POR = ?, FECHA_DECISION = ? WHERE ID = ? AND ESTADO IN ('Pendiente', 'Pendiente de aprobación')""", (
                empleado_id,fecha_decision,solicitud_id))

            if resultado.rowcount != 1:
                raise ValueError("La solicitud cambió de estado.")
            conexion.commit()
            return "Solicitud aprobada correctamente."
        except Exception:
            conexion.rollback()
            raise

def rechazar_solicitud(tipo, solicitud_id, empleado_id, motivo, *, ruta=RUTA_BD):
    tabla = tabla_solicitud(tipo)
    if not isinstance(motivo, str) or not motivo.strip():
        raise ValueError("Debe ingresar un motivo de rechazo.")
    motivo = motivo.strip()
    if len(motivo) > 1000:
        raise ValueError("El motivo no puede superar 1000 caracteres.")
    with closing(sqlite3.connect(ruta)) as conexion:
        conexion.execute("PRAGMA foreign_keys = ON")
        try:
            conexion.execute("BEGIN IMMEDIATE")
            validar_enfermero(conexion, empleado_id)
            preparar_aprobaciones(conexion)
            fila = conexion.execute(f"SELECT ESTADO FROM {tabla} WHERE ID = ?",(solicitud_id,)).fetchone()
            if fila is None:
                raise ValueError("La solicitud no existe.")
            if fila[0] not in ("Pendiente", "Pendiente de aprobación"):
                raise ValueError("La solicitud ya fue resuelta.")
            ahora = datetime.now(ZoneInfo(ZONA_HORARIA))
            hoy = ahora.date().isoformat()

            #las emergencias pueden tener donaciones guardadas
            if tipo == "Emergencia":
                crear_tabla_reservas_emergencia(conexion)
                reservas = conexion.execute("""SELECT DONACION_ID FROM RESERVAS_EMERGENCIA WHERE SOLICITUD_ID = ? """, (solicitud_id,)).fetchall()
                for (donacion_id,) in reservas:
                    #si aún esta vigente, vuelve a Disponible, si venció queda Vencida.
                    conexion.execute("""UPDATE DONACIONES SET ESTADO = CASE WHEN FECHA_VENCIMIENTO >= ? THEN 'Disponible' ELSE 'Vencida' END WHERE ID = ? AND ESTADO = 'Reservada' """, (hoy, donacion_id))

                #eliminar vinculos de una reserva rechazada,permitiendo futuras reservas de las bolsas liberadas
                conexion.execute("""DELETE FROM RESERVAS_EMERGENCIA WHERE SOLICITUD_ID = ?""", (solicitud_id,))
            resultado = conexion.execute(f"""UPDATE {tabla} SET ESTADO = 'Rechazada',DECIDIDO_POR = ?,FECHA_DECISION = ?,MOTIVO_RECHAZO = ?WHERE ID = ? AND ESTADO IN ('Pendiente', 'Pendiente de aprobación') """, (
                empleado_id,ahora.isoformat(timespec="seconds"),motivo,solicitud_id))
            if resultado.rowcount != 1:
                raise ValueError("La solicitud cambió de estado.")
            conexion.commit()
            return "Solicitud rechazada correctamente."
        except Exception:
            conexion.rollback()
            raise

def consultar_bolsas_asignadas(conexion, tipo, solicitud_id):
    tablas_reservas = {
        "Emergencia": "RESERVAS_EMERGENCIA",
        "Programado": "RESERVAS_PROGRAMADAS",
    }
    tabla = tablas_reservas.get(tipo)
    if tabla is None:
        raise ValueError("Tipo de solicitud inválido.")
    if conexion.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (tabla,)
    ).fetchone() is None:
        return []
    filas = conexion.execute(f"""
        SELECT u.ID, r.VOLUMEN_ML, u.CANTIDAD AS VOLUMEN_REAL_ML,
               u.FECHA_VENCIMIENTO, u.ESTADO
        FROM {tabla} AS r JOIN DONACIONES AS u ON u.ID = r.DONACION_ID
        WHERE r.SOLICITUD_ID = ?
        ORDER BY u.FECHA_VENCIMIENTO ASC, u.ID ASC
    """, (solicitud_id,))
    return [dict(fila) for fila in filas]


def consultar_detalle_solicitud(tipo, solicitud_id, *, ruta=RUTA_BD):
    tabla = tabla_solicitud(tipo)
    hoy = fecha_actual().isoformat()
    with closing(sqlite3.connect(ruta)) as conexion:
        conexion.row_factory = sqlite3.Row
        solicitud = conexion.execute(f"SELECT * FROM {tabla} WHERE ID = ?",(solicitud_id,)).fetchone()
        if solicitud is None:
            raise ValueError("La solicitud no existe.")
        datos = dict(solicitud)
        grupo = datos["GRUPO_SANGUINEO"]
        rh = datos["FACTOR_RH"]
        #stock disponible en el moemnto de el tipo de sangre y factor rh 
        disponibles = conexion.execute("""SELECT u.ID, u.CANTIDAD AS VOLUMEN_ML, u.FECHA_VENCIMIENTO, u.ESTADO FROM DONACIONES AS u LEFT JOIN DONANTES AS d
            ON d.ID = u.DONANTE WHERE u.ESTADO = 'Disponible' AND u.FECHA_VENCIMIENTO >= ? AND COALESCE(u.TIPO_SANGRE, d.GRUPO_SANGUINEO) = ? AND COALESCE(u.FACTOR_RH, d.FACTOR_RH) = ?
            AND u.CANTIDAD > 0 ORDER BY u.FECHA_VENCIMIENTO ASC, u.ID ASC """, (hoy, grupo, rh)).fetchall()
        bolsas_disponibles = [dict(fila) for fila in disponibles]
        bolsas_asignadas = consultar_bolsas_asignadas(conexion, tipo, solicitud_id)
        total_disponible = sum(
            bolsa["VOLUMEN_ML"]
            for bolsa in bolsas_disponibles)

        total_asignado = sum(bolsa["VOLUMEN_ML"]
            for bolsa in bolsas_asignadas)

        return {"solicitud": datos,"tipo": tipo, "bolsas_disponibles": bolsas_disponibles,"bolsas_asignadas": bolsas_asignadas,"total_disponible_ml": total_disponible,"total_asignado_ml": total_asignado}
