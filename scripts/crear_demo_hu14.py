import sqlite3
import sys
from contextlib import closing
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from datos.basededatos import inicializar_base
from servicios.liberacion import autorizar_liberacion
from servicios.muestras import registrar_muestra
from servicios.resultados_analisis import guardar_resultado
from servicios.vencimientos import (
    VIDA_UTIL_DIAS,
    ZONA_HORARIA,
    actualizar_vencimientos,
    consultar_resumen,
    fecha_actual,
)

ANALISIS_DEMO = [
    (1, "VIH_1_2", "Tamizaje de VIH 1 y 2"),
    (2, "HEPATITIS_B", "Tamizaje de hepatitis B"),
    (3, "HEPATITIS_C", "Tamizaje de hepatitis C"),
    (4, "HTLV_1_2", "Tamizaje de HTLV I y II"),
    (5, "CHAGAS", "Tamizaje de enfermedad de Chagas"),
    (6, "SIFILIS", "Tamizaje de sífilis"),
]


def crear_demo():
    ruta = RAIZ / "BancoDeSangre_HU14_demo.db"

    if ruta.exists():
        raise SystemExit(
            "La demo ya existe. Cierra la aplicación y "
            "archívala antes de ejecutar este generador."
        )

    inicializar_base(ruta)

    ahora = datetime.now(ZoneInfo(ZONA_HORARIA))
    hoy = fecha_actual(ahora)
    vencimiento = hoy + timedelta(days=3)
    extraccion = vencimiento - timedelta(days=VIDA_UTIL_DIAS)

    grupos = [
        ("A", "+"),
        ("A", "-"),
        ("B", "+"),
        ("B", "-"),
        ("AB", "+"),
        ("AB", "-"),
        ("O", "+"),
        ("O", "-"),
    ]

    casos = [
        "Sin muestras",
        "Muestra sin resultados",
        "Resultados parciales",
        "Conforme, pendiente de autorización",
        "Resultado No conforme",
        "Liberación autorizada",
        "Liberación revocada por nueva muestra",
        "Unidad vencida",
    ]

    with closing(sqlite3.connect(ruta)) as conexion, conexion:
        conexion.executemany(
            """
            INSERT INTO PERSONAL (
                ID_EMPLEADO, RUT, NOMBRE, ROL
            )
            VALUES (?, ?, ?, ?)
            """,
            [
                (1, "DEMO-HU14-1", "Matías Palacios", "Enfermero"),
                (2, "DEMO-HU14-2", "Entrevistador demo", "Entrevistador"),
            ],
        )

        conexion.executemany(
            """
            INSERT INTO CATALOGO_ANALISIS (
                ID, CODIGO, NOMBRE, OBLIGATORIO, ACTIVO
            )
            VALUES (?, ?, ?, 1, 1)
            """,
            ANALISIS_DEMO,
        )

        for identificador, ((grupo, rh), caso) in enumerate(
            zip(grupos, casos), start=1
        ):
            conexion.execute(
                """
                INSERT INTO DONANTES (
                    ID, NOMBRE, APELLIDO, EDAD, SEXO,
                    GRUPO_SANGUINEO, FACTOR_RH, PESO,
                    EMAIL, ELEGIBLE, FECHA_DE_NACIMIENTO
                )
                VALUES (
                    ?, 'Donante', ?, 30, 'Masculino',
                    ?, ?, 70, ?, 'Donante apto', '1996-01-01'
                )
                """,
                (
                    identificador,
                    f"Ficticio {identificador}",
                    grupo,
                    rh,
                    f"demo{identificador}@example.invalid",
                ),
            )

            conexion.execute(
                """
                INSERT INTO DONACIONES (
                    ID, DONANTE, TIPO_SANGRE, FACTOR_RH,
                    FECHA_EXTRACCIÓN, FECHA_VENCIMIENTO,
                    CANTIDAD, UBICACION, ESTADO
                )
                VALUES (?, ?, ?, ?, ?, ?, 450, ?, 'Disponible')
                """,
                (
                    identificador,
                    identificador,
                    grupo,
                    rh,
                    extraccion.isoformat(),
                    vencimiento.isoformat(),
                    f"DEMO HU14: {caso}",
                ),
            )

    def muestra(donacion_id):
        return registrar_muestra(
            donacion_id,
            1,
            ruta=ruta,
            ahora=ahora,
        )["ID"]

    def resultado(muestra_id, analisis_id, clasificacion="Conforme"):
        guardar_resultado(
            muestra_id=muestra_id,
            analisis_id=analisis_id,
            resultado=f"Informe ficticio del control {analisis_id}",
            clasificacion=clasificacion,
            empleado_id=1,
            ruta=ruta,
            ahora=ahora,
        )

    def completar(muestra_id):
        for analisis_id, codigo, nombre in ANALISIS_DEMO:
            resultado(muestra_id, analisis_id)

    def liberar(donacion_id):
        autorizar_liberacion(
            donacion_id,
            1,
            "Autorización ficticia para demostración de HU14",
            ruta=ruta,
            ahora=ahora,
        )

    # Caso 1: sin muestras.

    # Caso 2: muestra sin resultados.
    muestra(2)

    # Caso 3: solo uno de los dos controles.
    muestra_parcial = muestra(3)
    resultado(muestra_parcial, 1)

    # Caso 4: completo y conforme, sin autorización.
    muestra_conforme = muestra(4)
    completar(muestra_conforme)

    # Caso 5: el segundo control bloquea automáticamente.
    muestra_bloqueada = muestra(5)

    for analisis_id, codigo, nombre in ANALISIS_DEMO:
        clasificacion = (
            "No conforme" if analisis_id == 2 else "Conforme"
        )

        resultado(
            muestra_bloqueada,
            analisis_id,
            clasificacion,
        )

    # Caso 6: autorización explícita.
    muestra_liberada = muestra(6)
    completar(muestra_liberada)
    liberar(6)

    # Caso 7: una nueva muestra revoca la autorización.
    primera_muestra = muestra(7)
    completar(primera_muestra)
    liberar(7)
    muestra(7)

    # Caso 8: datos completos, pero la unidad después caduca.
    muestra_vencida = muestra(8)
    completar(muestra_vencida)

    with closing(sqlite3.connect(ruta)) as conexion, conexion:
        vencida = hoy - timedelta(days=1)
        extraccion_vencida = vencida - timedelta(days=VIDA_UTIL_DIAS)

        conexion.execute(
            """
            UPDATE DONACIONES
            SET FECHA_EXTRACCIÓN = ?, FECHA_VENCIMIENTO = ?
            WHERE ID = 8
            """,
            (
                extraccion_vencida.isoformat(),
                vencida.isoformat(),
            ),
        )

    actualizar_vencimientos(ruta=ruta, ahora=ahora)

    stock = consultar_resumen(ruta=ruta, ahora=ahora)

    if stock["unidades"] != 1:
        raise RuntimeError(
            "La demo no produjo el stock esperado. "
            "Revisa las conexiones de HU14-T3."
        )

    print(f"\nDemo creada: {ruta}")
    print("Inicio de sesión: ID 1 (Enfermero)")
    print("ID 2 permite comprobar el acceso como Entrevistador.")
    print("Controles ficticios, sin validez clínica.\n")

    with closing(sqlite3.connect(ruta)) as conexion:
        for identificador, caso in enumerate(casos, start=1):
            muestras = conexion.execute(
                """
                SELECT ID FROM MUESTRAS
                WHERE DONACION_ID = ?
                ORDER BY ID
                """,
                (identificador,),
            ).fetchall()

            ids = ", ".join(str(fila[0]) for fila in muestras)
            print(
                f"Donación {identificador} | "
                f"Muestras: {ids or 'ninguna'} | {caso}"
            )

    print("\nStock inicial: solo donación 6, AB-, 450 mL / 0.45 litros.")
    print("Alerta de vencimiento inicial: solo donación 6.")
    print("Los resultados esperados corresponden al día de generación.")


if __name__ == "__main__":
    crear_demo()