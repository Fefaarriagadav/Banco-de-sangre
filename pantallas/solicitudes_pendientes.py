import customtkinter as ctk
import sqlite3
from pantallas.hoja_ruta import mostrar_hoja_ruta
from servicios.despachos import (consultar_solicitudes_pendientes,consultar_detalle_solicitud,aprobar_solicitud,rechazar_solicitud)
from servicios.rutas_logisticas import consultar_despachos_aprobados

from tkinter import messagebox

def mostrar_solicitudes_pendientes(pantalla, rol, empleado_id, abrir_donaciones):
    # usamos frame contenido del personal
    for widget in pantalla.winfo_children():
        widget.destroy()
    #colores
    FONDO = "#F3F5F9"
    AZUL = "#193653"
    GRIS = "#64748B"

    vista = ctk.CTkFrame(pantalla, fg_color=FONDO)
    vista.pack(fill="both", expand=True)
    encabezado = ctk.CTkFrame(vista, fg_color=AZUL, corner_radius=15)
    encabezado.pack(fill="x", padx=25, pady=(20, 10))
    ctk.CTkLabel(encabezado,text="SOLICITUDES DE DESPACHO",font=("Arial", 26, "bold"),text_color="white").pack(pady=(20, 5))
    ctk.CTkLabel(encabezado,text="Las emergencias tienen prioridad sobre los despachos programados",text_color="#CBD5E1").pack(pady=(0, 20))

    barra = ctk.CTkFrame(vista, fg_color="transparent")
    barra.pack(pady=8)
    lista = ctk.CTkScrollableFrame(vista, fg_color=FONDO)
    lista.pack(fill="both", expand=True, padx=25, pady=10)
    mensaje = ctk.CTkLabel(vista, text="", text_color="#C62828")
    mensaje.pack(pady=5)
    es_enfermero = str(rol).strip().casefold() == "enfermero"
    vista_aprobadas = False

    def revisar_solicitud(tipo, solicitud_id):
        try:
            detalle = consultar_detalle_solicitud(tipo, solicitud_id)
        except (sqlite3.Error, ValueError) as error:
            messagebox.showerror("Error",str(error))
            return
        solicitud = detalle["solicitud"]
        ventana = ctk.CTkToplevel(vista)
        ventana.title("Revisión de solicitud")
        ventana.geometry("760x650")
        ventana.transient(vista.winfo_toplevel())
        ventana.grab_set()
        contenido = ctk.CTkScrollableFrame(ventana)
        contenido.pack(fill="both", expand=True, padx=15, pady=15)
        ctk.CTkLabel(contenido,text=f"REVISIÓN DE {tipo.upper()} #{solicitud_id}",font=("Arial", 23, "bold"),text_color="#193653").pack(pady=(12, 15))
        grupo = (f'{solicitud["GRUPO_SANGUINEO"]}' f'{solicitud["FACTOR_RH"]}')

        volumen = solicitud["VOLUMEN_ML"]
        if volumen is None:
            volumen_texto = (f'{solicitud["CANTIDAD"]} bolsas ' "(solicitud antigua)")
        else:
            volumen_texto = f"{volumen} mL"
        resumen = (f'Hospital: {solicitud["CENTRO"]}\n' f'Grupo sanguíneo: {grupo}\n' f'Volumen solicitado: {volumen_texto}\n' f'Estado: {solicitud["ESTADO"]}\n\n' f'Stock disponible actualmente: '
            f'{detalle["total_disponible_ml"]} mL\n' f'Bolsas disponibles: ' f'{len(detalle["bolsas_disponibles"])}\n' f'Volumen asignado a esta solicitud: ' f'{detalle["total_asignado_ml"]} mL')

        ctk.CTkLabel(contenido,text=resumen,font=("Arial", 15),text_color="#193653",justify="left",anchor="w").pack(fill="x", padx=15, pady=10)
        #bolsas reservadas
        ctk.CTkLabel(contenido,text="BOLSAS ASIGNADAS A ESTA SOLICITUD",font=("Arial", 17, "bold"),text_color="#C62828").pack(pady=(15, 8))
        if detalle["bolsas_asignadas"]:
            for bolsa in detalle["bolsas_asignadas"]:
                texto = (f'Bolsa #{bolsa["ID"]}  |  ' f'{bolsa["VOLUMEN_ML"]} mL  |  ' f'Vence: {bolsa["FECHA_VENCIMIENTO"]}  |  ' f'Estado: {bolsa["ESTADO"]}')
                ctk.CTkLabel(contenido,text=texto,font=("Arial", 14),text_color="#193653",anchor="w").pack(fill="x", padx=20, pady=3)
        else:
            ctk.CTkLabel(contenido,text="Esta solicitud todavía no tiene bolsas asignadas.",text_color="#B45309").pack(pady=8)
        #inventario actual
        ctk.CTkLabel(contenido,text="BOLSAS DISPONIBLES EN EL INVENTARIO",font=("Arial", 17, "bold"),text_color="#193653").pack(pady=(20, 8))

        if detalle["bolsas_disponibles"]:
            for bolsa in detalle["bolsas_disponibles"]:
                texto = (f'Bolsa #{bolsa["ID"]}  |  ' f'{bolsa["VOLUMEN_ML"]} mL  |  ' f'Vence: {bolsa["FECHA_VENCIMIENTO"]}')
                ctk.CTkLabel(contenido,text=texto,font=("Arial", 14),text_color="#193653",anchor="w").pack(fill="x", padx=20, pady=3)
        else:
            ctk.CTkLabel(contenido,text="No hay bolsas disponibles de este grupo.",text_color="#C62828").pack(pady=8)
        #decisiones
        botones = ctk.CTkFrame(contenido,fg_color="transparent")
        botones.pack(pady=25)

        def aprobar():
            ventana.destroy()
            confirmar_aprobacion(tipo, solicitud_id)

        def rechazar():
            ventana.destroy()
            confirmar_rechazo(tipo, solicitud_id)

        if str(rol).strip().casefold() == "enfermero":
            ctk.CTkButton(botones,text="Confirmar aprobación",command=aprobar,fg_color="#15803D",hover_color="#166534",width=200,height=42).pack(side="left", padx=8)
            ctk.CTkButton(botones,text="Rechazar",command=rechazar,fg_color="#DC2626",hover_color="#B91C1C",width=140,height=42).pack(side="left", padx=8)
        ctk.CTkButton(contenido,text="Cerrar revisión",command=ventana.destroy,fg_color="#64748B",width=180).pack(pady=(0, 15))

    def confirmar_aprobacion(tipo, solicitud_id):
        confirmar = messagebox.askyesno("Confirmar aprobación", f"¿Desea aprobar la solicitud {tipo} #{solicitud_id}?")
        if not confirmar:
            return
        try:
            resultado = aprobar_solicitud(tipo,solicitud_id,empleado_id)
            messagebox.showinfo("Solicitud aprobada", resultado)
            actualizar()
        except (sqlite3.Error, ValueError, PermissionError) as error:
            messagebox.showerror("No se pudo aprobar",str(error))
            actualizar()

    def confirmar_rechazo(tipo, solicitud_id):
        ventana = ctk.CTkInputDialog(text="Ingrese el motivo por el que rechaza la solicitud:",title="Rechazar solicitud")
        motivo = ventana.get_input()
        #si se cierra la ventana sin confirmar se cancela
        if motivo is None:
            return
        try:
            resultado = rechazar_solicitud(tipo,solicitud_id,empleado_id,motivo)
            messagebox.showinfo("Solicitud rechazada", resultado)
            actualizar()
        except (sqlite3.Error, ValueError, PermissionError) as error:
            messagebox.showerror("No se pudo rechazar",str(error))
            actualizar()

    def actualizar():
        for widget in lista.winfo_children():
            widget.destroy()
        try:
            solicitudes = (
                consultar_despachos_aprobados(empleado_id) if vista_aprobadas
                else consultar_solicitudes_pendientes()
            )
        except (sqlite3.Error, PermissionError) as error:
            mensaje.configure(text=f"Error al consultar las solicitudes: {error}")
            return
        mensaje.configure(text="")
        if not solicitudes:
            estado = "aprobadas" if vista_aprobadas else "pendientes"
            ctk.CTkLabel(lista,text=f"No hay solicitudes {estado}.",font=("Arial", 17),text_color=GRIS).pack(pady=30)
            return

        if vista_aprobadas:
            for solicitud in solicitudes:
                tipo = solicitud["TIPO"]
                solicitud_id = solicitud["ID"]
                tiene_hoja = solicitud["HOJA_ID"] is not None
                tarjeta = ctk.CTkFrame(lista, fg_color="#FFFFFF", corner_radius=15, border_width=1, border_color="#DDE5EF")
                tarjeta.pack(fill="x", padx=10, pady=8)
                ctk.CTkLabel(tarjeta, text=f"{tipo} · Solicitud #{solicitud_id}", font=("Arial", 19, "bold"), text_color=AZUL).pack(anchor="w", padx=20, pady=(14, 4))
                ctk.CTkLabel(tarjeta, text=f'{solicitud["CENTRO"]} · {solicitud["GRUPO_SANGUINEO"]}{solicitud["FACTOR_RH"]}', text_color=AZUL).pack(anchor="w", padx=20)
                ctk.CTkButton(
                    tarjeta, text="Consultar hoja de ruta" if tiene_hoja else "Generar hoja de ruta",
                    command=lambda t=tipo, s=solicitud_id, h=tiene_hoja: mostrar_hoja_ruta(
                        vista, t, s, empleado_id, tiene_hoja=h, actualizar=actualizar
                    ),
                ).pack(anchor="w", padx=20, pady=(8, 14))
            return

        for solicitud in solicitudes:
            tipo = solicitud["TIPO"]
            emergencia = tipo == "Emergencia"
            tarjeta = ctk.CTkFrame(lista,fg_color="#FFFFFF",corner_radius=15,border_width=1,border_color="#F4B4B4" if emergencia else "#DDE5EF")
            tarjeta.pack(fill="x", padx=10, pady=8)
            titulo = (f'🚨 EMERGENCIA · Solicitud #{solicitud["ID"]}'
                if emergencia
                else f'📅 PROGRAMADO · Solicitud #{solicitud["ID"]}')
            ctk.CTkLabel(tarjeta,text=titulo,font=("Arial", 19, "bold"),text_color="#C62828" if emergencia else "#2563EB").pack(anchor="w", padx=20, pady=(14, 5))

            grupo = (f'{solicitud["GRUPO_SANGUINEO"]}'f'{solicitud["FACTOR_RH"]}')
            volumen = solicitud["VOLUMEN_ML"]
            if volumen is not None:
                cantidad = f"{volumen} mL"
            else:
                cantidad = (f'{solicitud["CANTIDAD"]} bolsas' " (registro anterior)")
            datos = (f'Hospital: {solicitud["CENTRO"]}\n' f'Grupo sanguíneo: {grupo}\n' f'Cantidad: {cantidad}\n' f'Estado: {solicitud["ESTADO"]}')

            if emergencia:
                datos += (f'\nMotivo: {solicitud["MOTIVO"]}')
            else:
                datos += (f'\nDespacho: {solicitud["FECHA_DESPACHO"]}' f' a las {solicitud["HORA_DESPACHO"]}')

            ctk.CTkLabel(tarjeta,text=datos,justify="left",anchor="w",wraplength=750,text_color=AZUL).pack(fill="x", padx=20, pady=(0, 12))
            acciones = ctk.CTkFrame(tarjeta, fg_color="transparent")
            acciones.pack(anchor="w", padx=20, pady=(0, 15))

            #se habilitaran cuando se conecete
            if str(rol).strip().casefold() == "enfermero":
                ctk.CTkButton(acciones,text="Aprobar",command=lambda t = tipo, s = solicitud["ID"]: revisar_solicitud(t,s),fg_color="#15803D",hover_color="#166534",width=110).pack(side="left", padx=(0, 8))
                ctk.CTkButton(acciones,text="Rechazar",command=lambda t = tipo, s = solicitud["ID"]:confirmar_rechazo(t,s), fg_color="#DC2626", hover_color="#B91C1C",width=110).pack(side="left", padx=(0, 8))
            if not emergencia:
                ctk.CTkButton(acciones,text="Pedir donaciones",command=abrir_donaciones,fg_color="#16A34A",width=160).pack(side="left", padx=8)
            else:
                ctk.CTkButton(acciones,text="Derivar a otro banco",state="disabled",width=180).pack(side="left", padx=8)

    def cambiar_vista(opcion):
        nonlocal vista_aprobadas
        vista_aprobadas = opcion == "Aprobadas"
        actualizar()

    if es_enfermero:
        selector = ctk.CTkSegmentedButton(barra, values=["Pendientes", "Aprobadas"], command=cambiar_vista)
        selector.set("Pendientes")
        selector.pack(side="left", padx=(0, 10))
    ctk.CTkButton(barra,text="⟳ Actualizar solicitudes",command=actualizar,width=230).pack(side="left")
    actualizar()
