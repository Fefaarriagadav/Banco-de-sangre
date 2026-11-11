import customtkinter as ctk #bibliteca de interfaz grafica
from pantallas.agregar_donante import mostrar_registro
from pantallas.evaluar_donante import mostrar_evaluacion
from pantallas.lista_donaciones import mostrar_lista_donaciones
from pantallas.pedir_donaciones import mostrar_pedir_donaciones
from pantallas.agregar_donacion import mostrar_adonacion


def mostrar_principal(pantalla, nombre, rol, empleado_id, volver_login): #ventana principal una vez ya se haya ingresado sesión
    #se divide en frames para hacer mas facil el trabajo de cambio de pantallas y los clicks 
    frame_principal = ctk.CTkFrame(pantalla) #una nueva ventana en la pantalla
    frame_principal.place(relx=0,rely=0,relheight=1, relwidth=1) #donde se veera en la pantalla principal

    frame_contenido = ctk.CTkFrame(frame_principal, fg_color="transparent") #frame ocntenido, es generica ya que la puedo ocupar para un formulario de donantes como una nueva donación
    frame_contenido.place(relx=0 ,rely=0.08 ,relwidth= 1, relheight= 0.92)


    menu_lateral = ctk.CTkFrame(frame_principal, width=250, corner_radius=0, fg_color="#E0E0E0")
    #el menu lateral se crea aparte ya que puede estar en todos los frames
    def alternar_menu():
        if menu_lateral.winfo_manager() == "place": #winfo_maneger trae el resultado de si esta desplegado o no
            menu_lateral.place_forget() #si esta desplegado le dice que se cierre
            
        else: #en caso de estar cerrado, le indica en que parte de la pantalla tiene que posicionarse y con .lift lo despliega
            menu_lateral.place(x=0, y=75, relheight=0.85)
            menu_lateral.lift()

    #se crea el boton del menu, con todos sus atributos, cada vez que se apriete se trabaj la funcione de ver si esta desplegado o no
    boton_menu = ctk.CTkButton(frame_principal,text="☰", width=50, height=45, font=("Arial",28), fg_color="transparent", text_color="#333333", hover_color="#DDDDDD", command=alternar_menu)
    boton_menu.place(x=20, y=20) # donde se posiciona el boton de menu

    if rol == "Entrevistador": # solo el perosnal que tenga el rol asigando de entrevistador tiene el boton de agregar donante, y cuando se aprieta llama a la función mostrar_registro que esta en otro archivo por eso se importa
        boton_donante = ctk.CTkButton(menu_lateral, text="Agregar nuevo donante", width=210, height=45, text_color="#000000", fg_color="#C0F1FF", command=lambda: mostrar_registro(frame_contenido,rol))
        boton_donante.place(x=20, y=40)
        ctk.CTkButton(menu_lateral, text="Actualizar habilitación", width=210, height=45, command=lambda: mostrar_evaluacion(frame_contenido, empleado_id)).place(x=20, y=100)

    boton_pedir_donaciones = ctk.CTkButton(menu_lateral, text="Pedir donaciones", width=210, height=45, text_color="#000000", fg_color="#0D9488", command=lambda: mostrar_pedir_donaciones(frame_contenido))
    boton_pedir_donaciones.place(x=20, y=160)

    if rol == "Entrevistador": # solo el personal que tenga el rol asigando de entrevistador tiene el boton de agregar donacion, y cuando se aprieta llama a la función mostrar_adonacion que esta en otro archivo por eso se importa
            boton_donancion = ctk.CTkButton(menu_lateral, text="Agregar nueva donación", width=210, height=45, text_color="#000000", fg_color="#C0F1FF", command=lambda: mostrar_adonacion(frame_contenido,rol))
            boton_donancion.place(x=20, y=280)

    boton_lista_donaciones = ctk.CTkButton(menu_lateral, text="Lista de donaciones", width=210, height=45, text_color="#000000", fg_color="#0D9488", command=lambda: mostrar_lista_donaciones(frame_contenido))
    boton_lista_donaciones.place(x=20, y=330)

    def cerrar_sesion():
        frame_principal.destroy()
        volver_login()

    boton_cerrar_sesion = ctk.CTkButton(menu_lateral, text="Cerrar sesión", width=210, height=45, text_color="#FFFFFF", fg_color="#FF0000", command=cerrar_sesion)
    boton_cerrar_sesion.place(x=20, y=655)

    #la tarjeta de bienvenida se crea en el frame de contenido, se crea un recuadro donde trabajar esta tarjeta
    #se crea el titulo y donde se posiciona y lo mismo con el rol, el nombre y el rol se exraen de la base de datos
    tarjeta_bienvenida = ctk.CTkFrame(frame_contenido,width=600, height=250, corner_radius=20,fg_color= "#FFFFFF")
    tarjeta_bienvenida.place(relx=0.5, rely=0.25, anchor = "center")
    titulo = ctk.CTkLabel(tarjeta_bienvenida, text="Banco de Sangre", font=("Arial", 30, "bold"), text_color="#000000")
    titulo_nombre = ctk.CTkLabel(tarjeta_bienvenida, text=f"¡Bienvenid@, {nombre}!", font=("Arial", 30, "bold"), text_color="#000000")
    titulo_rol = ctk.CTkLabel(tarjeta_bienvenida, text=f"Rol : {rol}", font=("Arial", 30, "bold"), text_color="#000000")
    titulo.place(relx=0.5,rely=0.2, anchor = "center")
    titulo_nombre.place(relx=0.5, rely=0.5, anchor ="center")
    titulo_rol.place(relx=0.5, rely=0.8, anchor="center")

    boton_menu.lift()