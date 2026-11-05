import customtkinter as ctk #bibliteca de interfaz grafica
import sqlite3 #biblioteca de base de datos 
from pantalla_principal import mostrar_principal

#se crea la primera ventana, donde se debe inciiar sesión
pantalla = ctk.CTk()
pantalla.title("Banco de sangre") #titulo que lleva arriba de todo
ctk.set_default_color_theme("blue") # color de los botones
pantalla.state("zoomed") #atributos de la pantalla para que ocupe la pantalla completa

# iniciar sesión
frame_login = ctk.CTkFrame(pantalla)
frame_login.place(relx=0,rely=0,relheight=1, relwidth=1)
#caja de texto donde se debe ingresar el id
caja_id = ctk.CTkEntry(frame_login, placeholder_text= "Ingrese su ID", height = 80, width = 300, font =("Arial", 30))
caja_id.place(relx=0.5, rely=0.4, anchor="center") #donde se posiciona la caja de id en la pantalla
mensaje = ctk.CTkLabel(frame_login, text="", text_color="#000000", height = 80, width = 280, font=("Arial", 30)) #estructura del mensaje
mensaje.place(relx=0.5, rely= 0.3,anchor = "center") #donde se veera el mensaje

def inciar_sesion():
    id_ingresado = caja_id.get() #pide lo que se ingreso en la caja de id
    conexion = sqlite3.connect("BancoDeSangre.db") #conectamos a la base de datos para verificar que el id exista en personal
    cursor = conexion.cursor() # hacer consultas a la base de datos
    cursor.execute("SELECT * FROM PERSONAL WHERE ID_EMPLEADO = ?", (id_ingresado,)) #consulta por una tupla por eso una , dsp de id_ingresado
    resultado = cursor.fetchone() #devuelve el resultado de la busqueda en la base de datos
    if resultado is not None:
        cursor.execute("SELECT NOMBRE, ROL  FROM PERSONAL WHERE ID_EMPLEADO = ?", (id_ingresado,)) #busca el nombre y rol asociado al id que fue ingresado
        resultado = cursor.fetchone()
        nombre = resultado[0] #entrega una lista en el orden escrito por lo tanto nombre sera lo primero dsp el rol
        rol = resultado[1]
    conexion.close() #cerramos la conexión a la base de datos

    if resultado is not None: # si encontro el id, cierra la pagina de iniciar seisón y pasa a la pantalla principal
        frame_login.place_forget()
        mostrar_principal(pantalla, nombre, rol)
        mensaje.configure(text="Bienvenido, Personal Autorizado")
        
    else: #en caso que la base de datos no encuentre el id ingresado genera un mensaje de id invalido
        mensaje.configure(text="ID no encontrado. Intente nuevamente.")
        caja_id.delete(0, "end")

#Boton para que se genere la busqueda, si se aprieta el boton llama a la función de inciar sesión
boton = ctk.CTkButton(frame_login, text="Ingresar", command= inciar_sesion,fg_color="gray",hover_color="dimgray")
boton.place(relx=0.5, rely=0.5, anchor="center") #donde se ve el boton de ingresar en la pantalla


pantalla.mainloop() #mantiene la aplicación abierta 
