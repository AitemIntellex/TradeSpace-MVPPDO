import plotly.graph_objects as go


def prepare_plotly_data(
    instrument_structure,
    indicators,
    pivot_points,
    fib_data,
    nearest_levels,
    ote_analysis,
):
    # Подготовка данных для свечного графика
    ohlc = instrument_structure["ohlc"]
    candlestick = go.Candlestick(
        x=[bar["time"] for bar in ohlc],
        open=[bar["open"] for bar in ohlc],
        high=[bar["high"] for bar in ohlc],
        low=[bar["low"] for bar in ohlc],
        close=[bar["close"] for bar in ohlc],
        name="Candlesticks",
    )

    # Подготовка данных для индикаторов (например, скользящая средняя)
    moving_average = go.Scatter(
        x=[bar["time"] for bar in ohlc],
        y=indicators["moving_average"],
        mode="lines",
        name="Moving Average",
    )

    # Подготовка данных для уровней Pivot Points
    pivot_levels = go.Scatter(
        x=[bar["time"] for bar in ohlc],
        y=[pivot_points["pivot"] for _ in ohlc],
        mode="lines",
        name="Pivot Point",
    )

    # Подготовка данных для уровней Фибоначчи
    fib_levels = go.Scatter(
        x=[bar["time"] for bar in ohlc],
        y=fib_data["levels"],
        mode="lines",
        name="Fibonacci Levels",
    )

    # Подготовка данных для ближайших уровней поддержки и сопротивления
    nearest_support_resistance = go.Scatter(
        x=[bar["time"] for bar in ohlc],
        y=nearest_levels,
        mode="markers",
        name="Nearest Levels",
    )

    # Подготовка данных для OTE
    ote_levels = go.Scatter(
        x=[bar["time"] for bar in ohlc],
        y=ote_analysis["ote_levels"],
        mode="lines",
        name="OTE Levels",
    )

    # Собираем все данные в один список
    data = [
        candlestick,
        moving_average,
        pivot_levels,
        fib_levels,
        nearest_support_resistance,
        ote_levels,
    ]

    return data


def create_plotly_figure(data):
    fig = go.Figure(data=data)

    # Настройка макета графика
    fig.update_layout(
        title="Technical Analysis",
        xaxis_title="Time",
        yaxis_title="Price",
        xaxis_rangeslider_visible=False,
        template="plotly_dark",
    )

    return fig
