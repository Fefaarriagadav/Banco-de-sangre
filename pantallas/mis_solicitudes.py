import customtkinter as ctk
import sqlite3
from servicios.despachos import consultar_mis_solicitudes

def mostrar_mis_solicitudes(pantalla, centro, volver_stock):
    pantalla.title("Banco de sangre - Mis solicitudes")
    #colores
    FONDO = "#F3F5F9"
    AZUL = "#193653"
    BLANCO = "#FFFFFF"
    GRIS = "#64748B"

    vista = ctk.CTkFrame(pantalla,fg_color=FONDO,corner_radius=0)
    vista.place(relx=0,rely=0,relwidth=1,relheight=1)
    # encabezado
    encabezado = ctk.CTkFrame(vista,fg_color=AZUL,corner_radius=15)
    encabezado.pack(fill="x",padx=35,pady=(25, 15))
    ctk.CTkLabel(encabezado,text="MIS SOLICITUDES",font=("Arial", 28, "bold"),text_color=BLANCO).pack(pady=(20, 5))
    ctk.CTkLabel(encabezado,text=f"Centro médico: {centro}",font=("Arial", 16),text_color="#CBD5E1",wraplength=850).pack(pady=(0, 20))

    #botones
    barra_botones = ctk.CTkFrame(vista,fg_color="transparent")
    barra_botones.pack(pady=10)
   
    #dos columnas
    panel_solicitudes = ctk.CTkFrame(vista,fg_color="transparent")
    panel_solicitudes.pack(fill="both",expand=True,padx=35,pady=(10, 20))
    panel_solicitudes.grid_columnconfigure(0, weight=1, uniform="columnas")
    panel_solicitudes.grid_columnconfigure(1, weight=1, uniform="columnas")
    panel_solicitudes.grid_rowconfigure(1, weight=1)

    #columna despachos programdos
    ctk.CTkLabel(panel_solicitudes,text="📅 DESPACHOS PROGRAMADOS",font=("Arial", 19, "bold"),text_color="#2563EB").grid(row=0, column=0, pady=(0, 12))

    #columan despachos emergencias
    ctk.CTkLabel(panel_solicitudes,text="🚨 DESPACHOS DE EMERGENCIA",font=("Arial", 19, "bold"),text_color="#C62828").grid(row=0, column=1, pady=(0, 12))

    #lista de solicitudes programdos
    lista_programados = ctk.CTkScrollableFrame(panel_solicitudes,fg_color="#E9EFF6",corner_radius=15)
    lista_programados.grid(row=1,column=0,sticky="nsew",padx=(0, 10))

    #lista de solicitudes de emergencia
    lista_emergencias = ctk.CTkScrollableFrame(panel_solicitudes,fg_color="#FCEEEF",corner_radius=15)
    lista_emergencias.grid(row=1,column=1,sticky="nsew",padx=(10, 0))

    def actualizar_lista():
        for widget in lista_programados.winfo_children():
            widget.destroy()
        for widget in lista_emergencias.winfo_children():
            widget.destroy()

        try:
            solicitudes = consultar_mis_solicitudes(centro)
        except (sqlite3.Error, ValueError, PermissionError) as error:
            ctk.CTkLabel(
                lista_programados,
                text=f"No se pudieron cargar las solicitudes: {error}",
                text_color="#C62828"
            ).pack(pady=25)
            return

        if not solicitudes:
            for columna in (lista_programados, lista_emergencias):
                ctk.CTkLabel(columna,text="No hay solicitudes registradas.",font=("Arial", 15),text_color=GRIS).pack(pady=30)
            return
        for solicitud in solicitudes:
            tipo = solicitud["TIPO"]
            estado = solicitud["ESTADO"]
            color_tipo = ("#C62828"
                if tipo == "Emergencia"
                else "#2563EB")
            if tipo == "Emergencia":
                columna_destino = lista_emergencias
            else:
                columna_destino = lista_programados

            tarjeta = ctk.CTkFrame(columna_destino,fg_color=BLANCO,corner_radius=14,border_width=1,border_color="#E2E8F0")
            tarjeta.pack(fill="x",padx=10,pady=8)

            ctk.CTkLabel(tarjeta,text=f'{tipo} · Solicitud #{solicitud["ID"]}',font=("Arial", 19, "bold"),text_color=color_tipo).pack(anchor="w",padx=20,pady=(15, 5))

            grupo = (f'{solicitud["GRUPO_SANGUINEO"]}' f'{solicitud["FACTOR_RH"]}')

            volumen = solicitud["VOLUMEN_ML"]
            if volumen is not None:
                cantidad_texto = f"{volumen} mL"
            else:
                cantidad_antigua = solicitud.get("CANTIDAD")
                cantidad_texto = (f"{cantidad_antigua} bolsas" " (solicitud anterior)")

            if tipo == "Emergencia":
                fecha_texto = solicitud["FECHA_SOLICITUD"]
                detalle = (f'Grupo sanguíneo: {grupo}\n' f'Volumen solicitado: {cantidad_texto}\n' f'Fecha de solicitud: {fecha_texto}\n' f'Motivo: {solicitud["MOTIVO"]}')
            else:
                detalle = (f'Grupo sanguíneo: {grupo}\n' f'Cantidad solicitada: {cantidad_texto}\n' f'Fecha del despacho: ' f'{solicitud["FECHA_DESPACHO"]}\n' f'Hora: {solicitud["HORA_DESPACHO"]}')

            ctk.CTkLabel(tarjeta,text=detalle,font=("Arial", 14),text_color=AZUL,justify="left",anchor="w",wraplength=480).pack(fill="x",padx=20,pady=5)

            if estado in ("Aprobada", "Aprobado"):
                color_estado = "#15803D"
            elif estado in ("Rechazada", "Rechazado"):
                color_estado = "#C62828"
            else:
                color_estado = "#B45309"

            ctk.CTkLabel(tarjeta,text=f"Estado: {estado}",font=("Arial", 15, "bold"),text_color=color_estado).pack(anchor="w",padx=20,pady=(5, 15))

        if not any(s["TIPO"] == "Programado" for s in solicitudes):
            ctk.CTkLabel(lista_programados,text="No hay despachos programados.",text_color=GRIS).pack(pady=30)
        if not any(s["TIPO"] == "Emergencia" for s in solicitudes):
            ctk.CTkLabel(lista_emergencias,text="No hay solicitudes de emergencia.",text_color=GRIS).pack(pady=30)

    #actualizar
    ctk.CTkButton(barra_botones,text="⟳ Actualizar solicitudes",command=actualizar_lista,width=230,height=45,fg_color="#2563EB",hover_color="#1D4ED8").pack(side="left", padx=10)

    #volver
    def volver():
        vista.destroy()
        volver_stock()

    ctk.CTkButton(barra_botones,text="← Volver al inventario",command=volver,width=220,height=45,fg_color=GRIS,hover_color="#475569").pack(side="left", padx=10)

    actualizar_lista()
