from django.http import JsonResponse
from django.views.decorators.http import require_GET

# Импортируем функцию, которая уже умеет всё собирать:
# из brain.optimized.optimized_indicators import get_indicators_data


@require_GET
def get_data(request):
    """
    Единая точка входа для получения всех (или части) индикаторов,
    а также OHLC-данных и прочего.
    Примеры:
      /brain/api/data?symbol=EURUSD&timeframe=M15
      /brain/api/data?symbol=EURUSD&timeframe=M15&indicator=atr
      /brain/api/data?symbol=EURUSD&timeframe=M15&indicator=atr,macd
    """
    symbol = request.GET.get("symbol", "EURUSD")
    timeframe = request.GET.get("timeframe", "M15")
    # Сколько свечей подгружать (на ваш вкус), можно взять из GET
    num_candles = int(request.GET.get("num_candles", 500))

    # Список индикаторов, запрошенных в параметре "indicator"
    # Например, indicator=rsi,macd -> ["rsi","macd"]
    requested_indicators = request.GET.get("indicator", "")
    requested_indicators = [
        i.strip().lower() for i in requested_indicators.split(",") if i.strip()
    ]

    # Основной вызов, который собирает все данные:
    from brain.optimized.optimized_indicators import get_indicators_data

    raw_data = get_indicators_data(symbol, timeframe, num_candles)

    # Если нет параметра ?indicator=..., возвращаем все данные
    if not requested_indicators:
        return JsonResponse(raw_data, safe=False)

    # Иначе вытаскиваем только нужные поля
    # Например, если в requested_indicators=['atr','macd'],
    # то вернём {"atr": [...], "macd": (...), "ohlc": [...]} и т.д.
    filtered_data = {}
    for key, val in raw_data.items():
        # Если ключ совпадает с одним из запрошенных индикаторов
        # или является служебной частью OHLC (например, "ohlc")
        # и мы хотим всегда отдавать OHLC
        # — решаем, что оставляем.
        # Для упрощения добавим условие, что "ohlc" отдаём всегда.
        if key.lower() == "ohlc":
            filtered_data[key] = val
        elif key.lower() in requested_indicators:
            filtered_data[key] = val

    # Если в результате после фильтрации пусто, сообщим, что ничего не выбрали.
    if not filtered_data:
        return JsonResponse(
            {"error": "No valid indicators found in request."}, status=400
        )

    return JsonResponse(filtered_data, safe=False)
