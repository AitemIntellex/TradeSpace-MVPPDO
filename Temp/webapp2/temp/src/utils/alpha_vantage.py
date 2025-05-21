# src/utils/alpha_vantage.py

import requests

ALPHA_VANTAGE_API_KEY = "S5H9R9PTN5Z8IX2P"

def get_currency_quote(from_currency, to_currency):
    """
    Получить текущие котировки валютных пар.
    :param from_currency: Валюта, которую конвертируем (например, 'USD')
    :param to_currency: Целевая валюта (например, 'EUR')
    :return: Котировка валютной пары
    """
    url = f"https://www.alphavantage.co/query?function=CURRENCY_EXCHANGE_RATE&from_currency={from_currency}&to_currency={to_currency}&apikey={ALPHA_VANTAGE_API_KEY}"

    response = requests.get(url)
    data = response.json()

    if "Error Message" in data:
        raise Exception(f"Error fetching data for {from_currency}/{to_currency}: {data['Error Message']}")

    return data["Realtime Currency Exchange Rate"]
