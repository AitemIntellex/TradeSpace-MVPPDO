import logging
from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

# Импортируем функции из твоих модулей
from brain.optimized.optimized_indicators import generate_plotly_data, df_to_json
from brain.optimized.mt5_utils_optimized import get_trade_history

# Настройка логирования (если не настроена централизованно)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


@method_decorator(csrf_exempt, name="dispatch")
class MarketDataAPIView(View):
    """
    API-представление для получения рыночных данных, структуры инструмента и торговой истории.

    При вызове через GET-параметры:
      - symbol: символ инструмента (по умолчанию "EURUSD")
      - timeframe: таймфрейм в виде строки (например, "M15", "H1" и т.д.)
      - num_candles: количество баров (по умолчанию 500)

    Функциональность построена на ранее реализованных модулях,
    которые внутри конвертируют строковый таймфрейм в нужный формат MT5.
    """

    def get(self, request, *args, **kwargs):
        symbol = request.GET.get("symbol", "EURUSD")
        timeframe = request.GET.get("timeframe", "M15")
        try:
            num_candles = int(request.GET.get("num_candles", 500))
        except ValueError:
            num_candles = 500

        try:
            # Собираем данные для графиков (OHLC, индикаторы, рыночное время и т.д.)
            market_data = generate_plotly_data(symbol, timeframe, num_candles)
            # Создаем расширенную структуру инструмента, включая уровни Фибоначчи, ликвидности и т.д.
            structure_data = create_instrument_structure(symbol, timeframe)
            # Получаем торговую историю
            trade_history = get_trade_history()

            response_data = {
                "market_data": market_data,
                "structure": structure_data,
                "trade_history": trade_history,
            }
            return JsonResponse(
                response_data,
                safe=False,
                json_dumps_params={"indent": 4, "ensure_ascii": False},
            )
        except Exception as e:
            logging.error(f"Ошибка при генерации данных API: {e}")
            return JsonResponse({"error": str(e)}, status=500)


from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from brain.optimized.optimized_market_structure import (
    create_instrument_structure,
    identify_market_structure,
)
from brain.optimized.optimized_indicators import get_indicators_data
from brain.optimized.mt5_utils_optimized import get_trade_history, get_rates_dataframe

# Логирование
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


@method_decorator(csrf_exempt, name="dispatch")
class FullMarketDataAPIView(View):
    """
    API-представление для получения всех данных в одном запросе.
    """

    def get(self, request, *args, **kwargs):
        symbol = request.GET.get("symbol", "EURUSD")
        timeframe = request.GET.get("timeframe", "M15")
        num_candles = int(request.GET.get("num_candles", 500))

        try:
            # Сбор всех данных
            market_data = get_rates_dataframe(symbol, timeframe, num_candles)
            indicators_data = get_indicators_data(symbol, timeframe, num_candles)
            structure_data = create_instrument_structure(symbol, timeframe)
            trade_history = get_trade_history()

            # Формирование ответа
            response_data = {
                "market_data": (
                    market_data.to_dict(orient="records")
                    if not market_data.empty
                    else []
                ),
                "indicators": indicators_data,
                "structure": structure_data,
                "trade_history": trade_history,
            }
            return JsonResponse(
                response_data,
                safe=False,
                json_dumps_params={"indent": 4, "ensure_ascii": False},
            )

        except Exception as e:
            logging.error(f"Ошибка при генерации данных API: {e}")
            return JsonResponse({"error": str(e)}, status=500)


class MarketDataAPIView(APIView):
    """
    API для получения данных о рыночной структуре.
    """

    def get(self, request, *args, **kwargs):
        symbol = request.GET.get("symbol", "EURUSD")  # Символ по умолчанию
        timeframe = request.GET.get("timeframe", "M15")  # Таймфрейм по умолчанию
        num_candles = int(request.GET.get("num_candles", 500))  # Количество свечей

        try:
            market_data = identify_market_structure(symbol, timeframe)
            if not market_data:
                raise ValueError(
                    f"Ошибка получения рыночной структуры для {symbol} {timeframe}"
                )

            return Response(market_data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class IndicatorDataAPIView(APIView):
    """
    API для получения данных индикаторов.
    """

    def get(self, request, *args, **kwargs):
        symbol = request.GET.get("symbol", "EURUSD")  # Символ по умолчанию
        timeframe = request.GET.get("timeframe", "M15")  # Таймфрейм по умолчанию
        num_candles = int(request.GET.get("num_candles", 500))  # Количество свечей

        try:
            indicators = get_indicators_data(symbol, timeframe, num_candles)
            if "error" in indicators:
                raise ValueError(indicators["error"])

            return Response(indicators, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
