import logging
import openai

from django.shortcuts import render, redirect
from src.utils.mt5_utils import get_currency_tick
from webapp.models import Recommendation  # Добавьте этот импорт


def analyze_with_ai(result, calendar_events, news_items):
    """
    Отправляет данные анализа в OpenAI для получения прогноза, используя chat-комплит endpoint.
    """
    # Формирование основного контента с техническими индикаторами
    content = (
        f"На основе предоставленных данных для валютной пары {result['symbol']}:\n"
    )
    current_price = result.get("current_price", "N/A")
    content += f"Текущая цена: {current_price}\n\n"

    # Добавляем индикаторы по всем таймфреймам
    indicators_summary = result.get("indicators_summary", {})
    for timeframe, indicators in indicators_summary.items():
        content += f"Таймфрейм {timeframe}:\n"
        content += f"- RSI: {indicators.get('rsi', 'N/A')}\n"
        content += f"- MACD: {indicators.get('macd', 'N/A')}, Signal: {indicators.get('signal', 'N/A')}\n"
        content += f"- Bollinger Bands: Верхняя: {indicators.get('upper_band', 'N/A')}, Нижняя: {indicators.get('lower_band', 'N/A')}\n"
        content += f"- ATR: {indicators.get('atr', 'N/A')}\n"
        stochastic = indicators.get("stochastic", {})
        if stochastic:
            content += f"- Стохастик K: {stochastic.get('K', 'N/A')}, D: {stochastic.get('D', 'N/A')}\n"
        content += f"- Уровни Фибоначчи: {indicators.get('fibonacci_levels', 'N/A')}\n"
        content += f"- Канал регрессии: {indicators.get('regression_channel', 'N/A')}\n"
        content += f"- VWAP: {indicators.get('vwap', 'N/A')}\n"
        content += f"- CCI: {indicators.get('cci', 'N/A')}\n"
        content += f"- MFI: {indicators.get('mfi', 'N/A')}\n\n"

    # Добавляем данные экономического календаря
    content += "Экономический календарь на сегодня:\n"
    if calendar_events:
        for event in calendar_events:
            content += (
                f"- {event['time']} ({event['country']}): {event['name']} "
                f"(Факт: {event['fact']}, Предыдущее: {event['previous']}, Прогноз: {event['expected']}, Влияние: {event['impact']} звезд)\n"
            )
    else:
        content += "Нет значимых событий на сегодня.\n"
    # Технические индикаторы
    for timeframe, indicators in result["indicators_summary"].items():
        content += f"\nТаймфрейм {timeframe}:\n"
        content += f"RSI: {indicators.get('rsi', 'N/A')}\n"
        content += f"MACD: {indicators.get('macd', 'N/A')}, Signal: {indicators.get('signal', 'N/A')}\n"
        # Дополнительно добавить другие индикаторы...

    # Стратегии
    strategies_summary = result.get("strategies_summary", {})
    for strategy, data_by_timeframe in strategies_summary.items():
        content += f"\nСтратегия {strategy}:\n"
        for timeframe, strategy_data in data_by_timeframe.items():
            content += f"Таймфрейм {timeframe}: {strategy_data}\n"

    # Добавляем новости из RSS-ленты
    content += "\nПоследние новости:\n"
    if news_items:
        for news in news_items:
            content += f"- {news['title']}: {news['summary']}\n"
    else:
        content += "Нет доступных новостей.\n"

    messages = [
        {
            "role": "system",
            "content": (
                "У вас есть доступ к техническим индикаторам по разным таймфреймам, фундаментальному анализу (экономический календарь и новости), а также к результатам анализа стратегий SNR, ICT и SMC. Проанализируйте все эти данные. В частности, дайте рекомендации по:\n"
                "1. Открытию позиции: указать, следует ли открывать длинную (покупка) или короткую (продажа) позицию, или оставаться вне рынка, с учетом стратегий и текущих данных.\n"
                "2. Уровни для стоп-лосса и тейк-профита: укажите подходящие уровни, опираясь на результаты анализа по стратегиям и индикаторам.\n"
                "3. Отложенные ордера: если ситуация предполагает использование отложенного ордера, уточните тип (Buy Stop, Sell Stop, Buy Limit, Sell Limit) и цену для активации, а также условия для его активации.\n"
                "4. Оцените силу анализа по 5 бальной шкале.\n"
                "5. Подскажите, через сколько времени обратиться за новыми рекомендациями и анализом?\n"
                "Сделайте оформление между тегами div class=content-container и ul"
            ),
        },
        {"role": "user", "content": content},
    ]

    try:
        # Запрашиваем прогноз у модели GPT-4
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=850,
        )
        # Получаем текст ответа
        analysis = response["choices"][0]["message"]["content"].strip()

        # Сохраняем результат анализа в базу данных
        recommendation = Recommendation(
            symbol=result["symbol"],  # Здесь берем символ из результата анализа
            analysis=analysis,  # Используем полученный анализ вместо ai_analysis
        )
        recommendation.save()
        logging.debug(f"Отправляемые данные для анализа с AI: {result}")
        logging.info(f"Я думаю: {analysis}")
        return analysis
    except Exception as e:
        logging.error(f"Ошибка при работе с OpenAI: {e}")
        return "Не удалось получить анализ от OpenAI."
