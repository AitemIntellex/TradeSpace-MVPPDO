document.addEventListener("DOMContentLoaded", function () {
    fetchChartData();
});

function fetchChartData() {
    fetch("/trade-chart/?symbol=XAUUSD&timeframe=15m")
        .then(response => response.json())
        .then(data => {
            let fig = JSON.parse(data.graph);
            Plotly.newPlot("chart", fig.data, fig.layout);
        })
        .catch(error => console.error("Ошибка загрузки графика:", error));
}

function toggleIndicator(indicator) {
    let traces = document.getElementById("chart").data;
    traces.forEach(trace => {
        if (trace.name.toLowerCase().includes(indicator)) {
            trace.visible = trace.visible === true ? "legendonly" : true;
        }
    });
    Plotly.redraw("chart");
}

function fetchMultiTimeframeAnalysis() {
    fetch("/market-analysis/?symbol=XAUUSD&timeframes=all")
        .then(response => response.json())
        .then(data => {
            console.log("✅ Анализ по всем таймфреймам:", data);
        })
        .catch(error => console.error("Ошибка анализа:", error));
}

document.addEventListener("DOMContentLoaded", function () {
    fetchMultiTimeframeAnalysis();
});
