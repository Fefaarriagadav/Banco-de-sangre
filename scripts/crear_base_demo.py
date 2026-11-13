import sqlite3
import sys
from contextlib import closing
from datetime import timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from datos.basededatos import inicializar_base
from servicios.vencimientos import (
    DISPONIBLE,
    USADA,
    DESCARTADA,
    PENDIENTE,
    VIDA_UTIL_DIAS,
    fecha_actual,
    consultar_resumen,
)


def crear_demo():
    ruta = RAIZ / "BancoDeSangre_demo.db"

    if ruta.exists():
        raise SystemExit(
            "La demo ya existe. Cierra la aplicación y renombra "
            "únicamente BancoDeSangre_demo.db antes de regenerarla."
        )

    inicializar_base(ruta)
    hoy = fecha_actual()

    grupos = [
        (grupo, rh)
        for grupo in ("A", "B", "AB", "O")
        for rh in ("+", "-")
    ]

    with closing(sqlite3.connect(ruta)) as conexion, conexion:
        conexion.execute(
            """
            INSERT INTO PERSONAL (
                ID_EMPLEADO, RUT, NOMBRE, ROL
            )
            VALUES (
                1, 'DEMO-1', 'Personal demo', 'Entrevistador'
            )
            """
        )

        for donante_id, (grupo, rh) in enumerate(grupos, start=1):
            conexion.execute(
                """
                INSERT INTO DONANTES (
                    ID, NOMBRE, APELLIDO, EDAD, SEXO,
                    GRUPO_SANGUINEO, FACTOR_RH,
                    PESO, EMAIL, ELEGIBLE, FECHA_DE_NACIMIENTO
                )
                VALUES (
                    ?, 'Donante', 'Ficticio', 30, 'Masculino',
                    ?, ?, 70, ?, 'Donante apto', '1996-01-01'
                )
                """,
                (
                    donante_id,
                    grupo,
                    rh,
                    f"demo{donante_id}@example.invalid",
                ),
            )

            # Por grupo: 5 disponibles y 1 vencida.
            for dias in (0, 1, 7, 8, 20, -1):
                vencimiento = hoy + timedelta(days=dias)
                extraccion = min(
                    hoy,
                    vencimiento - timedelta(days=VIDA_UTIL_DIAS),
                )

                conexion.execute(
                    """
                    INSERT INTO DONACIONES (
                        DONANTE, TIPO_SANGRE, FACTOR_RH,
                        FECHA_EXTRACCIÓN, FECHA_VENCIMIENTO,
                        CANTIDAD, UBICACION, ESTADO
                    )
                    VALUES (?, ?, ?, ?, ?, 0.45, ?, ?)
                    """,
                    (
                        donante_id,
                        grupo,
                        rh,
                        extraccion.isoformat(),
                        vencimiento.isoformat(),
                        f"DEMO: vence en {dias} días",
                        DISPONIBLE,
                    ),
                )

        # Estados que deben quedar fuera del stock.
        for estado in (USADA, DESCARTADA, "Reservada"):
            conexion.execute(
                """
                INSERT INTO DONACIONES (
                    DONANTE, TIPO_SANGRE, FACTOR_RH,
                    FECHA_EXTRACCIÓN, FECHA_VENCIMIENTO,
                    CANTIDAD, UBICACION, ESTADO
                )
                VALUES (1, 'A', '+', ?, ?, 0.45, ?, ?)
                """,
                (
                    hoy.isoformat(),
                    (hoy + timedelta(days=3)).isoformat(),
                    f"DEMO: {estado}",
                    estado,
                ),
            )

        # Datos inconsistentes: no deben contarse como disponibles.
        casos = [
            (
                hoy,
                None,
                0.45,
                "Sin vencimiento",
            ),
            (
                hoy,
                "fecha inválida",
                0.45,
                "Fecha inválida",
            ),
            (
                hoy + timedelta(days=1),
                (hoy + timedelta(days=21)).isoformat(),
                0.45,
                "Extracción futura",
            ),
            (
                hoy,
                (hoy + timedelta(days=3)).isoformat(),
                0,
                "Cantidad cero",
            ),
        ]

        for extraccion, vencimiento, cantidad, descripcion in casos:
            conexion.execute(
                """
                INSERT INTO DONACIONES (
                    DONANTE, TIPO_SANGRE, FACTOR_RH,
                    FECHA_EXTRACCIÓN, FECHA_VENCIMIENTO,
                    CANTIDAD, UBICACION, ESTADO
                )
                VALUES (1, 'A', '+', ?, ?, ?, ?, ?)
                """,
                (
                    extraccion.isoformat(),
                    vencimiento,
                    cantidad,
                    f"DEMO: {descripcion}",
                    PENDIENTE,
                ),
            )

    datos = consultar_resumen(ruta)

    print(f"Demo creada: {ruta}")
    print("Inicio de sesión: ID 1")
    print(
        f"Stock: {datos['unidades']} unidades "
        f"/ {datos['litros']:.2f} litros"
    )
    print(f"Alertas: {len(datos['proximas'])}")
    print(f"Pendientes: {datos['pendientes']}")
    print("Resultados esperados el día de generación:")
    print("40 disponibles, 18 litros, 24 alertas, 8 vencidas.")
    print("4 pendientes, 1 usada, 1 descartada y 1 reservada.")
    print("Por grupo/Rh: 5 disponibles y 2.25 litros.")


if __name__ == "__main__":
    crear_demo()