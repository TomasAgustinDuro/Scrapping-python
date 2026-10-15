"""
Módulo auxiliar para envío de mensajes a través de la API de Telegram.

Actualmente no está integrado en el flujo principal del scraper,
pero está disponible para reemplazar o complementar el canal de email.

Para activarlo se necesita:
    - Un bot creado via @BotFather (obtiene el TOKEN).
    - El CHAT_ID del usuario o grupo destinatario.
"""

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Reintentos con backoff exponencial para fallas transitorias (429/5xx).
# backoff_factor=1 da esperas de ~1s, 2s, 4s entre intentos. Si Telegram
# responde 429 con header Retry-After, urllib3 respeta ese valor en vez
# del backoff calculado.
_RETRY_STRATEGY = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["POST"],
    respect_retry_after_header=True,
)


def _build_session() -> requests.Session:
    """Crea una Session de requests con reintentos configurados.

    Returns:
        Session con un HTTPAdapter que reintenta automáticamente ante
        fallas transitorias (429/5xx), usando backoff exponencial.
    """
    session = requests.Session()
    adapter = HTTPAdapter(max_retries=_RETRY_STRATEGY)
    session.mount("https://", adapter)
    return session


def enviar_mensaje_telegram(mensaje: str, chat_id: str, token: str) -> None:
    """Envía un mensaje de texto a un chat de Telegram usando la Bot API.

    Realiza una petición POST al endpoint sendMessage de la API de Telegram,
    reintentando automáticamente hasta 3 veces ante fallas transitorias
    (429 rate limit, 5xx errores de servidor) antes de darse por vencido.
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

    session = _build_session()

    try:
        response = session.post(url, data=payload, timeout=10)
    except requests.RequestException as request_error:
        print(f"Error de red al enviar mensaje a Telegram: {request_error}")
        return
    finally:
        session.close()

    if response.status_code == 200:
        print("Mensaje enviado con éxito")
    else:
        print(f"Error al enviar mensaje: {response.status_code}")
