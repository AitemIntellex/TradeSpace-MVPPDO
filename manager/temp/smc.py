from django.http import JsonResponse


def get_smc_data(request):
    """
    API-эндпоинт для получения данных SMC-стратегии в формате JSON для Plotly.
    """
    symbol = request.GET.get("symbol", "XAUUSD")
    timeframe = request.GET.get("timeframe", "H1")

    try:
        data = get_smc_plotly_data(symbol, timeframe)
        return JsonResponse(data, safe=False)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
