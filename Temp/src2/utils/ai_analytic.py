# # TradeSpace_v2/src/utils/ai_analisys.py
# import logging
# import openai

# from django.shortcuts import render, redirect
# from src.utils.mt5_utils import get_currency_tick
# from polygon.models import Recommendation  # Добавьте этот импорт


# def analyze_with_ai(result, calendar_events, news_items):
#     """
#     Отправляет данные анализа в OpenAI для получения прогноза, используя chat-комплит endpoint.
#     """
#     # Формирование основного контента с техническими индикаторами
#     content = f"Вам предоставлены последние, самые актуальные данные показателей индикаторов для инструмента {result['symbol']}:\n"
#     current_price = result.get("current_price", "N/A")
#     content += f"Текущая цена: {current_price}\n\n"

#     # Добавляем индикаторы по всем таймфреймам
#     indicators_summary = result.get("indicators_summary", {})
#     for timeframe, indicators in indicators_summary.items():
#         content += f"Таймфрейм {timeframe}:\n"
#         content += f"- RSI: {indicators.get('rsi', 'N/A')}\n"
#         content += f"- MACD: {indicators.get('macd', 'N/A')}, Signal: {indicators.get('signal', 'N/A')}\n"
#         content += f"- Bollinger Bands: Верхняя: {indicators.get('upper_band', 'N/A')}, Нижняя: {indicators.get('lower_band', 'N/A')}\n"
#         content += f"- ATR: {indicators.get('atr', 'N/A')}\n"
#         stochastic = indicators.get("stochastic", {})
#         if stochastic:
#             content += f"- Стохастик K: {stochastic.get('K', 'N/A')}, D: {stochastic.get('D', 'N/A')}\n"
#         content += f"- Уровни Фибоначчи: {indicators.get('fibonacci_levels', 'N/A')}\n"
#         content += f"- Канал регрессии: {indicators.get('regression_channel', 'N/A')}\n"
#         content += f"- VWAP: {indicators.get('vwap', 'N/A')}\n"
#         content += f"- CCI: {indicators.get('cci', 'N/A')}\n"
#         content += f"- MFI: {indicators.get('mfi', 'N/A')}\n\n"

#     # Добавляем данные экономического календаря
#     content += "Экономический календарь на сегодня:\n"
#     if calendar_events:
#         for event in calendar_events:
#             content += (
#                 f"- {event['time']} ({event['country']}): {event['name']} "
#                 f"(Факт: {event['fact']}, Предыдущее: {event['previous']}, Прогноз: {event['expected']}, Влияние: {event['impact']} звезд)\n"
#             )
#     else:
#         content += "Нет значимых событий на сегодня.\n"
#     # Технические индикаторы
#     for timeframe, indicators in result["indicators_summary"].items():
#         content += f"\nТаймфрейм {timeframe}:\n"
#         content += f"RSI: {indicators.get('rsi', 'N/A')}\n"
#         content += f"MACD: {indicators.get('macd', 'N/A')}, Signal: {indicators.get('signal', 'N/A')}\n"
#         # Дополнительно добавить другие индикаторы...

#     # Стратегии
#     strategies_summary = result.get("strategies_summary", {})
#     for strategy, data_by_timeframe in strategies_summary.items():
#         content += f"\nСтратегия {strategy}:\n"
#         for timeframe, strategy_data in data_by_timeframe.items():
#             content += f"Таймфрейм {timeframe}: {strategy_data}\n"

#     # Добавляем новости из RSS-ленты
#     content += "\nПоследние новости:\n"
#     if news_items:
#         for news in news_items:
#             content += f"- {news['title']}: {news['summary']}\n"
#     else:
#         content += "Нет доступных новостей.\n"

#     messages = [
#         {
#             "role": "system",
#             "content": (
# "У вас есть доступ к техническим индикаторам по разным таймфреймам, фундаментальному анализу (экономический календарь и новости), а также к результатам анализа стратегий SNR, ICT и SMC. Проанализируйте все эти данные. В частности, дайте рекомендации по:\n"
# "1. Открытию позиции: указать, следует ли открывать длинную (покупка) или короткую (продажа) позицию, или оставаться вне рынка, с учетом стратегий и текущих данных.\n"
# "2. Уровни для стоп-лосса и тейк-профита: укажите подходящие уровни, опираясь на результаты анализа по стратегиям и индикаторам.\n"
# "3. Отложенные ордера: если ситуация предполагает использование отложенного ордера, уточните тип (Buy Stop, Sell Stop, Buy Limit, Sell Limit) и цену для активации, а также условия для его активации.\n"
# "4. Оцените силу анализа по 3 бальной шкале.\n"
# "5. Подскажите, через сколько времени обратиться за новыми рекомендациями и анализом?\n"
# "Предоставьте ответ между тегами div class content-container и ul"
#                 # "1. Предоставьте весь полученный материал, в удобном для чтения виде и подскажите какие данные не хватают.\n"
#             ),
#         },
#         {"role": "user", "content": content},
#     ]

#     try:
#         # Запрашиваем прогноз у модели GPT-4
#         response = openai.ChatCompletion.create(
#             model="gpt-4o",
#             messages=messages,
#             max_tokens=850,
#         )
#         # Получаем текст ответа
#         analysis = response["choices"][0]["message"]["content"].strip()

#         # Сохраняем результат анализа в базу данных
#         recommendation = Recommendation(
#             symbol=result["symbol"],  # Здесь берем символ из результата анализа
#             analysis=analysis,  # Используем полученный анализ вместо ai_analysis
#         )
#         recommendation.save()
#         logging.debug(f"Отправляемые данные для анализа с AI: {result}")
#         logging.info(f"Я думаю: {analysis}")
#         return analysis
#     except Exception as e:
#         logging.error(f"Ошибка при работе с OpenAI: {e}")
#         return "Не удалось получить анализ от OpenAI."

import logging
import openai

from django.shortcuts import render, redirect
from src.utils.mt5_utils import get_currency_tick
from polygon.models import Recommendation


def analyze_with_ai(result, calendar_events, news_items):
    # Начинаем формировать контент для модели
    symbol = result.get("symbol", "N/A")
    current_price = result.get("current_price", "N/A")
    indicators_summary = result.get("indicators_summary", {})
    strategies_summary = result.get("strategies_summary", {})

    # Формируем содержимое для user-сообщения
    # Делим данные на логические блоки: Инструмент, Текущая цена, Индикаторы, Экономический календарь, Стратегии, Новости
    content_lines = []

    content_lines.append(f"Инструмент: {symbol}")
    content_lines.append(f"Текущая цена: {current_price}")

    content_lines.append("\n## Технические индикаторы по таймфреймам:")
    if indicators_summary:
        for timeframe, indicators in indicators_summary.items():
            content_lines.append(f"\n### Таймфрейм {timeframe}:")
            content_lines.append(f"- RSI: {indicators.get('rsi', 'N/A')}")
            content_lines.append(
                f"- MACD: {indicators.get('macd', 'N/A')}, Signal: {indicators.get('signal', 'N/A')}"
            )
            content_lines.append(
                f"- Bollinger Bands: Верхняя: {indicators.get('upper_band', 'N/A')}, Нижняя: {indicators.get('lower_band', 'N/A')}"
            )
            content_lines.append(f"- ATR: {indicators.get('atr', 'N/A')}")
            stochastic = indicators.get("stochastic", {})
            if stochastic:
                content_lines.append(
                    f"- Стохастик: K: {stochastic.get('K', 'N/A')}, D: {stochastic.get('D', 'N/A')}"
                )
            else:
                content_lines.append("- Стохастик: отсутствует")
            content_lines.append(
                f"- Уровни Фибоначчи: {indicators.get('fib_levels', 'данные отсутствуют')}"
            )
            content_lines.append(
                f"- Канал регрессии: {indicators.get('regression_channel', 'N/A')}"
            )
            content_lines.append(f"- VWAP: {indicators.get('vwap', 'N/A')}")
            content_lines.append(f"- CCI: {indicators.get('cci', 'N/A')}")
            content_lines.append(f"- MFI: {indicators.get('mfi', 'N/A')}")
    else:
        content_lines.append("Данные индикаторов отсутствуют.")

    content_lines.append("\n## Экономический календарь:")
    if calendar_events:
        for event in calendar_events:
            content_lines.append(
                f"- {event['time']} ({event['country']}): {event['name']} "
                f"(Факт: {event['fact']}, Пред: {event['previous']}, Прогноз: {event['expected']}, Влияние: {event['impact']} звезд)"
            )
    else:
        content_lines.append("Нет значимых событий.")

    content_lines.append("\n## Стратегии (SNR, ICT, SMC):")
    if strategies_summary:
        for strategy, data_by_timeframe in strategies_summary.items():
            content_lines.append(f"### Стратегия {strategy}:")
            for timeframe, strategy_data in data_by_timeframe.items():
                content_lines.append(f"- Таймфрейм {timeframe}: {strategy_data}")
    else:
        content_lines.append("Данные по стратегиям отсутствуют.")

    content_lines.append("\n## Последние новости:")
    if news_items:
        for news in news_items:
            title = news.get("title", "N/A")
            summary = news.get("summary", "N/A")
            content_lines.append(f"- {title}: {summary}")
    else:
        content_lines.append("Новости отсутствуют.")

    # Итоговый текст для user-сообщения
    user_message_content = "\n".join(content_lines)

    # Формируем массив сообщений для OpenAI
    messages = [
        {
            "role": "system",
            "content": (
                "У вас есть доступ к техническим индикаторам по разным таймфреймам, фундаментальному анализу (экономический календарь и новости), а также к результатам анализа стратегий SNR, ICT и SMC. Проанализируйте все эти данные. В частности, дайте рекомендации по:\n"
                "1. Открытию позиции: указать, следует ли открывать длинную (покупка) или короткую (продажа) позицию, или оставаться вне рынка, с учетом стратегий и текущих данных.\n"
                "2. Уровни для стоп-лосса и тейк-профита: укажите подходящие уровни, опираясь на результаты анализа по стратегиям и индикаторам.\n"
                "3. Отложенные ордера: если ситуация предполагает использование отложенного ордера, уточните тип (Buy Stop, Sell Stop, Buy Limit, Sell Limit) и цену для активации, а также условия для его активации.\n"
                "4. Оцените силу анализа по 3 бальной шкале.\n"
                "5. Подскажите, через сколько времени обратиться за новыми рекомендациями и анализом?\n"
                "Предоставьте ответ между тегами div class rec-container и ul"
            ),
        },
        {"role": "user", "content": user_message_content},
    ]

    # Для отладки:
    logging.debug("Отправляемые данные в OpenAI:")
    logging.debug(messages)

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=messages,
            # max_tokens=850,
        )
        analysis = response["choices"][0]["message"]["content"].strip()

        recommendation = Recommendation(
            symbol=symbol,
            analysis=analysis,
        )
        recommendation.save()

        logging.info(f"Результат анализа от AI: {analysis}")

        return analysis
    except Exception as e:
        logging.error(f"Ошибка при работе с OpenAI: {e}")
        return "Не удалось получить анализ от OpenAI."


def analyze_tech_data_with_ai(result):
    symbol = result.get("symbol", "N/A")
    indicators_summary = result.get("indicators_summary", {})
    current_price = result.get("current_price", "N/A")
    news = result.get("news", [])
    calendar = result.get("economic_calendar", [])

    # Формируем содержимое для user-сообщения
    content_lines = []
    content_lines.append(f"Инструмент: {symbol}")
    content_lines.append(f"Текущая цена: {current_price}")
    content_lines.append("\n## Последние значения индикаторов по таймфреймам:")

    if indicators_summary:
        for timeframe, indicators in indicators_summary.items():
            content_lines.append(f"\n### Таймфрейм {timeframe}:")
            for key, value in indicators.items():
                if isinstance(value, list):
                    content_lines.append(
                        f"- {key} (последние 3): {', '.join(map(str, value))}"
                    )
                elif isinstance(value, dict):
                    for sub_key, sub_value in value.items():
                        content_lines.append(
                            f"- {key} {sub_key} (последние 3): {', '.join(map(str, sub_value))}"
                        )
                else:
                    content_lines.append(f"- {key}: {value}")
    else:
        content_lines.append("Данные индикаторов отсутствуют.")

    # Добавляем новости
    content_lines.append("\n## Новости:")
    if news:
        for item in news:
            content_lines.append(
                f"- {item['title']}: {item['summary']} ({item['link']})"
            )
    else:
        content_lines.append("Новости отсутствуют.")

    # Добавляем экономический календарь
    content_lines.append("\n## Экономический календарь:")
    if calendar:
        for event in calendar:
            content_lines.append(
                f"- {event['time']} | {event['name']} ({event['country']}, {event['impact']} звезды): "
                f"Факт: {event['fact']}, Прогноз: {event['expected']}, Предыдущее: {event['previous']}"
            )
    else:
        content_lines.append("События в экономическом календаре отсутствуют.")

    # Итоговый текст для user-сообщения
    user_message_content = "\n".join(content_lines)

    # Формируем массив сообщений для OpenAI
    messages = [
        {
            "role": "system",
            "content": (
                "У вас есть доступ к техническим индикаторам по разным таймфреймам, фундаментальному анализу (экономический календарь и новости). Проанализируйте все эти данные. В частности, дайте рекомендации по:\n"
                "1. Открытию позиции: указать, следует ли открывать длинную (покупка) или короткую (продажа) позицию, или оставаться вне рынка, с учетом стратегий и текущих данных.\n"
                "2. Уровни для стоп-лосса и тейк-профита: укажите подходящие уровни, опираясь на результаты анализа по стратегиям и индикаторам.\n"
                "3. Отложенные ордера: если ситуация предполагает использование отложенного ордера, уточните тип (Buy Stop, Sell Stop, Buy Limit, Sell Limit) и цену для активации, а также условия для его активации.\n"
                "4. Оцените силу анализа по 3 бальной шкале.\n"
                "5. Подскажите, через сколько времени обратиться за новыми рекомендациями и анализом?\n"
                "Предоставьте ответ между тегами div class rec-container и ul"
            ),
        },
        {"role": "user", "content": user_message_content},
    ]

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=messages,
        )
        analysis = response["choices"][0]["message"]["content"].strip()

        recommendation = Recommendation(
            symbol=symbol,
            analysis=analysis,
        )
        recommendation.save()

        return analysis
    except Exception as e:
        logging.error(f"Ошибка при работе с OpenAI: {e}")
        return "Не удалось получить анализ от OpenAI."
