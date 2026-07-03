"""
Módulo de envío de alertas por email vía Gmail SMTP.

Expone la función email_sender que se conecta al servidor SMTP de Gmail,
se autentica con un App Password y envía la notificación de turnos
disponibles a los destinatarios configurados por variable de entorno.

Variables de entorno requeridas:
    MY_USERNAME: Email del remitente (también se usa como primer destinatario).
    SECRET_PASSWORD: App Password de Gmail (16 caracteres, no la contraseña normal).
    ANOTHER_EMAIL: Email del segundo destinatario.
"""

import os
from smtplib import SMTP
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from dotenv import load_dotenv


def email_sender(body_message: str) -> None:
    """Envía un email de alerta con los turnos disponibles.

    Se conecta a smtp.gmail.com:587 con STARTTLS, se autentica con
    las credenciales de entorno y envía el mensaje a los destinatarios.

    Si las credenciales no están configuradas, imprime una advertencia.
    Si la conexión SMTP falla, imprime el error sin relanzar la excepción
    para no interrumpir el flujo del scraper.

    Args:
        body_message: Cuerpo del email en texto plano con los turnos
                      encontrados y el link de reserva.
    """
    load_dotenv()

    sender_email = os.getenv("MY_USERNAME")
    sender_password = os.getenv("SECRET_PASSWORD")
    second_recipient = os.getenv("ANOTHER_EMAIL")

    if not sender_email or not sender_password:
        print(
            "Error: MY_USERNAME o SECRET_PASSWORD no están configurados. "
            "No se puede enviar el email.",
            flush=True,
        )
        return

    recipients = [sender_email, second_recipient]

    try:
        server = SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, sender_password)

        message = MIMEMultipart()
        message["From"] = sender_email
        message["To"] = ", ".join(recipients)
        message["Subject"] = "Nuevo turno disponible para Padel"
        message.attach(MIMEText(body_message, "plain"))

        server.sendmail(sender_email, recipients, message.as_string())
        server.quit()
    except Exception as smtp_error:
        print(f"Error al enviar el email: {smtp_error}", flush=True)
