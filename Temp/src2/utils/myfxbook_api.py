# src/utils/myfxbook_api.py

import requests

MYFXBOOK_LOGIN_URL = "https://www.myfxbook.com/api/login.json"
MYFXBOOK_ECONOMIC_CALENDAR_URL = "https://www.myfxbook.com/api/get-calendar.json"

def myfxbook_login(username, password):
    """Аутентификация в Myfxbook и получение ключа сессии."""
    payload = {
        'email': "blockanza@gmail.com",
        'password': "Aka4465611/2"
    }
    print("Отправляем запрос на вход в Myfxbook...")
    response = requests.get(MYFXBOOK_LOGIN_URL, params=payload)
    data = response.json()

    print(f"Ответ Myfxbook: {data}")  # Отладка, чтобы увидеть ответ

    response = requests.get(MYFXBOOK_LOGIN_URL, params=payload)
    data = response.json()

    if response.status_code != 200 or data['error']:
        raise Exception(f"Ошибка входа в Myfxbook: {data.get('message', 'Unknown error')}")

    return data['session']  # Возвращаем ключ сессии
def get_economic_calendar(session_key):
    """Получение данных экономического календаря с Myfxbook."""
    url = f"{MYFXBOOK_ECONOMIC_CALENDAR_URL}?session={session_key}"

    response = requests.get(url)
    data = response.json()

    if response.status_code != 200 or data['error']:
        raise Exception(f"Ошибка получения экономического календаря: {data.get('message', 'Unknown error')}")

    return data['calendar']  # Возвращаем данные календаря
