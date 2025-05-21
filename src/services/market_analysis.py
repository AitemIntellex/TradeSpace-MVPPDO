from src.trading.ict_strategy import ict_strategy
from src.trading.smc_strategy import smc_strategy
from src.trading.snr_strategy import snr_strategy

from src.indicators.market_helpers import identify_liquidity_zones
from src.indicators.market_structure import identify_market_structure
from src.indicators.technical_indicators import (
    calculate_fibonacci_levels,
    get_indicators_data,
    identify_fvg,
)

from src.utils.mt5_utils import get_ohlc_extended
from src.trading.forex_pair import (
    majors,
    metals,
    cryptocurrencies,
    stocks,
    indices,
    commodities,
)
import json
import MetaTrader5 as mt5

# Таймфреймы, с которыми мы работаем
TIMEFRAME_MAPPING = {
    "1m": mt5.TIMEFRAME_M1,
    "5m": mt5.TIMEFRAME_M5,
    "15m": mt5.TIMEFRAME_M15,
    "1h": mt5.TIMEFRAME_H1,
    "4h": mt5.TIMEFRAME_H4,
    "1d": mt5.TIMEFRAME_D1,
}


def format_dataframe(df):
    """Превращает DataFrame в JSON-список"""
    return df.round(5).to_dict(orient="records")  # Округляем и в JSON


def format_dict(data):
    """Округляет все числа в словаре"""
    if isinstance(data, dict):
        return {
            k: round(v, 5) if isinstance(v, (int, float)) else v
            for k, v in data.items()
        }
    return data


# Собираем все доступные символы
AVAILABLE_SYMBOLS = set(
    majors + metals + cryptocurrencies + stocks + indices + commodities
)


def get_market_analysis(symbol, timeframes="all", num_values=100):
    """Главная функция анализа рынка для всех таймфреймов"""

    # Проверяем, доступен ли символ
    if symbol not in AVAILABLE_SYMBOLS:
        return {"error": f"Символ {symbol} не найден в списке доступных!"}

    if timeframes == "all":
        timeframes = list(TIMEFRAME_MAPPING.keys())

    results = {}

    for tf in timeframes:
        # 🛠 Преобразуем таймфрейм в MT5-формат
        mt5_timeframe = TIMEFRAME_MAPPING.get(tf.lower(), mt5.TIMEFRAME_M15)

        # 🛠 Теперь передаём `int`, а не строку!
        df = get_ohlc_extended(symbol, mt5_timeframe, num_values)

        if df is None or df.empty:
            results[tf] = {"error": f"Нет данных для {tf}"}
            continue

        # Форматируем OHLC
        ohlc_data = format_dataframe(df)

        # Определяем структуру рынка
        market_structure = format_dict(identify_market_structure(symbol, tf))

        # Получаем уровни ликвидности
        liquidity_zones = format_dict(identify_liquidity_zones(symbol, tf))

        # Определяем зоны FVG
        fvg_zones = identify_fvg(df)

        # Вычисляем уровни Фибоначчи
        fib_levels = format_dict(calculate_fibonacci_levels(symbol, tf))

        # Берём основные индикаторы
        indicators = format_dict(get_indicators_data(symbol, tf, num_values))

        # Запускаем стратегии
        ict_result = format_dict(ict_strategy(symbol, tf))
        smc_result = format_dict(smc_strategy(symbol, tf))
        snr_result = format_dict(snr_strategy(symbol, tf))

        # Добавляем данные для текущего ТФ
        results[tf] = {
            "ohlc": ohlc_data,
            "market_structure": market_structure,
            "liquidity_zones": liquidity_zones,
            "fvg_zones": fvg_zones,
            "fibonacci": fib_levels,
            "indicators": indicators,
            "strategies": {
                "ICT": ict_result,
                "SMC": smc_result,
                "SNR": snr_result,
            },
        }

    return json.dumps(results, indent=4, ensure_ascii=False)
