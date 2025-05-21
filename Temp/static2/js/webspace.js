function updateTimezones() {
  const timeZones = {
    asia: "Asia/Tokyo",
    europe: "Europe/Berlin",
    usa: "America/New_York",
    mt5: "Etc/UTC", // MT5 время с секундами
    local: Intl.DateTimeFormat().resolvedOptions().timeZone, // Локальное время
  };

  Object.keys(timeZones).forEach((region) => {
    const options = {
      timeZone: timeZones[region],
      hour: "2-digit",
      minute: "2-digit",
      ...(region === "local" || region === "Tashkent" ? { second: "2-digit" } : {}), // Секунды только для local и mt5
      hourCycle: "h23",
    };

    const time = new Date().toLocaleString("en-US", options);
    console.log(`${region} time:`, time); // Проверяем вывод времени
    const element = document.getElementById(`${region}-time`);
    if (element) {
      element.innerText = time;
    } else {
      console.warn(`Element with ID ${region}-time not found`);
    }
  });

  highlightActiveSessions();
}

setInterval(updateTimezones, 1000);
updateTimezones();



function highlightActiveSessions() {
  const now = new Date();
  const utcHours = now.getUTCHours() + now.getUTCMinutes() / 60;

  // Настройка сессий
  const sessions = [
    { id: "asia-time", activeStart: 0, activeEnd: 9 },
    { id: "europe-time", activeStart: 7, activeEnd: 16 },
    { id: "usa-time", activeStart: 13, activeEnd: 22 },
    { id: "mt5-time", activeStart: 22, activeEnd: 24 },
    // { id: "server-time", activeStart: 0, activeEnd: 24 }, // Серверное время активно всегда
    { id: "local-time", activeStart: 2, activeEnd: 14 }, // Локальное время активно всегда
  ];

  // Подсветка активных сессий
  sessions.forEach((session) => {
    const element = document.getElementById(session.id);

    if (element) {
      if (utcHours >= session.activeStart && utcHours < session.activeEnd) {
        // Активная сессия
        element.style.color = "#00ff00"; // Зеленый цвет для активной сессии
        element.style.fontWeight = "normal";
        element.style.textShadow = "0 0 10px rgba(0, 255, 0, 0.7)"; // Дополнительное свечение
      } else {
        // Неактивная сессия
        element.style.color = "#a19b9b"; // Серый цвет
        element.style.fontWeight = "normal";
        element.style.textShadow = "none";
      }
    }
  });
}

// Обновляем каждую секунду
setInterval(updateTimezones, 1000);
updateTimezones();


async function fetchEconomicNews() {
  try {
    const response = await fetch("/fetch-economic-news/");
    const data = await response.json();

    if (data.error) {
      console.error("Ошибка получения новостей:", data.error);
      return;
    }

    const newsList = document.getElementById("economic-news-list");
    newsList.innerHTML = "";

    if (data.events.length === 0) {
      newsList.innerHTML = "<li>Нет ближайших новостей.</li>";
    } else {
      data.events.forEach((event) => {
        const li = document.createElement("li");
        li.innerHTML = `<strong>${event.time} (${event.country}):</strong> ${event.name} (Влияние: ${event.impact} звезды)`;
        newsList.appendChild(li);
      });
    }
  } catch (error) {
    console.error("Ошибка загрузки экономических новостей:", error);
  }
}

// Запрашиваем новости при загрузке страницы
fetchEconomicNews();
document.addEventListener("DOMContentLoaded", () => {
  const newsList = document.getElementById("economic-news-list");
  const toggleButton = document.getElementById("toggle-news");

  // Функция для обработки отображения новостей
  function showInitialNews() {
    const newsItems = newsList.querySelectorAll("li");
    newsItems.forEach((item, index) => {
      if (index < 2) {
        item.classList.add("visible"); // Показываем первые две новости
      }
    });

    // Если меньше 3 новостей, скрываем кнопку "Показать все"
    if (newsItems.length <= 2) {
      toggleButton.classList.add("hidden");
    }
  }

  // Функция для переключения отображения
  window.toggleNews = () => {
    const newsItems = newsList.querySelectorAll("li");
    const isExpanded = toggleButton.textContent === "Скрыть";

    newsItems.forEach((item, index) => {
      if (index >= 2) {
        item.classList.toggle("visible", !isExpanded); // Переключаем видимость остальных
      }
    });

    // Изменяем текст кнопки
    toggleButton.textContent = isExpanded ? "Показать все" : "Скрыть";
  };

  // Пример добавления данных (для динамической подгрузки)
  function addNews(news) {
    news.forEach((event) => {
      const li = document.createElement("li");
      li.textContent = `${event.time} - ${event.name} (${event.country})`;
      newsList.appendChild(li);
    });
    showInitialNews(); // Вызываем после добавления новостей
  }

  // Пример подгрузки данных
  const sampleNews = [
    { time: "12:30", name: "CPI Data", country: "USA" },
    { time: "14:00", name: "Retail Sales", country: "UK" },
  ];

  // Подгружаем данные экономических новостей
  addNews(sampleNews);
});
document.querySelectorAll('td[data-expand]').forEach(cell => {
    cell.addEventListener('click', () => {
        cell.classList.toggle('expanded');
    });
});
function refreshData() {
    fetch('/api/technical-indicators')
        .then(response => response.json())
        .then(data => {
            // Обновить содержимое таблицы
        });
}

function toggleDetails(id) {
    const details = document.getElementById(`fib_details_${id}`);
    if (details.style.display === "none") {
        details.style.display = "block";
    } else {
        details.style.display = "none";
    }
}
function renderCandlestickChart(data, chartId) {
    // Проверяем, существует ли элемент с указанным ID
    const chartElement = document.getElementById(chartId);
    if (!chartElement) {
        console.error(`Элемент с ID "${chartId}" не найден.`);
        return;
    }

    // Проверяем, есть ли данные
    if (!data || data.length === 0) {
        chartElement.innerHTML = 'Нет данных для отображения свечей';
        console.warn('OHLC данные пустые для графика:', chartId);
        return;
    }

    // Проверяем, достаточно ли данных
    if (data.length <= 1) {
        chartElement.innerHTML = 'Недостаточно данных для отображения свечей';
        console.warn('Недостаточно данных для графика:', chartId);
        return;
    }

    // Подготавливаем данные для Plotly
    const trace = {
        x: data.map(item => item.time),
        open: data.map(item => item.open),
        high: data.map(item => item.high),
        low: data.map(item => item.low),
        close: data.map(item => item.close),
        type: 'candlestick',
    };

    // Настройки макета графика
    const layout = {
        title: 'Японские свечи',
        xaxis: {
            title: 'Время',
            rangeslider: { visible: false },
        },
        yaxis: {
            title: 'Цена',
        },
    };

    // Построение графика
    Plotly.newPlot(chartId, [trace], layout);
}
