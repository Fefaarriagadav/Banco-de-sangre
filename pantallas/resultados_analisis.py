import sqlite3
from datetime import datetime
from tkinter import ttk

import customtkinter as ctk

from servicios.resultados_analisis import (
    CLASIFICACIONES,
    PENDIENTE,
    consultar_resultados,
    guardar_resultado,
)


def mostrar_resultados_analisis(pantalla, muestra_id, empleado_id):
    anterior = getattr(pantalla, "_pantalla_resultados", None)

    if anterior is not None and anterior.winfo_exists():
        anterior.destroy()

    frame = ctk.CTkFrame(pantalla)
    frame.place(relx=0, rely=0, relwidth=1, relheight=1)
    pantalla._pantalla_resultados = frame

    ctk.CTkLabel(
        frame,
        text=f"Resultados de la muestra #{muestra_id}",
        font=("Arial", 24, "bold"),
    ).pack(pady=(15, 5))

    resumen = ctk.CTkLabel(
        frame,
        text="Consultando...",
        wraplength=1000,
    )
    resumen.pack(pady=5)

    formulario = ctk.CTkFrame(frame)
    formulario.pack(fill="x", padx=20, pady=10)
    formulario.grid_columnconfigure(1, weight=1)

    ctk.CTkLabel(
        formulario, text="Análisis"
    ).grid(row=0, column=0, padx=10, pady=5, sticky="w")

    selector = ctk.CTkOptionMenu(
        formulario,
        values=["Sin catálogo"],
        width=350,
    )
    selector.grid(
        row=0, column=1, padx=10, pady=5, sticky="ew"
    )

    ctk.CTkLabel(
        formulario, text="Clasificación informada"
    ).grid(row=0, column=2, padx=10, pady=5)

    clasificacion = ctk.CTkOptionMenu(
        formulario,
        values=list(CLASIFICACIONES),
    )
    clasificacion.set(PENDIENTE)
    clasificacion.grid(row=0, column=3, padx=10, pady=5)

    ctk.CTkLabel(
        formulario, text="Resultado del informe"
    ).grid(row=1, column=0, padx=10, pady=5, sticky="w")

    resultado = ctk.CTkEntry(formulario)
    resultado.grid(
        row=1, column=1, columnspan=3,
        padx=10, pady=5, sticky="ew",
    )

    ctk.CTkLabel(
        formulario, text="Observaciones"
    ).grid(row=2, column=0, padx=10, pady=5, sticky="w")

    observaciones = ctk.CTkEntry(formulario)
    observaciones.grid(
        row=2, column=1, columnspan=3,
        padx=10, pady=5, sticky="ew",
    )

    ctk.CTkLabel(
        formulario, text="Motivo de corrección"
    ).grid(row=3, column=0, padx=10, pady=5, sticky="w")

    motivo = ctk.CTkEntry(
        formulario,
        placeholder_text="Obligatorio si modifica un resultado existente",
    )
    motivo.grid(
        row=3, column=1, columnspan=3,
        padx=10, pady=5, sticky="ew",
    )

    version = ctk.CTkLabel(formulario, text="")
    version.grid(
        row=4, column=0, columnspan=4, padx=10, pady=5
    )

    mensaje = ctk.CTkLabel(frame, text="", wraplength=1000)
    mensaje.pack(pady=5)

    def crear_tabla(titulo, columnas):
        ctk.CTkLabel(
            frame,
            text=titulo,
            font=("Arial", 16, "bold"),
        ).pack(pady=(5, 0))

        caja = ctk.CTkFrame(frame)
        caja.pack(fill="both", expand=True, padx=20, pady=5)
        caja.grid_columnconfigure(0, weight=1)
        caja.grid_rowconfigure(0, weight=1)

        tabla = ttk.Treeview(
            caja,
            columns=[clave for clave, nombre in columnas],
            show="headings",
            height=4,
        )

        for clave, nombre in columnas:
            tabla.heading(clave, text=nombre)
            tabla.column(
                clave, width=180, minwidth=90, anchor="center"
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

        return tabla

    tabla_resultados = crear_tabla(
        "Resultados actuales",
        [
            ("analisis", "Análisis"),
            ("resultado", "Resultado"),
            ("clasificacion", "Clasificación"),
            ("observaciones", "Observaciones"),
            ("responsable", "Responsable"),
            ("fecha", "Fecha"),
            ("version", "Versión"),
        ],
    )

    tabla_historial = crear_tabla(
        "Historial de versiones",
        [
            ("analisis", "Análisis"),
            ("version", "Versión"),
            ("resultado", "Resultado"),
            ("clasificacion", "Clasificación"),
            ("observaciones", "Observaciones"),
            ("responsable", "Responsable"),
            ("fecha", "Fecha"),
            ("motivo", "Motivo"),
        ],
    )

    datos_actuales = None
    analisis_por_etiqueta = {}

    def poner_texto(entrada, texto):
        entrada.delete(0, "end")
        entrada.insert(0, texto)

    def formatear_fecha(texto):
        return datetime.fromisoformat(texto).strftime(
            "%d-%m-%Y %H:%M:%S %z"
        )

    def limpiar_tabla(tabla):
        for item in tabla.get_children():
            tabla.delete(item)

    def cargar_analisis(valor=None):
        poner_texto(resultado, "")
        poner_texto(observaciones, "")
        poner_texto(motivo, "")
        clasificacion.set(PENDIENTE)
        version.configure(text="Nuevo resultado")

        if datos_actuales is None:
            return

        analisis_id = analisis_por_etiqueta.get(selector.get())

        for fila in datos_actuales["RESULTADOS"]:
            if fila["ANALISIS_ID"] == analisis_id:
                poner_texto(resultado, fila["RESULTADO"])
                poner_texto(observaciones, fila["OBSERVACIONES"])
                clasificacion.set(fila["CLASIFICACION"])
                version.configure(
                    text=(
                        f"Versión actual: {fila['VERSION']}. "
                        "Para corregirla debe indicar un motivo."
                    )
                )
                break

    selector.configure(command=cargar_analisis)

    def presentar(datos):
        nonlocal datos_actuales, analisis_por_etiqueta

        seleccion_anterior = selector.get()
        datos_actuales = datos
        muestra = datos["MUESTRA"]

        if not datos["CATALOGO_CONFIGURADO"]:
            estado_controles = (
                "Falta configurar el catálogo obligatorio. "
                "No se consideran completos los análisis."
            )
        elif datos["COMPLETOS"]:
            estado_controles = (
                "Controles completos. Requiere evaluación "
                "y autorización; la unidad NO está liberada."
            )
        else:
            estado_controles = (
                "Pendientes: " + ", ".join(datos["FALTANTES"])
            )

        if datos["TIENE_NO_CONFORMES"]:
            estado_controles += " Hay resultados No conformes."

        resumen.configure(
            text=(
                f"Donación #{muestra['DONACION_ID']} · "
                f"Muestra: {muestra['ESTADO']} · "
                f"Unidad: {muestra['ESTADO_UNIDAD']}\n"
                f"{estado_controles}"
            )
        )

        analisis_por_etiqueta = {
            (
                f"{fila['CODIGO']} — {fila['NOMBRE']} "
                f"({'obligatorio' if fila['OBLIGATORIO'] else 'opcional'})"
            ): fila["ID"]
            for fila in datos["CATALOGO"]
        }

        opciones = list(analisis_por_etiqueta)

        selector.configure(
            values=opciones or ["Sin catálogo"],
            state="normal" if opciones else "disabled",
        )
        selector.set(
            seleccion_anterior
            if seleccion_anterior in analisis_por_etiqueta
            else (opciones[0] if opciones else "Sin catálogo")
        )

        editable = (
            bool(opciones)
            and muestra["ESTADO"] in (
                "Pendiente de análisis",
                "Pendiente de revisión",
            )
            and muestra["ESTADO_UNIDAD"] == "Pendiente de análisis"
        )
        boton_guardar.configure(
            state="normal" if editable else "disabled"
        )

        limpiar_tabla(tabla_resultados)
        limpiar_tabla(tabla_historial)

        for fila in datos["RESULTADOS"]:
            tabla_resultados.insert(
                "",
                "end",
                values=(
                    fila["CODIGO"],
                    fila["RESULTADO"],
                    fila["CLASIFICACION"],
                    fila["OBSERVACIONES"],
                    f"{fila['RESPONSABLE']} (ID {fila['RESPONSABLE_ID']})",
                    formatear_fecha(fila["FECHA"]),
                    fila["VERSION"],
                ),
            )

        for fila in datos["HISTORIAL"]:
            tabla_historial.insert(
                "",
                "end",
                values=(
                    fila["CODIGO"],
                    fila["VERSION"],
                    fila["RESULTADO"],
                    fila["CLASIFICACION"],
                    fila["OBSERVACIONES"],
                    f"{fila['RESPONSABLE']} (ID {fila['RESPONSABLE_ID']})",
                    formatear_fecha(fila["FECHA"]),
                    fila["MOTIVO"],
                ),
            )

        cargar_analisis()

    def informar_error(error):
        mensaje.configure(
            text=str(error),
            text_color="#DC2626",
        )

    def cargar():
        nonlocal datos_actuales

        mensaje.configure(text="")

        try:
            datos = consultar_resultados(
                muestra_id, empleado_id
            )
        except (ValueError, PermissionError) as error:
            datos_actuales = None
            boton_guardar.configure(state="disabled")
            limpiar_tabla(tabla_resultados)
            limpiar_tabla(tabla_historial)
            resumen.configure(text="Información no disponible")
            informar_error(error)
            return
        except sqlite3.Error:
            datos_actuales = None
            boton_guardar.configure(state="disabled")
            limpiar_tabla(tabla_resultados)
            limpiar_tabla(tabla_historial)
            resumen.configure(text="Información no disponible")
            informar_error("No se pudieron consultar los resultados.")
            return

        presentar(datos)

    def guardar():
        analisis_id = analisis_por_etiqueta.get(selector.get())

        if analisis_id is None:
            informar_error("Seleccione un análisis del catálogo.")
            return

        try:
            datos = guardar_resultado(
                muestra_id=muestra_id,
                analisis_id=analisis_id,
                resultado=resultado.get(),
                clasificacion=clasificacion.get(),
                empleado_id=empleado_id,
                observaciones=observaciones.get(),
                motivo_cambio=motivo.get(),
            )
        except (ValueError, PermissionError) as error:
            informar_error(error)
            return
        except sqlite3.Error:
            informar_error(
                "No se pudo guardar. La operación fue revertida."
            )
            return

        presentar(datos)
        mensaje.configure(
            text="Resultado guardado con su historial.",
            text_color=("#166534", "#86EFAC"),
        )

    def volver():
        from pantallas.muestras import mostrar_muestras

        frame.destroy()
        mostrar_muestras(pantalla, empleado_id)

    acciones = ctk.CTkFrame(frame, fg_color="transparent")
    acciones.pack(pady=10)

    boton_guardar = ctk.CTkButton(
        acciones,
        text="Guardar resultado",
        command=guardar,
        state="disabled",
    )
    boton_guardar.pack(side="left", padx=8)

    ctk.CTkButton(
        acciones,
        text="Actualizar consulta",
        command=cargar,
    ).pack(side="left", padx=8)

    ctk.CTkButton(
        acciones,
        text="Volver a muestras",
        command=volver,
    ).pack(side="left", padx=8)

    cargar()