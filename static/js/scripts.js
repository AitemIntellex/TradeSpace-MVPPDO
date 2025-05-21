document.addEventListener("DOMContentLoaded", () => {
  const sidebar = document.querySelector(".sidebar");
  const mainContent = document.querySelector(".main");
  const collapseBreakpoint = 992; // Ширина, при которой меню сворачивается

  function handleResize() {
    if (window.innerWidth <= collapseBreakpoint) {
      sidebar.classList.add("collapsed");
      mainContent.classList.add("expanded");
    } else {
      sidebar.classList.remove("collapsed");
      mainContent.classList.remove("expanded");
    }
  }

  // Запускаем проверку при загрузке и изменении размера окна
  handleResize();
  window.addEventListener("resize", handleResize);
});

document.addEventListener("DOMContentLoaded", function () {
  const sidebar = document.querySelector(".sidebar");
  const mainContent = document.querySelector(".main");
  const toggleButton = document.querySelector(".sidebar-toggle");

  // Проверяем состояние из localStorage
  if (localStorage.getItem("sidebarCollapsed") === "true") {
    sidebar.classList.add("collapsed");
    mainContent.classList.add("expanded");
  }

  // Добавляем обработчик клика для кнопки
  toggleButton.addEventListener("click", function () {
    sidebar.classList.toggle("collapsed");
    mainContent.classList.toggle("expanded");

    // Сохраняем состояние в localStorage
    const isCollapsed = sidebar.classList.contains("collapsed");
    localStorage.setItem("sidebarCollapsed", isCollapsed);
  });
});

function loadPage(pageName) {
  fetch(`/dynamic-page/${pageName}/`)
    .then((response) => response.text())
    .then((html) => {
      document.getElementById("dynamic-content").innerHTML = html;
    });
}
