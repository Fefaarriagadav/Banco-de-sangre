import sqlite3
from contextlib import closing
from datetime import datetime
from zoneinfo import ZoneInfo
from datos.configuracion import RUTA_BD
from servicios.vencimientos import ZONA_HORARIA, fecha_actual
from servicios.despachos import (
    GRUPOS,
    FACTORES_RH,
    crear_tabla_emergencias,
    preparar_aprobaciones,
    validar_enfermero,
    _volumen_disponible,
)


def migrar_redirecciones(conexion):
    """H13-T2: Crea tablas de disponibilidad externa y trazabilidad sin borrar datos."""
    conexion.execute("""
        CREATE TABLE IF NOT EXISTS CENTROS_MEDICOS (
            NOMBRE TEXT PRIMARY KEY NOT NULL,
            DIRECCION TEXT,
            COMUNA TEXT
        )
    """)

    conexion.execute("""
        CREATE TABLE IF NOT EXISTS CENTROS_EXTERNOS_STOCK (
            ID INTEGER PRIMARY KEY AUTOINCREMENT,
            CENTRO TEXT NOT NULL REFERENCES CENTROS_MEDICOS(NOMBRE),
            GRUPO_SANGUINEO TEXT NOT NULL CHECK (GRUPO_SANGUINEO IN ('A', 'B', 'AB', 'O')),
            FACTOR_RH TEXT NOT NULL CHECK (FACTOR_RH IN ('+', '-')),
            VOLUMEN_DISPONIBLE_ML INTEGER NOT NULL CHECK (VOLUMEN_DISPONIBLE_ML >= 0),
            PRIORIDAD_CERCANIA INTEGER NOT NULL DEFAULT 1,
            ACTUALIZADO_EN TEXT NOT NULL,
            UNIQUE(CENTRO, GRUPO_SANGUINEO, FACTOR_RH)
        )
    """)

    crear_tabla_emergencias(conexion)

    conexion.execute("""
        CREATE TABLE IF NOT EXISTS REDIRECCIONES_EMERGENCIA (
            ID INTEGER PRIMARY KEY AUTOINCREMENT,
            ORDEN_ID INTEGER NOT NULL UNIQUE REFERENCES DESPACHOS_EMERGENCIA(ID),
            CENTRO_SOLICITANTE TEXT NOT NULL,
            CENTRO_EXTERNO_DESTINO TEXT,
            GRUPO_SANGUINEO TEXT NOT NULL,
            FACTOR_RH TEXT NOT NULL,
            VOLUMEN_REQUERIDO_ML INTEGER NOT NULL,
            STOCK_PROPIO_DISPONIBLE_ML INTEGER NOT NULL,
            MOTIVO TEXT NOT NULL,
            ESTADO_REDIRECCION TEXT NOT NULL,
            EMPLEADO_ID INTEGER NOT NULL REFERENCES PERSONAL(ID_EMPLEADO),
            FECHA_HORA TEXT NOT NULL
        )
    """)

    # Semilla inicial de centros externos si el catálogo está vacío
    total = conexion.execute("SELECT COUNT(*) FROM CENTROS_EXTERNOS_STOCK").fetchone()[0]
    if total == 0:
        ahora = datetime.now(ZoneInfo(ZONA_HORARIA)).isoformat(timespec="seconds")
        centros_seed = [
            ("Hospital Guillermo Grant Benavente", "Av. San Martín 1436", "Concepción"),
            ("Hospital Las Higueras", "Alto Horno 777", "Talcahuano"),
            ("Clínica Biobío", "Av. Jorge Alessandri 3515", "Talcahuano"),
        ]
        for nombre, direccion, comuna in centros_seed:
            conexion.execute(
                "INSERT OR IGNORE INTO CENTROS_MEDICOS (NOMBRE, DIRECCION, COMUNA) VALUES (?, ?, ?)",
                (nombre, direccion, comuna),
            )

        stocks_seed = [
            ("Hospital Guillermo Grant Benavente", "O", "+", 2500, 1),
            ("Hospital Guillermo Grant Benavente", "O", "-", 1500, 1),
            ("Hospital Guillermo Grant Benavente", "A", "+", 1800, 1),
            ("Hospital Las Higueras", "O", "+", 1200, 2),
            ("Hospital Las Higueras", "B", "+", 1500, 2),
            ("Hospital Las Higueras", "A", "-", 1000, 2),
            ("Clínica Biobío", "A", "+", 2000, 3),
            ("Clínica Biobío", "AB", "+", 1200, 3),
        ]
        for centro, grupo, rh, vol, prio in stocks_seed:
            conexion.execute("""
                INSERT OR IGNORE INTO CENTROS_EXTERNOS_STOCK
                (CENTRO, GRUPO_SANGUINEO, FACTOR_RH, VOLUMEN_DISPONIBLE_ML, PRIORIDAD_CERCANIA, ACTUALIZADO_EN)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (centro, grupo, rh, vol, prio, ahora))

def _volumen_reservado_apto(conexion, orden_id, hoy):
    fila = conexion.execute(
        """
        SELECT COALESCE(SUM(r.VOLUMEN_ML), 0)
        FROM RESERVAS_EMERGENCIA AS r
        JOIN DONACIONES AS d ON d.ID = r.DONACION_ID
        WHERE r.SOLICITUD_ID = ?
          AND d.ESTADO = 'Reservada'
          AND d.ESTADO_LABORATORIO = 'Liberada'
          AND d.FECHA_VENCIMIENTO >= ?
          AND r.VOLUMEN_ML = d.CANTIDAD
          AND r.VOLUMEN_ML > 0
        """,
        (orden_id, hoy.isoformat()),
    ).fetchone()

    return int(fila[0])

def evaluar_deficit_y_seleccionar_centro(
    orden_id,
    empleado_id,
    *,
    ruta=RUTA_BD,
    ahora=None,
):
    """
    H13-T1: Evalúa si el stock propio es insuficiente para la orden de emergencia
    y selecciona un centro externo compatible sin modificar inventario local ni de terceros.
    """
    with closing(sqlite3.connect(ruta)) as conexion:
        conexion.row_factory = sqlite3.Row
        validar_enfermero(conexion, empleado_id, accion="evaluar redirección de emergencias")
        migrar_redirecciones(conexion)

        orden = conexion.execute(
            "SELECT * FROM DESPACHOS_EMERGENCIA WHERE ID = ?",
            (orden_id,),
        ).fetchone()
        if orden is None:
            raise ValueError("La orden de emergencia indicada no existe.")

        datos_orden = dict(orden)
        grupo = datos_orden["GRUPO_SANGUINEO"]
        rh = datos_orden["FACTOR_RH"]
        requerido_ml = int(datos_orden["VOLUMEN_ML"])
        solicitante = datos_orden["CENTRO"]

        hoy = fecha_actual(ahora)
        disponible_propio_ml = _volumen_disponible(conexion, grupo, rh, hoy)

        # También consideramos bolsas ya reservadas específicamente a esta orden
        reservado_orden_ml = 0
        tiene_reservas = conexion.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='RESERVAS_EMERGENCIA'"
        ).fetchone()
        if tiene_reservas:
            reservado_orden_ml = _volumen_reservado_apto(
                conexion, orden_id, hoy
            )

        cobertura_propia_ml = disponible_propio_ml + reservado_orden_ml

        # Criterio: Si el stock propio cubre la orden, el flujo continúa normal en H9/H11
        if cobertura_propia_ml >= requerido_ml:
            return {
                "requiere_redireccion": False,
                "orden_id": orden_id,
                "grupo_sanguineo": grupo,
                "factor_rh": rh,
                "volumen_requerido_ml": requerido_ml,
                "stock_propio_ml": cobertura_propia_ml,
                "centro_seleccionado": None,
                "mensaje": (
                    f"Stock propio suficiente ({cobertura_propia_ml} mL disponibles "
                    f"para {requerido_ml} mL requeridos). No requiere redirección."
                ),
            }

        # Hay déficit: buscar centros externos distintos al solicitante con disponibilidad suficiente
        candidatos = conexion.execute("""
            SELECT s.ID, s.CENTRO, c.DIRECCION, c.COMUNA,
                   s.VOLUMEN_DISPONIBLE_ML, s.PRIORIDAD_CERCANIA
            FROM CENTROS_EXTERNOS_STOCK AS s
            JOIN CENTROS_MEDICOS AS c ON c.NOMBRE = s.CENTRO
            WHERE s.GRUPO_SANGUINEO = ?
              AND s.FACTOR_RH = ?
              AND s.VOLUMEN_DISPONIBLE_ML >= ?
              AND s.CENTRO != ?
            ORDER BY s.PRIORIDAD_CERCANIA ASC, s.VOLUMEN_DISPONIBLE_ML DESC, s.CENTRO ASC
        """, (grupo, rh, requerido_ml, solicitante)).fetchall()

        if not candidatos:
            return {
                "requiere_redireccion": True,
                "hay_centro_disponible": False,
                "orden_id": orden_id,
                "centro_solicitante": solicitante,
                "grupo_sanguineo": grupo,
                "factor_rh": rh,
                "volumen_requerido_ml": requerido_ml,
                "stock_propio_ml": cobertura_propia_ml,
                "centro_seleccionado": None,
                "mensaje": (
                    f"Déficit detectado ({cobertura_propia_ml} mL propios vs {requerido_ml} mL requeridos), "
                    f"pero ningún centro externo cuenta con stock suficiente de {grupo}{rh}."
                ),
            }
        lista_candidatos = [dict(c) for c in candidatos]
        elegido = lista_candidatos[0]
        return {
            "requiere_redireccion": True,
            "hay_centro_disponible": True,
            "orden_id": orden_id,
            "centro_solicitante": solicitante,
            "grupo_sanguineo": grupo,
            "factor_rh": rh,
            "volumen_requerido_ml": requerido_ml,
            "stock_propio_ml": cobertura_propia_ml,
            "centro_seleccionado": elegido,
            "centros_candidatos": lista_candidatos,
            "mensaje": (
                f"Stock propio insuficiente ({cobertura_propia_ml} mL disponibles). "
                f"Se encontraron {len(lista_candidatos)} centros externos disponibles."
            ),
        }


def ejecutar_redireccion_emergencia(
    orden_id,
    empleado_id,
    *,
    centro_elegido=None,
    ruta=RUTA_BD,
    ahora=None,
):
    """
    H13-T1 + H13-T2: Evalúa déficit, previene duplicados, persiste trazabilidad
    y actualiza el estado de la orden de emergencia sin tocar el inventario propio.
    """
    if not empleado_id:
        raise ValueError("El identificador del empleado es obligatorio para registrar la redirección.")

    momento = datetime.now(ZoneInfo(ZONA_HORARIA)) if ahora is None else ahora
    if momento.tzinfo is None:
        momento = momento.replace(tzinfo=ZoneInfo(ZONA_HORARIA))
    fecha_hora = momento.isoformat(timespec="seconds")

    with closing(sqlite3.connect(ruta)) as conexion:
        conexion.execute("PRAGMA foreign_keys = ON")
        try:
            conexion.execute("BEGIN IMMEDIATE")
            validar_enfermero(conexion, empleado_id, accion="redirigir órdenes de emergencia")
            preparar_aprobaciones(conexion)
            migrar_redirecciones(conexion)

            orden = conexion.execute(
                "SELECT * FROM DESPACHOS_EMERGENCIA WHERE ID = ?",
                (orden_id,),
            ).fetchone()
            if orden is None:
                raise ValueError("La orden de emergencia no existe.")

            cols = [f[1] for f in conexion.execute("PRAGMA table_info(DESPACHOS_EMERGENCIA)")]
            datos_orden = dict(zip(cols, orden))

            # Prevención de duplicados
            existente = conexion.execute(
                "SELECT ID, CENTRO_EXTERNO_DESTINO, ESTADO_REDIRECCION FROM REDIRECCIONES_EMERGENCIA WHERE ORDEN_ID = ?",
                (orden_id,),
            ).fetchone()
            if existente is not None:
                raise ValueError(
                    f"La orden #{orden_id} ya fue procesada para redirección "
                    f"(Estado: {existente[2]})."
                )

            if datos_orden["ESTADO"] not in ("Pendiente", "Pendiente de aprobación", "En déficit"):
                raise ValueError(f"La orden #{orden_id} no puede redirigirse en estado '{datos_orden['ESTADO']}'.")

            grupo = datos_orden["GRUPO_SANGUINEO"]
            rh = datos_orden["FACTOR_RH"]
            requerido_ml = int(datos_orden["VOLUMEN_ML"])
            solicitante = datos_orden["CENTRO"]

            hoy = fecha_actual(momento)
            disponible_propio_ml = _volumen_disponible(conexion, grupo, rh, hoy)

            reservado_orden_ml = 0
            tiene_reservas = conexion.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='RESERVAS_EMERGENCIA'"
            ).fetchone()
            if tiene_reservas:
                reservado_orden_ml = _volumen_reservado_apto(
                    conexion, orden_id, hoy
                )

            cobertura_propia_ml = disponible_propio_ml + reservado_orden_ml
            if cobertura_propia_ml >= requerido_ml:
                raise ValueError(
                    f"El stock propio ({cobertura_propia_ml} mL) cubre la solicitud ({requerido_ml} mL). "
                    "Puede aprobarla directamente sin redirigir."
                )

            # Si tenía reservas parciales bloqueadas, las liberamos antes de derivar para no retener stock local
            if tiene_reservas:
                reservas = conexion.execute(
                    "SELECT DONACION_ID FROM RESERVAS_EMERGENCIA WHERE SOLICITUD_ID = ?",
                    (orden_id,),
                ).fetchall()
                for (don_id,) in reservas:
                    conexion.execute(
                        """
                        UPDATE DONACIONES
                        SET ESTADO = CASE
                            WHEN FECHA_VENCIMIENTO < ?
                                THEN 'Vencida'
                            WHEN ESTADO_LABORATORIO = 'Bloqueada'
                                THEN 'Bloqueada'
                            WHEN ESTADO_LABORATORIO = 'Liberada'
                                 AND FECHA_VENCIMIENTO >= ?
                                THEN 'Disponible'
                            ELSE 'Pendiente de análisis'
                        END
                        WHERE ID = ? AND ESTADO = 'Reservada'
                        """,
                        (
                            hoy.isoformat(),
                            hoy.isoformat(),
                            don_id,
                        ),
                    )
                conexion.execute("DELETE FROM RESERVAS_EMERGENCIA WHERE SOLICITUD_ID = ?", (orden_id,))

            if centro_elegido:
                candidato = conexion.execute("""
                    SELECT s.CENTRO, c.DIRECCION, c.COMUNA, s.VOLUMEN_DISPONIBLE_ML
                    FROM CENTROS_EXTERNOS_STOCK AS s
                    JOIN CENTROS_MEDICOS AS c ON c.NOMBRE = s.CENTRO
                    WHERE s.CENTRO = ?
                      AND s.GRUPO_SANGUINEO = ?
                      AND s.FACTOR_RH = ?
                      AND s.VOLUMEN_DISPONIBLE_ML >= ?
                      AND s.CENTRO != ?
                """, (centro_elegido, grupo, rh, requerido_ml, solicitante)).fetchone()
                if candidato is None:
                    raise ValueError(f"El centro '{centro_elegido}' no cuenta con stock suficiente para cubrir la orden.")
            else:
                candidato = conexion.execute("""
                    SELECT s.CENTRO, c.DIRECCION, c.COMUNA, s.VOLUMEN_DISPONIBLE_ML
                    FROM CENTROS_EXTERNOS_STOCK AS s
                    JOIN CENTROS_MEDICOS AS c ON c.NOMBRE = s.CENTRO
                    WHERE s.GRUPO_SANGUINEO = ?
                      AND s.FACTOR_RH = ?
                      AND s.VOLUMEN_DISPONIBLE_ML >= ?
                      AND s.CENTRO != ?
                    ORDER BY s.PRIORIDAD_CERCANIA ASC, s.VOLUMEN_DISPONIBLE_ML DESC, s.CENTRO ASC
                    LIMIT 1
                """, (grupo, rh, requerido_ml, solicitante)).fetchone()

            motivo_deficit = (
                f"Déficit de stock propio ({disponible_propio_ml} mL disponibles "
                f"vs {requerido_ml} mL solicitados)"
            )

            if candidato is None:
                # Sin alternativas: registrar trazabilidad como No resuelta / Sin centro disponible
                estado_redireccion = "Sin centro externo disponible"
                cursor = conexion.execute("""
                    INSERT INTO REDIRECCIONES_EMERGENCIA (
                        ORDEN_ID, CENTRO_SOLICITANTE, CENTRO_EXTERNO_DESTINO,
                        GRUPO_SANGUINEO, FACTOR_RH, VOLUMEN_REQUERIDO_ML,
                        STOCK_PROPIO_DISPONIBLE_ML, MOTIVO, ESTADO_REDIRECCION,
                        EMPLEADO_ID, FECHA_HORA
                    ) VALUES (?, ?, NULL, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    orden_id, solicitante, grupo, rh, requerido_ml,
                    disponible_propio_ml, motivo_deficit, estado_redireccion,
                    empleado_id, fecha_hora,
                ))
                conexion.execute("""
                    UPDATE DESPACHOS_EMERGENCIA
                    SET ESTADO = 'No resuelta - Sin stock externo',
                        DECIDIDO_POR = ?,
                        FECHA_DECISION = ?
                    WHERE ID = ?
                """, (empleado_id, fecha_hora, orden_id))
                conexion.commit()
                return {
                    "redirigida": False,
                    "redireccion_id": cursor.lastrowid,
                    "orden_id": orden_id,
                    "centro_destino": None,
                    "estado_redireccion": estado_redireccion,
                    "motivo": motivo_deficit,
                    "fecha_hora": fecha_hora,
                    "mensaje": (
                        f"ALERTA CRÍTICA: Ningún centro externo cuenta con {requerido_ml} mL "
                        f"de {grupo}{rh}. La orden #{orden_id} quedó registrada como no resuelta "
                        "para gestión manual urgente."
                    ),
                }

            centro_destino, direccion_dest, comuna_dest, vol_ext = candidato
            estado_redireccion = "Pendiente de confirmación del centro"

            cursor = conexion.execute("""
                INSERT INTO REDIRECCIONES_EMERGENCIA (
                    ORDEN_ID, CENTRO_SOLICITANTE, CENTRO_EXTERNO_DESTINO,
                    GRUPO_SANGUINEO, FACTOR_RH, VOLUMEN_REQUERIDO_ML,
                    STOCK_PROPIO_DISPONIBLE_ML, MOTIVO, ESTADO_REDIRECCION,
                    EMPLEADO_ID, FECHA_HORA
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                orden_id, solicitante, centro_destino, grupo, rh, requerido_ml,
                disponible_propio_ml, motivo_deficit, estado_redireccion,
                empleado_id, fecha_hora,
            ))

            conexion.execute("""
                UPDATE DESPACHOS_EMERGENCIA
                SET ESTADO = 'Redirigida a centro externo',
                    DECIDIDO_POR = ?,
                    FECHA_DECISION = ?
                WHERE ID = ?
            """, (empleado_id, fecha_hora, orden_id))

            conexion.commit()
            return {
                "redirigida": True,
                "redireccion_id": cursor.lastrowid,
                "orden_id": orden_id,
                "centro_destino": centro_destino,
                "direccion_destino": f"{direccion_dest}, {comuna_dest}",
                "volumen_externo_ml": vol_ext,
                "estado_redireccion": estado_redireccion,
                "motivo": motivo_deficit,
                "fecha_hora": fecha_hora,
                "mensaje": (
                    f"Orden #{orden_id} redirigida automáticamente a {centro_destino}.\n"
                    f"Motivo: {motivo_deficit}.\n"
                    f"Estado: {estado_redireccion} (no descuenta stock local)."
                ),
            }
        except Exception:
            conexion.rollback()
            raise


def consultar_redirecciones(*, ruta=RUTA_BD):
    """H13-T3: Consulta el historial completo de órdenes redirigidas o sin cobertura."""
    with closing(sqlite3.connect(ruta)) as conexion:
        conexion.row_factory = sqlite3.Row
        migrar_redirecciones(conexion)
        filas = conexion.execute("""
            SELECT r.*, p.NOMBRE AS NOMBRE_EMPLEADO
            FROM REDIRECCIONES_EMERGENCIA AS r
            LEFT JOIN PERSONAL AS p ON p.ID_EMPLEADO = r.EMPLEADO_ID
            ORDER BY r.ID DESC
        """).fetchall()
        return [dict(f) for f in filas]