import sqlite3
from datetime import datetime
from tkinter import ttk
from zoneinfo import ZoneInfo

import customtkinter as ctk

from servicios.vencimientos import (
    ZONA_HORARIA,
    consultar_stock_detallado,
)


def mostrar_stocks(pantalla):
    # Evita acumular pantallas Stocks y sus temporizadores.
    anterior = getattr(pantalla, "_pantalla_stocks", None)
    if anterior is not None and anterior.winfo_exists():
        anterior.destroy()

    frame = ctk.CTkFrame(pantalla)
    frame.place(relx=0, rely=0, relwidth=1, relheight=1)
    pantalla._pantalla_stocks = frame

    ctk.CTkLabel(
        frame,
        text="Stocks disponibles",
        font=("Arial", 26, "bold"),
    ).pack(pady=(15, 5))

    resumen = ctk.CTkLabel(frame, text="")
    resumen.pack(pady=5)

    estilo = ttk.Style(frame)
    estilo.theme_use("clam")

    estilo.configure(
        "Stocks.Treeview",
        background="#282D35",
        fieldbackground="#282D35",
        foreground="#E5E7EB",
        rowheight=32,
        font=("Arial", 11),
        borderwidth=0,
        relief="flat",
    )

    estilo.configure(
        "Stocks.Treeview.Heading",
        background="#E2E8F0",
        foreground="#172033",
        font=("Arial", 11, "bold"),
        padding=(8, 10),
    )

    estilo.map(
        "Stocks.Treeview",
        background=[("selected", "#24577A")],
        foreground=[("selected", "#FFFFFF")],
    )


    def crear_tabla(contenedor, columnas, alto):
        caja = ctk.CTkFrame(contenedor)
        caja.pack(fill="both", expand=True, padx=20, pady=5)
        caja.grid_columnconfigure(0, weight=1)
        caja.grid_rowconfigure(0, weight=1)

        tabla = ttk.Treeview(
            caja,
            columns=[clave for clave, titulo in columnas],
            show="headings",
            height=alto,
            style="Stocks.Treeview",
        )

        for clave, titulo in columnas:
            tabla.heading(clave, text=titulo)
            tabla.column(
                clave,
                width=150,
                minwidth=100,
                anchor="center",
            )

        vertical = ttk.Scrollbar(
            caja,
            orient="vertical",
            command=tabla.yview,
        )
        horizontal = ttk.Scrollbar(
            caja,
            orient="horizontal",
            command=tabla.xview,
        )

        tabla.configure(
            yscrollcommand=vertical.set,
            xscrollcommand=horizontal.set,
        )

        tabla.grid(row=0, column=0, sticky="nsew")
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal.grid(row=1, column=0, sticky="ew")

        return tabla

    contenido = ctk.CTkFrame(
        frame, fg_color="transparent"
    )
    contenido.pack(
        fill="both", expand=True, padx=10, pady=5
    )
    contenido.grid_columnconfigure(
        0, weight=3, uniform="stock"
    )
    contenido.grid_columnconfigure(
        1, weight=2, uniform="stock"
    )
    contenido.grid_rowconfigure(0, weight=1)

    izquierda = ctk.CTkFrame(
        contenido,
        fg_color="#242424",
        corner_radius=12,
        border_width=1,
        border_color="#3A3A3A",
    )
    izquierda.grid(
        row=0, column=0, sticky="nsew", padx=(0, 8)
    )

    derecha = ctk.CTkFrame(
        contenido,
        fg_color="#242424",
        corner_radius=12,
        border_width=1,
        border_color="#5A4930",
    )
    derecha.grid(
        row=0, column=1, sticky="nsew", padx=(8, 0)
    )

    ctk.CTkLabel(
        izquierda,
        text="Totales por tipo de sangre",
        font=("Arial", 17, "bold"),
    ).pack(pady=(10, 0))

    ctk.CTkLabel(
        izquierda,
        text="Unidades liberadas y disponibles para despacho",
        text_color="#AAB4C3",
    ).pack(pady=5)

    tabla_totales = crear_tabla(
        izquierda,
        [
            ("grupo", "Grupo sanguíneo"),
            ("rh", "Factor Rh"),
            ("unidades", "Unidades disponibles"),
            ("litros", "Litros disponibles"),
            ("vencimiento", "Próximo vencimiento"),
        ],
        alto=8,
    )

    ctk.CTkLabel(
        izquierda,
        text="Detalle de unidades disponibles",
        font=("Arial", 17, "bold"),
    ).pack(pady=(10, 0))

    tabla_unidades = crear_tabla(
        izquierda,
        [
            ("id", "ID unidad"),
            ("grupo", "Grupo sanguíneo"),
            ("rh", "Factor Rh"),
            ("litros", "Litros"),
            ("extraccion", "Fecha de extracción"),
            ("vencimiento", "Fecha de vencimiento"),
        ],
        alto=6,
    )

    ctk.CTkLabel(
        derecha,
        text="Stock en revisión",
        font=("Arial", 17, "bold"),
    ).pack(pady=(10, 0))

    ctk.CTkLabel(
        derecha,
        text=(
            "Unidades pendientes"
            " · No disponibles para despacho"
        ),
        wraplength=350,
    ).pack(pady=5)

    tabla_revision = crear_tabla(
        derecha,
        [
            ("id", "ID unidad"),
            ("sangre", "Sangre / Rh"),
            ("estado", "Situación"),
            ("vencimiento", "Vencimiento"),
        ],
        alto=14,
    )

    pie = ctk.CTkLabel(frame, text="")
    pie.pack(pady=5)

    def formatear_fecha(valor):
        if not valor:
            return "—"
        return datetime.strptime(
            valor, "%Y-%m-%d"
        ).strftime("%d-%m-%Y")

    def limpiar_tablas():
        for tabla in (
            tabla_totales,
            tabla_unidades,
            tabla_revision,
        ):
            for item in tabla.get_children():
                tabla.delete(item)

    def refrescar():
        try:
            datos = consultar_stock_detallado()
        except (sqlite3.Error, ValueError, RuntimeError):
            limpiar_tablas()
            resumen.configure(
                text="Stock no disponible",
                text_color="#DC2626",
            )
            pie.configure(
                text="Error al consultar. Se reintentará automáticamente."
            )
            return

        limpiar_tablas()

        for total in datos["totales"]:
            tabla_totales.insert(
                "",
                "end",
                values=(
                    total["grupo"],
                    total["rh"],
                    total["unidades"],
                    f"{total['litros']:.2f}",
                    formatear_fecha(
                        total["proximo_vencimiento"]
                    ),
                ),
            )

        for unidad in datos["unidades"]:
            tabla_unidades.insert(
                "",
                "end",
                values=(
                    unidad["ID"],
                    unidad["GRUPO"],
                    unidad["RH"],
                    f"{(unidad['CANTIDAD'] or 0) / 1000.0:.2f}",
                    formatear_fecha(unidad["EXTRACCION"]),
                    formatear_fecha(unidad["VENCIMIENTO"]),
                ),
            )

        for unidad in datos.get("revision", []):
            situacion = (
                unidad["ESTADO_LABORATORIO"]
                if unidad["ESTADO"] == "Disponible"
                else unidad["ESTADO"]
            )

            tabla_revision.insert(
                "",
                "end",
                values=(
                    unidad["ID"],
                    f"{unidad['GRUPO']}{unidad['RH']}",
                    situacion,
                    formatear_fecha(
                        unidad["VENCIMIENTO"]
                    ),
                ),
            )

        cantidad = len(datos["unidades"])
        litros = sum(
            total["litros"] for total in datos["totales"]
        )

        resumen.configure(
            text=(
                f"Total disponible: {cantidad} unidades"
                f" · {litros:.2f} litros"
                f" | En revisión: "
                f"{len(datos.get('revision', []))} unidades"
            ),
            text_color=("#111827", "#F9FAFB"),
        )

        hora = datetime.now(
            ZoneInfo(ZONA_HORARIA)
        ).strftime("%d-%m-%Y %H:%M:%S %Z")

        pie.configure(text=f"Última actualización: {hora}")

    ctk.CTkButton(
        frame,
        text="Actualizar ahora",
        command=refrescar,
    ).pack(pady=(0, 10))

    tarea = None
    ultimo_minuto = None

    def ciclo():
        nonlocal tarea, ultimo_minuto

        minuto = datetime.now(
            ZoneInfo(ZONA_HORARIA)
        ).strftime("%Y-%m-%d %H:%M %z")

        if minuto != ultimo_minuto:
            refrescar()
            ultimo_minuto = minuto

        tarea = frame.after(1_000, ciclo)

    def cancelar(event):
        nonlocal tarea

        if event.widget == frame and tarea is not None:
            frame.after_cancel(tarea)
            tarea = None

    frame.bind("<Destroy>", cancelar, add="+")
    ciclo()
