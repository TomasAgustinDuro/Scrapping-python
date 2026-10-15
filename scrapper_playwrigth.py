import os
import sys
from datetime import datetime
from typing import TypedDict

from dotenv import load_dotenv
from playwright.sync_api import (
    Error as PlaywrightError,
)
from playwright.sync_api import (
    Playwright,
    sync_playwright,
)
from playwright.sync_api import (
    TimeoutError as PlaywrightTimeoutError,
)

load_dotenv()

url_login = "https://login.buenosaires.gob.ar/"
url_reserva = (
    "https://formulario-sigeci.buenosaires.gob.ar/InicioTramiteComun?idPrestacion=5206"
)

my_username = os.getenv("MY_USERNAME")
my_password = os.getenv("MY_PASSWORD")


class Turnos(TypedDict):
    """Estructura de datos que representa un turno disponible en el calendario.

    Attributes:
        dia: Fecha del turno en formato ISO 8601 (YYYY-MM-DD).
        horarios: Texto plano con los horarios disponibles para ese día,
                  tal como los devuelve el elemento #hoursBody del portal.
    """

    dia: str
    horarios: str


class Browser:
    turnos: list[Turnos]

    # TO DO: context para ahorrar login.

    def __init__(self, playwright: Playwright):
        self.browser = playwright.chromium.launch(headless=False)
        self.page = self.browser.new_page()

    def open_login_page(self, url: str):
        self.page.goto(url)
        self.page.locator("#email").fill(my_username)
        self.page.locator("#password-text-field").fill(my_password)
        self.page.locator("#login").click()

    def open_reserve_page(self, url: str):
        self.page.goto(url)

        self.page.locator('[data-start="fecha"]').click()

    def extract_calendar_turns(self):
        self.page.locator("#calendar").wait_for(state="visible", timeout=4000)
        day_elements = self.page.locator("#calendar div > div > h4").all()
        save_button = self.page.locator("div.container-button  #save ")

        obtained_turns = []

        for day_element in day_elements:
            try:
                dia = day_element.get_attribute("data-date")
                if not dia:
                    continue
                day_element.click()

                try:
                    save_button.wait_for(state="visible", timeout=3000)
                    save_button.click()

                    hours_element = self.page.locator("#hoursBody")

                    turno: Turnos = {"dia": dia, "horarios": hours_element.inner_text()}

                    obtained_turns.append(turno)

                    self.page.locator("#edit").click()
                except PlaywrightTimeoutError:
                    continue

            except PlaywrightError as error:
                print(error)

        return obtained_turns

    def filter_turns(self, hours: list[str], turns: list[Turnos]) -> list[Turnos]:
        """Filtra los turnos acumulados para conservar solo los que contienen las horas deseadas.

        Args:
            hours: Lista de strings con los horarios de interés (ej: ["19:00 hs"]).

        Returns:
            Lista de Turnos que contienen al menos uno de los horarios solicitados.
        """

        def has_requested_hour(turn: Turnos) -> bool:
            """Verifica si alguna de las horas solicitadas está en el turno."""
            return any(hour in turn["horarios"] for hour in hours)

        return list(filter(has_requested_hour, turns))

    def close_browser(self):
        self.browser.close()


def return_filter_turns(filtered_turns, selected_hours: list[str]):
    turnos_per_hour: dict[str, list[str]] = {hour: [] for hour in selected_hours}

    for turn in filtered_turns:
        formatted_day = datetime.strptime(turn["dia"], "%Y-%m-%d").strftime("%d/%m")

        for hour in selected_hours:
            if hour in turn["horarios"]:
                turnos_per_hour[hour].append(formatted_day)

    return turnos_per_hour


def create_message(turnos_per_hour: dict[str, list[str]]):
    return [
        f"Turnos disponibles a las {hour}: {', '.join(dias)}"
        for hour, dias in turnos_per_hour.items()
        if dias
    ]


def run():
    selected_hours = ["12:00"]
    browser = None

    with sync_playwright() as p:
        try:
            print("Comenzamos..")

            browser = Browser(playwright=p)

            browser.open_login_page(url_login)

            browser.open_reserve_page(url_reserva)

            turnos = browser.extract_calendar_turns()

            turnos_filtrados = browser.filter_turns(selected_hours, turnos)

            turnos_agrupados = return_filter_turns(turnos_filtrados, selected_hours)

            mensaje = create_message(turnos_agrupados)

            if mensaje:
                print(mensaje)
            else:
                print("No hubo turnos encontrados")

            print("Finalizado")
        except (PlaywrightError, PlaywrightTimeoutError) as error:
            print(f"❌ El script falló: {error!s}", file=sys.stderr)
        finally:
            if browser is not None:
                browser.close_browser()


if __name__ == "__main__":
    run()
