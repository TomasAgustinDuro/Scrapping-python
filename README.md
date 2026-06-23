# 🎾 Padel Court Availability Notifier

A Python automation bot that monitors available padel court reservations on a Buenos Aires government booking system and sends an **email alert** the moment your preferred time slot opens up.

Built and maintained by [Tomás Duro](https://tommasdev.vercel.app) 🇦🇷

---

## ¿Qué hace este proyecto?

El sistema de reservas de canchas de pádel del GCBA (a través del portal SIGECI) no envía notificaciones cuando un turno se libera. Este bot resuelve ese problema:

1. **Se autentica** automáticamente en el portal `login.buenosaires.gob.ar` con tus credenciales.
2. **Navega** al formulario de reserva de la prestación `5206` (cancha de pádel).
3. **Recorre el calendario** disponible y, por cada día, registra los horarios disponibles.
4. **Filtra** únicamente los turnos que te interesan (las horas que configuraste).
5. **Envía un email** con los días y horarios encontrados, incluyendo el link directo para reservar.

El script se ejecuta de forma **completamente automatizada** cada 3 horas mediante GitHub Actions, sin necesidad de tener nada corriendo en tu máquina.

---

## 🗂 Estructura del proyecto

```
Scrapping-python/
├── scrapper_date.py        # Script principal: lógica de scraping y orquestación
├── email_sender.py         # Módulo de envío de email vía Gmail SMTP
├── telegram_sender.py      # Módulo auxiliar para envíos por Telegram (sin uso activo)
├── requirements.txt        # Dependencias del proyecto
├── .env                    # Variables de entorno locales (NO commitear)
├── .github/
│   └── workflows/
│       └── main.yml        # Pipeline de GitHub Actions (cron cada 3 horas)
└── workflows/
    └── run-script.yml      # Workflow alternativo (uso local / debug)
```

---

## 🛠️ Tech Stack

| Tecnología | Uso |
|---|---|
| Python 3.11 | Lenguaje principal |
| Selenium | Automatización del navegador (headless Chrome) |
| webdriver-manager | Gestión automática del ChromeDriver |
| python-dotenv | Carga de variables de entorno desde `.env` |
| smtplib / email | Envío de alertas por Gmail |
| GitHub Actions | Ejecución programada en la nube (cron) |

---

## ⚙️ Cómo correrlo localmente

### 1. Prerrequisitos

- Python 3.11+
- Google Chrome instalado
- Una cuenta de Gmail con **App Password** habilitada (ver sección de configuración)

### 2. Clonar el repositorio

```bash
git clone https://github.com/TomasAgustinDuro/Scrapping-python.git
cd Scrapping-python
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Crear el archivo `.env`

Crear un archivo `.env` en la raíz del proyecto con las siguientes variables:

```env
# Credenciales del portal buenosaires.gob.ar
MY_USERNAME=tu_email@gmail.com
MY_PASSWORD=tu_contraseña_del_portal

# Contraseña de aplicación de Gmail (para enviar el email de alerta)
SECRET_PASSWORD=tu_app_password_de_gmail

# Email adicional que recibirá las alertas (puede ser el mismo que MY_USERNAME)
ANOTHER_EMAIL=otro_email@gmail.com
```

> ⚠️ **Importante**: nunca commitees el archivo `.env`. Ya está incluido en el `.gitignore`.

### 5. Configurar las horas de interés

En `scrapper_date.py`, buscá y modificá esta línea para definir qué horarios te interesan:

```python
selected_hours = ["15:00 hs", "19:00 hs"]
```

### 6. Ejecutar

```bash
python scrapper_date.py
```

---

## ☁️ Ejecución automatizada con GitHub Actions

El archivo `.github/workflows/main.yml` ejecuta el script **cada 3 horas** (cron `0 */3 * * *`) sobre un runner `ubuntu-latest`.

Para que funcione en tu fork, debés cargar los siguientes **secrets** en la configuración del repositorio (`Settings > Secrets and variables > Actions`):

| Secret | Descripción |
|---|---|
| `MY_USERNAME` | Tu email del portal GCBA |
| `MY_PASSWORD` | Tu contraseña del portal GCBA |
| `TOKEN` | Token del bot de Telegram (reservado para uso futuro) |
| `CHAT_ID` | Chat ID de Telegram (reservado para uso futuro) |

> Los secrets `SECRET_PASSWORD` y `ANOTHER_EMAIL` también deben agregarse si querés recibir los emails desde el runner de GitHub Actions.

También podés disparar el workflow manualmente desde la pestaña **Actions** del repositorio usando el trigger `workflow_dispatch`.

---

## 🔐 Cómo obtener un App Password de Gmail

Para que el script pueda enviar emails desde tu cuenta de Gmail sin usar tu contraseña real:

1. Activá la [verificación en dos pasos](https://myaccount.google.com/security) en tu cuenta Google.
2. Ingresá a [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords).
3. Seleccioná **"Otra (nombre personalizado)"** y creá la contraseña.
4. Copiá los 16 caracteres generados y usalos como `SECRET_PASSWORD`.

---

## 📬 Módulos

### `scrapper_date.py`
Contiene la clase `Browser` que encapsula toda la interacción con Selenium:
- `open_page(url)` — abre una URL en el navegador headless.
- `login_linkedin(username, password)` — completa el formulario de login del portal GCBA.
- `get_info_test(by, value)` — recorre el calendario y extrae los turnos disponibles.
- `filter_turns(hours)` — filtra los turnos por la lista de horas de interés.

### `email_sender.py`
Envía un email vía Gmail SMTP con las credenciales de entorno. Utiliza `MIMEMultipart` para estructurar el mensaje.

### `telegram_sender.py`
Módulo auxiliar que permite enviar mensajes a un bot de Telegram. Actualmente no se usa en el flujo principal, pero está disponible para integrarse.

---

## 🤝 Cómo contribuir

1. Hacé un fork del repositorio.
2. Creá una rama para tu feature: `git checkout -b feature/mi-mejora`.
3. Commiteá tus cambios con un mensaje descriptivo.
4. Abrí un Pull Request explicando qué cambiaste y por qué.

---

## 🙋‍♂️ Autor

Desarrollado por **Tomás Duro** — [tommasdev.vercel.app](https://tommasdev.vercel.app)  
Buenos Aires, Argentina 🇦🇷
