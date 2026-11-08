import customtkinter as ctk
import sqlite3
from datos.configuracion import RUTA_BD
from servicios.enviar_correos import enviar_correo

def mostrar_pedir_donaciones(pantalla):
    frame_filtro = ctk.CTkFrame(pantalla)
    frame_filtro.place(relx=0, rely=0, relwidth=1, relheight=1)
    titulo = ctk.CTkLabel(frame_filtro,text="Filtro de donantes",font=("Arial", 30, "bold"),text_color="#000000")
    titulo.place(relx=0.5, rely=0.05, anchor="center")

    frame_seleccion = ctk.CTkFrame(frame_filtro)
    frame_seleccion.place(relx=0.5,rely=0.15,anchor="n",relwidth=0.6,relheight=0.3)
    frame_seleccion.grid_columnconfigure(0, weight=1)
    frame_seleccion.grid_columnconfigure(1, weight=1)

    titulo_ts = ctk.CTkLabel(frame_seleccion,text="Seleccionar tipo de sangre",font=("Arial", 20, "bold"),text_color="#000000")
    titulo_ts.grid(row=0, column=0, padx=20, pady=5)

    sangres = ["Seleccione", "A", "B", "AB", "O"]
    ts = ctk.CTkOptionMenu(frame_seleccion,values=sangres,width=280,height=55,font=("Arial", 17))
    ts.set("Seleccione")
    ts.grid(row=1, column=0, padx=10, pady=20)

    titulo_rh = ctk.CTkLabel(frame_seleccion,text="Seleccionar factor RH",font=("Arial", 20, "bold"),text_color="#000000")
    titulo_rh.grid(row=0, column=1, padx=20, pady=5)
    factores = ["Seleccione", "Positivo", "Negativo"]
    rh = ctk.CTkOptionMenu(frame_seleccion,values=factores, width=280,height=55,font=("Arial", 17))
    rh.set("Seleccione")
    rh.grid(row=1, column=1, padx=10, pady=20)

    mensaje_error = ctk.CTkLabel(frame_filtro,text="",text_color="#DC2626",font=("Arial", 16, "bold"))
    mensaje_error.place(relx=0.5, rely=0.47, anchor="center")

    temporizador_mensaje = None
    def mostrar_mensaje(texto, color="#DC2626"):
        nonlocal temporizador_mensaje

        if temporizador_mensaje is not None:
            frame_filtro.after_cancel(temporizador_mensaje)
            temporizador_mensaje = None

        mensaje_error.configure(text=texto, text_color=color)

        if texto:
            temporizador_mensaje = frame_filtro.after(5000,lambda: mensaje_error.configure(text=""))

    frame_resultados = ctk.CTkScrollableFrame(frame_filtro,label_text="Donantes encontrados")
    frame_resultados.place(relx=0.5,rely=0.50,anchor="n",relwidth=0.6,relheight=0.30)

    for columna in range(3):
        frame_resultados.grid_columnconfigure(columna, weight=1)

    total_donantes = ctk.CTkLabel(frame_filtro,text="Total de donantes aptos: 0",font=("Arial", 20, "bold"))
    total_donantes.place(relx=0.5,rely=0.85,anchor="center")

    donantes_encontrados = []
    filtros_buscados = None

    def limpiar_resultados():
        nonlocal donantes_encontrados, filtros_buscados

        donantes_encontrados = []
        filtros_buscados = None

        boton_correo.configure(state="disabled")
        total_donantes.configure(text="Total de donantes aptos: 0")

        for widget in frame_resultados.winfo_children():
            widget.destroy()

    def invalidar_busqueda(valor=None):
        limpiar_resultados()
        mostrar_mensaje("")

    def buscar_donantes():
        nonlocal donantes_encontrados, filtros_buscados

        limpiar_resultados()
        ts_seleccionado = ts.get()
        rh_seleccionado = rh.get()
        if (ts_seleccionado == "Seleccione" or rh_seleccionado == "Seleccione"):
            mostrar_mensaje("Por favor, seleccione ambos filtros.")
            return

        mostrar_mensaje("")
        rh_bd = "+" if rh_seleccionado == "Positivo" else "-"
        try:
            conexion = sqlite3.connect(RUTA_BD)
            try:
                cursor = conexion.cursor()
                cursor.execute("""SELECT ID, GRUPO_SANGUINEO, FACTOR_RH, EMAIL FROM DONANTES WHERE GRUPO_SANGUINEO = ? AND FACTOR_RH = ? AND ELEGIBLE = 'Donante apto' """, (ts_seleccionado, rh_bd))
                donantes_encontrados = cursor.fetchall()
            finally:
                conexion.close()
        except sqlite3.Error:
            mostrar_mensaje("No se pudo consultar la base de datos.")
            return

        filtros_buscados = (ts_seleccionado, rh_bd)

        total_donantes.configure(text=f"Total de donantes aptos: {len(donantes_encontrados)}")
        encabezados = ["ID","Grupo sanguíneo","Factor Rh"]

        for columna, encabezado in enumerate(encabezados):
            etiqueta = ctk.CTkLabel(frame_resultados,text=encabezado,font=("Arial", 15, "bold"))
            etiqueta.grid(row=0,column=columna,padx=15,pady=10)

        for fila, donante in enumerate(donantes_encontrados, start=1):
            for columna, dato in enumerate(donante[:3]):
                etiqueta = ctk.CTkLabel(frame_resultados,text=str(dato),font=("Arial", 14))
                etiqueta.grid(row=fila,column=columna,padx=15,pady=5)

        if donantes_encontrados:
            boton_correo.configure(state="normal")
        else:
            mostrar_mensaje(
                "No hay donantes aptos para contactar."
            )

    def limpiar_filtros():
        ts.set("Seleccione")
        rh.set("Seleccione")
        limpiar_resultados()
        mostrar_mensaje("")

    def mandar_correos():

        if not donantes_encontrados:
            mostrar_mensaje(
                "No hay donantes para enviar correos."
            )
            return

        rh_actual = "+" if rh.get() == "Positivo" else "-"

        if filtros_buscados != (ts.get(), rh_actual):
            limpiar_resultados()
            mostrar_mensaje("Los filtros cambiaron. Realice una nueva búsqueda.")
            return
        
        ids_encontrados = [donante[0] for donante in donantes_encontrados]
        try:
            conexion = sqlite3.connect(RUTA_BD)
            try:
                cursor = conexion.cursor()
                candidatos_vigentes = []
                for donante_id in ids_encontrados:
                    cursor.execute("""SELECT ID, EMAIL FROM DONANTES WHERE ID = ? AND GRUPO_SANGUINEO = ? AND FACTOR_RH = ? AND ELEGIBLE = 'Donante apto' """, (donante_id, filtros_buscados[0],filtros_buscados[1]))
                    fila = cursor.fetchone()
                    if fila is not None and fila[1]:
                        candidatos_vigentes.append(fila)
            finally:
                conexion.close()
        except sqlite3.Error:
            mostrar_mensaje("No se pudo verificar la elegibilidad.")
            return

        if len(candidatos_vigentes) != len(donantes_encontrados):
            limpiar_resultados()
            mostrar_mensaje("La elegibilidad de los donantes cambió. Busque nuevamente.")
            return

        if not candidatos_vigentes:
            mostrar_mensaje("No hay destinatarios válidos.")
            return
        
        ventana_confirmacion = ctk.CTkToplevel(frame_filtro)
        ventana_confirmacion.title("Confirmar envío")
        ancho = 420
        alto = 260
        ventana_confirmacion.update_idletasks()
        pantalla_principal = frame_filtro.winfo_toplevel()
        x = (pantalla_principal.winfo_rootx() + (pantalla_principal.winfo_width() - ancho) // 2)
        y = (pantalla_principal.winfo_rooty() + (pantalla_principal.winfo_height() - alto) // 2)
        ventana_confirmacion.geometry(f"{ancho}x{alto}+{x}+{y}")

        ventana_confirmacion.transient(pantalla_principal)
        ventana_confirmacion.grab_set()

        mensaje_confirmacion = ctk.CTkLabel(ventana_confirmacion,text=(f"¿Desea enviar una invitación a " f"{len(candidatos_vigentes)} donantes?"),font=("Arial", 16),wraplength=360)
        mensaje_confirmacion.pack(pady=(30, 20))

        def confirmar_envio():
            ventana_confirmacion.destroy()
            boton_correo.configure(state="disabled")

            enviados = 0
            fallidos = 0

            for donante_id, destinatario in candidatos_vigentes:
                try:
                    enviar_correo(destinatario)
                    enviados += 1
                except Exception as error:
                    fallidos += 1
                    print(f"Error con donante {donante_id}: " f"{type(error).__name__}: {error}")
            mostrar_mensaje(f"Correos aceptados: {enviados}. " f"Fallidos: {fallidos}.", color="#15803D" if fallidos == 0 else "#DC2626")

        boton_cancelar = ctk.CTkButton(ventana_confirmacion,text="Cancelar",command=ventana_confirmacion.destroy, fg_color="dimgray",width=180,height=40)
        boton_cancelar.pack(pady=5)

        boton_confirmar = ctk.CTkButton(ventana_confirmacion,text="Confirmar envío",command=confirmar_envio,fg_color="#15803D",text_color="#FFFFFF",width=180,height=40)
        boton_confirmar.pack(pady=5)
    ts.configure(command=invalidar_busqueda)
    rh.configure(command=invalidar_busqueda)

    buscar_boton = ctk.CTkButton(frame_seleccion,text="Buscar",command=buscar_donantes,text_color="#FFFFFF",fg_color="#DC2626",width=200,height=45)
    buscar_boton.grid(row=3,column=0,pady=20)

    boton_limpiar = ctk.CTkButton(frame_seleccion,text="Limpiar filtros",command=limpiar_filtros,fg_color="#64748B",text_color="#FFFFFF",width=200,height=45)
    boton_limpiar.grid(row=3,column=1,pady=20)

    boton_correo = ctk.CTkButton(frame_filtro,text="Enviar correo",command=mandar_correos,fg_color="#15803D",text_color="#FFFFFF",font=("Arial", 17, "bold"),width=220,height=45,state="disabled")
    boton_correo.place(relx=0.5,rely=0.94,anchor="center")