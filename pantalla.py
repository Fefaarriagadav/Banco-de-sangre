import customtkinter as ctk
import sqlite3
from pantalla_principal import mostrar_principal

pantalla = ctk.CTk()
pantalla.title("Banco de sangre")
ctk.set_default_color_theme("blue") # color de los botones
pantalla.attributes("-fullscreen", True)

# iniciar sesión
frame_login = ctk.CTkFrame(pantalla)
frame_login.place(relx=0,rely=0,relheight=1, relwidth=1)
caja_id = ctk.CTkEntry(frame_login, placeholder_text= "Ingrese su ID", height = 80, width = 300, font =("Arial", 30))
caja_id.place(relx=0.5, rely=0.4, anchor="center")
mensaje = ctk.CTkLabel(frame_login, text="", text_color="#000000", height = 80, width = 280, font=("Arial", 30))
mensaje.place(relx=0.5, rely= 0.3,anchor = "center")

def inciar_sesion():
    id_ingresado = caja_id.get()
    conexion = sqlite3.connect("BancoDeSangre.db")
    cursor = conexion.cursor() # hacer consultas a la base de datos
    cursor.execute("SELECT * FROM PERSONAL WHERE ID_EMPLEADO = ?", (id_ingresado,))
    resultado = cursor.fetchone()
    if resultado is not None:
        cursor.execute("SELECT NOMBRE, ROL  FROM PERSONAL WHERE ID_EMPLEADO = ?", (id_ingresado,))
        resultado = cursor.fetchone()
        nombre = resultado[0]
        rol = resultado[1]
    conexion.close()

    if resultado is not None:
        frame_login.place_forget()
        mostrar_principal(pantalla, nombre, rol)
        mensaje.configure(text="Bienvenido, Personal Autorizado")
        
    else: 
        mensaje.configure(text="ID no encontrado. Intente nuevamente.")
        caja_id.delete(0, "end")


boton = ctk.CTkButton(frame_login, text="Ingresar", command= inciar_sesion,fg_color="gray",hover_color="dimgray")
boton.place(relx=0.5, rely=0.5, anchor="center")


pantalla.mainloop()
