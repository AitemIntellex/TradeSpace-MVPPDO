import requests
from bs4 import BeautifulSoup
from datetime import datetime


def get_investing_calendar():
    """Парсинг экономического календаря с сайта Investing.com."""
    url = "https://ru.investing.com/economic-calendar/"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
    }
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        raise Exception(
            f"Ошибка получения данных с Investing.com: {response.status_code}"
        )

    soup = BeautifulSoup(response.content, "html.parser")
    events = []
    today = datetime.now().date()

    # Найдем блоки с событиями
    rows = soup.select("tr.js-event-item")
    for row in rows:
        event_time = row.select_one(".time").get_text(strip=True)
        event_name = row.select_one(".event").get_text(strip=True)
        country = row.select_one(".flagCur").get_text(strip=True)
        fact_value = row.select_one(".act").get_text(strip=True) or "N/A"
        previous_value = row.select_one(".prev").get_text(strip=True) or "N/A"
        expected_value = row.select_one(".fore").get_text(strip=True) or "N/A"

        # Преобразуем время события в нужный формат
        try:
            event_datetime = datetime.strptime(event_time, "%H:%M").replace(
                year=today.year, month=today.month, day=today.day
            )
        except ValueError:
            continue  # Пропускаем события с неверным временем

        # Фильтрация по уровню влияния (2 звезды и больше)
        stars = len(row.select(".sentiment i.grayFullBullishIcon"))
        if stars >= 2 and event_datetime.date() == today:
            events.append(
                {
                    "time": event_time,
                    "name": event_name,
                    "impact": stars,
                    "country": country,
                    "fact": fact_value,
                    "previous": previous_value,
                    "expected": expected_value,
                }
            )

    return events
