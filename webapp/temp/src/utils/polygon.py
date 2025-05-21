# src/utils/polygon.py

import requests

POLYGON_API_KEY = "wZis37fCULeybCJx7QbyLbsynAzpWRwK"


def get_historical_data(
    from_currency, to_currency, timespan="day", limit=200, price_type="close"
):
    """
    Получить исторические данные для валютной пары через Polygon.io.
    :param from_currency: Валюта, которую конвертируем (например, 'USD')
    :param to_currency: Целевая валюта (например, 'EUR')
    :param timespan: Временной интервал (например, 'day', 'minute', 'hour')
    :param limit: Количество точек данных (например, 200 для SMA(200))
    :param price_type: Тип цены для возврата (например, 'close', 'high', 'low')
    :return: Список цен (например, цены закрытия)
    """
    url = f"https://api.polygon.io/v2/aggs/ticker/C:{from_currency}{to_currency}/range/1/{timespan}/2023-01-01/2024-01-01?adjusted=true&limit={limit}&apiKey={POLYGON_API_KEY}"

    response = requests.get(url)
    data = response.json()

    if response.status_code != 200 or "results" not in data:
        raise Exception(
            f"Error fetching data for {from_currency}/{to_currency}: {data.get('error', 'Unknown error')}"
        )

    # Определяем, какие цены использовать
    if price_type == "close":
        prices = [item["c"] for item in data["results"]]
    elif price_type == "high":
        prices = [item["h"] for item in data["results"]]
    elif price_type == "low":
        prices = [item["l"] for item in data["results"]]
    else:
        raise ValueError(f"Invalid price_type: {price_type}")

    return prices


def get_currency_quote(from_currency, to_currency):
    print("get_currency_quote вызвана")  # Тестовое сообщение
    # ... остальной код

    """
    Получить текущие котировки валютных пар через Polygon.io.
    :param from_currency: Валюта, которую конвертируем (например, 'USD')
    :param to_currency: Целевая валюта (например, 'EUR')
    :return: Котировка валютной пары
    """
    if not POLYGON_API_KEY:
        raise Exception("API Key not found")

    url = f"https://api.polygon.io/v2/aggs/ticker/C:{from_currency}{to_currency}/prev?apiKey={POLYGON_API_KEY}"

    response = requests.get(url)
    data = response.json()

    if response.status_code != 200 or "error" in data:
        raise Exception(
            f"Error fetching data for {from_currency}/{to_currency}: {data.get('error', 'Unknown error')}"
        )

    return data["results"][0]
    print(f"Загружен API ключ: {POLYGON_API_KEY}")
