import customtkinter as ctk
from servicios.alertas_stock import obtener_alertas_sobreabastecimiento, sugerir_redistribucion

def mostrar_alertas_redistribucion(pantalla):
    # Limpiar el frame (mismo patrón que evaluar_donante.py)
    for widget in pantalla.winfo_children():
        widget.destroy()

    frame_principal = ctk.CTkFrame(pantalla, fg_color="transparent")
    frame_principal.place(relx=0, rely=0, relwidth=1, relheight=1)

    titulo = ctk.CTkLabel(frame_principal, text="Alertas de Sobreabastecimiento", font=("Arial", 26, "bold"), text_color="#000000")
    titulo.pack(pady=(20, 5))
    
    subtitulo = ctk.CTkLabel(frame_principal, text="Seleccione una alerta para ver sugerencias de redistribución (Acción solo informativa)", text_color="#333333")
    subtitulo.pack(pady=(0, 20))

    # Frame contenedor para las dos columnas (Alertas y Sugerencias)
    frame_columnas = ctk.CTkFrame(frame_principal, fg_color="transparent")
    frame_columnas.pack(fill="both", expand=True, padx=20, pady=10)
    frame_columnas.grid_columnconfigure(0, weight=1)
    frame_columnas.grid_columnconfigure(1, weight=1)

    # --- COLUMNA 1: ALERTAS ---
    frame_alertas = ctk.CTkScrollableFrame(frame_columnas, label_text="Stock Excedente", label_font=("Arial", 16, "bold"))
    frame_alertas.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

    # --- COLUMNA 2: SUGERENCIAS ---
    frame_sugerencias = ctk.CTkScrollableFrame(frame_columnas, label_text="Destinos Sugeridos", label_font=("Arial", 16, "bold"))
    frame_sugerencias.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
    
    mensaje_sugerencias = ctk.CTkLabel(frame_sugerencias, text="Seleccione un grupo sanguíneo a la izquierda", text_color="gray")
    mensaje_sugerencias.pack(pady=20)

    def cargar_sugerencias(grupo, rh, excedente):
        # Limpiar frame derecho
        for widget in frame_sugerencias.winfo_children():
            widget.destroy()
            
        try:
            destinos = sugerir_redistribucion(grupo, rh)
        except ValueError:
            ctk.CTkLabel(frame_sugerencias, text="Error al cargar destinos", text_color="red").pack(pady=20)
            return

        ctk.CTkLabel(frame_sugerencias, text=f"Excedente a reubicar: {excedente} unidades de {grupo}{rh}", font=("Arial", 14, "bold")).pack(pady=10)

        # Criterio de Aceptación: Sin destinos válidos conocidos
        if not destinos:
            ctk.CTkLabel(frame_sugerencias, text="⚠️ Se muestra el excedente pero no hay una\nsugerencia de destino disponible en clínicas.", text_color="#DC2626", font=("Arial", 13, "bold")).pack(pady=20)
            return

        # Listar destinos sugeridos
        for dest in destinos:
            caja_dest = ctk.CTkFrame(frame_sugerencias, fg_color="#F1F5F9", corner_radius=10)
            caja_dest.pack(fill="x", padx=10, pady=5)
            
            ctk.CTkLabel(caja_dest, text=f"🏥 {dest['nombre']}", font=("Arial", 15, "bold"), text_color="#0F172A", anchor="w").pack(fill="x", padx=10, pady=(5,0))
            ctk.CTkLabel(caja_dest, text=f"Ubicación: {dest['direccion']}", text_color="#475569", anchor="w").pack(fill="x", padx=10)
            ctk.CTkLabel(caja_dest, text=f"Requiere: {dest['requiere']} bolsas", text_color="#059669", font=("Arial", 13, "bold"), anchor="w").pack(fill="x", padx=10, pady=(0,5))

    def cargar_alertas():
        for widget in frame_alertas.winfo_children():
            widget.destroy()
            
        try:
            alertas = obtener_alertas_sobreabastecimiento()
        except ValueError:
            ctk.CTkLabel(frame_alertas, text="Datos de stock o umbrales inválidos.\nNo puede determinarse el excedente.", text_color="red").pack(pady=20)
            return
            
        if not alertas:
            ctk.CTkLabel(frame_alertas, text="✅ Niveles normales. Ningún grupo supera su umbral.", text_color="green", font=("Arial", 14)).pack(pady=30)
            return

        for alerta in alertas:
            caja_alerta = ctk.CTkFrame(frame_alertas, fg_color="#FEE2E2", corner_radius=10)
            caja_alerta.pack(fill="x", padx=10, pady=5)
            
            texto_alerta = f"Sangre: {alerta['grupo']}{alerta['rh']}  |  Stock: {alerta['stock']} (Max: {alerta['umbral']})"
            ctk.CTkLabel(caja_alerta, text=texto_alerta, font=("Arial", 14, "bold"), text_color="#991B1B", anchor="w").pack(fill="x", padx=10, pady=(10,0))
            
            ctk.CTkLabel(caja_alerta, text=f"🔴 Excedente: {alerta['excedente']} bolsas", font=("Arial", 13), text_color="#7F1D1D", anchor="w").pack(fill="x", padx=10)
            
            btn_ver = ctk.CTkButton(caja_alerta, text="Ver Destinos", fg_color="#DC2626", hover_color="#991B1B", width=100,
                                    command=lambda g=alerta['grupo'], r=alerta['rh'], e=alerta['excedente']: cargar_sugerencias(g, r, e))
            btn_ver.pack(pady=10)

    # Botón para refrescar
    ctk.CTkButton(frame_principal, text="Actualizar Alertas", command=cargar_alertas, fg_color="#0D9488").pack(pady=10)

    # Carga inicial
    cargar_alertas()