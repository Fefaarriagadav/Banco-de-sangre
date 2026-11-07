import sqlite3
import unicodedata
from contextlib import contextmanager
from datos.configuracion import RUTA_BD

RESULTADOS = ("Apto", "No apto")


@contextmanager
def conectar(ruta=RUTA_BD):
    conexion = sqlite3.connect(ruta)
    conexion.row_factory = sqlite3.Row
    conexion.execute("PRAGMA foreign_keys = ON")
    try:
        with conexion:
            yield conexion
    finally:
        conexion.close()


def preparar_elegibilidad(ruta=RUTA_BD):
    with conectar(ruta) as conexion:
        conexion.execute("""CREATE TABLE IF NOT EXISTS EVALUACIONES_ELEGIBILIDAD (
            DONANTE_ID INTEGER PRIMARY KEY REFERENCES DONANTES(ID),
            RESULTADO TEXT NOT NULL CHECK (RESULTADO IN ('Apto', 'No apto'))
        )""")


def validar_id(valor):
    texto = str(valor).strip()
    if not texto.isascii() or not texto.isdecimal() or int(texto) <= 0:
        raise ValueError("Ingrese un ID de donante válido.")
    return int(texto)


def consultar_donante(donante_id, ruta=RUTA_BD):
    donante_id = validar_id(donante_id)
    with conectar(ruta) as conexion:
        fila = conexion.execute("""SELECT d.ID, d.NOMBRE, d.APELLIDO,
            e.RESULTADO FROM DONANTES d
            LEFT JOIN EVALUACIONES_ELEGIBILIDAD e ON e.DONANTE_ID = d.ID
            WHERE d.ID = ?""", (donante_id,)).fetchone()
    if fila is None:
        raise ValueError("No existe un donante con ese ID.")
    return dict(fila)


def buscar_donantes(texto, ruta=RUTA_BD):
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


def guardar_resultado(donante_id, resultado, empleado_id, ruta=RUTA_BD):
    # Se consulta el rol real al guardar; no se confía en el menú de la interfaz.
    with conectar(ruta) as conexion:
        empleado = conexion.execute(
            "SELECT ROL FROM PERSONAL WHERE ID_EMPLEADO = ?",
            (empleado_id,),
        ).fetchone()
        if empleado is None or empleado["ROL"] != "Entrevistador":
            raise PermissionError("No tiene autorización para modificar la evaluación.")
        donante_id = validar_id(donante_id)
        if resultado not in RESULTADOS:
            raise ValueError("Seleccione Apto o No apto.")
        if conexion.execute("SELECT ID FROM DONANTES WHERE ID = ?", (donante_id,)).fetchone() is None:
            raise ValueError("No existe un donante con ese ID.")
        conexion.execute("""INSERT INTO EVALUACIONES_ELEGIBILIDAD
            (DONANTE_ID, RESULTADO) VALUES (?, ?)
            ON CONFLICT(DONANTE_ID) DO UPDATE SET RESULTADO = excluded.RESULTADO""",
            (donante_id, resultado))
