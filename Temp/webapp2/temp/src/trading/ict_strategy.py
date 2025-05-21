import MetaTrader5 as mt5
import logging
from src.trading.trading import (
    get_rates_dataframe,
    calculate_macd,
    calculate_atr,
    calculate_rsi,  # Добавляем RSI
    calculate_bollinger_bands,  # Добавляем полосы Боллинджера
    calculate_stochastic,  # Добавляем Стохастик
    identify_liquidity_zones,
)


def ict_strategy(symbol, timeframe):
    """
    Улучшенная стратегия ICT для анализа рынка с добавлением дополнительных индикаторов.
    Возвращает сигналы для открытия позиций с более детализированными условиями.
    """
    analysis_info = {}

    # Получаем рыночные данные
    df = get_rates_dataframe(symbol, timeframe, 100)
    if df is None:
        print(f"Ошибка: Не удалось получить данные для {symbol}")
        return {"error": "Нет данных"}

    # Функция для добавления результатов анализа к analysis_info
    def update_analysis(label, data, error_message="Ошибка расчета"):
        analysis_info[label] = data if all(data.values()) else error_message

    # Получаем текущую цену
    current_price = mt5.symbol_info_tick(symbol).ask
    analysis_info["current_price"] = current_price

    # Анализируем индикаторы
    indicators = {
        "macd": calculate_macd(symbol, timeframe),
        "liquidity": identify_liquidity_zones(symbol, timeframe),
        "atr": (calculate_atr(symbol, timeframe),),
        "rsi": (calculate_rsi(symbol, timeframe),),
        "bollinger_bands": calculate_bollinger_bands(symbol, timeframe),
        "stochastic": calculate_stochastic(symbol, timeframe),
    }

    # Обновляем результаты анализа
    update_analysis(
        "macd", {"value": indicators["macd"][0], "signal": indicators["macd"][1]}
    )
    update_analysis(
        "liquidity",
        {
            "support": indicators["liquidity"][0],
            "resistance": indicators["liquidity"][1],
        },
    )
    update_analysis("atr", {"value": indicators["atr"][0]})
    update_analysis("rsi", {"value": indicators["rsi"][0]})
    update_analysis(
        "bollinger_bands",
        {
            "sma": indicators["bollinger_bands"][0],
            "upper_band": indicators["bollinger_bands"][1],
            "lower_band": indicators["bollinger_bands"][2],
        },
    )
    update_analysis(
        "stochastic",
        {"k": indicators["stochastic"][0], "d": indicators["stochastic"][1]},
    )

    # Логика стратегии с добавлением индикаторов
    macd_value, signal_value = indicators["macd"]
    support, resistance = indicators["liquidity"]
    atr_value = indicators["atr"][0]
    rsi_value = indicators["rsi"][0]

    if (
        current_price > resistance
        and macd_value > signal_value
        and atr_value > 0.001
        and rsi_value < 70
    ):
        signal = "buy"
        analysis_info["decision"] = (
            "Открываем BUY: цена выше сопротивления, MACD выше сигнальной линии, ATR высокий, RSI ниже 70."
        )
    elif (
        current_price < support
        and macd_value < signal_value
        and atr_value > 0.001
        and rsi_value > 30
    ):
        signal = "sell"
        analysis_info["decision"] = (
            "Открываем SELL: цена ниже поддержки, MACD ниже сигнальной линии, ATR высокий, RSI выше 30."
        )
    else:
        signal = "no_signal"
        analysis_info["decision"] = "Нет сигнала для открытия позиции."

    # Возвращаем анализ и решение стратегии
    analysis_info["signal"] = signal
    return analysis_info
