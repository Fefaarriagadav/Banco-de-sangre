import sqlite3
from concurrent.futures import ThreadPoolExecutor

import customtkinter as ctk
from tkinter import messagebox

from pantallas.selector_programacion import CAMPO, TINTA, SelectorProgramacion
from servicios.rutas_logisticas import (
    consultar_destino_emergencia,
    consultar_hoja_ruta,
    formatear_hoja_ruta,
    generar_hoja_ruta,
    notificar_logistica,
)


ERRORES_HOJA = (PermissionError, ValueError, sqlite3.Error)


def mostrar_hoja_ruta(padre, tipo, solicitud_id, empleado_id, *, tiene_hoja, actualizar):
    ventana = ctk.CTkToplevel(padre)
    ventana.title(f"Hoja de ruta · {tipo} #{solicitud_id}")
    ventana.geometry("720x630")
    ventana.transient(padre.winfo_toplevel())
    ventana.grab_set()
    contenido = ctk.CTkScrollableFrame(ventana)
    contenido.pack(fill="both", expand=True, padx=16, pady=16)

    def cargar_hoja():
        try:
            hoja = consultar_hoja_ruta(tipo, solicitud_id, empleado_id)
        except ERRORES_HOJA as error:
            messagebox.showerror("No se pudo consultar la hoja", str(error), parent=ventana)
            return

        for widget in contenido.winfo_children():
            widget.destroy()
        resumen = ctk.CTkTextbox(contenido, height=295, wrap="word")
        resumen.pack(fill="x", padx=8, pady=(8, 12))
        resumen.insert("1.0", formatear_hoja_ruta(hoja))
        resumen.configure(state="disabled")

        ctk.CTkLabel(contenido, text="Notificaciones a logística", font=("Arial", 17, "bold")).pack(anchor="w", padx=8)
        intentos = hoja["notificaciones"]
        if not intentos:
            ctk.CTkLabel(contenido, text="Todavía no hay intentos de notificación.").pack(anchor="w", padx=8)
        for intento in intentos:
            fecha = intento["FECHA"].replace("T", " ")
            texto = f"{fecha} · {intento['ESTADO']} · Empleado #{intento['EMPLEADO_ID']}"
            if intento["DESTINATARIO"]:
                texto += f"\nDestinatario: {intento['DESTINATARIO']}"
            if intento["DETALLE"]:
                texto += f"\n{intento['DETALLE']}"
            ctk.CTkLabel(contenido, text=texto, justify="left", wraplength=605).pack(anchor="w", padx=8, pady=4)

        acciones = ctk.CTkFrame(contenido, fg_color="transparent")
        acciones.pack(anchor="w", padx=8, pady=12)
        cerrar = ctk.CTkButton(acciones, text="Cerrar", command=ventana.destroy)
        cerrar.pack(side="right")
        ventana.protocol("WM_DELETE_WINDOW", ventana.destroy)
        if intentos and intentos[0]["ESTADO"] == "Enviado":
            return

        estado = ctk.CTkLabel(contenido, text="", justify="left", wraplength=605)
        estado.pack(anchor="w", padx=8)

        def enviar():
            notificar.configure(state="disabled")
            cerrar.configure(state="disabled")
            ventana.protocol("WM_DELETE_WINDOW", lambda: None)
            estado.configure(text="Enviando aviso a logística…")
            executor = ThreadPoolExecutor(max_workers=1)
            futuro = executor.submit(notificar_logistica, tipo, solicitud_id, empleado_id)
            executor.shutdown(wait=False)

            def revisar_resultado():
                if not futuro.done():
                    ventana.after(100, revisar_resultado)
                    return
                cerrar.configure(state="normal")
                notificar.configure(state="normal")
                ventana.protocol("WM_DELETE_WINDOW", ventana.destroy)
                try:
                    resultado = futuro.result()
                except ERRORES_HOJA as error:
                    estado.configure(text=str(error), text_color="#C62828")
                    return
                cargar_hoja()
                mostrar = messagebox.showinfo if resultado["estado"] == "Enviado" else messagebox.showerror
                mostrar("Notificación a logística", resultado["detalle"], parent=ventana)

            revisar_resultado()

        notificar = ctk.CTkButton(
            acciones, text="Reintentar notificación" if intentos else "Notificar a logística", command=enviar
        )
        notificar.pack(side="left", padx=(0, 10))

    if tiene_hoja:
        cargar_hoja()
        return

    ctk.CTkLabel(contenido, text="Generar hoja de ruta", font=("Arial", 23, "bold")).pack(anchor="w", padx=8, pady=(8, 4))
    programacion = None
    direccion = None
    if tipo == "Emergencia":
        try:
            centro, direccion = consultar_destino_emergencia(solicitud_id, empleado_id)
        except ERRORES_HOJA as error:
            ctk.CTkLabel(
                contenido, text=str(error), justify="left", wraplength=605,
                text_color=("#B91C1C", "#FCA5A5"),
            ).pack(anchor="w", padx=8, pady=12)
            ctk.CTkButton(contenido, text="Cerrar", command=ventana.destroy).pack(anchor="w", padx=8)
            return

        destino = ctk.CTkFrame(contenido, fg_color=CAMPO, corner_radius=10)
        destino.pack(fill="x", padx=8, pady=(8, 14))
        ctk.CTkLabel(destino, text="Destino de entrega", font=("Arial", 14, "bold"), text_color=TINTA).pack(
            anchor="w", padx=12, pady=(8, 0),
        )
        ctk.CTkLabel(destino, text=f"{centro}\n{direccion}", justify="left", wraplength=570, text_color=TINTA).pack(
            anchor="w", padx=12, pady=(1, 8),
        )
        programacion = SelectorProgramacion(contenido, etiqueta_fecha="Fecha de traslado")
        programacion.pack(fill="x", padx=8)
    else:
        ctk.CTkLabel(contenido, text="Se usarán los datos de traslado del despacho programado.").pack(anchor="w", padx=8)

    def generar():
        try:
            fecha, horario = programacion.obtener() if programacion is not None else (None, None)
            generar_hoja_ruta(tipo, solicitud_id, empleado_id, destino=direccion, fecha=fecha, horario=horario)
        except ERRORES_HOJA as error:
            messagebox.showerror("No se pudo generar la hoja", str(error), parent=ventana)
            return
        actualizar()
        cargar_hoja()

    ctk.CTkButton(contenido, text="Generar hoja de ruta", command=generar).pack(anchor="w", padx=8, pady=12)
