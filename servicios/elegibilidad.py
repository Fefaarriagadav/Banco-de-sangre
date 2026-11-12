import sqlite3
import unicodedata
from contextlib import contextmanager
from datetime import date, datetime
from datos.configuracion import RUTA_BD

# Estados posibles del donante en la base de datos.
APTO = "Donante apto"
TEMPORAL = "Donante NO apto temporalmente"
PERMANENTE = "Donante NO apto PERMANENTEMENTE"
RESULTADOS = (APTO, TEMPORAL, PERMANENTE)
FORMATO_FECHA = "%d-%m-%Y"

# Un donante puede ser convocado si está apto, o si su restricción temporal ya terminó.
# Una restricción temporal SIN fecha final (datos antiguos) se considera vigente.
# El parámetro "?" es la fecha de hoy en formato ISO (AAAA-MM-DD).
SQL_HABILITADO = ("(ELEGIBLE = 'Donante apto' OR (ELEGIBLE = 'Donante NO apto temporalmente' "
                  "AND INHABILITACION_FIN IS NOT NULL AND INHABILITACION_FIN < ?))")


@contextmanager
def conectar(ruta=RUTA_BD):
    # Abre una conexión reutilizable para cada operación de lectura o escritura.
    conexion = sqlite3.connect(ruta)
    conexion.row_factory = sqlite3.Row
    conexion.execute("PRAGMA foreign_keys = ON")
    try:
        with conexion:
            yield conexion
    finally:
        conexion.close()


def validar_id(valor):
    # Normaliza y valida el identificador antes de usarlo en consultas.
    texto = str(valor).strip()
    if not texto.isascii() or not texto.isdecimal() or int(texto) <= 0:
        raise ValueError("Ingrese un ID de donante válido.")
    return int(texto)


def consultar_donante(donante_id, ruta=RUTA_BD):
    # Recupera la información básica del donante para mostrarla en la interfaz.
    donante_id = validar_id(donante_id)
    with conectar(ruta) as conexion:
        fila = conexion.execute("""SELECT ID, NOMBRE, APELLIDO, ELEGIBLE AS RESULTADO, INHABILITACION_INICIO AS INICIO, INHABILITACION_FIN AS FIN FROM DONANTES WHERE ID = ? """, (donante_id,)).fetchone()
    if fila is None:
        raise ValueError("No existe un donante con ese ID.")
    return dict(fila)

def consultar_donanteSangre(donante_id, ruta=RUTA_BD): #nose si puedo modificar esta función, pero agregue una copia para poder obtener el grupo sanguineo y el factor rh del donante - oliver/ricardo
    # Recupera la información básica del donante para mostrarla en la interfaz.
    donante_id = validar_id(donante_id)
    with conectar(ruta) as conexion:
        fila = conexion.execute("""SELECT ID, NOMBRE, APELLIDO, ELEGIBLE AS RESULTADO, INHABILITACION_INICIO AS INICIO, FACTOR_RH, GRUPO_SANGUINEO, INHABILITACION_FIN AS FIN FROM DONANTES WHERE ID = ? """, (donante_id,)).fetchone()
    if fila is None:
        raise ValueError("No existe un donante con ese ID.")
    return dict(fila)

def consultar_donanteApto(donante_id, ruta=RUTA_BD, hoy=None):
    # Consulta si el donante (unico) sigue siendo apto para donar (sin restricciones vigentes).
    donante_id = validar_id(donante_id)
    hoy = hoy or date.today().isoformat()
    with conectar(ruta) as conexion:
        fila = conexion.execute(
                    "SELECT ID, GRUPO_SANGUINEO, FACTOR_RH, EMAIL FROM DONANTES "
                    "WHERE ID = ? AND " + SQL_HABILITADO,
                    (donante_id, hoy)).fetchone()
    if fila is None:
        raise ValueError("No existe un donante apto con ese ID.")
    return dict(fila)


def _leer_fecha(texto, nombre):
    # Convierte la fecha ingresada por la interfaz al tipo date con validación.
    texto = (texto or "").strip()
    if not texto:
        raise ValueError(f"Ingrese la fecha {nombre} de la restricción.")
    try:
        return datetime.strptime(texto, FORMATO_FECHA).date()
    except ValueError:
        raise ValueError(f"La fecha {nombre} no es válida. Use el formato DD-MM-AAAA.")


def validar_periodo(inicio, fin, hoy=None):
    # Verifica que la restricción temporal tenga un rango coherente y vigente.
    hoy = hoy or date.today()
    fecha_inicio = _leer_fecha(inicio, "inicial")
    fecha_fin = _leer_fecha(fin, "final")
    if fecha_fin < fecha_inicio:
        raise ValueError("La fecha final no puede ser anterior a la fecha inicial.")
    if fecha_inicio > hoy:
        raise ValueError("La fecha inicial no puede ser futura.")
    if fecha_fin < hoy:
        raise ValueError("La fecha final no puede estar en el pasado.")
    return fecha_inicio.isoformat(), fecha_fin.isoformat()


def describir_estado(resultado, inicio, fin, hoy=None):
    # Genera un mensaje claro para la interfaz según el estado y la vigencia de la restricción.
    """Texto legible del estado actual del donante, considerando si la restricción sigue vigente."""
    hoy = (hoy or date.today()).isoformat()
    if not resultado:
        return "Sin resultado médico registrado"
    if resultado != TEMPORAL:
        return resultado
    if not fin:
        return f"{resultado} (sin fecha de término registrada)"
    desde = datetime.fromisoformat(inicio).strftime(FORMATO_FECHA) if inicio else "—"
    hasta = datetime.fromisoformat(fin).strftime(FORMATO_FECHA)
    if fin < hoy:
        return f"Restricción finalizada el {hasta}: puede ser convocado nuevamente"
    return f"{resultado} (del {desde} al {hasta})"


def buscar_candidatos(grupo, rh, ruta=RUTA_BD, hoy=None):
    # Busca candidatos elegibles para una solicitud de sangre según grupo y factor RH.
    """Donantes de un grupo y Rh que pueden ser convocados hoy (excluye restricciones vigentes)."""
    hoy = (hoy or date.today()).isoformat()
    with conectar(ruta) as conexion:
        filas = conexion.execute(
            "SELECT ID, GRUPO_SANGUINEO, FACTOR_RH, EMAIL FROM DONANTES "
            "WHERE GRUPO_SANGUINEO = ? AND FACTOR_RH = ? AND " + SQL_HABILITADO,
            (grupo, rh, hoy)).fetchall()
    return [tuple(fila) for fila in filas]

def buscar_sangre(grupo, rh, apta, ruta=RUTA_BD):
    # Busca donaciones aptas para una solicitud de sangre según grupo y factor RH.
    """Donaciones de un grupo, Rh y aptas."""
    with conectar(ruta) as conexion:
        filas = conexion.execute(
            "SELECT ID, GRUPO_SANGUINEO, FACTOR_RH, APTA FROM DONACIONES"
            "WHERE GRUPO_SANGUINEO = ? AND FACTOR_RH = ? AND APTA = ? AND",
            (grupo, rh, apta)).fetchall()
    return [tuple(fila) for fila in filas]

def candidato_vigente(donante_id, grupo, rh, ruta=RUTA_BD, hoy=None):
    # Verifica una última vez si el donante sigue habilitado antes de enviar comunicaciones.
    """Revalida a un donante justo antes de enviarle un correo. Devuelve (ID, EMAIL) o None."""
    hoy = (hoy or date.today()).isoformat()
    with conectar(ruta) as conexion:
        fila = conexion.execute(
            "SELECT ID, EMAIL FROM DONANTES WHERE ID = ? AND GRUPO_SANGUINEO = ? AND FACTOR_RH = ? AND "
            + SQL_HABILITADO, (donante_id, grupo, rh, hoy)).fetchone()
    return tuple(fila) if fila else None


def buscar_donantes(texto, ruta=RUTA_BD):
    # Busca donantes por nombre, apellido o email sin distinguir tildes ni mayúsculas(se implemento, pero no se usa en la interfaz(yo si lo ocupe -oliver)).
    palabras = texto.strip().split()
    if not palabras:
        raise ValueError("Ingrese nombre, apellido o correo del donante.")

    def normalizar(valor):
        return ''.join(c for c in unicodedata.normalize('NFD', valor or '')
                       if not unicodedata.combining(c)).casefold()

    with conectar(ruta) as conexion:
        conexion.create_function('normalizar', 1, normalizar)
        condiciones = ' AND '.join(
            "instr(normalizar(NOMBRE || ' ' || APELLIDO || ' ' || EMAIL), ?) > 0"
            for _ in palabras)
        filas = conexion.execute(
            'SELECT ID, NOMBRE, APELLIDO, EMAIL FROM DONANTES WHERE '
            + condiciones + ' ORDER BY APELLIDO, NOMBRE, ID LIMIT 51',
            [normalizar(palabra) for palabra in palabras]).fetchall()
    return [dict(fila) for fila in filas]

def buscar_donacion(texto, ruta=RUTA_BD):
    # Busca donaciones por id de donante o id de donacion.
    palabras = texto.strip().split()
    if not palabras:
        raise ValueError("Ingrese id de donante o id de donacion.")

    with conectar(ruta) as conexion:
        condiciones = ' AND '.join(
            "instr(DONANTE || ' ' || ID, ?) > 0"
            for _ in palabras)
        filas = conexion.execute(
            'SELECT ID, DONANTE, CANTIDAD, FECHA_EXTRACCIÓN, FECHA_VENCIMIENTO FROM DONACIONES WHERE '
            + condiciones + ' ORDER BY FECHA_EXTRACCIÓN DESC LIMIT 51',
            [palabra for palabra in palabras]).fetchall()
    return [dict(fila) for fila in filas]

def donacion_vigente(donacion_id, ruta=RUTA_BD, hoy=None):
    # Verifica si la donación sigue vigente (no vencida ni usada).
    hoy = (hoy or date.today()).isoformat()
    with conectar(ruta) as conexion:
        fila = conexion.execute(
            "SELECT ID, DONANTE, CANTIDAD, FECHA_EXTRACCIÓN, FECHA_VENCIMIENTO FROM DONACIONES "
            "WHERE ID = ? AND APTA = 'Si' AND FECHA_VENCIMIENTO >= ?",
            (donacion_id, hoy)).fetchone()
    return dict(fila) if fila else None


def guardar_resultado(donante_id, resultado, empleado_id, inicio=None, fin=None, ruta=RUTA_BD, hoy=None):
    # Actualiza la elegibilidad del donante y registra el cambio en el historial.
    with conectar(ruta) as conexion:
        # Se consulta el rol real al guardar; no se confía en el menú de la interfaz.
        empleado = conexion.execute(
            "SELECT ROL FROM PERSONAL WHERE ID_EMPLEADO = ?",
            (empleado_id,),
        ).fetchone()
        if empleado is None or empleado["ROL"] != "Entrevistador":
            raise PermissionError("No tiene autorización para modificar la habilitación.")
        donante_id = validar_id(donante_id)
        if resultado not in RESULTADOS:
            raise ValueError("Seleccione un estado de habilitación.")
        anterior = conexion.execute("SELECT ELEGIBLE FROM DONANTES WHERE ID = ?", (donante_id,)).fetchone()
        if anterior is None:
            raise ValueError("No existe un donante con ese ID.")

        if resultado == TEMPORAL:
            inicio_sql, fin_sql = validar_periodo(inicio, fin, hoy)
        else:
            inicio_sql = fin_sql = None  # al habilitar o inhabilitar permanente no queda período

        conexion.execute(
            "UPDATE DONANTES SET ELEGIBLE = ?, INHABILITACION_INICIO = ?, INHABILITACION_FIN = ? WHERE ID = ?",
            (resultado, inicio_sql, fin_sql, donante_id))
        conexion.execute(
            "INSERT INTO HISTORIAL_HABILITACION (DONANTE_ID, ESTADO_ANTERIOR, ESTADO_NUEVO, FECHA_INICIO, "
            "FECHA_FIN, EMPLEADO_ID, FECHA_CAMBIO) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (donante_id, anterior["ELEGIBLE"], resultado, inicio_sql, fin_sql, empleado_id,
             datetime.now().isoformat(timespec="seconds")))