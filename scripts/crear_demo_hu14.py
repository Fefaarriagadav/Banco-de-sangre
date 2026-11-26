import sqlite3
import sys
from contextlib import closing
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from datos.basededatos import inicializar_base
from servicios.muestras import registrar_muestra
from servicios.vencimientos import (
    calcular_vencimiento,
    fecha_actual,
)


def crear_demo():
    ruta = RAIZ / "BancoDeSangre_HU14_demo.db"

    if ruta.exists():
        raise SystemExit(
            "La demo HU14 ya existe. No se sobrescribió."
        )

    inicializar_base(ruta)
    extraccion = fecha_actual().isoformat()
    vencimiento = calcular_vencimiento(extraccion)

    with closing(sqlite3.connect(ruta)) as conexion, conexion:
        conexion.execute(
            """
            INSERT INTO PERSONAL (
                ID_EMPLEADO, RUT, NOMBRE, ROL
            )
            VALUES (
                1, 'DEMO-HU14-1', 'Enfermero demo', 'Enfermero'
            )
            """
        )

        conexion.execute(
            """
            INSERT INTO DONANTES (
                ID, NOMBRE, APELLIDO, EDAD, SEXO,
                GRUPO_SANGUINEO, FACTOR_RH, PESO,
                EMAIL, ELEGIBLE, FECHA_DE_NACIMIENTO
            )
            VALUES (
                1, 'Donante', 'Ficticio', 30, 'Masculino',
                'A', '+', 70, 'demo@example.invalid',
                'Donante apto', '1996-01-01'
            )
            """
        )

        conexion.execute(
            """
            INSERT INTO DONACIONES (
                ID, DONANTE, TIPO_SANGRE, FACTOR_RH,
                FECHA_EXTRACCIÓN, FECHA_VENCIMIENTO,
                CANTIDAD, UBICACION, ESTADO
            )
            VALUES (
                1, 1, 'A', '+', ?, ?, 450,
                'DEMO HU14', 'Disponible'
            )
            """,
            (extraccion, vencimiento),
        )

        conexion.executemany(
            """
            INSERT INTO CATALOGO_ANALISIS (
                CODIGO, NOMBRE, OBLIGATORIO, ACTIVO
            )
            VALUES (?, ?, 1, 1)
            """,
            [
                ("DEMO_1", "Control ficticio uno"),
                ("DEMO_2", "Control ficticio dos"),
            ],
        )

    muestra = registrar_muestra(1, 1, ruta=ruta)

    print(f"Demo creada: {ruta}")
    print("ID para iniciar sesión: 1")
    print("ID de donación: 1")
    print(f"ID de muestra: {muestra['ID']}")
    print("Controles ficticios, sin validez clínica.")


if __name__ == "__main__":
    crear_demo()