document.addEventListener("DOMContentLoaded", function () {
  // Элементы интерфейса
  const toggleButton = document.querySelector(".sidebar-toggle");
  const sidebar = document.querySelector(".sidebar");
  const mainContent = document.querySelector(".main");
  const logo = document.getElementById("logo-toggle");
  const loadingIndicator = document.getElementById("loading-indicator");
  const table = document.getElementById("analysis-table");
  const themeToggleButton = document.getElementById("theme-toggle");

  const collapseBreakpoint = 992; // Ширина, при которой меню сворачивается
  let selectedRow = null;

  // Функция обновления состояния сайдбара
  const updateSidebarState = (isCollapsed) => {
    sidebar.classList.toggle("collapsed", isCollapsed);
    mainContent.classList.toggle("expanded", isCollapsed);
    localStorage.setItem("sidebarCollapsed", isCollapsed);
  };

  // Инициализация состояния сайдбара
  const initializeSidebarState = () => {
    const isCollapsed = JSON.parse(localStorage.getItem("sidebarCollapsed") || "false");
    updateSidebarState(isCollapsed);
  };

  // Обработчик клика для переключения сайдбара
  const toggleSidebar = () => {
    updateSidebarState(!sidebar.classList.contains("collapsed"));
  };

  // Логика обработки изменения размера
  const handleResize = () => {
    if (window.innerWidth <= collapseBreakpoint) {
      updateSidebarState(true);
    }
  };

  // Подписка на события
  toggleButton?.addEventListener("click", toggleSidebar);
  logo?.addEventListener("click", toggleSidebar);
  window.addEventListener("resize", debounce(handleResize, 100));

  // Дебаунс функция
  function debounce(func, wait) {
    let timeout;
    return (...args) => {
      clearTimeout(timeout);
      timeout = setTimeout(() => func.apply(this, args), wait);
    };
  }

  // Сохранение и восстановление позиции скролла
  window.addEventListener("beforeunload", () => {
    localStorage.setItem("scrollPosition", window.scrollY);
  });

  window.addEventListener("load", () => {
    const scrollPosition = parseInt(localStorage.getItem("scrollPosition"), 10);
    if (!isNaN(scrollPosition)) window.scrollTo(0, scrollPosition);
  });

  // Загрузка страницы
  const loadPage = async (pageName) => {
    if (loadingIndicator) loadingIndicator.style.display = "block"; // Показать индикатор

    try {
      const response = await fetch(`/dynamic-page/${pageName}/`, { cache: "no-cache" });
      if (!response.ok) throw new Error(`HTTP error! Status: ${response.status}`);
      const html = await response.text();
      document.getElementById("dynamic-content").innerHTML = html;
    } catch (error) {
      console.error("Ошибка загрузки страницы:", error);
      document.getElementById("dynamic-content").innerHTML = "<p>Ошибка загрузки данных. Попробуйте позже.</p>";
    } finally {
      if (loadingIndicator) loadingIndicator.style.display = "none"; // Скрыть индикатор
    }
  };

  // Обработка таблицы
  const handleTableRows = (rows) => {
    rows.forEach((row) => {
      row.addEventListener("mouseenter", () => {
        if (row !== selectedRow) row.style.backgroundColor = "#191919";
      });

      row.addEventListener("mouseleave", () => {
        if (row !== selectedRow) row.style.backgroundColor = "";
      });

      row.addEventListener("click", () => {
        selectedRow?.classList.remove("selected");
        selectedRow?.style.removeProperty("background-color");
        row.classList.add("selected");
        selectedRow = row;
      });
    });
  };

  if (table) handleTableRows(table.querySelectorAll("tbody tr"));

  // Переключение темы
  const currentTheme = localStorage.getItem("theme") || "light";
  document.documentElement.setAttribute("data-theme", currentTheme);

  themeToggleButton?.addEventListener("click", () => {
    const newTheme = currentTheme === "light" ? "dark" : "light";
    document.documentElement.setAttribute("data-theme", newTheme);
    localStorage.setItem("theme", newTheme);
  });

  // Инициализация состояния сайдбара
  initializeSidebarState();
});

const ctx = document.getElementById('chart').getContext('2d');
const data = {
  labels: [...timeframes], // Таймфреймы
  datasets: [
    {
      label: 'Pivot',
      data: [...pivot_data], // Данные Pivot Points
      borderColor: 'orange',
      borderWidth: 2,
      fill: false,
    },
    {
      label: 'Resistance Levels',
      data: [...resistance_data], // Уровни сопротивления
      borderColor: 'red',
      borderWidth: 2,
      fill: false,
    },
    {
      label: 'Support Levels',
      data: [...support_data], // Уровни поддержки
      borderColor: 'blue',
      borderWidth: 2,
      fill: false,
    },
    {
      label: 'Upper Regression Channel',
      data: [...upper_channel_data], // Верхний уровень регрессии
      borderColor: 'green',
      borderWidth: 2,
      fill: false,
    },
    {
      label: 'Lower Regression Channel',
      data: [...lower_channel_data], // Нижний уровень регрессии
      borderColor: 'purple',
      borderWidth: 2,
      fill: false,
    },
  ],
};

const chart = new Chart(ctx, {
  type: 'line',
  data: data,
  options: {
    responsive: true,
    plugins: {
      legend: {
        position: 'top',
      },
    },
    scales: {
      x: {
        title: {
          display: true,
          text: 'Timeframes',
        },
      },
      y: {
        title: {
          display: true,
          text: 'Price Levels',
        },
      },
    },
  },
});
