import smtplib #libreria que conecta con el servidor de correo
import os #accede a las credenciales desde .env
from email.message import EmailMessage #crea correo con destinatario, asunto y contenido
from dotenv import load_dotenv #carga las varuiables desde .env
from pathlib import Path


ruta_env = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(ruta_env)

correo = os.getenv("CORREO_REMITENTE")
contrasena = os.getenv("CONTRASENA_APP")

def enviar_correo(destinatario):
    # Crear el mensaje de correo
    mensaje = EmailMessage()
    mensaje["From"] = correo
    mensaje["To"] = destinatario
    mensaje["Subject"] = "Tu donación puede salvar vidas | Banco de Sangre"

    mensaje.set_content("Estimado/a donante:\n\n"
    "Esperamos que se encuentre muy bien.\n\n"
    "Nos comunicamos con usted desde el Banco de Sangre porque "
    "actualmente necesitamos reforzar nuestras reservas de sangre "
    "y su colaboración podría ser de gran ayuda.\n\n"
    "Cada donación representa una oportunidad de salvar vidas y "
    "brindar esperanza a pacientes que necesitan transfusiones "
    "o tratamientos médicos.\n\n"
    "¡Su solidaridad puede marcar la diferencia!\n\n"
    "Si se encuentra en condiciones de donar y desea colaborar, "
    "le invitamos a acercarse a nuestro banco de sangre o "
    "contactarnos para conocer los pasos necesarios para "
    "realizar una donación.\n\n"
    "Agradecemos sinceramente su tiempo, disposición y compromiso "
    "con el bienestar de nuestra comunidad.\n\n"
    "Atentamente,\n"
    "Equipo del Banco de Sangre")

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as servidor:
        servidor.login(correo, contrasena)
        servidor.send_message(mensaje)