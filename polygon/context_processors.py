from datetime import datetime
import pytz
import MetaTrader5 as mt5
from src.indicators.market_helpers import identify_market_structure

from src.utils.mt5_utils import get_currency_tick
from src.trading.forex_pair import (
    majors,
    metals,
    cryptocurrencies,
    stocks,
    indices,
    commodities,
)


def global_market_context(request):
    # Получаем символ с установкой по умолчанию
    symbol = request.GET.get("symbol", request.COOKIES.get("selected_pair", "XAUUSD"))

    # Инициализация MetaTrader5
    if not mt5.initialize():
        return {"error": "MetaTrader5 не запущен."}

    tick = get_currency_tick(symbol)
    bid = tick.get("bid", "-")
    ask = tick.get("ask", "-")

    # Определение рыночной структуры
    current_structure = identify_market_structure(symbol, mt5.TIMEFRAME_M5)
    trend = (
        current_structure.get("trend", "Нет данных")
        if current_structure
        else "Нет данных"
    )

    # Времена
    server_time = datetime.now(pytz.utc)  # Время сервера (UTC)

    # Получаем время MT5
    mt5_time = (
        datetime.utcfromtimestamp(mt5.symbol_info_tick(symbol).time)
        if tick
        else server_time
    )

    # Конвертируем серверное время в разные часовые пояса
    timezone_mapping = {
        "central_asia": "Asia/Almaty",
        "central_europe": "Europe/Berlin",
        "central_usa": "America/New_York",
    }

    time_zones = {
        key: server_time.astimezone(pytz.timezone(tz))
        for key, tz in timezone_mapping.items()
    }

    # Определяем торговую сессию
    session = (
        "Азиатская"
        if server_time.hour < 8
        else "Европейская" if server_time.hour < 16 else "Американская"
    )

    return {
        "symbol": symbol,
        "bid": bid,
        "ask": ask,
        "trend": trend,
        "server_time": server_time.strftime("%Y-%m-%d %H:%M:%S"),
        "mt5_time": mt5_time.strftime("%H:%M:%S"),
        **{
            key: tz.strftime("%H:%M") for key, tz in time_zones.items()
        },  # Добавляем временные зоны в результат
        "session": session,
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def trading_symbols(request):
    symbol_from_cookie = request.COOKIES.get("selected_pair", "XAUUSD")

    # Получаем валютную пару из GET-запроса или используем значение из cookie
    symbol = request.GET.get("symbol", symbol_from_cookie)
    num_values = request.GET.get("num_values", "1")
    # Преобразуем в int, если нужно
    try:
        num_values_int = int(num_values)
    except ValueError:
        num_values_int = 1
    context = {
        "majors": majors,
        "metals": metals,
        "cryptocurrencies": cryptocurrencies,
        "stocks": stocks,
        "indices": indices,
        "commodities": commodities,
        "selected_pair": symbol,
        "num_values": num_values,  # Для отображения текущего выбора
    }

    all_symbols = majors + metals + cryptocurrencies + stocks + indices + commodities

    return {
        "majors": majors,
        "metals": metals,
        "cryptocurrencies": cryptocurrencies,
        "stocks": stocks,
        "indices": indices,
        "commodities": commodities,
        "all_symbols": all_symbols,
        "num_values": num_values,
    }
