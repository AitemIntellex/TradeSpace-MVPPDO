document.getElementById("pair-select").addEventListener("change", function () {
  const selectedPair = this.value;

  fetch(`/?symbol=${selectedPair}`)
    .then((response) => response.json())
    .then((data) => {
      if (data.error) {
        alert(`Ошибка: ${data.error}`);
        return;
      }

      // Обновляем данные в интерфейсе
      document.querySelector(".pair-info h5").textContent = selectedPair;
      document.getElementById("currentPrice").textContent =
        data.bid || "Нет данных";
      document.getElementById("tradingVolume").textContent =
        data.tradingVolume || "-";
      document.getElementById("direction").textContent = data.direction || "-";
    })
    .catch((error) => {
      console.error("Ошибка при запросе данных:", error);
    });
});

document.querySelector(".navbar").addEventListener("click", function (event) {
  if (!event.target.closest(".pair-selector, .sidebar-toggle")) {
    const pairInfo = document.querySelector(".pair-info");
    pairInfo.classList.toggle("expanded");
  }
});

// JS для отрисовки графиков на основе данных из контекста CHART's
document.addEventListener("DOMContentLoaded", function () {
  // Подразумевается, что переменные balanceData, equityData, profitData и labels будут определены в глобальной области видимости
  const balanceData = window.balanceHistory; // Используйте window. для доступа к данным
  const equityData = window.equityHistory;
  const profitData = window.profitHistory;
  const labels = window.dateLabels;

  // Отрисовка графика баланса и капитала
  const ctxBalance = document.getElementById("balanceChart").getContext("2d");
  new Chart(ctxBalance, {
    type: "line",
    data: {
      labels: labels,
      datasets: [
        {
          label: "Баланс",
          data: balanceData,
          borderColor: "rgba(75, 192, 192, 1)",
          fill: false,
        },
        {
          label: "Капитал",
          data: equityData,
          borderColor: "rgba(54, 162, 235, 1)",
          fill: false,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
    },
  });

  // Отрисовка графика профита
  const ctxProfit = document.getElementById("profitChart").getContext("2d");
  new Chart(ctxProfit, {
    type: "line",
    data: {
      labels: labels,
      datasets: [
        {
          label: "Профит",
          data: profitData,
          borderColor: "rgba(255, 99, 132, 1)",
          fill: false,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
    },
  });
});
