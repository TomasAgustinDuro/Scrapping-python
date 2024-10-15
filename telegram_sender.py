import requests

def enviar_mensaje_telegram(mensaje, chat_id, token):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": mensaje
    }
    
    response = requests.post(url, data=data)
    
    if response.status_code == 200:
        print("Mensaje enviado con éxito")
    else:
        print(f"Error al enviar mensaje: {response.status_code}")


