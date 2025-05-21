document.addEventListener("DOMContentLoaded", function () {
  // Элементы интерфейса
  const toggleButton = document.querySelector(".sidebar-toggle");
  const sidebar = document.querySelector(".sidebar");
  const mainContent = document.querySelector(".main");
  const logo = document.getElementById("logo-toggle");
  const loadingIndicator = document.getElementById("loading-indicator");
  const table = document.getElementById("analysis-table");
  const themeToggleButton = document.getElementById("theme-toggle");
  const refreshButton = document.getElementById("refresh-button");

  const collapseBreakpoint = 992; // Ширина, при которой меню сворачивается

  // --- ФУНКЦИЯ ОБНОВЛЕНИЯ СОСТОЯНИЯ САЙДБАРА ---
  function updateSidebarState(isCollapsed) {
    if (sidebar && mainContent) {
      sidebar.classList.toggle("collapsed", isCollapsed);
      mainContent.classList.toggle("expanded", isCollapsed);
      localStorage.setItem("sidebarCollapsed", isCollapsed);
    }
  }

  // --- УСТАНОВКА СОСТОЯНИЯ САЙДБАРА ИЗ LOCALSTORAGE ---
  function initializeSidebarState() {
    const isCollapsed = localStorage.getItem("sidebarCollapsed") === "true";
    updateSidebarState(isCollapsed);
  }

  // --- ОБРАБОТЧИК ИЗМЕНЕНИЯ РАЗМЕРА ОКНА ---
  function handleResize() {
    if (window.innerWidth <= collapseBreakpoint) {
      updateSidebarState(true);
    }
  }

  window.addEventListener("resize", debounce(handleResize, 100));

  // --- ФУНКЦИЯ ДЕБАУНСА ---
  function debounce(func, wait) {
    let timeout;
    return function (...args) {
      const context = this;
      clearTimeout(timeout);
      timeout = setTimeout(() => func.apply(context, args), wait);
    };
  }

  // --- ПЕРЕКЛЮЧЕНИЕ СОСТОЯНИЯ САЙДБАРА ---
  const toggleSidebar = () => {
    if (sidebar && mainContent) {
      const currentIsCollapsed = sidebar.classList.contains("collapsed");
      updateSidebarState(!currentIsCollapsed);
    }
  };

  if (toggleButton) toggleButton.addEventListener("click", toggleSidebar);
  if (logo) logo.addEventListener("click", toggleSidebar);

  // --- ЗАГРУЗКА СТРАНИЦЫ ---
  function loadPage(pageName) {
    if (loadingIndicator) loadingIndicator.style.display = "block"; // Показать индикатор

    fetch(`/dynamic-page/${pageName}/`, { cache: "no-cache" })
      .then((response) => {
        if (!response.ok)
          throw new Error(`HTTP error! Status: ${response.status}`);
        return response.text();
      })
      .then((html) => {
        const dynamicContent = document.getElementById("dynamic-content");
        if (dynamicContent) dynamicContent.innerHTML = html;
      })
      .catch((error) => {
        console.error("Ошибка загрузки страницы:", error);
        const dynamicContent = document.getElementById("dynamic-content");
        if (dynamicContent) {
          dynamicContent.innerHTML =
            "<p>Ошибка загрузки данных. Попробуйте позже.</p>";
        }
      })
      .finally(() => {
        if (loadingIndicator) loadingIndicator.style.display = "none"; // Скрыть индикатор
      });
  }

  // --- ОБНОВЛЕНИЕ ДАННЫХ БЕЗ КЕША ---
  function refreshData() {
    if (loadingIndicator) loadingIndicator.style.display = "block"; // Показать индикатор

    fetch("/update-database/", { method: "POST", cache: "no-cache" })
      .then((response) => {
        if (!response.ok)
          throw new Error(`Ошибка обновления базы. Код: ${response.status}`);

        return response.json();
      })
      .then((data) => {
        console.log("База обновлена:", data);
        loadPage("current");
      })
      .catch((error) => {
        console.error("Ошибка обновления базы:", error);
        alert("Не удалось обновить базу данных. Попробуйте позже.");
      })
      .finally(() => {
        if (loadingIndicator) loadingIndicator.style.display = "none"; // Скрыть индикатор
      });
  }

  if (refreshButton) {
    refreshButton.addEventListener("click", refreshData);
  }

  // --- ОБРАБОТКА ТАБЛИЦЫ ---
  if (table) {
    const rows = table.querySelectorAll("tbody tr");
    let selectedRow = null;

    rows.forEach((row) => {
      row.addEventListener("mouseenter", () => {
        if (row !== selectedRow) row.style.backgroundColor = "#191919";
      });

      row.addEventListener("mouseleave", () => {
        if (row !== selectedRow) row.style.backgroundColor = "";
      });

      row.addEventListener("click", () => {
        if (selectedRow) {
          selectedRow.classList.remove("selected");
          selectedRow.style.backgroundColor = "";
        }
        row.classList.add("selected");
        selectedRow = row;
      });
    });
  }

  // --- ПЕРЕКЛЮЧЕНИЕ ТЕМЫ ---
  const currentTheme = localStorage.getItem("theme") || "light";
  document.documentElement.setAttribute("data-theme", currentTheme);

  if (themeToggleButton) {
    themeToggleButton.addEventListener("click", () => {
      const newTheme = currentTheme === "light" ? "dark" : "light";
      document.documentElement.setAttribute("data-theme", newTheme);
      localStorage.setItem("theme", newTheme);
    });
  } else {
    console.warn(
      "Элемент с ID 'theme-toggle' не найден. Переключение темы недоступно."
    );
  }

  // --- ИНИЦИАЛИЗАЦИЯ ---
  initializeSidebarState();
  handleResize();
});
// candlestick.js

function renderCandlestickChart(data, chartId) {
    // Проверяем, есть ли данные
    if (!data || data.length === 0) {
        document.getElementById(chartId).innerHTML = 'Нет данных для отображения свечей';
        return;
    }

    // Проверяем, достаточно ли данных для построения графика
    if (data.length <= 1) {
        document.getElementById(chartId).innerHTML = 'Недостаточно данных для отображения свечей';
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

    // Построение графика с Plotly
    Plotly.newPlot(chartId, [trace], layout);
}
