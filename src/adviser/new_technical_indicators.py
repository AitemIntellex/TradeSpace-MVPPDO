import logging
from typing import Dict, Any, List, Optional
from src.utils.mt5_utils import get_ohlc_extended, get_ohlc
from src.indicators.technical_indicators import (
    calculate_macd,
    calculate_bollinger_bands,
    calculate_rsi,
    calculate_atr,
    check_vwap,
    calculate_cci,
    calculate_mfi,
    calculate_stochastic_with_divergence,
    calculate_pivot_points,
)

# Настраиваем логирование для терминала
logging.basicConfig(
    level=logging.INFO,  # Устанавливаем уровень логов (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    format="%(asctime)s - %(levelname)s - %(message)s",  # Формат сообщения
    handlers=[logging.StreamHandler()],  # Выводим сообщения в консоль
)


from typing import Optional, List, Dict, Any
import logging
import MetaTrader5 as mt5
import pandas as pd


def fetch_ohlc_data(
    symbol: str, timeframe: str, num_values: int, use_extended: bool = True
) -> Optional[List[Dict[str, Any]]]:
    try:
        # Маппинг таймфреймов из строкового формата в числовой
        TIMEFRAME_MAPPING = {
            "M1": mt5.TIMEFRAME_M1,
            "M3": mt5.TIMEFRAME_M3,
            "M5": mt5.TIMEFRAME_M5,
            "M15": mt5.TIMEFRAME_M15,
            "H1": mt5.TIMEFRAME_H1,
            "D1": mt5.TIMEFRAME_D1,
            "W1": mt5.TIMEFRAME_W1,
            # Дополнительные варианты:
            "15M": mt5.TIMEFRAME_M15,
            "15m": mt5.TIMEFRAME_M15,
        }
        mt5_timeframe = TIMEFRAME_MAPPING.get(timeframe)
        if not mt5_timeframe:
            raise ValueError(f"Неверный таймфрейм: {timeframe}")

        # Вызов get_ohlc_extended или get_ohlc
        ohlc_data = (
            get_ohlc_extended(symbol, mt5_timeframe, num_values)
            if use_extended
            else get_ohlc(symbol, mt5_timeframe, num_values)
        )

        return ohlc_data.to_dict(orient="records")
    except Exception as e:
        logging.exception(f"Error fetching OHLC data for {symbol} on {timeframe}: {e}")
        return None


# Example utility functions for fetching data
def get_ohlc(symbol: str, timeframe: int, num_values: int) -> pd.DataFrame:
    if not mt5.symbol_select(symbol, True):
        raise Exception(f"Failed to select symbol {symbol}.")

    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, num_values)
    if rates is None:
        raise Exception(f"Failed to fetch OHLC data for {symbol}.")

    rates_frame = pd.DataFrame(rates)
    rates_frame["time"] = pd.to_datetime(rates_frame["time"], unit="s")
    return rates_frame[["time", "open", "high", "low", "close"]]


TIMEFRAME_MAPPING = {
    "M1": mt5.TIMEFRAME_M1,
    "M3": mt5.TIMEFRAME_M3,
    "M5": mt5.TIMEFRAME_M5,
    "M15": mt5.TIMEFRAME_M15,
    "H1": mt5.TIMEFRAME_H1,
    "D1": mt5.TIMEFRAME_D1,
    "W1": mt5.TIMEFRAME_W1,
    # Дополнительные варианты:
    "15M": mt5.TIMEFRAME_M15,
    "15m": mt5.TIMEFRAME_M15,
}


def get_ohlc_extended(
    symbol: str, timeframe, number_of_candles: int, round_digits: int = 5
) -> pd.DataFrame:
    """
    Получает расширенные OHLC-данные для заданного символа.
    При этом timeframe может быть передан как строка, которая конвертируется в mt5.TIMEFRAME_*.
    """
    # Если timeframe передан как строка, преобразуем его в целочисленное значение
    if isinstance(timeframe, str):
        tf_key = timeframe.strip().upper()
        if tf_key not in TIMEFRAME_MAPPING:
            raise ValueError(f"Неверный формат таймфрейма: {timeframe}")
        mt5_timeframe = TIMEFRAME_MAPPING[tf_key]
    else:
        mt5_timeframe = timeframe

    # Активируем символ
    if not mt5.symbol_select(symbol, True):
        logging.info(f"Попытка активировать символ: {symbol}")
        raise Exception(f"Не удалось выбрать символ {symbol}")

    rates = mt5.copy_rates_from_pos(symbol, mt5_timeframe, 0, number_of_candles)
    if rates is None:
        raise Exception(f"Не удалось получить данные для символа {symbol}")
    rates_frame = pd.DataFrame(rates)
    rates_frame["time"] = pd.to_datetime(rates_frame["time"], unit="s")
    for col in ["open", "high", "low", "close"]:
        rates_frame[col] = rates_frame[col].round(round_digits)
    return rates_frame[["time", "open", "high", "low", "close"]]


# def get_ohlc_extended(symbol, timeframe, number_of_candles, round_digits=5):
#     if not mt5.symbol_select(symbol, True):
#         raise Exception(f"Не удалось выбрать символ {symbol}")
#     rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, number_of_candles)
#     if rates is None:
#         raise Exception(f"Не удалось получить данные для символа {symbol}")
#     rates_frame = pd.DataFrame(rates)
#     rates_frame["time"] = pd.to_datetime(rates_frame["time"], unit="s")

#     # Округление
#     rates_frame["open"] = rates_frame["open"].round(round_digits)
#     rates_frame["high"] = rates_frame["high"].round(round_digits)
#     rates_frame["low"] = rates_frame["low"].round(round_digits)
#     rates_frame["close"] = rates_frame["close"].round(round_digits)

#     return rates_frame[["time", "open", "high", "low", "close"]]


def get_historical_data(symbol, timeframe, num_bars):
    ohlc_data = fetch_ohlc_data(symbol, timeframe, num_bars, use_extended=True)
    if not ohlc_data:
        raise ValueError(
            f"Не удалось получить данные OHLC для {symbol} на {timeframe}."
        )
    return ohlc_data


def retrieve_historical_ohlc(
    symbol: str, timeframe: str, num_values: int, extended: bool = True
) -> Optional[List[Dict[str, Any]]]:
    """
    Retrieve historical OHLC data for a given trading symbol and timeframe.

    Args:
        symbol (str): The trading symbol to retrieve data for.
        timeframe (str): The desired timeframe for the data (e.g., 'M5').
        num_values (int): The number of historical bars to fetch.
        extended (bool): Whether to retrieve extended OHLC data. Default is True.

    Returns:
        Optional[List[Dict[str, Any]]]: A list of dictionaries representing OHLC data.
    """
    try:
        ohlc_data = (
            get_ohlc_extended(symbol, timeframe, num_values)
            if extended
            else get_ohlc(symbol, timeframe, num_values)
        )
        logging.info(f"Retrieved historical OHLC data for {symbol} on {timeframe}.")
        return ohlc_data.to_dict(orient="records")
    except Exception as e:
        logging.exception(
            f"Error retrieving historical OHLC data for {symbol} on {timeframe}: {e}"
        )
        return None


def calculate_indicators(
    symbol: str, timeframe: str, num_values: int
) -> Dict[str, Any]:
    """
    Calculate various technical indicators for the specified symbol and timeframe.

    Args:
        symbol (str): Trading symbol.
        timeframe (str): Timeframe (e.g., 'M5').
        num_values (int): Number of values to calculate.

    Returns:
        Dict[str, Any]: Calculated indicators.
    """
    logging.info(f"Calculating indicators for {symbol} on {timeframe}.")
    indicators = {}

    # MACD
    try:
        macd_values, signal_values = calculate_macd(
            symbol, timeframe, num_values=num_values
        )
        indicators["macd"] = macd_values
        indicators["signal"] = signal_values
        logging.info(f"MACD calculated for {symbol} on {timeframe}.")
    except Exception as e:
        logging.exception(f"Error calculating MACD for {symbol} on {timeframe}: {e}")
        indicators["macd"] = [None] * num_values
        indicators["signal"] = [None] * num_values

    # Bollinger Bands
    try:
        sma_values, upper_band_values, lower_band_values = calculate_bollinger_bands(
            symbol, timeframe, num_values=num_values
        )
        indicators["sma"] = sma_values
        indicators["upper_band"] = upper_band_values
        indicators["lower_band"] = lower_band_values
        logging.info(f"Bollinger Bands calculated for {symbol} on {timeframe}.")
    except Exception as e:
        logging.exception(
            f"Error calculating Bollinger Bands for {symbol} on {timeframe}: {e}"
        )
        indicators["sma"] = [None] * num_values
        indicators["upper_band"] = [None] * num_values
        indicators["lower_band"] = [None] * num_values

    # RSI
    try:
        rsi_values = calculate_rsi(symbol, timeframe, num_values=num_values)
        indicators["rsi"] = rsi_values
        logging.info(f"RSI calculated for {symbol} on {timeframe}.")
    except Exception as e:
        logging.exception(f"Error calculating RSI for {symbol} on {timeframe}: {e}")
        indicators["rsi"] = [None] * num_values

    # ATR
    try:
        atr_values = calculate_atr(symbol, timeframe, num_values=num_values)
        indicators["atr"] = atr_values
        logging.info(f"ATR calculated for {symbol} on {timeframe}.")
    except Exception as e:
        logging.exception(f"Error calculating ATR for {symbol} on {timeframe}: {e}")
        indicators["atr"] = [None] * num_values

    # VWAP
    try:
        vwap_values = check_vwap(symbol, timeframe, num_values=num_values)
        indicators["vwap"] = vwap_values
        logging.info(f"VWAP calculated for {symbol} on {timeframe}.")
    except Exception as e:
        logging.exception(f"Error calculating VWAP for {symbol} on {timeframe}: {e}")
        indicators["vwap"] = [None] * num_values

    # CCI
    try:
        cci_values = calculate_cci(symbol, timeframe, num_values=num_values)
        indicators["cci"] = cci_values
        logging.info(f"CCI calculated for {symbol} on {timeframe}.")
    except Exception as e:
        logging.exception(f"Error calculating CCI for {symbol} on {timeframe}: {e}")
        indicators["cci"] = [None] * num_values

    # MFI
    try:
        mfi_values = calculate_mfi(symbol, timeframe, num_values=num_values)
        indicators["mfi"] = mfi_values
        logging.info(f"MFI calculated for {symbol} on {timeframe}.")
    except Exception as e:
        logging.exception(f"Error calculating MFI for {symbol} on {timeframe}: {e}")
        indicators["mfi"] = [None] * num_values

    # Stochastic
    try:
        stochastic_k, stochastic_d, divergences = calculate_stochastic_with_divergence(
            symbol, timeframe, num_values
        )
        indicators["stochastic_k"] = stochastic_k
        indicators["stochastic_d"] = stochastic_d
        indicators["stochastic_divergence"] = divergences
        logging.info(f"Stochastic calculated for {symbol} on {timeframe}.")
    except Exception as e:
        logging.exception(
            f"Error calculating Stochastic for {symbol} on {timeframe}: {e}"
        )
        indicators["stochastic_k"] = []
        indicators["stochastic_d"] = []
        indicators["stochastic_divergence"] = []

    # Pivot Points
    try:
        pivot_points = calculate_pivot_points(symbol, timeframe, num_values=num_values)
        indicators["pivot"] = [item["pivot"] for item in pivot_points]
        indicators["pp_resistance"] = [item["pp_resistance"] for item in pivot_points]
        indicators["pp_support"] = [item["pp_support"] for item in pivot_points]
        logging.info(f"Pivot Points calculated for {symbol} on {timeframe}.")
    except Exception as e:
        logging.exception(
            f"Error calculating Pivot Points for {symbol} on {timeframe}: {e}"
        )
        indicators["pivot"] = [None] * num_values
        indicators["pp_resistance"] = [[None] * 3 for _ in range(num_values)]
        indicators["pp_support"] = [[None] * 3 for _ in range(num_values)]

    return indicators


def get_new_indicators_data(
    symbol: str, timeframe: str, num_values: int = 128, use_extended: bool = True
) -> Dict[str, Any]:
    """
    Main function to fetch OHLC data and calculate indicators.

    Args:
        symbol (str): Trading symbol.
        timeframe (str): Timeframe (e.g., 'M5').
        num_values (int): Number of bars to fetch.
        use_extended (bool): Whether to use extended OHLC data.

    Returns:
        Dict[str, Any]: Combined data for indicators and OHLC.
    """
    logging.info(f"Fetching indicator data for {symbol} on {timeframe}.")
    data = {}

    # Fetch OHLC data
    data["ohlc"] = fetch_ohlc_data(symbol, timeframe, num_values, use_extended)

    # Calculate indicators
    indicators = calculate_indicators(symbol, timeframe, num_values)
    data.update(indicators)

    logging.info(f"Indicators successfully calculated for {symbol} on {timeframe}.")
    return data


import plotly.graph_objects as go


import json


def prepare_indicators_for_json(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Преобразует данные индикаторов в формат {indicator: {"x": [...], "y": [...]}} для Plotly.

    Args:
        data (Dict[str, Any]): Сырые данные с OHLC и индикаторами.

    Returns:
        Dict[str, Any]: Данные в формате {indicator: {"x": [...], "y": [...]}}.
    """
    if not data or not isinstance(data, dict):
        raise ValueError("Ошибка: Переданы некорректные данные (None или не словарь).")

    # Проверяем наличие OHLC данных
    ohlc = data.get("ohlc", None)
    if not isinstance(ohlc, list) or len(ohlc) == 0:
        raise ValueError("Ошибка: OHLC данные отсутствуют или пустые.")

    try:
        timestamps = [bar["time"] for bar in ohlc if "time" in bar]  # Временные метки
    except Exception as e:
        raise ValueError(f"Ошибка при обработке OHLC: {e}")

    # Проверяем индикаторы
    indicators = {}
    for key, values in data.items():
        if key == "ohlc":  # Пропускаем OHLC
            continue

        if values is None:
            print(
                f"⚠️ Предупреждение: Индикатор '{key}' имеет значение None и будет пропущен."
            )
            continue

        if isinstance(values, list):
            indicators[key] = {
                "x": timestamps[: len(values)],  # Временные метки для индикатора
                "y": values[: len(timestamps)],  # Значения индикатора
            }
        else:
            print(
                f"⚠️ Предупреждение: Пропущен индикатор '{key}', т.к. он не является списком."
            )

    return indicators


def plot_main_chart(df, indicators):
    """
    df: DataFrame с колонками ['time', 'open', 'high', 'low', 'close']
    indicators: словарь с ключами 'sma', 'upper_band', 'lower_band', 'vwap', 'pivot' и т.д.
    """
    fig = go.Figure()

    # Свечной график
    fig.add_trace(
        go.Candlestick(
            x=df["time"],
            open=df["open"],
            high=df["high"],
            low=df["low"],
            close=df["close"],
            name="Price",
        )
    )

    # Bollinger Bands (если нужно показывать прямо поверх свечей)
    fig.add_trace(
        go.Scatter(
            x=df["time"],
            y=indicators["upper_band"],
            line=dict(color="blue", width=1),
            name="Upper Band",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df["time"],
            y=indicators["lower_band"],
            line=dict(color="blue", width=1),
            name="Lower Band",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df["time"],
            y=indicators["sma"],
            line=dict(color="orange", width=1),
            name="Bollinger SMA",
        )
    )

    # VWAP (одна линия)
    fig.add_trace(
        go.Scatter(
            x=df["time"],
            y=indicators["vwap"],
            line=dict(color="green", width=1),
            name="VWAP",
        )
    )

    # Pivot Points: можно просто добавить несколько горизонтальных линий
    shapes = []
    if "pivot" in indicators:
        # pivot[i] = сам пивот,
        # pp_resistance[i] = список [R1, R2, R3],
        # pp_support[i] = список [S1, S2, S3]
        for i, t in enumerate(df["time"]):
            pivot_val = indicators["pivot"][i]
            # И так далее с resistances, supports...
            # Но проще бывает брать последний бар, если это дневной пивот.
            # Или же, если хотим нарисовать линию на всю ширину графика:
            # xref='paper', x0=0, x1=1, y0=pivot_val, y1=pivot_val

    fig.update_layout(
        title="Candles + Bollinger + VWAP + Pivot",
        xaxis_title="Time",
        yaxis_title="Price",
        shapes=shapes,
    )
    return fig


import plotly.graph_objects as go
from plotly.subplots import make_subplots


def plot_multiple_subplots(df, indicators):
    """
    Пример: свечи в первом ряду, MACD во втором, RSI в третьем и т.д.
    """
    # Указываем, сколько всего строк будет, и что ось X одна на всех
    fig = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.02,
        row_heights=[0.5, 0.25, 0.25],
    )  # Пропорции высот

    # 1) Candlestick (Row 1)
    fig.add_trace(
        go.Candlestick(
            x=df["time"],
            open=df["open"],
            high=df["high"],
            low=df["low"],
            close=df["close"],
            name="Price",
        ),
        row=1,
        col=1,
    )

    # Если хотим Bollinger Bands на этом же подграфике (Row 1)
    fig.add_trace(
        go.Scatter(
            x=df["time"],
            y=indicators["upper_band"],
            line=dict(color="blue", width=1),
            name="Upper Band",
        ),
        row=1,
        col=1,
    )
    # и т.д.

    # 2) MACD на Row 2
    macd_vals = indicators["macd"]
    signal_vals = indicators["signal"]
    fig.add_trace(
        go.Scatter(
            x=df["time"], y=macd_vals, mode="lines", line=dict(color="red"), name="MACD"
        ),
        row=2,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=df["time"],
            y=signal_vals,
            mode="lines",
            line=dict(color="blue"),
            name="MACD Signal",
        ),
        row=2,
        col=1,
    )
    # Можно добавить bar для гистограммы (разницы MACD - Signal)

    # 3) RSI на Row 3
    rsi_vals = indicators["rsi"]
    fig.add_trace(
        go.Scatter(
            x=df["time"],
            y=rsi_vals,
            mode="lines",
            line=dict(color="orange"),
            name="RSI",
        ),
        row=310,
        col=1,
    )

    # Настройки оформления
    fig.update_layout(
        title="Candles, MACD, RSI",
        xaxis=dict(title="Time"),
    )

    # Дополнительные подписи осей, например, fig.update_yaxes(..., row=2, col=1)
    return fig
