"""
Módulo auxiliar para envío de mensajes a través de la API de Telegram.

Actualmente no está integrado en el flujo principal del scraper,
pero está disponible para reemplazar o complementar el canal de email.

Para activarlo se necesita:
    - Un bot creado via @BotFather (obtiene el TOKEN).
    - El CHAT_ID del usuario o grupo destinatario.
"""

import requests


def enviar_mensaje_telegram(mensaje: str, chat_id: str, token: str) -> None:
    """Envía un mensaje de texto a un chat de Telegram usando la Bot API.

    Realiza una petición POST al endpoint sendMessage de la API de Telegram.
    Imprime el resultado de la operación (éxito o código de error HTTP).

    Args:
        mensaje: Texto del mensaje a enviar.
        chat_id: Identificador del chat o usuario destinatario.
                 Se obtiene hablándole al bot o usando @userinfobot.
        token: Token de autenticación del bot generado por @BotFather.

    Example:
        enviar_mensaje_telegram(
            mensaje="Turno disponible a las 19:00 hs",
            chat_id="123456789",
            token="123456:ABC-DEF..."
        )
    """
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": mensaje,
    }

    response = requests.post(url, data=payload)

    if response.status_code == 200:
        print("Mensaje enviado con éxito")
    else:
        print(f"Error al enviar mensaje: {response.status_code}")
