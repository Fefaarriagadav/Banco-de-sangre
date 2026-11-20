import customtkinter as ctk
import sqlite3
from datos.configuracion import RUTA_BD
from pantallas.stock_hospitales import mostrar_stock_hospitales

def acceso_clinica(pantalla, volver_login):
    pantalla.title("Banco de sangre - Acceso Hospital/Clinica") #titulo que lleva arriba de todo
    ctk.set_default_color_theme("blue") # color de los botones
    pantalla.state("zoomed") #atributos de la pantalla para que ocupe la pantalla completa

    frame_acceso = ctk.CTkFrame(pantalla)
    frame_acceso.place(relx=0,rely=0,relheight=1, relwidth=1)

    mensaje = ctk.CTkLabel(frame_acceso, text="Acceso Hospital/Clinica", text_color="#000000", height = 80, width = 280, font=("Arial", 30)) #estructura del mensaje
    mensaje.place(relx=0.5, rely= 0.2,anchor = "center") #donde se veera el mensaje

    clin_hosp = ["Clínica Andes Salud Concepción", "Clínica del Sur Achs Salud", "Sanatorio Alemán", "Clínica Biobío", "Hospital Clínico Regional de Concepción", "Hospital Las Higueras de Talcahuano", "Hospital de Lota", "Hospital de Coronel", "Hospital de Mulchén", "Hospital de Nacimiento", "Hospital de Yumbel", "Hospital de Tomé", "Hospital de Penco", "Hospital Traumatológico de Concepción", "Hospital Naval Almirante Adriazola", "Hospital Clínico IST del Biobío", "Hospital Clorinda Avello", "Hospital San Agustín de Florida", "Hospital Provincial Dr. Rafael Avaria Valenzuela", "Clínica San Pedro"]
    clin_hosp = ["Seleccione"] + sorted(clin_hosp, key=str.casefold)
    centros_medicos = ctk.CTkOptionMenu(frame_acceso,values=clin_hosp,width=280,height=55,font=("Arial", 17))
    centros_medicos.set("Seleccione")
    centros_medicos.place(relx=0.5, rely=0.35, anchor="center")

    mensaje_error = ctk.CTkLabel(frame_acceso,text="",text_color="red",font=("Arial", 16))
    mensaje_error.place(relx=0.5,rely=0.6,anchor="center")

    def confirmar_acceso(): # Obtener el centro médico seleccionado
        centro_seleccionado = centros_medicos.get()
        # Validar que se haya seleccionado uno
        if centro_seleccionado == "Seleccione":
            mensaje_error.configure(text="Debe seleccionar un hospital o clínica")
            return
        mensaje_error.configure(text="")

        # Buscar los datos del centro en SQLite
        try:
            conexion = sqlite3.connect(RUTA_BD)
            try:
                cursor = conexion.cursor()
                cursor.execute("""SELECT NOMBRE, DIRECCION, COMUNA FROM CENTROS_MEDICOS WHERE NOMBRE = ? """, (centro_seleccionado,))
                resultado = cursor.fetchone()
            finally:
                conexion.close()

        except sqlite3.Error:
            mensaje_error.configure(text="No se pudo consultar la base de datos")
            return

        # Comprobar que el centro exista
        if resultado is None:
            mensaje_error.configure(text="El centro médico no está registrado")
            return

        nombre, direccion, comuna = resultado
        # Crear ventana de confirmación
        ventana_confirmacion = ctk.CTkToplevel(frame_acceso)
        ventana_confirmacion.title("Confirmar acceso")
        ancho = 550
        alto = 350
        ventana_principal = frame_acceso.winfo_toplevel()
        ventana_principal.update_idletasks()
        x = ventana_principal.winfo_rootx() + (ventana_principal.winfo_width() - ancho) // 2
        y = ventana_principal.winfo_rooty() + (ventana_principal.winfo_height() - alto) // 2

        ventana_confirmacion.geometry(f"{ancho}x{alto}+{x}+{y}")
        ventana_confirmacion.resizable(False, False)
        ventana_confirmacion.transient(frame_acceso.winfo_toplevel())
        ventana_confirmacion.grab_set()

        titulo = ctk.CTkLabel(ventana_confirmacion,text="Confirmación de acceso",font=("Arial", 24, "bold"))
        titulo.pack(pady=(25, 15))

        texto_confirmacion = ("¿Desea acceder como el siguiente centro médico?\n\n" f"{nombre}\n\n" f"Dirección: {direccion or 'No registrada'}\n" f"Comuna: {comuna or 'No registrada'}")

        informacion = ctk.CTkLabel(ventana_confirmacion,text=texto_confirmacion,font=("Arial", 17),justify="center",wraplength=480)
        informacion.pack(pady=10)

        # Función que se ejecuta al confirmar
        def aceptar_acceso():
            ventana_confirmacion.destroy()
            frame_acceso.destroy()
            mostrar_stock_hospitales(pantalla, nombre, volver_login)

        frame_botones = ctk.CTkFrame(ventana_confirmacion,fg_color="transparent")
        frame_botones.pack(pady=20)

        boton_cancelar = ctk.CTkButton(frame_botones,text="Cancelar",width=150,height=45,fg_color="gray",command=ventana_confirmacion.destroy)
        boton_cancelar.pack(side="left", padx=10)

        boton_confirmar = ctk.CTkButton(frame_botones,text="Confirmar",width=150,height=45,fg_color="#16A34A",command=aceptar_acceso)
        boton_confirmar.pack(side="left", padx=10)

    boton_acceder = ctk.CTkButton(frame_acceso, text="Acceder", command=confirmar_acceso, fg_color="gray", hover_color="dimgray", width=200, height=50)
    boton_acceder.place(relx=0.5, rely=0.5, anchor="center")

    boton_volver = ctk.CTkButton(frame_acceso, text="Volver", command=volver_login, fg_color="gray", hover_color="dimgray", width=100, height=25)
    boton_volver.place(relx=0.5, rely=0.9, anchor="center")