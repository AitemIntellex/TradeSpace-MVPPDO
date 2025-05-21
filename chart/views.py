import MetaTrader5 as mt5
from django.http import JsonResponse
from django.views import View
import logging
from brain.optimized.mt5_utils_optimized import initialize_mt5
from brain.optimized.optimized_indicators import fetch_ohlc_data, get_indicators_data
from brain.optimized.optimized_market_structure import create_instrument_structure

# Словарь для преобразования таймфрейма
TIMEFRAME_MAPPING = {
    "1m": "M1",
    "5m": "M5",
    "15m": "M15",
    "30m": "M30",
    "1h": "H1",
    "4h": "H4",
    "1d": "D1",
    "1w": "W1",
}


class ChartDataView(View):
    def get(self, request):
        try:
            initialize_mt5()

            symbol = request.GET.get("symbol", "EURUSD")
            timeframe = request.GET.get("timeframe", "15m")
            num_candles = int(request.GET.get("num_candles", 50))

            # Конвертируем таймфрейм
            mt5_timeframe = TIMEFRAME_MAPPING.get(timeframe, "M15")

            print(f"✅ API запрос: {symbol}, {mt5_timeframe}, {num_candles} свечей")

            # Загружаем данные OHLC
            ohlc_data = fetch_ohlc_data(symbol, mt5_timeframe, num_candles)
            if ohlc_data is None or ohlc_data.empty:
                raise Exception(f"❌ Нет данных OHLC для {symbol} {timeframe}")

            # Загружаем индикаторы
            indicators = get_indicators_data(symbol, mt5_timeframe, num_candles)

            # Загружаем структуру рынка
            market_structure = create_instrument_structure(
                symbol, mt5_timeframe, num_candles
            )

            response_data = {
                "ohlc": ohlc_data.to_dict(orient="records"),
                "indicators": indicators,
                "market_structure": market_structure,
            }

            return JsonResponse(response_data, safe=False)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
