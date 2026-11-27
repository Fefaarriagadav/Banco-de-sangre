"""Carga los controles de HU14 sin crear resultados ni autorizaciones."""
import sqlite3
import sys
from contextlib import closing
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from datos.basededatos import inicializar_base


CONTROLES = (
    ("VIH_1_2", "Tamizaje de VIH 1 y 2"),
    ("HEPATITIS_B", "Tamizaje de hepatitis B"),
    ("HEPATITIS_C", "Tamizaje de hepatitis C"),
    ("HTLV_1_2", "Tamizaje de HTLV I y II"),
    ("CHAGAS", "Tamizaje de enfermedad de Chagas"),
    ("SIFILIS", "Tamizaje de sífilis"),
)


def configurar_catalogo():
    ruta = RAIZ / "BancoDeSangre.db"

    if not ruta.is_file():
        raise ValueError(f"No existe la base: {ruta}")

    # Aplica las migraciones existentes del proyecto.
    inicializar_base(ruta)

    with closing(sqlite3.connect(ruta)) as conexion, conexion:
        conexion.execute("BEGIN IMMEDIATE")

        actuales = {
            codigo: (obligatorio, activo)
            for codigo, obligatorio, activo in conexion.execute(
                "SELECT CODIGO, OBLIGATORIO, ACTIVO "
                "FROM CATALOGO_ANALISIS"
            )
        }

        cambia_reglas = any(
            actuales.get(codigo) != (1, 1)
            for codigo, _ in CONTROLES
        )

        liberadas = conexion.execute(
            "SELECT COUNT(*) FROM DONACIONES "
            "WHERE ESTADO_LABORATORIO = 'Liberada'"
        ).fetchone()[0]

        if cambia_reglas and liberadas:
            raise ValueError(
                "Hay unidades ya liberadas. Antes de agregar requisitos "
                "nuevos debemos revisar sus autorizaciones. "
                "No se modificó el catálogo."
            )

        conexion.executemany(
            """
            INSERT INTO CATALOGO_ANALISIS (
                CODIGO, NOMBRE, OBLIGATORIO, ACTIVO
            )
            VALUES (?, ?, 1, 1)
            ON CONFLICT(CODIGO) DO UPDATE SET
                OBLIGATORIO = 1,
                ACTIVO = 1
            """,
            CONTROLES,
        )

    print("Controles obligatorios configurados en BancoDeSangre.db:")
    for codigo, nombre in CONTROLES:
        print(f"  {codigo}: {nombre}")

    print("No se crearon resultados ni autorizaciones.")


if __name__ == "__main__":
    try:
        configurar_catalogo()
    except (ValueError, sqlite3.Error) as error:
        raise SystemExit(str(error)) from error