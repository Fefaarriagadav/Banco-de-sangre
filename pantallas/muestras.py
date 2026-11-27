import sqlite3
from datetime import datetime
from tkinter import messagebox, ttk

import customtkinter as ctk

from servicios.muestras import registrar_muestra
from servicios.consulta_laboratorio import (
    SITUACIONES,
    TIPOS,
    listar_laboratorio,
    filtrar_registros,
)


def mostrar_muestras(pantalla, empleado_id):
    anterior = getattr(pantalla, "_pantalla_muestras", None)

    if anterior is not None and anterior.winfo_exists():
        anterior.destroy()

    frame = ctk.CTkFrame(pantalla)
    frame.place(relx=0, rely=0, relwidth=1, relheight=1)
    pantalla._pantalla_muestras = frame

    frame.grid_columnconfigure(0, weight=1)
    frame.grid_rowconfigure(3, weight=1)

    ctk.CTkLabel(
        frame,
        text="Laboratorio: muestras y donaciones",
        font=("Arial", 24, "bold"),
    ).grid(row=0, column=0, pady=(15, 5))

    filtros = ctk.CTkFrame(frame)
    filtros.grid(
        row=1, column=0, sticky="ew", padx=15, pady=5
    )
    filtros.grid_columnconfigure(0, weight=1)

    busqueda = ctk.CTkEntry(
        filtros,
        placeholder_text=(
            "Filtrar por ID de muestra, donación, "
            "donante o responsable"
        ),
    )
    busqueda.grid(
        row=0, column=0, sticky="ew", padx=8, pady=10
    )

    situacion = ctk.CTkOptionMenu(
        filtros,
        values=list(SITUACIONES),
        width=225,
    )
    situacion.grid(row=0, column=1, padx=8)

    tipo = ctk.CTkOptionMenu(
        filtros,
        values=list(TIPOS),
        width=100,
    )
    tipo.grid(row=0, column=2, padx=8)

    mensaje = ctk.CTkLabel(
        frame, text="", wraplength=1000
    )
    mensaje.grid(row=2, column=0, padx=15, pady=5)

    pestanas = ctk.CTkTabview(frame)
    pestanas.grid(
        row=3, column=0, sticky="nsew", padx=15, pady=5
    )

    pie = ctk.CTkFrame(frame, fg_color="transparent")
    pie.grid(
        row=4, column=0, sticky="ew", padx=15, pady=10
    )

    seleccion = ctk.CTkLabel(
        pie, text="Seleccione una fila para trabajar."
    )
    seleccion.pack(side="left", padx=5)

    def crear_tabla(nombre, columnas):
        tab = pestanas.add(nombre)
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(0, weight=1)

        control = ttk.Treeview(
            tab,
            columns=[clave for clave, titulo in columnas],
            show="headings",
            selectmode="browse",
            height=8,
        )

        for clave, titulo in columnas:
            control.heading(clave, text=titulo)
            control.column(
                clave,
                width=175,
                minwidth=90,
                anchor="center",
            )

        vertical = ttk.Scrollbar(
            tab, orient="vertical", command=control.yview
        )
        horizontal = ttk.Scrollbar(
            tab, orient="horizontal", command=control.xview
        )

        control.configure(
            yscrollcommand=vertical.set,
            xscrollcommand=horizontal.set,
        )

        control.grid(row=0, column=0, sticky="nsew")
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal.grid(row=1, column=0, sticky="ew")

        return control

    columnas_muestras = [
        ("MUESTRA_ID", "ID muestra"),
        ("DONACION_ID", "ID donación / unidad"),
        ("DONANTE_ID", "ID donante"),
        ("TIPO", "Sangre / Rh"),
        ("AVANCE", "Controles completos"),
        ("SITUACION", "Situación de la unidad"),
        ("ESTADO_MUESTRA", "Estado registrado de muestra"),
        ("INVENTARIO", "Inventario"),
        ("RESPONSABLE", "Responsable"),
        ("FECHA_REGISTRO", "Registro de muestra"),
    ]

    columnas_donaciones = [
        ("DONACION_ID", "ID donación / unidad"),
        ("DONANTE_ID", "ID donante"),
        ("TIPO", "Sangre / Rh"),
        ("NUM_MUESTRAS", "Muestras registradas"),
        ("SITUACION", "Situación de la unidad"),
        ("INVENTARIO", "Inventario"),
        ("EXTRACCION", "Extracción"),
        ("VENCIMIENTO", "Vencimiento"),
    ]

    tablas = {
        "Muestras": crear_tabla("Muestras", columnas_muestras),
        "Donaciones": crear_tabla("Donaciones", columnas_donaciones),
    }
    columnas = {
        "Muestras": columnas_muestras,
        "Donaciones": columnas_donaciones,
    }

    datos = {"MUESTRAS": [], "DONACIONES": []}
    referencias = {"Muestras": {}, "Donaciones": {}}

    def elegida():
        nombre = pestanas.get()
        items = tablas[nombre].selection()

        return (
            referencias[nombre].get(items[0])
            if items
            else None
        )

    def actualizar_seleccion(event=None):
        fila = elegida()

        if fila is None:
            seleccion.configure(
                text="Seleccione una fila para trabajar."
            )
        else:
            texto = f"Donación #{fila['DONACION_ID']}"

            if "MUESTRA_ID" in fila:
                texto += f" · Muestra #{fila['MUESTRA_ID']}"

            seleccion.configure(text=texto)

        boton_resultados.configure(
            state=(
                "normal"
                if fila and pestanas.get() == "Muestras"
                else "disabled"
            )
        )
        boton_registrar.configure(
            state="normal" if fila else "disabled"
        )

    def aplicar(event=None):
        cantidades = []

        for nombre, clave in (
            ("Muestras", "MUESTRAS"),
            ("Donaciones", "DONACIONES"),
        ):
            control = tablas[nombre]

            for item in control.get_children():
                control.delete(item)

            referencias[nombre] = {}

            filas = filtrar_registros(
                datos[clave],
                busqueda.get(),
                situacion.get(),
                tipo.get(),
            )

            for fila in filas:
                valores = []

                for campo, titulo in columnas[nombre]:
                    valor = fila.get(campo)

                    if valor and campo == "FECHA_REGISTRO":
                        valor = datetime.fromisoformat(
                            valor
                        ).strftime("%d-%m-%Y %H:%M:%S %z")

                    elif valor and campo in (
                        "EXTRACCION", "VENCIMIENTO"
                    ):
                        try:
                            valor = datetime.strptime(
                                valor, "%Y-%m-%d"
                            ).strftime("%d-%m-%Y")
                        except ValueError:
                            pass

                    valores.append(
                        "—" if valor is None else valor
                    )

                item = control.insert(
                    "", "end", values=valores
                )
                referencias[nombre][item] = fila

            cantidades.append(f"{nombre}: {len(filas)}")

        mensaje.configure(
            text=" · ".join(cantidades),
            text_color=("gray30", "gray80"),
        )
        actualizar_seleccion()

    def recargar():
        nonlocal datos

        try:
            datos = listar_laboratorio(empleado_id)
        except (
            ValueError,
            PermissionError,
            sqlite3.Error,
        ) as error:
            datos = {"MUESTRAS": [], "DONACIONES": []}
            aplicar()
            mensaje.configure(
                text=f"No se pudo cargar el listado: {error}",
                text_color="#DC2626",
            )
            return

        aplicar()

    def limpiar():
        busqueda.delete(0, "end")
        situacion.set("Todas")
        tipo.set("Todos")
        aplicar()

    def abrir_resultados(event=None):
        fila = elegida()

        if pestanas.get() != "Muestras" or fila is None:
            return

        from pantallas.resultados_analisis import (
            mostrar_resultados_analisis,
        )

        mostrar_resultados_analisis(
            pantalla,
            fila["MUESTRA_ID"],
            empleado_id,
        )

    def registrar():
        fila = elegida()

        if fila is None:
            return

        donacion_id = fila["DONACION_ID"]

        confirmado = messagebox.askyesno(
            "Registrar muestra",
            (
                f"¿Registrar una nueva muestra para "
                f"la donación #{donacion_id}?\n\n"
                "La unidad quedará pendiente y fuera "
                "del stock disponible."
            ),
            parent=frame,
        )

        if not confirmado:
            return

        try:
            nueva = registrar_muestra(
                donacion_id, empleado_id
            )
        except (
            ValueError,
            PermissionError,
            sqlite3.Error,
        ) as error:
            mensaje.configure(
                text=str(error),
                text_color="#DC2626",
            )
            return

        limpiar()
        recargar()
        pestanas.set("Muestras")

        for item, registro in referencias["Muestras"].items():
            if registro["MUESTRA_ID"] == nueva["ID"]:
                tablas["Muestras"].selection_set(item)
                tablas["Muestras"].see(item)
                break

        actualizar_seleccion()
        mensaje.configure(
            text=(
                f"Muestra #{nueva['ID']} registrada para "
                f"donación #{donacion_id}."
            ),
            text_color=("#166534", "#86EFAC"),
        )

    boton_resultados = ctk.CTkButton(
        pie,
        text="Abrir resultados",
        command=abrir_resultados,
        state="disabled",
    )
    boton_resultados.pack(side="right", padx=5)

    boton_registrar = ctk.CTkButton(
        pie,
        text="Registrar nueva muestra",
        command=registrar,
        state="disabled",
    )
    boton_registrar.pack(side="right", padx=5)

    ctk.CTkButton(
        filtros,
        text="Limpiar filtros",
        command=limpiar,
        width=110,
    ).grid(row=0, column=3, padx=5)

    ctk.CTkButton(
        filtros,
        text="Actualizar",
        command=recargar,
        width=100,
    ).grid(row=0, column=4, padx=5)

    situacion.configure(command=lambda valor: aplicar())
    tipo.configure(command=lambda valor: aplicar())
    busqueda.bind("<KeyRelease>", aplicar)
    pestanas.configure(command=actualizar_seleccion)

    for control in tablas.values():
        control.bind(
            "<<TreeviewSelect>>",
            actualizar_seleccion,
        )

    tablas["Muestras"].bind(
        "<Double-1>", abrir_resultados
    )

    recargar()