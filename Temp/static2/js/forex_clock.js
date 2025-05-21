function updateForexClock() {
  const now = new Date();

  // Временные зоны для каждого рынка
  const timeZones = {
    tokyo: "Asia/Tokyo",
    london: "Europe/London",
    newYork: "America/New_York",
    sydney: "Australia/Sydney",
  };

  // Получаем время для каждого рынка и обновляем отображение
  Object.keys(timeZones).forEach((city) => {
    const time = now.toLocaleTimeString("en-US", {
      timeZone: timeZones[city],
      hour: '2-digit',
      minute: '2-digit'
    });
    document.getElementById(`${city}-time`).innerText = time;
  });

  const utcHours = now.getUTCHours();

  // Активные сессии
  const sessions = {
    tokyo: utcHours >= 0 && utcHours < 9,
    london: utcHours >= 7 && utcHours < 16,
    newYork: utcHours >= 13 && utcHours < 22,
    sydney: utcHours >= 22 || utcHours < 7,
  };

  // Подсветка активных сессий
  Object.keys(sessions).forEach(session => {
    const element = document.getElementById(session);
    element.style.backgroundColor = sessions[session] ? "rgba(0, 255, 0, 0.5)" : "rgba(0, 123, 255, 0.1)";
  });
}

// Обновляем каждые 10 секунд
setInterval(updateForexClock, 10000);
updateForexClock();
