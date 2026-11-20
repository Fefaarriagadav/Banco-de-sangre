import sqlite3
from calendar import monthrange
from datetime import date

import customtkinter as ctk

from servicios.despachos import (
    FACTORES_RH,
    GRUPOS,
    PENDIENTE,
    consultar_despachos,
    consultar_direccion_despacho,
    registrar_despacho,
)
from servicios.vencimientos import fecha_actual


MESES = (
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
)


FONDO = ("#F1F5F9", "#151D29")
SUPERFICIE = ("#FFFFFF", "#212C3B")
BORDE = ("#DDE5EF", "#354255")
TINTA = ("#193653", "#F1F5F9")
TEXTO_SECUNDARIO = ("#53677E", "#B4C2D3")
CAMPO = ("#EDF3F9", "#2D3C50")
BOTON_CAMPO = ("#DCE8F4", "#3B506A")
DESTACADO = ("#FBF1F3", "#382633")
BORDE_DESTINO = ("#F0D8DF", "#624351")
ACENTO = ("#912B46", "#A73956")


def mostrar_despacho_programado(pantalla, centro, volver_stock):
    pantalla.title("Banco de sangre - Despacho programado")
    vista = ctk.CTkFrame(pantalla, corner_radius=0, fg_color=FONDO)
    vista.place(relwidth=1, relheight=1)
    contenido = ctk.CTkFrame(vista, fg_color="transparent")
    contenido.pack(fill="both", expand=True, padx=24, pady=(20, 12))

    def ajustar_margen(evento):
        contenido.pack_configure(padx=max(20, (evento.width - 1100) // 2))

    vista.bind("<Configure>", ajustar_margen, add="+")

    def volver():
        vista.destroy()
        volver_stock()

    encabezado = ctk.CTkFrame(contenido, fg_color="#193653", corner_radius=18)
    encabezado.pack(fill="x")
    encabezado.columnconfigure(0, weight=1)
    ctk.CTkLabel(
        encabezado, text="BANCO DE SANGRE", font=("Arial", 11, "bold"),
        text_color="#BCD1E7", height=16,
    ).grid(row=0, column=0, sticky="w", padx=24, pady=(16, 0))
    ctk.CTkLabel(
        encabezado, text="Despacho programado", font=("Arial", 30, "bold"),
        text_color="#FFFFFF", height=40,
    ).grid(row=1, column=0, sticky="w", padx=24)
    ctk.CTkLabel(
        encabezado, text=f"Centro solicitante: {centro}", font=("Arial", 14),
        text_color="#DFEAF6", anchor="w", justify="left", wraplength=480,
    ).grid(row=2, column=0, sticky="w", padx=24, pady=(0, 15))
    ctk.CTkButton(
        encabezado, text="← Volver al inventario", command=volver,
        fg_color="#284B6D", hover_color="#355F86", text_color="#FFFFFF",
        font=("Arial", 13, "bold"), height=38, width=172, corner_radius=10,
    ).grid(row=0, column=1, rowspan=3, padx=(8, 22))

    pestanas = ctk.CTkTabview(
        contenido, anchor="nw", fg_color=FONDO, text_color=TINTA,
        segmented_button_fg_color=BOTON_CAMPO,
        segmented_button_selected_color=SUPERFICIE,
        segmented_button_selected_hover_color=SUPERFICIE,
        segmented_button_unselected_color=BOTON_CAMPO,
        segmented_button_unselected_hover_color=CAMPO,
    )
    pestanas.pack(fill="both", expand=True, pady=(6, 0))
    nueva_solicitud = pestanas.add("Nueva solicitud")
    formulario = ctk.CTkScrollableFrame(
        nueva_solicitud, fg_color="transparent",
        scrollbar_button_color=BORDE, scrollbar_button_hover_color=BOTON_CAMPO,
    )
    formulario.pack(fill="both", expand=True)
    consulta = pestanas.add("Mis solicitudes")

    def seccion(titulo, *, color=SUPERFICIE, borde=BORDE):
        tarjeta = ctk.CTkFrame(
            formulario, fg_color=color, border_color=borde, border_width=1, corner_radius=14,
        )
        tarjeta.pack(fill="x", padx=3, pady=(0, 10))
        ctk.CTkLabel(
            tarjeta, text=titulo, font=("Arial", 18, "bold"), text_color=TINTA, height=25,
        ).pack(anchor="w", padx=18, pady=(11, 5))
        cuerpo = ctk.CTkFrame(tarjeta, fg_color="transparent")
        cuerpo.pack(fill="x", padx=18, pady=(0, 13))
        return cuerpo

    def etiqueta(padre, texto, *, secundaria=False):
        return ctk.CTkLabel(
            padre, text=texto, anchor="w",
            font=("Arial", 12 if secundaria else 14, "bold"),
            text_color=TEXTO_SECUNDARIO if secundaria else TINTA,
            height=20 if secundaria else 22,
        )

    estilo_menu = {
        "fg_color": CAMPO, "button_color": BOTON_CAMPO, "button_hover_color": BORDE,
        "text_color": TINTA, "font": ("Arial", 13), "height": 34, "corner_radius": 8,
    }
    bolsas = seccion("Unidades solicitadas")
    for columna in range(3):
        bolsas.columnconfigure(columna, weight=1, uniform="bolsas")
    grupo = ctk.CTkOptionMenu(bolsas, values=list(GRUPOS), width=140, **estilo_menu)
    grupo.set("Seleccione")
    rh = ctk.CTkOptionMenu(bolsas, values=list(FACTORES_RH), width=140, **estilo_menu)
    rh.set("Seleccione")
    cantidad = ctk.CTkEntry(
        bolsas, placeholder_text="Ej. 3", width=140, height=34, corner_radius=8,
        fg_color=CAMPO, border_color=BORDE, border_width=1,
        text_color=TINTA, placeholder_text_color=TEXTO_SECUNDARIO, font=("Arial", 13),
    )
    for columna, (nombre, control) in enumerate((
        ("Tipo de sangre", grupo),
        ("Factor Rh", rh),
        ("Cantidad de bolsas de sangre", cantidad),
    )):
        margen = (0, 14) if columna < 2 else (0, 0)
        etiqueta(bolsas, nombre).grid(row=0, column=columna, sticky="ew", padx=margen)
        control.grid(row=1, column=columna, sticky="ew", padx=margen, pady=(4, 0))

    def agregar_selector(padre, columna, nombre, valores, inicial, ancho, *, tipo=ctk.CTkOptionMenu):
        etiqueta(padre, nombre, secundaria=True).grid(row=0, column=columna, sticky="w")
        opciones = {"border_color": BORDE, "border_width": 1} if tipo is ctk.CTkComboBox else {}
        control = tipo(padre, values=valores, width=ancho, **estilo_menu, **opciones)
        control.set(inicial)
        control.grid(row=1, column=columna, sticky="w", padx=(0, 8), pady=(3, 0))
        return control

    programacion = seccion("Programación")
    programacion.columnconfigure(0, weight=1)
    programacion.columnconfigure(1, weight=1)
    etiqueta(programacion, "Fecha de despacho").grid(row=0, column=0, sticky="w")
    etiqueta(programacion, "Hora de Santiago").grid(row=0, column=1, sticky="w")
    hoy = fecha_actual()
    fecha = ctk.CTkFrame(programacion, fg_color="transparent")
    fecha.grid(row=1, column=0, sticky="w", pady=(3, 0), padx=(0, 16))
    dia = agregar_selector(fecha, 0, "Día", ["01"], f"{hoy.day:02}", 68)
    mes = agregar_selector(fecha, 1, "Mes", list(MESES), MESES[hoy.month - 1], 130)
    anios = [str(anio) for anio in range(hoy.year, min(hoy.year + 5, 10000))]
    anio = agregar_selector(fecha, 2, "Año", anios, str(hoy.year), 90, tipo=ctk.CTkComboBox)

    def actualizar_dias(_=None):
        try:
            ultimo_dia = monthrange(int(anio.get()), MESES.index(mes.get()) + 1)[1]
        except ValueError:
            return
        dias = [f"{numero:02}" for numero in range(1, ultimo_dia + 1)]
        dia.configure(values=dias)
        if dia.get() not in dias:
            dia.set("—")

    mes.configure(command=actualizar_dias)
    anio.configure(command=actualizar_dias)
    anio.bind("<FocusOut>", actualizar_dias)
    actualizar_dias()

    horario = ctk.CTkFrame(programacion, fg_color="transparent")
    horario.grid(row=1, column=1, sticky="w", pady=(3, 0))
    hora = agregar_selector(horario, 0, "Hora", [f"{h:02}" for h in range(24)], "—", 76)
    minuto = agregar_selector(horario, 1, "Minuto", [f"{m:02}" for m in range(60)], "00", 76)

    direccion = ""
    error_destino = ""
    try:
        direccion = consultar_direccion_despacho(centro)
    except (ValueError, PermissionError) as error:
        error_destino = str(error)
    except sqlite3.Error:
        error_destino = "No se pudo cargar la dirección. Vuelva a abrir el formulario."

    destino = seccion("Destino de entrega", color=DESTACADO, borde=BORDE_DESTINO)
    ctk.CTkLabel(
        destino, text=direccion or "Dirección no disponible", text_color=TINTA,
        font=("Arial", 15, "bold"), anchor="w", justify="left", wraplength=460,
    ).pack(anchor="w")
    confirmar_direccion = ctk.CTkCheckBox(
        destino, text="Confirmo la dirección de entrega", text_color=TINTA,
        fg_color=ACENTO, hover_color=ACENTO, border_color=ACENTO,
        checkbox_width=18, checkbox_height=18, border_width=2,
        font=("Arial", 13), state="normal" if direccion else "disabled",
    )
    confirmar_direccion.pack(anchor="w", pady=(6, 0))

    pie = ctk.CTkFrame(nueva_solicitud, fg_color="transparent")
    pie.pack(side="bottom", fill="x", padx=(7, 22), pady=(7, 9))
    mensaje = ctk.CTkLabel(
        pie, text=error_destino, anchor="w", justify="left", wraplength=520,
        text_color=("#B91C1C", "#FCA5A5"),
    )
    if error_destino:
        mensaje.pack(fill="x", padx=3, pady=(0, 4))

    def mostrar_mensaje(texto, color):
        mensaje.configure(text=texto, text_color=color)
        if not mensaje.winfo_manager():
            mensaje.pack(fill="x", padx=3, pady=(0, 4), before=acciones_formulario)

    def guardar():
        try:
            if not confirmar_direccion.get():
                raise ValueError("Confirme la dirección de entrega.")
            fecha_elegida = f"{dia.get()}-{MESES.index(mes.get()) + 1:02}-{anio.get().strip()}"
            hora_elegida = f"{hora.get()}:{minuto.get()}"
            solicitud_id = registrar_despacho(
                centro, grupo.get(), rh.get(), cantidad.get(), fecha_elegida,
                hora_elegida, direccion_confirmada=direccion,
            )
        except (ValueError, PermissionError) as error:
            mostrar_mensaje(str(error), ("#B91C1C", "#FCA5A5"))
            return
        except sqlite3.Error:
            mostrar_mensaje(
                "No se pudo guardar la solicitud. Intente nuevamente.", ("#B91C1C", "#FCA5A5")
            )
            return

        grupo.set("Seleccione")
        rh.set("Seleccione")
        cantidad.delete(0, "end")
        hora.set("—")
        minuto.set("00")
        confirmar_direccion.deselect()
        mostrar_mensaje(
            f"Solicitud #{solicitud_id} registrada. Estado: {PENDIENTE}.",
            ("#166534", "#86EFAC"),
        )

    acciones_formulario = ctk.CTkFrame(pie, fg_color="transparent")
    acciones_formulario.pack(fill="x")
    ctk.CTkButton(
        acciones_formulario, text="Registrar solicitud", command=guardar,
        fg_color=ACENTO, hover_color="#732238", text_color="#FFFFFF",
        font=("Arial", 14, "bold"), height=40, width=182, corner_radius=10,
        state="normal" if direccion else "disabled",
    ).pack(side="right")
    ctk.CTkLabel(
        acciones_formulario, text="La solicitud queda pendiente y no reserva unidades.",
        anchor="w", justify="left", wraplength=360, text_color=TEXTO_SECUNDARIO,
        font=("Arial", 13),
    ).pack(side="left", padx=(3, 10))

    acciones = ctk.CTkFrame(consulta, fg_color="transparent")
    acciones.pack(fill="x", padx=12, pady=(12, 8))
    lista = ctk.CTkScrollableFrame(consulta, fg_color="transparent")
    lista.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    def mostrar_mensaje_consulta(texto):
        ctk.CTkLabel(lista, text=texto, wraplength=520).pack(pady=12)

    def actualizar_solicitudes():
        for hijo in lista.winfo_children():
            hijo.destroy()
        try:
            solicitudes = consultar_despachos(centro)
        except PermissionError as error:
            mostrar_mensaje_consulta(str(error))
            return
        except sqlite3.Error:
            mostrar_mensaje_consulta("No se pudieron consultar las solicitudes.")
            return

        if not solicitudes:
            mostrar_mensaje_consulta("Aún no hay solicitudes para este centro.")
        for solicitud in solicitudes:
            tarjeta = ctk.CTkFrame(lista)
            tarjeta.pack(fill="x", padx=8, pady=(0, 8))
            fecha_visible = date.fromisoformat(solicitud["FECHA_DESPACHO"]).strftime("%d-%m-%Y")
            cantidad_pedida = solicitud["CANTIDAD"]
            unidad = "bolsa" if cantidad_pedida == 1 else "bolsas"
            texto = (
                f'{solicitud["CENTRO"]}\n'
                f'{cantidad_pedida} {unidad} de sangre '
                f'{solicitud["GRUPO_SANGUINEO"]}{solicitud["FACTOR_RH"]}\n'
                f'Despacho: {fecha_visible} a las {solicitud["HORA_DESPACHO"]}\n'
                f'Destino: {solicitud["DESTINO"]}'
            )
            ctk.CTkLabel(
                tarjeta, text=f'Solicitud #{solicitud["ID"]} · {solicitud["ESTADO"]}',
                font=("Arial", 15, "bold"),
            ).pack(anchor="w", padx=14, pady=(8, 0))
            ctk.CTkLabel(tarjeta, text=texto, justify="left", wraplength=600).pack(
                anchor="w", padx=14, pady=(0, 10)
            )

    ctk.CTkButton(acciones, text="Actualizar lista", command=actualizar_solicitudes).pack(
        side="right"
    )

    def cambiar_pestana():
        if pestanas.get() == "Mis solicitudes":
            actualizar_solicitudes()

    pestanas.configure(command=cambiar_pestana)
