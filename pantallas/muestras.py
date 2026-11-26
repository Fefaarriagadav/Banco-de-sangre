import sqlite3
from datetime import datetime
from tkinter import messagebox, ttk

import customtkinter as ctk

from servicios.muestras import (
    registrar_muestra,
    consultar_muestra,
    consultar_muestras_donacion,
)


def mostrar_muestras(pantalla, empleado_id):
    anterior = getattr(pantalla, "_pantalla_muestras", None)

    if anterior is not None and anterior.winfo_exists():
        anterior.destroy()

    frame = ctk.CTkFrame(pantalla)
    frame.place(relx=0, rely=0, relwidth=1, relheight=1)
    pantalla._pantalla_muestras = frame

    ctk.CTkLabel(
        frame,
        text="Registro y consulta de muestras",
        font=("Arial", 25, "bold"),
    ).pack(pady=(20, 10))

    ctk.CTkLabel(
        frame,
        text=(
            "Registrar una muestra deja la unidad pendiente "
            "de análisis y fuera del stock disponible."
        ),
        wraplength=750,
    ).pack(pady=(0, 15))

    formulario = ctk.CTkFrame(frame)
    formulario.pack(fill="x", padx=25, pady=5)

    ctk.CTkLabel(
        formulario,
        text="ID de donación:",
    ).grid(row=0, column=0, padx=10, pady=15)

    entrada_donacion = ctk.CTkEntry(
        formulario,
        placeholder_text="Donación existente",
        width=200,
    )
    entrada_donacion.grid(
        row=0, column=1, padx=10, pady=15
    )

    mensaje = ctk.CTkLabel(
        frame,
        text="",
        wraplength=800,
    )
    mensaje.pack(pady=10)

    consulta = ctk.CTkFrame(frame)
    consulta.pack(fill="x", padx=25, pady=5)

    tipo_consulta = ctk.CTkOptionMenu(
        consulta,
        values=["ID de muestra", "ID de donación"],
    )
    tipo_consulta.grid(
        row=0, column=0, padx=10, pady=15
    )

    entrada_busqueda = ctk.CTkEntry(
        consulta,
        placeholder_text="Identificador",
        width=200,
    )
    entrada_busqueda.grid(
        row=0, column=1, padx=10, pady=15
    )

    tabla_frame = ctk.CTkFrame(frame)
    tabla_frame.pack(
        fill="both", expand=True, padx=25, pady=15
    )
    tabla_frame.grid_columnconfigure(0, weight=1)
    tabla_frame.grid_rowconfigure(0, weight=1)

    columnas = (
        "muestra",
        "donacion",
        "estado",
        "unidad",
        "responsable",
        "fecha",
    )

    tabla = ttk.Treeview(
        tabla_frame,
        columns=columnas,
        show="headings",
    )

    encabezados = {
        "muestra": "ID muestra",
        "donacion": "ID donación",
        "estado": "Estado de muestra",
        "unidad": "Estado de unidad",
        "responsable": "Responsable",
        "fecha": "Fecha de registro",
    }

    for columna, titulo in encabezados.items():
        tabla.heading(columna, text=titulo)
        tabla.column(
            columna,
            width=180,
            minwidth=100,
            anchor="center",
        )

    tabla.column("muestra", width=100)
    tabla.column("donacion", width=100)
    tabla.column("fecha", width=230)

    barra_vertical = ttk.Scrollbar(
        tabla_frame,
        orient="vertical",
        command=tabla.yview,
    )
    barra_horizontal = ttk.Scrollbar(
        tabla_frame,
        orient="horizontal",
        command=tabla.xview,
    )

    tabla.configure(
        yscrollcommand=barra_vertical.set,
        xscrollcommand=barra_horizontal.set,
    )

    tabla.grid(row=0, column=0, sticky="nsew")
    barra_vertical.grid(row=0, column=1, sticky="ns")
    barra_horizontal.grid(row=1, column=0, sticky="ew")

    def limpiar_resultados():
        for item in tabla.get_children():
            tabla.delete(item)

    def mostrar_resultados(muestras):
        limpiar_resultados()

        for muestra in muestras:
            fecha = datetime.fromisoformat(
                muestra["FECHA_REGISTRO"]
            ).strftime("%d-%m-%Y %H:%M:%S %z")

            tabla.insert(
                "",
                "end",
                values=(
                    muestra["ID"],
                    muestra["DONACION_ID"],
                    muestra["ESTADO"],
                    muestra["ESTADO_UNIDAD"],
                    (
                        f"{muestra['RESPONSABLE']} "
                        f"(ID {muestra['REGISTRADA_POR']})"
                    ),
                    fecha,
                ),
            )

    def informar_error(error):
        limpiar_resultados()
        mensaje.configure(
            text=str(error),
            text_color="#DC2626",
        )

    def buscar():
        mensaje.configure(text="")

        try:
            identificador = entrada_busqueda.get()

            if tipo_consulta.get() == "ID de muestra":
                muestras = [
                    consultar_muestra(
                        identificador,
                        empleado_id,
                    )
                ]
            else:
                muestras = consultar_muestras_donacion(
                    identificador,
                    empleado_id,
                )

            mostrar_resultados(muestras)

            mensaje.configure(
                text=(
                    f"Muestras encontradas: {len(muestras)}"
                    if muestras
                    else "La donación existe, pero no tiene muestras."
                ),
                text_color=("#166534", "#86EFAC"),
            )

        except (ValueError, PermissionError) as error:
            informar_error(error)
        except sqlite3.Error:
            informar_error(
                "No se pudo consultar la base de datos."
            )

    def registrar():
        donacion_id = entrada_donacion.get().strip()

        if not donacion_id:
            informar_error("Ingrese el ID de la donación.")
            return

        confirmado = messagebox.askyesno(
            "Registrar muestra",
            (
                f"¿Registrar una muestra para la donación "
                f"#{donacion_id}?\n\n"
                "La unidad quedará pendiente de análisis "
                "y fuera del stock disponible."
            ),
            parent=frame,
        )

        if not confirmado:
            return

        try:
            muestra = registrar_muestra(
                donacion_id,
                empleado_id,
            )
        except (ValueError, PermissionError) as error:
            informar_error(error)
            return
        except sqlite3.Error:
            informar_error(
                "No se pudo registrar la muestra. "
                "La operación no fue completada."
            )
            return

        # El registro ya quedó confirmado en la base.
        mostrar_resultados([muestra])

        mensaje.configure(
            text=(
                f"Muestra #{muestra['ID']} registrada para "
                f"la donación #{muestra['DONACION_ID']}. "
                "Estado: Pendiente de análisis."
            ),
            text_color=("#166534", "#86EFAC"),
        )

        tipo_consulta.set("ID de donación")
        entrada_busqueda.delete(0, "end")
        entrada_busqueda.insert(
            0, str(muestra["DONACION_ID"])
        )
        entrada_donacion.delete(0, "end")

    ctk.CTkButton(
        formulario,
        text="Registrar muestra",
        command=registrar,
    ).grid(row=0, column=2, padx=15, pady=15)

    ctk.CTkButton(
        consulta,
        text="Consultar",
        command=buscar,
    ).grid(row=0, column=2, padx=15, pady=15)

    entrada_busqueda.bind(
        "<Return>", lambda evento: buscar()
    )

    entrada_donacion.focus_set()