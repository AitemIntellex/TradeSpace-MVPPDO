import logging
import openai

from django.shortcuts import render, redirect
from src.indicators.technical_indicators import get_indicators_data
from src.adviser.new_technical_indicators import (
    fetch_ohlc_data,
    get_historical_data,
    retrieve_historical_ohlc,
)
from src.utils.mt5_utils import get_currency_tick, initialize_mt5, shutdown_mt5
from src.utils.investing_calendar import get_investing_calendar
from src.utils.rss_news import get_fxstreet_news
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
                "Предоставьте ответ между тегами div class rec-container и ul. Предоставьте ответ на английском языке"
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


from django.http import JsonResponse
import logging
import json

# from src.utils.mt5_utils import fetch_ohlc_data
from src.utils.ai_analytic import analyze_tech_data_with_ai


def analyze_single_timeframe_with_ai(result, ohlc_data, calendar_events, news_items):
    """
    Анализ конкретного таймфрейма с прикреплением OHLC-данных.
    Принимает:
      - result: словарь с информацией (symbol, current_price, индикаторы, стратегии и т.д.)
      - ohlc_data: список/массив баров (time, open, high, low, close), относящихся к одному таймфрейму
      - calendar_events: события экономического календаря
      - news_items: новости
    """

    symbol = result.get("symbol", "N/A")
    current_price = result.get("current_price", "N/A")

    # Начинаем формировать контент
    content_lines = []
    content_lines.append(f"Инструмент: {symbol}")
    content_lines.append(f"Текущая цена: {current_price}")

    # OHLC по выбранному таймфрейму
    content_lines.append("\n## OHLC по выбранному таймфрейму:")
    if ohlc_data and isinstance(ohlc_data, list):
        for bar in ohlc_data:
            content_lines.append(
                f"- Время: {bar.get('time')}, "
                f"Open: {bar.get('open')}, High: {bar.get('high')}, "
                f"Low: {bar.get('low')}, Close: {bar.get('close')}"
            )
    else:
        content_lines.append("Нет данных по свечам.")

    # Индикаторы/стратегии (при желании можно уточнить, что это за таймфрейм)
    indicators_summary = result.get("indicators_summary", {})
    strategies_summary = result.get("strategies_summary", {})

    content_lines.append("\n## Технические индикаторы (для этого таймфрейма):")
    if indicators_summary:
        # Если у тебя внутри словаря уже всё разбито по таймфреймам,
        # можно вытаскивать нужный ключ. Для примера берём сразу всё:
        for tf, indicators in indicators_summary.items():
            content_lines.append(f"\n### Таймфрейм {tf}:")
            content_lines.append(f"- RSI: {indicators.get('rsi', 'N/A')}")
            content_lines.append(f"- MACD: {indicators.get('macd', 'N/A')}")
            # ... и остальные индикаторы
    else:
        content_lines.append("Данные индикаторов отсутствуют.")

    content_lines.append("\n## Экономический календарь:")
    if calendar_events:
        for event in calendar_events:
            content_lines.append(
                f"- {event['time']} ({event['country']}): {event['name']} "
                f"(Факт: {event['fact']}, Пред: {event['previous']}, Прогноз: {event['expected']}, "
                f"Влияние: {event['impact']} звезд)"
            )
    else:
        content_lines.append("Нет значимых событий.")

    content_lines.append("\n## Стратегии (SNR, ICT, SMC):")
    if strategies_summary:
        for strategy_name, data_by_tf in strategies_summary.items():
            content_lines.append(f"\n### Стратегия {strategy_name}:")
            for tf, strategy_data in data_by_tf.items():
                content_lines.append(f"- Таймфрейм {tf}: {strategy_data}")
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

    # Формируем user-сообщение
    user_message_content = "\n".join(content_lines)

    # Массив сообщений для OpenAI
    messages = [
        {
            "role": "system",
            "content": ("Верните полученные данные в удобном формате"),
        },
        {"role": "user", "content": user_message_content},
    ]

    logging.debug("Отправляемые данные в OpenAI (single timeframe):")
    logging.debug(messages)

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",  # или нужная тебе модель
            messages=messages,
        )
        analysis = response["choices"][0]["message"]["content"].strip()

        recommendation = Recommendation(symbol=symbol, analysis=analysis)
        recommendation.save()

        logging.info(f"Результат анализа (single timeframe) от AI: {analysis}")

        return analysis
    except Exception as e:
        logging.error(f"Ошибка при работе с OpenAI (single timeframe): {e}")
        return "Не удалось получить анализ от OpenAI."

def appeal_to_ai_with_historical_data(request):
    if request.method != "POST":
        return JsonResponse({"error": "Ожидается POST-запрос"}, status=400)

    try:
        symbol = request.POST.get("symbol", request.COOKIES.get("selected_pair", "XAUUSD"))
        timeframes = define_timeframes()

        initialize_mt5()
        try:
            tick = get_currency_tick(symbol)
            if not tick:
                raise Exception(f"Не удалось получить тик для {symbol}")
            current_price = tick.get("bid") or tick.get("ask")

            indicators_summary = {}
            for label, tf in timeframes.items():
                indicators = get_indicators_data(symbol, tf, num_values=3)
                indicators_summary[label] = {
                    "rsi": indicators.get("rsi", [])[-3:],
                    "macd": indicators.get("macd", [])[-3:],
                    "signal": indicators.get("signal", [])[-3:],
                    "upper_band": indicators.get("upper_band", [])[-3:],
                    "lower_band": indicators.get("lower_band", [])[-3:],
                    "atr": indicators.get("atr", [])[-3:],
                    "stochastic": {
                        "K": indicators.get("stochastic_k", [])[-3:],
                        "D": indicators.get("stochastic_d", [])[-3:],
                    },
                    "fibonacci_levels": indicators.get("fibonacci_levels", {}),
                    "regression_channel": indicators.get("regression_channel", {}),
                    "vwap": indicators.get("vwap", [])[-3:],
                    "cci": indicators.get("cci", [])[-3:],
                    "mfi": indicators.get("mfi", [])[-3:],
                }

            ohlc_data = get_rates_dataframe(symbol, mt5.TIMEFRAME_D1, period=50)
            ohlc_dict = ohlc_data.to_dict("records") if ohlc_data is not None else []

            economic_calendar = get_investing_calendar()
            news = get_fxstreet_news()

            result = {
                "symbol": symbol,
                "current_price": current_price,
                "indicators_summary": indicators_summary,
                "ohlc_data": ohlc_dict,
                "economic_calendar": economic_calendar,
                "news": news,
            }

            ai_analysis = analyze_with_ai(result, economic_calendar, news)
            recommendation = Recommendation(symbol=symbol, analysis=ai_analysis)
            recommendation.save()

            return JsonResponse({"analysis": ai_analysis})

        finally:
            shutdown_mt5()

    except Exception as e:
        logging.error(f"Ошибка в appeal_to_ai_with_historical_data: {e}")
        return JsonResponse({"error": str(e)}, status=500)

# Основная функция ai_analysis
def ai_analysis(request):
    symbol_from_cookie = request.COOKIES.get("selected_pair", "XAUUSD")
    symbol = request.GET.get("symbol", symbol_from_cookie)

    # Кэширование отключено из-за проблем с пиклированием
    # cache_key = f"ai_analysis_{symbol}"
    # cached_data = cache.get(cache_key)
    # if cached_data and request.method != "POST":
    #     return render(request, "ai_analysis.html", cached_data)

    timeframes = define_timeframes()
    context = {
        "majors": majors,
        "metals": metals,
        "cryptocurrencies": cryptocurrencies,
        "stocks": stocks,
        "indices": indices,
        "commodities": commodities,
        "selected_pair": symbol,
    }
    all_symbols = majors + metals + cryptocurrencies + stocks + indices + commodities
    context["all_symbols"] = all_symbols

    try:
        initialize_mt5()
        try:
            account_info, open_positions = get_account_and_positions()
            context.update(account_info)
            context["open_positions"] = open_positions

            selected_pair_tick = get_currency_tick(symbol)
            if selected_pair_tick is None:
                raise Exception(f"Не удалось получить тик для символа {symbol}.")
            context["tick_value"] = selected_pair_tick.get("tick_value", 0)
            context["selected_pair_tick"] = selected_pair_tick
            context["last_updated"] = timezone.now()

            (
                indicators_by_timeframe,
                ict_strategies,
                smc_strategies_by_timeframe,
                snr_strategies_by_timeframe,
            ) = analyze_strategies_for_timeframes(symbol, timeframes)
            context["indicators_by_timeframe"] = indicators_by_timeframe

            if request.method == "POST":
                if "open_position" in request.POST:
                    try:
                        volume = float(request.POST.get("volume", 0.01))
                        direction = request.POST.get("direction", "buy")
                        take_profit = float(request.POST.get("take_profit", 0))
                        stop_loss = float(request.POST.get("stop_loss", 0))
                        result = open_market_position(symbol, volume, direction, take_profit, stop_loss)
                        if result:
                            messages.success(request, f"Позиция по {symbol} успешно открыта.")
                        else:
                            messages.error(request, f"Ошибка при открытии позиции по {symbol}.")
                    except Exception as e:
                        logging.error(f"Ошибка при открытии позиции по {symbol}: {e}")
                        messages.error(request, f"Не удалось открыть позицию по {symbol}: {str(e)}")

                elif "place_pending_order" in request.POST:
                    try:
                        volume = float(request.POST.get("volume", 0.01))
                        order_type = request.POST.get("order_type", "buy_limit")
                        price = float(request.POST.get("price", 0))
                        take_profit = float(request.POST.get("take_profit", 0))
                        stop_loss = float(request.POST.get("stop_loss", 0))
                        result = place_pending_order(symbol, volume, order_type, price, take_profit, stop_loss)
                        if result:
                            messages.success(request, f"Отложенный ордер по {symbol} успешно установлен.")
                        else:
                            messages.error(request, f"Ошибка при установке отложенного ордера по {symbol}.")
                    except Exception as e:
                        logging.error(f"Ошибка при установке отложенного ордера по {symbol}: {e}")
                        messages.error(request, f"Не удалось установить отложенный ордер по {symbol}: {str(e)}")

                elif "analyze_x3" in request.POST:
                    try:
                        result = analyze_with_ai_x3(request)  # Прямой вызов, без импорта
                        context["x3_analysis"] = result.json().get("analysis") if result.status_code == 200 else "Ошибка анализа x3"
                    except Exception as e:
                        logging.error(f"Ошибка в analyze_with_ai_x3: {e}")
                        context["x3_analysis"] = f"Ошибка: {str(e)}"

                elif "analyze_with_history" in request.POST:
                    try:
                        result = appeal_to_ai_with_historical_data(request)  # Прямой вызов, без импорта
                        context["historical_analysis"] = result.json().get("analysis") if result.status_code == 200 else "Ошибка анализа с историей"
                    except Exception as e:
                        logging.error(f"Ошибка в appeal_to_ai_with_historical_data: {e}")
                        context["historical_analysis"] = f"Ошибка: {str(e)}"

                elif "analyze_with_ai" in request.POST:
                    indicators_summary = {
                        timeframe: {
                            "rsi": indicators.get("rsi"),
                            "macd": indicators.get("macd"),
                            "signal": indicators.get("signal"),
                            "upper_band": indicators.get("upper_band"),
                            "lower_band": indicators.get("lower_band"),
                            "atr": indicators.get("atr"),
                            "stochastic": {
                                "K": indicators.get("stochastic_k"),
                                "D": indicators.get("stochastic_d"),
                            },
                            "fibonacci_levels": indicators.get("fibonacci_levels"),
                            "regression_channel": indicators.get("regression_channel"),
                            "vwap": indicators.get("vwap"),
                            "cci": indicators.get("cci"),
                            "mfi": indicators.get("mfi"),
                        } for timeframe, indicators in indicators_by_timeframe.items()
                    }

                    result = {
                        "symbol": symbol,
                        "current_price": selected_pair_tick.get("bid") or selected_pair_tick.get("ask"),
                        "indicators_summary": indicators_summary,
                        "economic_calendar": get_investing_calendar(),
                        "news": get_fxstreet_news(),
                        "strategies": {
                            "ICT": ict_strategies,
                            "SNR": snr_strategies_by_timeframe,
                            "SMC": smc_strategies_by_timeframe,
                        },
                    }

                    try:
                        ai_analysis_result = analyze_with_ai(result, get_investing_calendar(), get_fxstreet_news())
                        context["ai_analysis"] = ai_analysis_result
                    except Exception as e:
                        logging.error(f"Ошибка при выполнении анализа с AI: {e}")
                        messages.error(request, "Не удалось выполнить анализ с AI.")

                elif "news_overview" in request.POST:
                    calendar_events = get_investing_calendar()
                    news_items = get_fxstreet_news()
                    messages_to_openai = [
                        {"role": "system", "content": "Ты аналитик по фундаментальному анализу. Дай обзор ключевых новостей и событий, и укажи, на какой валютной паре стоит сосредоточить внимание для торговли сегодня."},
                        {"role": "user", "content": f"Календарь: {calendar_events}\nНовости: {news_items}"},
                    ]
                    response = openai.ChatCompletion.create(model="gpt-4o", messages=messages_to_openai)
                    analysis = response["choices"][0]["message"]["content"].strip()
                    context["news_analysis"] = analysis
                    recommendation = Recommendation(symbol="Новости экономики", analysis=analysis)
                    recommendation.save()

                elif "deep_tech_analyst" in request.POST:
                    indicators_history = get_indicators_data_history(symbol, "M15", count=20)
                    messages_to_openai = [
                        {"role": "system", "content": "Ты технический аналитик. Анализируй рынок по индикаторам и свечам."},
                        {"role": "user", "content": f"История индикаторов и свечей:\n{indicators_history}"},
                    ]
                    response = openai.ChatCompletion.create(model="gpt-4o", messages=messages_to_openai)
                    context["deep_tech_analysis"] = response["choices"][0]["message"]["content"]

            # Кэширование отключено из-за проблем с пиклированием
            # cache.set(cache_key, context, timeout=300)

        finally:
            shutdown_mt5()

    except Exception as e:
        error_msg = f"Ошибка при анализе {symbol}: {str(e)}"
        logging.error(error_msg)
        messages.error(request, error_msg)
        context["error"] = error_msg

    return render(request, "ai_analysis.html", context)

# def appeal_to_ai_with_historical_data(request):
#     if request.method != "POST":
#         return JsonResponse({"error": "Ожидается POST-запрос"}, status=400)

#     try:
#         symbol = request.POST.get("symbol", request.COOKIES.get("selected_pair", "XAUUSD"))
#         timeframes = define_timeframes()

#         initialize_mt5()
#         try:
#             # Получаем текущую цену
#             tick = get_currency_tick(symbol)
#             if not tick:
#                 raise Exception(f"Не удалось получить тик для {symbol}")
#             current_price = tick.get("bid") or tick.get("ask")

#             # Получаем последние 3 значения индикаторов по всем таймфреймам
#             indicators_summary = {}
#             for label, tf in timeframes.items():
#                 indicators = get_indicators_data(symbol, tf, num_values=3)
#                 indicators_summary[label] = {
#                     "rsi": indicators.get("rsi", [])[-3:],
#                     "macd": indicators.get("macd", [])[-3:],
#                     "signal": indicators.get("signal", [])[-3:],
#                     "upper_band": indicators.get("upper_band", [])[-3:],
#                     "lower_band": indicators.get("lower_band", [])[-3:],
#                     "atr": indicators.get("atr", [])[-3:],
#                     "stochastic": {
#                         "K": indicators.get("stochastic_k", [])[-3:],
#                         "D": indicators.get("stochastic_d", [])[-3:],
#                     },
#                     "fibonacci_levels": indicators.get("fibonacci_levels", {}),
#                     "regression_channel": indicators.get("regression_channel", {}),
#                     "vwap": indicators.get("vwap", [])[-3:],
#                     "cci": indicators.get("cci", [])[-3:],
#                     "mfi": indicators.get("mfi", [])[-3:],
#                 }

#             # Получаем OHLC для последних 50 баров на таймфрейме D1
#             ohlc_data = get_rates_dataframe(symbol, mt5.TIMEFRAME_D1, period=50)
#             ohlc_dict = ohlc_data.to_dict("records") if ohlc_data is not None else []

#             # Получаем новости и календарь
#             economic_calendar = get_investing_calendar()
#             news = get_fxstreet_news()

#             # Формируем данные для OpenAI
#             result = {
#                 "symbol": symbol,
#                 "current_price": current_price,
#                 "indicators_summary": indicators_summary,
#                 "ohlc_data": ohlc_dict,
#                 "economic_calendar": economic_calendar,
#                 "news": news,
#             }

#             # Выполняем анализ
#             ai_analysis = analyze_with_ai(result, economic_calendar, news)

#             # Сохраняем рекомендацию
#             recommendation = Recommendation(symbol=symbol, analysis=ai_analysis)
#             recommendation.save()

#             return JsonResponse({"analysis": ai_analysis})

#         finally:
#             shutdown_mt5()

#     except Exception as e:
#         logging.error(f"Ошибка в appeal_to_ai_with_historical_data: {e}")
#         return JsonResponse({"error": str(e)}, status=500)
