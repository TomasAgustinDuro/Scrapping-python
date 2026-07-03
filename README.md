# 🎾 Padel Court Availability Notifier

Bot de automatización en Python que monitorea la disponibilidad de turnos de pádel en el sistema de reservas del Gobierno de la Ciudad de Buenos Aires (GCBA) y envía una alerta por email cuando se abre un horario deseado.

Desarrollado por [Tomás Duro](https://tommasdev.vercel.app) 🇦🇷

---

## ¿Qué hace este proyecto?

El sistema de reservas del GCBA (portal SIGECI) no envía notificaciones cuando un turno se libera. Este bot resuelve ese problema:

1. **Se autentica** automáticamente en `login.buenosaires.gob.ar`.
2. **Navega** al formulario de reserva de la prestación 5206 (cancha de pádel).
3. **Recorre el calendario** del mes actual y, si está disponible, del mes siguiente.
4. **Extrae los horarios** disponibles por día usando interacción JavaScript con el DOM.
5. **Filtra** únicamente los turnos en los horarios configurados.
6. **Envía un email** con los días y horarios encontrados + link directo para reservar.

El script se ejecuta **automáticamente cada 3 horas** vía GitHub Actions.

---

## 🗂 Estructura del proyecto

```
Scrapping-python/
├── scrapper_date.py        # Script principal: scraping, navegación y orquestación
├── email_sender.py         # Envío de alertas vía Gmail SMTP
├── telegram_sender.py      # Módulo auxiliar para Telegram (sin uso activo)
├── requirements.txt        # Dependencias del proyecto
├── .env                    # Variables de entorno locales (NO commitear)
└── .github/
    └── workflows/
        └── main.yml        # GitHub Actions: cron cada 3 horas + dispatch manual
```

---

## 🛠️ Tech Stack

| Tecnología | Uso |
|---|---|
| Python 3.11 | Lenguaje principal |
| Selenium 4.25 | Automatización del navegador Chrome |
| Selenium Manager | Gestión automática de ChromeDriver (sin dependencias externas) |
| python-dotenv | Carga de variables de entorno desde `.env` |
| smtplib / email | Envío de alertas por Gmail SMTP |
| GitHub Actions | Ejecución programada en la nube (cron cada 3 horas) |

---

## ⚙️ Cómo correrlo localmente

### 1. Prerrequisitos

- Python 3.11+
- Google Chrome instalado (Selenium Manager descarga ChromeDriver automáticamente)
- Cuenta de Gmail con **App Password** habilitada

### 2. Clonar e instalar

```bash
git clone https://github.com/TomasAgustinDuro/Scrapping-python.git
cd Scrapping-python
pip install python-dotenv selenium requests python-dateutil pytz tzdata
```

### 3. Crear el archivo `.env`

```env
# Credenciales del portal buenosaires.gob.ar
MY_USERNAME=tu_email@gmail.com
MY_PASSWORD=tu_contraseña_del_portal

# App Password de Gmail (para enviar alertas)
SECRET_PASSWORD=tu_app_password_de_gmail

# Email adicional que recibirá las alertas
ANOTHER_EMAIL=otro_email@gmail.com
```

> ⚠️ Nunca commitees el archivo `.env`. Ya está incluido en `.gitignore`.

### 4. Configurar horarios de interés

En `scrapper_date.py`, modificá esta línea:

```python
selected_hours = ["15:00 hs", "19:00 hs"]
```

### 5. Ejecutar

```bash
python scrapper_date.py
```

En local se abre Chrome con ventana visible. Para correr headless localmente, definí la variable `HEADLESS=1` en tu `.env`.

---

## ☁️ GitHub Actions

El workflow `.github/workflows/main.yml` ejecuta el script cada 3 horas en modo headless sobre `ubuntu-latest`.

### Secrets requeridos

Los secrets deben estar en el **environment "scrapping"** del repositorio (`Settings > Environments > scrapping > Environment secrets`):

| Secret | Descripción |
|---|---|
| `MY_USERNAME` | Email del portal GCBA y remitente de alertas |
| `MY_PASSWORD` | Contraseña del portal GCBA |
| `SECRET_PASSWORD` | App Password de Gmail (16 caracteres) |
| `ANOTHER_EMAIL` | Segundo destinatario de alertas |
| `TOKEN` | Token del bot de Telegram (reservado) |
| `CHAT_ID` | Chat ID de Telegram (reservado) |

También podés disparar el workflow manualmente desde la pestaña **Actions > Run workflow**.

---

## 🔐 Cómo obtener un App Password de Gmail

1. Activá la [verificación en dos pasos](https://myaccount.google.com/security).
2. Ingresá a [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords).
3. Creá una contraseña para "Otra (nombre personalizado)".
4. Copiá los 16 caracteres y usalos como `SECRET_PASSWORD`.

---

## 📬 Módulos

### `scrapper_date.py`

Clase `Browser` que encapsula la interacción con Selenium:

| Método | Descripción |
|---|---|
| `open_page(url)` | Navega a una URL |
| `login(username, password)` | Completa el formulario de login GCBA |
| `extract_calendar_turns(by, value)` | Recorre el calendario y extrae turnos (click vía JS) |
| `change_month()` | Avanza al mes siguiente en el calendario |
| `filter_turns(hours)` | Filtra turnos por horarios de interés |

Función `run()` orquesta el flujo completo: login → navegación → extracción → filtrado → email.

### `email_sender.py`

Envía alertas por Gmail SMTP con STARTTLS. Requiere `MY_USERNAME`, `SECRET_PASSWORD` y `ANOTHER_EMAIL` como variables de entorno.

### `telegram_sender.py`

Módulo auxiliar para enviar mensajes a un bot de Telegram. No se usa activamente en el flujo principal.

---

## 🤝 Cómo contribuir

1. Fork del repositorio.
2. Creá una rama: `git checkout -b feature/mi-mejora`.
3. Commiteá con mensaje descriptivo.
4. Abrí un Pull Request.

---

## 🙋‍♂️ Autor

**Tomás Duro** — [tommasdev.vercel.app](https://tommasdev.vercel.app)  
Buenos Aires, Argentina 🇦🇷
