import sqlite3
from datetime import datetime
from zoneinfo import ZoneInfo


import customtkinter as ctk

from servicios.vencimientos import (
    DIAS_ALERTA,
    ZONA_HORARIA,
    consultar_resumen,
    fecha_actual,
)


def mostrar_panel_vencimientos(pantalla):
    panel = ctk.CTkFrame(
        pantalla,
        corner_radius=15,
        border_width=1,
        border_color=("#D1D5DB", "#454545"),
    )
    panel.place(
        relx=0.98,
        rely=0.08,
        anchor="ne",
        relwidth=0.26,
        relheight=0.82,
    )

    panel.grid_columnconfigure(0, weight=1)
    panel.grid_rowconfigure(2, weight=1)

    ctk.CTkLabel(
        panel,
        text="Próximos a expirar",
        font=("Arial", 23, "bold"),
        text_color=("#DC2626", "#F87171"),
    ).grid(
        row=0,
        column=0,
        padx=15,
        pady=(20, 5),
        sticky="w",
    )

    ctk.CTkLabel(
        panel,
        text=f"Vencimientos en los próximos {DIAS_ALERTA} días",
        font=("Arial", 13),
        text_color=("gray40", "gray70"),
    ).grid(
        row=1,
        column=0,
        padx=15,
        pady=(0, 15),
        sticky="w",
    )

    lista = ctk.CTkScrollableFrame(
        panel,
        fg_color="transparent",
    )
    lista.grid(
        row=2,
        column=0,
        padx=10,
        pady=5,
        sticky="nsew",
    )
    lista.grid_columnconfigure(0, weight=1)

    pie = ctk.CTkLabel(
        panel,
        text="",
        font=("Arial", 12),
        text_color=("gray40", "gray70"),
    )
    pie.grid(
        row=3,
        column=0,
        padx=15,
        pady=(10, 5),
    )

    def limpiar_lista():
        for widget in lista.winfo_children():
            widget.destroy()

    def refrescar():
        try:
            datos = consultar_resumen()
        except (sqlite3.Error, ValueError, RuntimeError):
            limpiar_lista()

            ctk.CTkLabel(
                lista,
                text="No se pudieron consultar los vencimientos.\n"
                     "Se reintentará automáticamente.",
                text_color=("#DC2626", "#F87171"),
                wraplength=240,
                justify="left",
            ).grid(
                row=0,
                column=0,
                padx=10,
                pady=15,
                sticky="w",
            )

            pie.configure(text="Información no disponible")
            return

        limpiar_lista()

        if not datos["proximas"]:
            ctk.CTkLabel(
                lista,
                text="No hay unidades próximas a expirar.",
                wraplength=240,
                justify="left",
            ).grid(
                row=0,
                column=0,
                padx=10,
                pady=15,
                sticky="w",
            )

        hoy = fecha_actual()

        for fila, unidad in enumerate(datos["proximas"]):
            vencimiento = datetime.strptime(
                unidad["FECHA_VENCIMIENTO"],
                "%Y-%m-%d",
            ).date()

            fecha = vencimiento.strftime("%d-%m-%Y")
            dias_restantes = (vencimiento - hoy).days

            if dias_restantes == 0:
                aviso = "Vence hoy"
            elif dias_restantes == 1:
                aviso = "Vence mañana"
            else:
                aviso = f"En {dias_restantes} días"

            tarjeta = ctk.CTkFrame(
                lista,
                corner_radius=10,
            )
            tarjeta.grid(
                row=fila,
                column=0,
                padx=3,
                pady=(0, 10),
                sticky="ew",
            )
            tarjeta.grid_columnconfigure(0, weight=1)

            ctk.CTkLabel(
                tarjeta,
                text=f"Unidad #{unidad['ID']}",
                font=("Arial", 16, "bold"),
                anchor="w",
            ).grid(
                row=0,
                column=0,
                padx=12,
                pady=(10, 3),
                sticky="w",
            )

            ctk.CTkLabel(
                tarjeta,
                text=f"Tipo de sangre: {unidad['GRUPO']}{unidad['RH']}",
                font=("Arial", 14),
                anchor="w",
            ).grid(
                row=1,
                column=0,
                padx=12,
                pady=3,
                sticky="w",
            )

            ctk.CTkLabel(
                tarjeta,
                text=f"{aviso}\nVencimiento: {fecha}",
                justify="left",
                font=("Arial", 14, "bold"),
                text_color=("#DC2626", "#F87171"),
                anchor="w",
            ).grid(
                row=2,
                column=0,
                padx=12,
                pady=(3, 10),
                sticky="w",
            )

        hora = datetime.now(
            ZoneInfo(ZONA_HORARIA)
        ).strftime("%d-%m-%Y %H:%M:%S")

        pie.configure(text=f"Actualizado: {hora}")

    ctk.CTkButton(
        panel,
        text="Actualizar",
        command=refrescar,
        fg_color="#DC2626",
        hover_color="#B91C1C",
    ).grid(
        row=4,
        column=0,
        padx=15,
        pady=(5, 15),
        sticky="ew",
    )

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

        tarea = panel.after(1_000, ciclo)

    def cancelar(event):
        nonlocal tarea

        if event.widget == panel and tarea is not None:
            panel.after_cancel(tarea)
            tarea = None

    panel.bind("<Destroy>", cancelar, add="+")
    ciclo()

    return panel