import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz


def get_investing_calendar():
    """Парсинг экономического календаря с сайта Investing.com."""
    url = "https://ru.investing.com/economic-calendar/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
    }

    response = requests.get(url, headers=headers)
    response.raise_for_status()  # Automatically raise an exception for bad responses

    soup = BeautifulSoup(response.content, "html.parser")
    events = []
    today = datetime.now().date()

    # Часовые пояса
    server_timezone = pytz.timezone("Etc/GMT-3")  # Время сайта (GMT+3)
    local_timezone = pytz.timezone("Asia/Tashkent")  # Замените на ваш часовой пояс

    # Найдем блоки с событиями
    rows = soup.select("tr.js-event-item")

    for row in rows:
        # Извлекаем данные
        event_time = row.select_one(".time").get_text(strip=True)
        event_name = row.select_one(".event").get_text(strip=True)
        country = row.select_one(".flagCur").get_text(strip=True)
        fact_value = row.select_one(".act").get_text(strip=True) or "-"
        previous_value = row.select_one(".prev").get_text(strip=True) or "-"
        expected_value = row.select_one(".fore").get_text(strip=True) or "-"

        # Преобразуем время события
        try:
            event_datetime_server = datetime.strptime(event_time, "%H:%M").replace(
                year=today.year, month=today.month, day=today.day
            )
            event_datetime_server = server_timezone.localize(event_datetime_server)

            event_datetime_local = event_datetime_server.astimezone(local_timezone)
            if event_datetime_local.date() != today:
                continue  # Пропускаем события не из сегодняшнего дня

            event_time_local = event_datetime_local.strftime("%H:%M")
        except ValueError:
            continue  # Пропускаем события с неверным временем

        # Фильтрация по уровню влияния (2 звезды и больше)
        stars = len(row.select(".sentiment i.grayFullBullishIcon"))
        if stars >= 2:
            events.append(
                {
                    "time": event_time_local,
                    "name": event_name,
                    "impact": stars,
                    "country": country,
                    "fact": fact_value,
                    "previous": previous_value,
                    "expected": expected_value,
                }
            )

    return events
