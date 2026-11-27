import sqlite3
from datetime import datetime
from tkinter import messagebox, ttk

import customtkinter as ctk

from servicios.liberacion import (
    LIBERADA,
    autorizar_liberacion,
    consultar_liberacion,
)


def mostrar_liberacion(pantalla, donacion_id, empleado_id, muestra_id):
    anterior = getattr(pantalla, "_pantalla_liberacion", None)

    if anterior is not None and anterior.winfo_exists():
        anterior.destroy()

    contenedor = ctk.CTkFrame(pantalla)
    contenedor.place(relx=0, rely=0, relwidth=1, relheight=1)
    pantalla._pantalla_liberacion = contenedor

    pie_acciones = ctk.CTkFrame(
        contenedor, fg_color="transparent"
    )
    pie_acciones.pack(side="bottom", fill="x")

    cabecera = ctk.CTkFrame(
        contenedor, fg_color="transparent"
    )
    cabecera.pack(side="top", fill="x")

    frame = ctk.CTkScrollableFrame(contenedor)
    frame.pack(fill="both", expand=True)

    ctk.CTkLabel(
        cabecera,
        text="Revisión y autorización de laboratorio",
        font=("Arial", 24, "bold"),
    ).pack(pady=(15, 5))

    identidad = ctk.CTkFrame(cabecera)
    identidad.pack(fill="x", padx=20, pady=10)

    ctk.CTkLabel(
        identidad,
        text=(
            f"DONACIÓN / UNIDAD #{donacion_id}"
            f"     →     MUESTRA ABIERTA #{muestra_id}"
        ),
        font=("Arial", 19, "bold"),
    ).pack(padx=15, pady=(12, 5))

    ctk.CTkLabel(
        identidad,
        text=(
            "Está revisando esta muestra. La autorización afecta "
            "a la unidad completa y considera todas sus muestras."
        ),
        wraplength=1000,
    ).pack(padx=15, pady=(0, 12))

    resumen = ctk.CTkLabel(
        frame,
        text="Consultando...",
        wraplength=1100,
        justify="left",
    )
    resumen.pack(padx=20, pady=10)

    ctk.CTkLabel(
        frame,
        text="Motivo de autorización",
        font=("Arial", 15, "bold"),
    ).pack(pady=(10, 5))

    motivo = ctk.CTkEntry(
        frame,
        placeholder_text="Indique el motivo de la autorización",
        width=700,
    )
    motivo.pack(fill="x", padx=30, pady=5)

    mensaje = ctk.CTkLabel(
        frame,
        text="",
        wraplength=1100,
    )
    mensaje.pack(pady=10)

    ctk.CTkLabel(
        frame,
        text="Historial de actividad y autorizaciones",
        font=("Arial", 17, "bold"),
    ).pack(pady=5)

    caja = ctk.CTkFrame(frame)
    caja.pack(fill="both", expand=True, padx=20, pady=10)
    caja.grid_columnconfigure(0, weight=1)
    caja.grid_rowconfigure(0, weight=1)

    columnas = (
        "fecha",
        "muestra",
        "accion",
        "anterior",
        "nuevo",
        "inventario",
        "responsable",
    )

    tabla = ttk.Treeview(
        caja,
        columns=columnas,
        show="headings",
        height=8,
    )

    encabezados = {
        "fecha": "Fecha y hora",
        "muestra": "Muestra de referencia",
        "accion": "Acción realizada",
        "anterior": "Decisión anterior",
        "nuevo": "Decisión nueva",
        "inventario": "Inventario resultante",
        "responsable": "Responsable",
    }

    for columna, titulo in encabezados.items():
        tabla.heading(columna, text=titulo)
        tabla.column(
            columna, width=190, minwidth=100, anchor="center"
        )

    vertical = ttk.Scrollbar(
        caja, orient="vertical", command=tabla.yview
    )
    horizontal = ttk.Scrollbar(
        caja, orient="horizontal", command=tabla.xview
    )

    tabla.configure(
        yscrollcommand=vertical.set,
        xscrollcommand=horizontal.set,
    )

    tabla.grid(row=0, column=0, sticky="nsew")
    vertical.grid(row=0, column=1, sticky="ns")
    horizontal.grid(row=1, column=0, sticky="ew")

    ctk.CTkLabel(
        frame,
        text="Seleccione una decisión para consultar su motivo y referencias.",
    ).pack()

    detalle = ctk.CTkTextbox(frame, height=90)
    detalle.pack(fill="x", padx=20, pady=5)
    detalle.configure(state="disabled")

    datos_actuales = None
    historial_por_fila = {}

    def mostrar_detalle(texto):
        detalle.configure(state="normal")
        detalle.delete("1.0", "end")
        detalle.insert("1.0", texto)
        detalle.configure(state="disabled")

    def seleccionar_decision(event=None):
        seleccion = tabla.selection()

        if not seleccion:
            return

        decision = historial_por_fila.get(seleccion[0])

        if decision is None:
            return

        mostrar_detalle(
            f"Decisión #{decision['ID']} · "
            f"Donación #{decision['DONACION_ID']}\n"
            f"Muestra de referencia: "
            f"{decision['MUESTRA_ID'] or 'Varias; ver motivo'}\n"
            f"Motivo: {decision['MOTIVO']}"
        )

    tabla.bind("<<TreeviewSelect>>", seleccionar_decision)

    def cargar():
        nonlocal datos_actuales, historial_por_fila

        datos_actuales = None
        boton_autorizar.configure(state="disabled")

        for item in tabla.get_children():
            tabla.delete(item)

        historial_por_fila = {}
        mostrar_detalle("")

        try:
            datos = consultar_liberacion(
                donacion_id,
                empleado_id,
            )
        except (ValueError, PermissionError) as error:
            resumen.configure(text="Información no disponible.")
            mensaje.configure(
                text=str(error), text_color="#DC2626"
            )
            return
        except sqlite3.Error:
            resumen.configure(text="Información no disponible.")
            mensaje.configure(
                text="No se pudo consultar la liberación.",
                text_color="#DC2626",
            )
            return

        datos_actuales = datos
        unidad = datos["UNIDAD"]
        ya_liberada = unidad["ESTADO_LABORATORIO"] == LIBERADA

        if ya_liberada and not datos["PROBLEMAS"]:
            evaluacion = (
                "La unidad ya tiene autorización de laboratorio."
            )
        elif datos["PROBLEMAS"]:
            evaluacion = "\n".join(
                f"• {problema}"
                for problema in datos["PROBLEMAS"]
            )
        else:
            evaluacion = (
                "Controles completos y conformes. "
                "Puede autorizar expresamente su liberación."
            )

        if datos["FALTANTES"]:
            evaluacion += (
                "\nDetalle de pendientes: "
                + "; ".join(datos["FALTANTES"])
            )

        muestras_incluidas = ", ".join(
            f"Muestra #{identificador}"
            for identificador in datos["MUESTRAS"]
        ) or "Ninguna"

        if ya_liberada:
            decision_visible = "Liberada"
        elif (
            unidad["ESTADO_LABORATORIO"] == "Bloqueada"
            or datos["NO_CONFORMES"]
        ):
            decision_visible = "Bloqueada"
        elif datos["PUEDE_LIBERARSE"]:
            decision_visible = "Pendiente de autorización"
        else:
            decision_visible = "Sin autorización"

        resumen.configure(
            text=(
                f"Muestras incluidas en la evaluación: "
                f"{muestras_incluidas}\n\n"
                f"Situación de laboratorio: "
                f"{decision_visible}\n"
                f"Estado en inventario: {unidad['ESTADO']}\n\n"
                f"{evaluacion}"
            ),
            font=("Arial", 15),
        )

        habilitado = (
            datos["PUEDE_LIBERARSE"]
            and not ya_liberada
            and unidad["ESTADO_LABORATORIO"] != "Bloqueada"
        )
        boton_autorizar.configure(
            state="normal" if habilitado else "disabled"
        )

        for decision in datos["HISTORIAL"]:
            fecha = datetime.fromisoformat(
                decision["FECHA"]
            ).strftime("%d-%m-%Y %H:%M:%S %z")

            item = tabla.insert(
                "",
                "end",
                values=(
                    fecha,
                    (
                        f"Muestra #{decision['MUESTRA_ID']}"
                        if decision["MUESTRA_ID"] is not None
                        else "Evaluación conjunta"
                    ),
                    decision["ACCION"],
                    decision["ESTADO_LAB_ANTERIOR"],
                    decision["ESTADO_LAB_NUEVO"],
                    decision["ESTADO_UNIDAD_NUEVO"],
                    (
                        f"{decision['RESPONSABLE']} "
                        f"(ID {decision['RESPONSABLE_ID']})"
                    ),
                ),
            )
            historial_por_fila[item] = decision

    def autorizar():
        if datos_actuales is None:
            return

        texto_motivo = motivo.get().strip()

        if not texto_motivo or len(texto_motivo) > 1000:
            mensaje.configure(
                text="Ingrese un motivo de entre 1 y 1000 caracteres.",
                text_color="#DC2626",
            )
            return

        confirmado = messagebox.askyesno(
            "Autorizar liberación",
            (
                f"¿Autorizar la liberación de la unidad "
                f"#{donacion_id}?\n\n"
                "Se comprobarán nuevamente todas sus muestras, "
                "resultados, vigencia y estado de inventario."
            ),
            parent=frame,
        )

        if not confirmado:
            return

        try:
            autorizar_liberacion(
                donacion_id,
                empleado_id,
                texto_motivo,
            )
        except (ValueError, PermissionError) as error:
            cargar()
            mensaje.configure(
                text=str(error), text_color="#DC2626"
            )
            return
        except sqlite3.Error:
            cargar()
            mensaje.configure(
                text="No se pudo completar la autorización.",
                text_color="#DC2626",
            )
            return

        motivo.delete(0, "end")
        cargar()
        mensaje.configure(
            text="Liberación autorizada y registrada en el historial.",
            text_color=("#166534", "#86EFAC"),
        )

    def actualizar():
        mensaje.configure(text="")
        cargar()

    def volver():
        from pantallas.resultados_analisis import (
            mostrar_resultados_analisis,
        )

        contenedor.destroy()
        mostrar_resultados_analisis(
            pantalla,
            muestra_id,
            empleado_id,
        )

    acciones = ctk.CTkFrame(
        pie_acciones, fg_color="transparent"
    )
    acciones.pack(pady=15)

    boton_autorizar = ctk.CTkButton(
        acciones,
        text="Autorizar liberación",
        command=autorizar,
        state="disabled",
        fg_color="#15803D",
        hover_color="#166534",
    )
    boton_autorizar.pack(side="left", padx=8)

    ctk.CTkButton(
        acciones,
        text="Actualizar evaluación",
        command=actualizar,
    ).pack(side="left", padx=8)

    ctk.CTkButton(
        acciones,
        text="Volver a resultados",
        command=volver,
    ).pack(side="left", padx=8)

    cargar()