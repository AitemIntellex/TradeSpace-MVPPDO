import logging
import numpy as np
import pandas as pd
import talib


def calculate_moving_average(data, period=14):
    """Calculate Moving Average."""
    if len(data) < period:
        return pd.Series([None] * len(data))  # Недостаточно данных для расчета
    return data["close"].rolling(window=period).mean()


def calculate_rsi(data, period=14):
    """Calculate Relative Strength Index (RSI)."""
    if len(data) < period:
        return pd.Series([None] * len(data))  # Недостаточно данных для расчета
    delta = data["close"].diff(1)
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def calculate_macd(data):
    """Calculate Moving Average Convergence Divergence (MACD)."""
    if len(data) < 26:  # Для MACD требуется минимум 26 периодов
        return pd.Series([None] * len(data)), pd.Series([None] * len(data))

    exp1 = data["close"].ewm(span=12, adjust=False).mean()
    exp2 = data["close"].ewm(span=26, adjust=False).mean()
    macd = exp1 - exp2
    signal = macd.ewm(span=9, adjust=False).mean()
    return macd, signal


def calculate_bollinger_bands(data, period=20):
    """Calculate Bollinger Bands."""
    if len(data) < period:
        return None, None  # Недостаточно данных для расчета
    sma = data["close"].rolling(window=period).mean()
    std = data["close"].rolling(window=period).std()
    upper_band = sma + (2 * std)
    lower_band = sma - (2 * std)
    return upper_band, lower_band
